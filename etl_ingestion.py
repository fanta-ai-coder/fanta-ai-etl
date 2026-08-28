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
    raise ValueError(
        f"❌ SEASON non valida: {SEASON}"
    )


# ============================================================
# API-FOOTBALL
# ============================================================

BASE_URL = "https://v3.football.api-sports.io"

TEAMS_ENDPOINT = f"{BASE_URL}/teams"
PLAYERS_ENDPOINT = f"{BASE_URL}/players"

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
# API REQUEST
# ============================================================

def api_get(endpoint, params):
    """
    Esegue una richiesta API-Football e controlla
    sia HTTP status che errors restituiti dall'API.
    """

    try:

        response = requests.get(
            endpoint,
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
            "❌ Risposta API non JSON"
        )

    errors = data.get("errors")

    if errors:

        raise RuntimeError(
            f"❌ API-Football errors: {errors}"
        )

    return data


# ============================================================
# GET TEAMS
# ============================================================

def get_serie_a_teams():

    print("")
    print(
        f"📡 Recupero squadre Serie A "
        f"stagione {SEASON}",
        flush=True
    )

    params = {
        "league": LEAGUE_ID,
        "season": SEASON
    }

    data = api_get(
        TEAMS_ENDPOINT,
        params
    )

    teams = data.get(
        "response",
        []
    )

    if not teams:

        raise RuntimeError(
            f"❌ Nessuna squadra trovata "
            f"per la stagione {SEASON}"
        )

    print(
        f"🏆 Squadre trovate: {len(teams)}",
        flush=True
    )

    return teams


# ============================================================
# SAVE TEAM
# ============================================================

def save_team(team_data):

    team = team_data.get(
        "team",
        {}
    ) or {}

    team_id = team.get("id")

    if not team_id:

        raise RuntimeError(
            "❌ Squadra senza API Football ID"
        )

    payload = {

        "api_football_id": team_id,

        "name": team.get(
            "name"
        ),

        "code": team.get(
            "code"
        ),

        "country": team.get(
            "country"
        ),

        "logo": team.get(
            "logo"
        )
    }

    (
        supabase
        .table("teams")
        .upsert(
            payload,
            on_conflict="api_football_id"
        )
        .execute()
    )


# ============================================================
# GET PLAYERS FOR TEAM
# ============================================================

def get_players_for_team(team_id, team_name):

    print("")
    print(
        f"📡 Squadra: {team_name} "
        f"(ID {team_id})",
        flush=True
    )

    all_players = []

    page = 1

    while True:

        params = {
            "league": LEAGUE_ID,
            "season": SEASON,
            "team": team_id,
            "page": page
        }

        print(
            f"   📄 Richiesta pagina {page}",
            flush=True
        )

        data = api_get(
            PLAYERS_ENDPOINT,
            params
        )

        players = data.get(
            "response",
            []
        )

        paging = data.get(
            "paging",
            {}
        )

        current_page = paging.get(
            "current",
            page
        )

        total_pages = paging.get(
            "total",
            1
        )

        print(
            f"   📊 Pagina "
            f"{current_page}/{total_pages} "
            f"→ {len(players)} giocatori",
            flush=True
        )

        # ----------------------------------------------------
        # PAGINA VUOTA
        # ----------------------------------------------------

        if not players:

            # Se è la prima pagina significa che
            # la squadra non ha dati giocatore.
            if page == 1:

                print(
                    "   ⚠️ Nessun giocatore restituito",
                    flush=True
                )

                break

            raise RuntimeError(
                f"❌ Pagina {page} vuota "
                f"prima della fine della paginazione "
                f"per {team_name}"
            )

        all_players.extend(players)

        # ----------------------------------------------------
        # LIMITE PIANO FREE
        # ----------------------------------------------------

        if total_pages > 3:

            raise RuntimeError(
                f"❌ API-Football indica {total_pages} "
                f"pagine per {team_name}. "
                f"Il piano Free permette massimo "
                f"page=3."
            )

        # ----------------------------------------------------
        # FINE
        # ----------------------------------------------------

        if current_page >= total_pages:

            break

        page += 1

    return all_players


# ============================================================
# SAVE PLAYER
# ============================================================

