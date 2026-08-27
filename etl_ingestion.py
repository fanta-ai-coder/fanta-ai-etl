import os
import requests
from supabase import create_client

# ============================================================
# CONFIGURAZIONE
# ============================================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY, API_FOOTBALL_KEY]):
    raise ValueError(
        "⚠️ Mancano una o più variabili d'ambiente necessarie nei Secrets!"
    )

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

API_URL = "https://v3.football.api-sports.io/players"

HEADERS = {
    "x-apisports-key": API_FOOTBALL_KEY.strip()
}

SERIE_A_LEAGUE_ID = 135

# Stagioni da importare
START_SEASON = 2022
END_SEASON = 2026

# Limite prudenziale di chiamate per esecuzione
DAILY_REQUEST_BUDGET = 30


# ============================================================
# CHECKPOINT
# ============================================================

def get_checkpoint():
    """
    Recupera lo stato dell'ETL.
    """

    try:
        res = (
            supabase
            .table("etl_checkpoint")
            .select("*")
            .eq("id", 1)
            .execute()
        )

        if res.data:
            return res.data[0]

    except Exception as e:
        print(f"⚠️ Errore lettura checkpoint: {e}")

    return {
        "id": 1,
        "current_season": START_SEASON,
        "current_page": 1,
        "is_completed": False
    }


def update_checkpoint(season, page, is_completed=False):
    """
    Salva lo stato dell'ETL.
    """

    payload = {
        "id": 1,
        "current_season": season,
        "current_page": page,
        "is_completed": is_completed
    }

    try:
        supabase
            .table("etl_checkpoint")
            .upsert(payload, on_conflict="id")
            .execute()

    except Exception as e:
        print(f"⚠️ Errore aggiornamento checkpoint: {e}")


# ============================================================
# UTILITY
# ============================================================

def safe_int(value, default=0):
    """
    Converte un valore in int evitando errori con None/stringhe.
    """

    if value is None:
        return default

    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value):
    """
    Converte un valore in float.
    """

    if value is None:
        return None

    try:
        return float(value)
    except (ValueError, TypeError):
        return None


# ============================================================
# GESTIONE PLAYER
# ============================================================

def get_existing_player(api_id):
    """
    Cerca il giocatore nella tabella players tramite API-Football ID.
    """

    try:
        res = (
            supabase
            .table("players")
            .select("*")
            .eq("api_football_id", api_id)
            .limit(1)
            .execute()
        )

        if res.data:
            return res.data[0]

    except Exception as e:
        print(f"⚠️ Errore ricerca player {api_id}: {e}")

    return None


def create_or_update_player(player_data):
    """
    Crea/aggiorna il giocatore senza cancellare
    i dati provenienti da Fantacalcio.

    IMPORTANTE:
    non invia colonne NOT NULL di Fantacalcio con valore NULL.
    """

    player = player_data.get("player", {}) or {}

    api_id = player.get("id")
    api_name = player.get("name")

    if not api_id:
        print("⚠️ Player senza API Football ID, salto.")
        return None

    existing = get_existing_player(api_id)

    # --------------------------------------------------------
    # PLAYER GIÀ PRESENTE
    # --------------------------------------------------------

    if existing:

        update_payload = {}

        # Aggiorniamo solamente i campi API Football.
        # NON tocchiamo nome_fantacalcio, ruolo, squadra_fantacalcio ecc.

        if api_name and existing.get("api_football_name") != api_name:
            update_payload["api_football_name"] = api_name

        if update_payload:
            try:
                (
                    supabase
                    .table("players")
                    .update(update_payload)
                    .eq("id", existing["id"])
                    .execute()
                )

            except Exception as e:
                print(
                    f"⚠️ Errore aggiornamento player "
                    f"{api_name}: {e}"
                )

        return existing["id"]

    # --------------------------------------------------------
    # PLAYER NUOVO
    # --------------------------------------------------------

    # ATTENZIONE:
    # Se players ha colonne NOT NULL senza default
    # (es. nome_fantacalcio), bisogna valorizzarle.
    #
    # Qui usiamo api_name come fallback temporaneo.
    # Successivamente potrà essere sostituito dal nome
    # ufficiale Fantacalcio.

    insert_payload = {
        "api_football_id": api_id,
        "api_football_name": api_name,
        "nome_fantacalcio": api_name
    }

    try:

        res = (
            supabase
            .table("players")
            .insert(insert_payload)
            .execute()
        )

        if res.data:
            return res.data[0]["id"]

    except Exception as e:

        print(
            f"⚠️ Errore inserimento giocatore "
            f"{api_name}: {e}"
        )

    return None


# ============================================================
# STATISTICHE
# ============================================================

