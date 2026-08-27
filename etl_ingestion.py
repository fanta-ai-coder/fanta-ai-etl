import os
import requests
import pandas as pd
from supabase import create_client, ClientOptions

# 1. Configurazione Credenziali
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY, API_FOOTBALL_KEY]):
    raise ValueError("⚠️ Mancano le variabili d'ambiente necessarie nei Secrets!")

# Inizializza client Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Costanti API-Football
API_URL = "https://v3.football.api-sports.io/players"
# Metti .strip() per pulire la chiave da eventuali \n o spazi
HEADERS = {
    "x-apisports-key": API_FOOTBALL_KEY.strip()
}
SERIE_A_LEAGUE_ID = 135  # ID della Serie A su API-Football
DAILY_REQUEST_BUDGET = 30 # Limite prudenziale per singola esecuzione (Piano Free ha 100 req/giorno)

def get_checkpoint():
    """Recupera lo stato attuale dell'ingestion."""
    res = supabase.table("etl_checkpoint").select("*").eq("id", 1).execute()
    if res.data:
        return res.data[0]
    return {"current_season": 2022, "current_page": 1, "is_completed": False}

def update_checkpoint(season, page, is_completed=False):
    """Aggiorna lo stato su Supabase."""
    supabase.table("etl_checkpoint").update({
        "current_season": season,
        "current_page": page,
        "is_completed": is_completed,
        "last_run_at": "now()"
    }).eq("id", 1).execute()

def upsert_player_and_stats(player_data, season):
    """Inserisce/aggiorna l'anagrafica del giocatore e le sue statistiche stagionali."""
    p_info = player_data.get("player", {})
    s_info = player_data.get("statistics", [{}])[0] # Statistiche per la Serie A
    
    api_id = p_info.get("id")
    api_name = p_info.get("name")
    team_name = s_info.get("team", {}).get("name")
    
    # 1. Aggiorna o Inserisce il Giocatore in 'players' se c'è un match tramite API ID
    # Se il giocatore è già stato mappato con l'ID Fantacalcio, colleghiamo i dati
    supabase.table("players").upsert({
        "api_football_id": api_id,
        "api_football_name": api_name
    }, on_conflict="api_football_id").execute()
    
    # 2. Inserisce/Aggiorna le Statistiche in 'player_stats'
    games = s_info.get("games", {}) or {}
    goals = s_info.get("goals", {}) or {}
    cards = s_info.get("cards", {}) or {}
    shots = s_info.get("shots", {}) or {}
    passes = s_info.get("passes", {}) or {}
    
    rating_str = games.get("rating")
    rating = float(rating_str) if rating_str else None

    stat_payload = {
        "api_football_id": api_id,
        "season": season,
        "team": team_name,
        "matches_played": games.get("appearances") or 0,
        "minutes_played": games.get("minutes") or 0,
        "goals": goals.get("total") or 0,
        "assists": goals.get("assists") or 0,
        "yellow_cards": cards.get("yellow") or 0,
        "red_cards": cards.get("red") or 0,
        "shots_total": shots.get("total") or 0,
        "shots_on_target": shots.get("on") or 0,
        "passes_total": passes.get("total") or 0,
        "passes_key": passes.get("key") or 0,
        "rating": rating
    }
    
    supabase.table("player_stats").upsert(
        stat_payload, 
        on_conflict="api_football_id,season"
    ).execute()

def run_ingestion():
    checkpoint = get_checkpoint()
    
    if checkpoint.get("is_completed"):
        print("✅ Ingestion storica già completata per tutte le stagioni previste.")
        return

    current_season = checkpoint["current_season"]
    current_page = checkpoint["current_page"]
    requests_made = 0
    
    print(f"🚀 Avvio Ingestion | Stagione: {current_season} | Pagina iniziale: {current_page}")

    while requests_made < DAILY_REQUEST_BUDGET:
        params = {
            "league": SERIE_A_LEAGUE_ID,
            "season": current_season,
            "page": current_page
        }
        
        response = requests.get(API_URL, headers=HEADERS, params=params)
        requests_made += 1
        
        if response.status_code != 200:
            print(f"❌ Errore API ({response.status_code}): {response.text}")
            break
            
        data = response.json()
        players_list = data.get("response", [])
        paging = data.get("paging", {})
        total_pages = paging.get("total", 1)
        
        print(f"  [Req {requests_made}/{DAILY_REQUEST_BUDGET}] Stagione {current_season} - Pagina {current_page}/{total_pages} - Trovati {len(players_list)} giocatori")

        # Inserisci i dati nel DB
        for item in players_list:
            try:
                upsert_player_and_stats(item, current_season)
            except Exception as e:
                print(f"⚠️ Errore salvataggio giocatore {item.get('player', {}).get('name')}: {e}")

        # Passa alla pagina successiva
        if current_page < total_pages:
            current_page += 1
        else:
            # Stagione completata, passa alla stagione successiva
            print(f"🎉 Completata Stagione {current_season}!")
            current_season += 1
            current_page = 1
            
            # Se abbiamo raggiunto la stagione corrente (es. 2026), segnamo come completata l'ingestion storica
            if current_season > 2026:
                update_checkpoint(current_season, current_page, is_completed=True)
                print("🏆 Ingestion storica interamente completata!")
                break

        # Salva lo stato dopo ogni chiamata per sicurezza
        update_checkpoint(current_season, current_page)

    print(f"🛑 Budget giornaliero di chiamate raggiunto ({requests_made} req effettuate). Stato salvato.")

if __name__ == "__main__":
    run_ingestion()