def save_player(player):

    player_id = player.get("id")

    if not player_id:

        return False

    payload = {

        "api_football_id": player_id,

        "api_football_name": player.get(
            "name"
        ),

        "firstname": player.get(
            "firstname"
        ),

        "lastname": player.get(
            "lastname"
        ),

        "age": player.get(
            "age"
        ),

        "nationality": player.get(
            "nationality"
        ),

        "height": player.get(
            "height"
        ),

        "weight": player.get(
            "weight"
        ),

        "photo": player.get(
            "photo"
        )
    }

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


# ============================================================
# SAVE PLAYER STATS
# ============================================================

def save_player_stats(
    player,
    team_id,
    team_name
):

    player_id = player.get("id")

    if not player_id:

        return False

    statistics = player.get(
        "statistics",
        []
    ) or []

    if not statistics:

        return False

    # --------------------------------------------------------
    # Cerchiamo la statistica relativa alla squadra corrente.
    # --------------------------------------------------------

    selected_stat = None

    for stat in statistics:

        stat_team = stat.get(
            "team",
            {}
        ) or {}

        if stat_team.get("id") == team_id:

            selected_stat = stat
            break

    # Fallback: prima statistica disponibile
    if selected_stat is None:

        selected_stat = statistics[0]

    stat = selected_stat or {}

    games = stat.get(
        "games",
        {}
    ) or {}

    goals = stat.get(
        "goals",
        {}
    ) or {}

    cards = stat.get(
        "cards",
        {}
    ) or {}

    shots = stat.get(
        "shots",
        {}
    ) or {}

    passes = stat.get(
        "passes",
        {}
    ) or {}

    payload = {

        "api_football_id": player_id,

        "season": SEASON,

        "team_id": team_id,

        "team": team_name,

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

    (
        supabase
        .table("player_stats")
        .upsert(
            payload,
            on_conflict=(
                "api_football_id,"
                "season,"
                "team_id"
            )
        )
        .execute()
    )

    return True


# ============================================================
# PROCESS TEAM
# ============================================================

def process_team(team_data):

    team = team_data.get(
        "team",
        {}
    ) or {}

    team_id = team.get("id")
    team_name = team.get("name")

    if not team_id:

        raise RuntimeError(
            "❌ Team senza ID"
        )

    print("")
    print("=" * 60)
    print(
        f"🏟️ {team_name}"
    )
    print("=" * 60)

    # --------------------------------------------------------
    # Salva squadra
    # --------------------------------------------------------

    save_team(team_data)

    # --------------------------------------------------------
    # Recupera giocatori
    # --------------------------------------------------------

    players = get_players_for_team(
        team_id,
        team_name
    )

    saved_players = 0
    saved_stats = 0

    # --------------------------------------------------------
    # Salvataggio
    # --------------------------------------------------------

    for item in players:

        player = item.get(
            "player",
            {}
        ) or {}

        if save_player(player):

            saved_players += 1

        if save_player_stats(
            player,
            team_id,
            team_name
        ):

            saved_stats += 1

    print(
        f"✅ {team_name}: "
        f"{len(players)} record API | "
        f"{saved_players} player | "
        f"{saved_stats} stats",
        flush=True
    )

    return (
        len(players),
        saved_players,
        saved_stats
    )


# ============================================================
# MAIN INGESTION
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
        f"📅 Stagione   : {SEASON}"
    )
    print("=" * 60)

    # --------------------------------------------------------
    # 1. Recupera squadre
    # --------------------------------------------------------

    teams = get_serie_a_teams()

    total_players = 0
    total_saved_players = 0
    total_saved_stats = 0

    # --------------------------------------------------------
    # 2. Processa ogni squadra
    # --------------------------------------------------------

    for index, team_data in enumerate(
        teams,
        start=1
    ):

        team_name = (
            team_data
            .get("team", {})
            .get("name", "Unknown")
        )

        print("")
        print(
            f"🔄 Squadra {index}/{len(teams)}: "
            f"{team_name}",
            flush=True
        )

        (
            players_count,
            saved_players,
            saved_stats
        ) = process_team(team_data)

        total_players += players_count
        total_saved_players += saved_players
        total_saved_stats += saved_stats

        # Piccola pausa
        time.sleep(0.5)

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
        f"🏟️ Squadre: {len(teams)}"
    )

    print(
        f"📡 Record giocatore ricevuti: "
        f"{total_players}"
    )

    print(
        f"👤 Player upsert: "
        f"{total_saved_players}"
    )

    print(
        f"📊 Stats upsert: "
        f"{total_saved_stats}"
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
