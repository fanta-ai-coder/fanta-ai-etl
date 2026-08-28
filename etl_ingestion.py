import os
import sys
import time
import requests
from supabase import create_client


# ============================================================
# CONFIGURAZIONE
# ============================================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
SEASON = os.getenv("SEASON")


if not SUPABASE_URL:
    raise ValueError("❌ SUPABASE_URL non configurata")

if not SUPABASE_KEY:
    raise ValueError("❌ SUPABASE_KEY non configurata")

if not API_FOOTBALL_KEY:
    raise ValueError("❌ API_FOOTBALL_KEY non configurata")

if not SEASON:
    raise ValueError("❌ SEASON non configurata")


try:
    SEASON = int(SEASON)
except ValueError:
    raise ValueError(f"❌ SEASON non valida: {SEASON}")


# ============================================================
# API-FOOTBALL
# ============================================================

BASE_URL = "https://v3.football.api-sports.io"
TEAMS_ENDPOINT = f"{BASE_URL}/teams"
PLAYERS_ENDPOINT = f"{BASE_URL}/players"

LEAGUE_ID = 135  # Serie A

HEADERS = {
    "x-apisports-key": API_FOOTBALL_KEY.strip()
}


# ============================================================
# SUPABASE
# ============================================================

print("🔵 Connessione a Supabase...", flush=True)

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

print("✅ Supabase connesso", flush=True)


# ============================================================
# UTILITY
# ============================================================

def safe_int(value):
    if value is None:
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def safe_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


# ============================================================
# API REQUEST
# ============================================================

def api_get(endpoint, params):
    """
    Esegue una richiesta ad API-Football e controlla
    sia HTTP status che eventuali errori restituiti dall'API.
    """
    try:
        response = requests.get(
            endpoint,
            headers=HEADERS,
            params=params,
            timeout=30
        )
    except requests.RequestException as e:
        raise RuntimeError(f"❌ Errore connessione API: {e}")

    print(f"    HTTP {response.status_code}", flush=True)

    if response.status_code != 200:
        raise RuntimeError(
            f"❌ API-Football HTTP {response.status_code}: {response.text}"
        )

    try:
        data = response.json()
    except ValueError:
        raise RuntimeError("❌ Risposta API non JSON")

    errors = data.get("errors")
    if errors:
        raise RuntimeError(f"❌ API-Football errors: {errors}")

    return data


# ============================================================
# GET & SAVE TEAMS
# ============================================================

def sync_serie_a_teams():
    """Recupera e salva tutte le squadre della stagione corrente."""
    print("", flush=True)
    print(f"📡 Recupero e salvataggio squadre Serie A (Stagione {SEASON})", flush=True)

    params = {
        "league": LEAGUE_ID,
        "season": SEASON
    }

    data = api_get(TEAMS_ENDPOINT, params)
    teams = data.get("response", [])

    if not teams:
        raise RuntimeError(f"❌ Nessuna squadra trovata per la stagione {SEASON}")

    saved_teams = 0
    for item in teams:
        team = item.get("team", {}) or {}
        team_id = team.get("id")

        if not team_id:
            continue

        payload = {
            "api_football_id": team_id,
            "name": team.get("name"),
            "code": team.get("code"),
            "country": team.get("country"),
            "logo": team.get("logo")
        }

        supabase.table("teams").upsert(
            payload,
            on_conflict="api_football_id"
        ).execute()

        saved_teams += 1

    print(f"🏆 Squadre sincronizzate: {saved_teams}", flush=True)
    return teams


# ============================================================
# SAVE PLAYER
# ============================================================

def save_player(player):
    player_id = player.get("id")
    if not player_id:
        return False

    payload = {
        "api_football_id": player_id,
        "api_football_name": player.get("name"),
        "firstname": player.get("firstname"),
        "lastname": player.get("lastname"),
        "age": player.get("age"),
        "nationality": player.get("nationality"),
        "height": player.get("height"),
        "weight": player.get("weight"),
        "photo": player.get("photo")
    }

    supabase.table("players").upsert(
        payload,
        on_conflict="api_football_id"
    ).execute()

    return True


# ============================================================
# SAVE PLAYER STATS
# ============================================================

