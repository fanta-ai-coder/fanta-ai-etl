import os
import sys
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
    raise ValueError(
        f"❌ SEASON non valida: {SEASON}"
    )


# ============================================================
# CONFIG API
# ============================================================

API_URL = "https://v3.football.api-sports.io/players"

LEAGUE_ID = 135

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
# API FOOTBALL
# ============================================================

def get_page(page):

    params = {
        "league": LEAGUE_ID,
        "season": SEASON,
        "page": page
    }

    print(
        f"📡 API-Football → "
        f"season={SEASON}, page={page}",
        flush=True
    )

    try:

        response = requests.get(
            API_URL,
            headers=HEADERS,
            params=params,
            timeout=30
        )

    except requests.RequestException as e:

        raise RuntimeError(
            f"❌ Errore connessione API: {e}"
        )

    print(
        f"   HTTP {response.status_code}",
        flush=True
    )

    if response.status_code != 200:

        raise RuntimeError(
            f"❌ API-Football HTTP "
            f"{response.status_code}: "
            f"{response.text}"
        )

    try:

        data = response.json()

    except ValueError:

        raise RuntimeError(
            "❌ API-Football ha restituito "
            "una risposta non JSON"
        )

    # --------------------------------------------------------
    # ERRORI API
    # --------------------------------------------------------

    errors = data.get("errors")

    if errors:

        raise RuntimeError(
            f"❌ API-Football errors: {errors}"
        )

    return data


# ============================================================
# PLAYER
# ============================================================

def upsert_player(player):

    api_id = player.get("id")

    if not api_id:
        return False

    payload = {
        "api_football_id": api_id,
        "api_football_name": player.get("name"),

        "firstname": player.get("firstname"),
        "lastname": player.get("lastname"),

        "age": player.get("age"),
        "nationality": player.get("nationality"),
        "height": player.get("height"),
        "weight": player.get("weight"),

        "photo": player.get("photo")
    }

    try:

        (
            supabase
            .table("players")
            .upsert(
                payload,
                on_conflict="api_football_id"
            )
            .execute()
        )

        return True

    except Exception as e:

        print(
            f"❌ Errore salvataggio player "
            f"{player.get('name')}: {e}",
            flush=True
        )

        return False


# ============================================================
# PLAYER STATS
# ============================================================

def upsert_player_stats(
    player,
    statistics
):

    api_id = player.get("id")

    if not api_id:
        return False

    if not statistics:
        return False

    # --------------------------------------------------------
    # Per Serie A utilizziamo la prima statistica restituita
    # --------------------------------------------------------

    stat = statistics[0] or {}

    team = stat.get("team", {}) or {}
    games = stat.get("games", {}) or {}
    goals = stat.get("goals", {}) or {}
    cards = stat.get("cards", {}) or {}
    shots = stat.get("shots", {}) or {}
    passes = stat.get("passes", {}) or {}

    payload = {

        "api_football_id": api_id,

        "season": SEASON,

        "team_id": team.get("id"),
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

        "rating": safe_float(
            games.get("rating")
        )
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

        return True

    except Exception as e:

        print(
            f"❌ Errore stats "
            f"{player.get('name')}: {e}",
            flush=True
        )

        return False


# ============================================================
# PROCESS PAGE
# ============================================================

def process_page(data):

    players = data.get(
        "response",
        []
    )

    paging = data.get(
        "paging",
        {}
    )

    current_page = paging.get(
        "current"
    )

    total_pages = paging.get(
        "total"
    )

    print(
        f"📊 Pagina "
        f"{current_page}/{total_pages} "
        f"→ {len(players)} giocatori",
        flush=True
    )

    saved_players = 0
    saved_stats = 0

    for item in players:

        player = item.get(
            "player",
            {}
        ) or {}

        statistics = item.get(
            "statistics",
            []
        ) or []

        # ----------------------------------------------------
        # PLAYER
        # ----------------------------------------------------

        if upsert_player(player):
            saved_players += 1

        # ----------------------------------------------------
        # STATS
        # ----------------------------------------------------

        if upsert_player_stats(
            player,
            statistics
        ):
            saved_stats += 1

    return (
        current_page,
        total_pages,
        len(players),
        saved_players,
        saved_stats
    )


# ============================================================
# INGESTION COMPLETA
# ============================================================

def run():

    print("")
    print("=" * 60)
    print("🚀 API-FOOTBALL PLAYER INGESTION")
    print("=" * 60)

    print(
        f"🏆 Campionato : Serie A"
    )

    print(
        f"🆔 League ID  : {LEAGUE_ID}"
    )

    print(
        f"📅 Season     : {SEASON}"
    )

    print("=" * 60)
    print("")

    page = 1

    total_received = 0
    total_players = 0
    total_stats = 0

    while True:

        data = get_page(page)

        (
            current_page,
            total_pages,
            received,
            saved_players,
            saved_stats
        ) = process_page(data)

        total_received += received
        total_players += saved_players
        total_stats += saved_stats

        # ----------------------------------------------------
        # CONTROLLO RISPOSTA VUOTA
        # ----------------------------------------------------

        if received == 0:

            raise RuntimeError(
                f"❌ Pagina {page} vuota "
                f"prima della fine della paginazione. "
                f"Non considero la stagione completata."
            )

        # ----------------------------------------------------
        # FINE
        # ----------------------------------------------------

        if current_page >= total_pages:

            break

        page += 1

    # ========================================================
    # RISULTATO
    # ========================================================

    print("")
    print("=" * 60)
    print("🏆 INGESTION COMPLETATA")
    print("=" * 60)

    print(
        f"📅 Stagione: {SEASON}"
    )

    print(
        f"📡 Record ricevuti API: {total_received}"
    )

    print(
        f"👤 Player upsert: {total_players}"
    )

    print(
        f"📊 Stats upsert: {total_stats}"
    )

    print(
        f"📄 Pagine elaborate: {page}"
    )

    print("=" * 60)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    try:

        run()

    except Exception as e:

        print("")
        print("=" * 60)
        print("💥 INGESTION FALLITA")
        print("=" * 60)
        print(str(e))
        print("=" * 60)

        sys.exit(1)
