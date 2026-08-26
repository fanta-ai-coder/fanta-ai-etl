import os
import pandas as pd
import soccerdata as sd
from supabase import Client, create_client


# ============================================================
# CONFIGURAZIONE
# ============================================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError(
        "Credenziali SUPABASE_URL o SUPABASE_KEY non trovate "
        "nei GitHub Secrets!"
    )

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


# ============================================================
# FUNZIONI DI SUPPORTO
# ============================================================

def to_numeric(series, default=0):
    """
    Converte una Series in numerico gestendo valori nulli/non validi.
    """
    return pd.to_numeric(series, errors="coerce").fillna(default)


def fetch_and_process_data(seasons=None):
    """
    Scarica le statistiche stagionali dei giocatori da Understat
    tramite SoccerData e prepara il DataFrame per Supabase.
    """

    if seasons is None:
        seasons = ["2024"]

    print(
        f"Scaricamento dati Understat per le stagioni: {seasons}..."
    )

    try:
        understat = sd.Understat(
            leagues="ITA-Serie A",
            seasons=seasons
        )

        df_player = understat.read_player_season_stats()

    except Exception as e:
        print(
            f"Errore durante il download dei dati da Understat: {e}"
        )
        return None

    if df_player is None or df_player.empty:
        print("Understat non ha restituito alcun dato.")
        return None

    # --------------------------------------------------------
    # RESET INDEX
    # --------------------------------------------------------

    df_player = df_player.reset_index()

    print(
        f"Ricevuti {len(df_player)} record da Understat."
    )

    print(
        "Colonne ricevute:",
        list(df_player.columns)
    )

    # --------------------------------------------------------
    # CONTROLLO COLONNE
    # --------------------------------------------------------

    required_columns = [
        "player",
        "player_id",
        "team",
        "season",
        "position",
        "matches",
        "minutes",
        "goals",
        "assists",
        "xg",
        "xa",
        "shots",
        "key_passes",
        "yellow_cards",
        "red_cards",
        "xg_chain",
        "xg_buildup",
        "np_goals",
        "np_xg"
    ]

    missing_columns = [
        col for col in required_columns
        if col not in df_player.columns
    ]

    if missing_columns:
        raise ValueError(
            "Mancano colonne attese da SoccerData: "
            + ", ".join(missing_columns)
        )

    # ========================================================
    # CREAZIONE DATAFRAME PULITO
    # ========================================================

    df_clean = pd.DataFrame()

    # --------------------------------------------------------
    # IDENTIFICATIVI / ANAGRAFICA
    # --------------------------------------------------------

    df_clean["player_id"] = (
        pd.to_numeric(
            df_player["player_id"],
            errors="coerce"
        )
        .astype("Int64")
    )

    df_clean["player_name"] = (
        df_player["player"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    df_clean["team"] = (
        df_player["team"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    df_clean["season"] = (
        df_player["season"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    df_clean["position"] = (
        df_player["position"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # --------------------------------------------------------
    # PRESENZE E MINUTI
    # --------------------------------------------------------

    df_clean["matches_played"] = (
        to_numeric(df_player["matches"])
        .astype(int)
    )

    df_clean["minutes_played"] = (
        to_numeric(df_player["minutes"])
        .astype(int)
    )

    # --------------------------------------------------------
    # GOL / ASSIST
    # --------------------------------------------------------

    df_clean["goals"] = (
        to_numeric(df_player["goals"])
        .astype(int)
    )

    df_clean["assists"] = (
        to_numeric(df_player["assists"])
        .astype(int)
    )

    # --------------------------------------------------------
    # EXPECTED GOALS / EXPECTED ASSISTS
    # --------------------------------------------------------

    df_clean["xg"] = (
        to_numeric(df_player["xg"])
        .round(2)
    )

    df_clean["xa"] = (
        to_numeric(df_player["xa"])
        .round(2)
    )

    # --------------------------------------------------------
    # NON-PENALTY GOALS / XG
    # --------------------------------------------------------

    df_clean["np_goals"] = (
        to_numeric(df_player["np_goals"])
        .astype(int)
    )

    df_clean["np_xg"] = (
        to_numeric(df_player["np_xg"])
        .round(2)
    )

    # --------------------------------------------------------
    # TIRI E PASSAGGI CHIAVE
    # --------------------------------------------------------

    df_clean["shots_total"] = (
        to_numeric(df_player["shots"])
        .astype(int)
    )

    df_clean["key_passes"] = (
        to_numeric(df_player["key_passes"])
        .astype(int)
    )

    # --------------------------------------------------------
    # CARTELLINI
    # --------------------------------------------------------

    df_clean["yellow_cards"] = (
        to_numeric(df_player["yellow_cards"])
        .astype(int)
    )

    df_clean["red_cards"] = (
        to_numeric(df_player["red_cards"])
        .astype(int)
    )

    # --------------------------------------------------------
    # METRICHE AVANZATE UNDERSTAT
    # --------------------------------------------------------

    df_clean["xg_chain"] = (
        to_numeric(df_player["xg_chain"])
        .round(2)
    )

    df_clean["xg_buildup"] = (
        to_numeric(df_player["xg_buildup"])
        .round(2)
    )

    # ========================================================
    # KPI PER 90 MINUTI
    # ========================================================

    minutes = df_clean["minutes_played"]

    df_clean["goals_per_90"] = (
        df_clean["goals"] / (minutes / 90)
    ).where(
        minutes > 0,
        0.0
    ).round(2)

    df_clean["assists_per_90"] = (
        df_clean["assists"] / (minutes / 90)
    ).where(
        minutes > 0,
        0.0
    ).round(2)

    df_clean["xg_per_90"] = (
        df_clean["xg"] / (minutes / 90)
    ).where(
        minutes > 0,
        0.0
    ).round(2)

    df_clean["xa_per_90"] = (
        df_clean["xa"] / (minutes / 90)
    ).where(
        minutes > 0,
        0.0
    ).round(2)

    df_clean["shots_per_90"] = (
        df_clean["shots_total"] / (minutes / 90)
    ).where(
        minutes > 0,
        0.0
    ).round(2)

    df_clean["key_passes_per_90"] = (
        df_clean["key_passes"] / (minutes / 90)
    ).where(
        minutes > 0,
        0.0
    ).round(2)

    # --------------------------------------------------------
    # ID UNIVOCO
    # --------------------------------------------------------
    #
    # Non usiamo player_name perché può cambiare.
    # Usiamo player_id + stagione.
    #

    df_clean["id"] = (
        df_clean["player_id"].astype(str)
        + "_"
        + df_clean["season"]
    )

    # --------------------------------------------------------
    # ORDINAMENTO COLONNE
    # --------------------------------------------------------

    columns_order = [
        "id",
        "player_id",
        "player_name",
        "team",
        "season",
        "position",

        "matches_played",
        "minutes_played",

        "goals",
        "assists",

        "xg",
        "xa",

        "np_goals",
        "np_xg",

        "shots_total",
        "key_passes",

        "yellow_cards",
        "red_cards",

        "xg_chain",
        "xg_buildup",

        "goals_per_90",
        "assists_per_90",
        "xg_per_90",
        "xa_per_90",
        "shots_per_90",
        "key_passes_per_90"
    ]

    df_clean = df_clean[columns_order]

    # --------------------------------------------------------
    # CONTROLLO FINALE
    # --------------------------------------------------------

    df_clean = df_clean.drop_duplicates(
        subset=["player_id", "season"]
    )

    print(
        f"DataFrame finale: {len(df_clean)} giocatori."
    )

    print("\nEsempio dati:")
    print(df_clean.head())

    return df_clean


# ============================================================
# UPLOAD SUPABASE
# ============================================================

def upload_to_supabase(df, batch_size=500):
    """
    Carica i dati su Supabase tramite upsert.
    I record vengono inviati a batch per evitare richieste
    troppo grandi.
    """

    if df is None or df.empty:
        print("Nessun dato valido da caricare.")
        return

    print(
        f"\nInizio caricamento di {len(df)} record su Supabase..."
    )

    # --------------------------------------------------------
    # Conversione DataFrame -> JSON
    # --------------------------------------------------------

    records = df.to_dict(orient="records")

    # Supabase/PostgREST non gestisce bene alcuni tipi
    # Pandas come Int64.
    for record in records:
        for key, value in record.items():

            if pd.isna(value):
                record[key] = None

            elif hasattr(value, "item"):
                record[key] = value.item()

    # --------------------------------------------------------
    # UPLOAD A BATCH
    # --------------------------------------------------------

    total = len(records)

    try:

        for start in range(0, total, batch_size):

            end = min(
                start + batch_size,
                total
            )

            batch = records[start:end]

            print(
                f"Upload record {start + 1}-{end} "
                f"di {total}..."
            )

            response = (
                supabase
                .table("player_stats")
                .upsert(
                    batch,
                    on_conflict="player_id,season"
                )
                .execute()
            )

            print(
                f"Batch {start + 1}-{end} completato."
            )

        print(
            "\nCaricamento completato con successo!"
        )

    except Exception as e:

        print(
            f"\nErrore durante l'upsert su Supabase: {e}"
        )

        raise


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    # 2024 = stagione 2024/25
    seasons = ["2024"]

    df_processed = fetch_and_process_data(
        seasons=seasons
    )

    upload_to_supabase(
        df_processed
    )