def save_player_stats(player_item):
    player = player_item.get("player", {}) or {}
    player_id = player.get("id")

    if not player_id:
        return False

    statistics = player_item.get("statistics", []) or []
    if not statistics:
        return False

    stat = statistics[0] or {}

    team_info = stat.get("team", {}) or {}
    team_id = team_info.get("id")
    team_name = team_info.get("name")

    games = stat.get("games", {}) or {}
    goals = stat.get("goals", {}) or {}
    cards = stat.get("cards", {}) or {}
    shots = stat.get("shots", {}) or {}
    passes = stat.get("passes", {}) or {}

    # Correzione presenze: API-Football usa la chiave "appearences"
    matches_played = games.get("appearences") if games.get("appearences") is not None else games.get("appearances")

    payload = {
        "api_football_id": player_id,
        "season": SEASON,
        "team_id": team_id,
        "team": team_name,
        "matches_played": safe_int(matches_played),
        "minutes_played": safe_int(games.get("minutes")),
        "goals": safe_int(goals.get("total")),
        "assists": safe_int(goals.get("assists")),
        "yellow_cards": safe_int(cards.get("yellow")),
        "red_cards": safe_int(cards.get("red")),
        "shots_total": safe_int(shots.get("total")),
        "shots_on_target": safe_int(shots.get("on")),
        "passes_total": safe_int(passes.get("total")),
        "passes_key": safe_int(passes.get("key")),
        "rating": safe_float(games.get("rating"))
    }

    supabase.table("player_stats").upsert(
        payload,
        on_conflict="api_football_id,season"
    ).execute()

    return True


# ============================================================
# MAIN INGESTION
# ============================================================

def run():
    print("", flush=True)
    print("=" * 60, flush=True)
    print("🚀 API-FOOTBALL PLAYER INGESTION (LEAGUE-WIDE)", flush=True)
    print("=" * 60, flush=True)
    print(f"🏆 Campionato : Serie A", flush=True)
    print(f"🆔 League ID  : {LEAGUE_ID}", flush=True)
    print(f"📅 Stagione   : {SEASON}", flush=True)
    print("=" * 60, flush=True)

    # 1. Sincronizza prima le squadre
    sync_serie_a_teams()

    # 2. Paginazione su tutta la lega per aggirare il blocco page>3 per squadra
    page = 1
    total_saved_players = 0
    total_saved_stats = 0
    total_api_records = 0

    while True:
        print("", flush=True)
        print(f"📄 Richiesta pagina {page} per Serie A...", flush=True)

        params = {
            "league": LEAGUE_ID,
            "season": SEASON,
            "page": page
        }

        data = api_get(PLAYERS_ENDPOINT, params)
        players_list = data.get("response", [])
        paging = data.get("paging", {}) or {}

        current_page = paging.get("current", page)
        total_pages = paging.get("total", 1)

        print(
            f"📊 Pagina {current_page}/{total_pages} → Trovati {len(players_list)} giocatori",
            flush=True
        )

        if not players_list:
            print("⚠️ Nessun giocatore restituito in questa pagina.", flush=True)
            break

        total_api_records += len(players_list)

        for item in players_list:
            player = item.get("player", {}) or {}

            if save_player(player):
                total_saved_players += 1

            if save_player_stats(item):
                total_saved_stats += 1

        if current_page >= total_pages:
            print("🎉 Raggiunta l'ultima pagina della lega!", flush=True)
            break

        page += 1
        time.sleep(0.3)

    # ========================================================
    # RISULTATO
    # ========================================================

    print("", flush=True)
    print("=" * 60, flush=True)
    print("🏆 INGESTION COMPLETATA CON SUCCESSO", flush=True)
    print("=" * 60, flush=True)
    print(f"📅 Stagione          : {SEASON}", flush=True)
    print(f"📄 Pagine elaborate  : {page}/{total_pages}", flush=True)
    print(f"📡 Record letti API  : {total_api_records}", flush=True)
    print(f"👤 Player upsert     : {total_saved_players}", flush=True)
    print(f"📊 Stats upsert      : {total_saved_stats}", flush=True)
    print("=" * 60, flush=True)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print("", flush=True)
        print("=" * 60, flush=True)
        print("💥 INGESTION FALLITA", flush=True)
        print("=" * 60, flush=True)
        print(str(e), flush=True)
        print("=" * 60, flush=True)
        sys.exit(1)