def save_player_stats(player_data, season):
    """
    Salva le statistiche stagionali del giocatore.
    """

    player = player_data.get("player", {}) or {}

    statistics = player_data.get("statistics", []) or []

    if not statistics:
        print(
            f"⚠️ Nessuna statistica per "
            f"{player.get('name')}"
        )
        return

    # La prima statistica dovrebbe essere quella della Serie A
    stats = statistics[0] or {}

    api_id = player.get("id")

    if not api_id:
        return

    team = stats.get("team", {}) or {}

    games = stats.get("games", {}) or {}
    goals = stats.get("goals", {}) or {}
    cards = stats.get("cards", {}) or {}
    shots = stats.get("shots", {}) or {}
    passes = stats.get("passes", {}) or {}

    rating = safe_float(games.get("rating"))

    payload = {
        "api_football_id": api_id,
        "season": season,

        "team": team.get("name"),

        "matches_played": safe_int(
            games.get("appearances")
        ),

        "minutes_played": safe_int(
            games.get("minutes")
        ),

        "goals": safe_int(
            goals.get("total")
        ),

        "assists": safe_int(
            goals.get("assists")
        ),

        "yellow_cards": safe_int(
            cards.get("yellow")
        ),

        "red_cards": safe_int(
            cards.get("red")
        ),

        "shots_total": safe_int(
            shots.get("total")
        ),

        "shots_on_target": safe_int(
            shots.get("on")
        ),

        "passes_total": safe_int(
            passes.get("total")
        ),

        "passes_key": safe_int(
            passes.get("key")
        ),

        "rating": rating
    }

    try:

        (
            supabase
            .table("player_stats")
            .upsert(
                payload,
                on_conflict="api_football_id,season"
            )
            .execute()
        )

    except Exception as e:

        print(
            f"⚠️ Errore salvataggio statistiche "
            f"{player.get('name')} "
            f"(stagione {season}): {e}"
        )


# ============================================================
# SALVATAGGIO COMPLETO PLAYER
# ============================================================

def process_player(player_data, season):

    player = player_data.get("player", {}) or {}

    player_name = player.get("name", "Sconosciuto")

    try:

        player_id = create_or_update_player(player_data)

        if player_id is None:
            print(
                f"⚠️ Impossibile creare/aggiornare "
                f"{player_name}"
            )
            return

        save_player_stats(
            player_data,
            season
        )

    except Exception as e:

        print(
            f"⚠️ Errore salvataggio giocatore "
            f"{player_name}: {e}"
        )


# ============================================================
# API FOOTBALL
# ============================================================

def get_players_page(season, page):

    params = {
        "league": SERIE_A_LEAGUE_ID,
        "season": season,
        "page": page
    }

    try:

        response = requests.get(
            API_URL,
            headers=HEADERS,
            params=params,
            timeout=30
        )

    except requests.RequestException as e:

        print(f"❌ Errore connessione API: {e}")
        return None

    if response.status_code != 200:

        print(
            f"❌ Errore API "
            f"({response.status_code}): "
            f"{response.text}"
        )

        return None

    try:
        return response.json()

    except ValueError:

        print("❌ Risposta API non valida.")
        return None


# ============================================================
# INGESTION
# ============================================================

def run_ingestion():

    checkpoint = get_checkpoint()

    if checkpoint.get("is_completed"):

        print(
            "✅ Ingestion storica già completata."
        )

        return

    current_season = checkpoint.get(
        "current_season",
        START_SEASON
    )

    current_page = checkpoint.get(
        "current_page",
        1
    )

    requests_made = 0

    print("")
    print("=" * 60)
    print("🚀 AVVIO INGESTION API-FOOTBALL")
    print("=" * 60)
    print(
        f"Stagione iniziale : {current_season}"
    )
    print(
        f"Pagina iniziale   : {current_page}"
    )
    print(
        f"Budget chiamate   : {DAILY_REQUEST_BUDGET}"
    )
    print("=" * 60)

    while requests_made < DAILY_REQUEST_BUDGET:

        # ----------------------------------------------------
        # CONTROLLO FINE INGESTION
        # ----------------------------------------------------

        if current_season > END_SEASON:

            update_checkpoint(
                current_season,
                1,
                is_completed=True
            )

            print("")
            print(
                "🏆 INGESTION STORICA COMPLETATA!"
            )

            return

        # ----------------------------------------------------
        # CHIAMATA API
        # ----------------------------------------------------

        print("")
        print(
            f"📡 Richiesta "
            f"Stagione {current_season} "
            f"- Pagina {current_page}"
        )

        data = get_players_page(
            current_season,
            current_page
        )

        requests_made += 1

        if data is None:

            print(
                "🛑 Richiesta fallita. "
                "Checkpoint mantenuto."
            )

            break

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        players_list = data.get(
            "response",
            []
        )

        paging = data.get(
            "paging",
            {}
        )

        total_pages = safe_int(
            paging.get("total"),
            1
        )

        print(
            f"📊 Stagione {current_season} "
            f"| Pagina {current_page}/{total_pages} "
            f"| Giocatori: {len(players_list)}"
        )

        # ----------------------------------------------------
        # SALVATAGGIO PLAYER
        # ----------------------------------------------------

        for player_data in players_list:

            process_player(
                player_data,
                current_season
            )

        # ----------------------------------------------------
        # CHECKPOINT
        # ----------------------------------------------------

        if current_page < total_pages:

            current_page += 1

        else:

            print("")
            print(
                f"🎉 Stagione "
                f"{current_season} completata!"
            )

            current_season += 1
            current_page = 1

        update_checkpoint(
            current_season,
            current_page,
            is_completed=False
        )

        print(
            f"💾 Checkpoint salvato: "
            f"{current_season} / pagina {current_page}"
        )

    # --------------------------------------------------------
    # FINE BUDGET
    # --------------------------------------------------------

    print("")
    print("=" * 60)
    print("🛑 BUDGET API RAGGIUNTO")
    print("=" * 60)
    print(
        f"Richieste effettuate: {requests_made}"
    )
    print(
        f"Prossima stagione: {current_season}"
    )
    print(
        f"Prossima pagina: {current_page}"
    )
    print("=" * 60)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    run_ingestion()
