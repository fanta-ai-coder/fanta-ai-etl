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
# STAGIONI DA IMPORTARE
# ============================================================

# SoccerData / Understat utilizza l'anno di inizio della stagione:
#
# 2020 = 2020/21
# 2021 = 2021/22
# 2022 = 2022/23
# 2023 = 2023/24
# 2024 = 2024/25

SEASONS = [
    "2020",
    "2021",
    "2022",
    "2023",
    "2024",
    "2025",
    "2026"
]


# ============================================================
# FUNZIONI DI SUPPORTO
# ============================================================

def to_numeric(series, default=0):
    """
    Converte una Series Pandas in numerico gestendo
    valori nulli o non validi.
    """
    return pd.to_numeric(
        series,
        errors="coerce"
    ).fillna(default)


# ============================================================
# DOWNLOAD + TRASFORMAZIONE
# ============================================================

def fetch_and_process_data(season):
    """
    Scarica le statistiche stagionali dei giocatori da Understat
    tramite SoccerData per una singola stagione.
    """

    print("\n" + "=" * 70)
    print(f"DOWNLOAD STAGIONE {season}/{int(season) + 1}")
    print("=" * 70)

    try:

        understat = sd.Understat(
            leagues="ITA-Serie A",
            seasons=[season]
        )

        df_player = understat.read_player_season_stats()

    except Exception as e:

        print(
            f"ERRORE download Understat stagione {season}: {e}"
        )

        return None

    if df_player is None or df_player.empty:

        print(
            f"Nessun dato restituito per la stagione {season}."
        )

        return None

    # --------------------------------------------------------
    # RESET INDEX
    # --------------------------------------------------------

    df_player = df_player.reset_index()

    print(
        f"Ricevuti {len(df_player)} record da Understat."
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
        col
        for col in required_columns
        if col not in df_player.columns
    ]

    if missing_columns:

        raise ValueError(
            f"Colonne mancanti per stagione {season}: "
            + ", ".join(missing_columns)
        )

    # ========================================================
    # DATAFRAME PULITO
    # ========================================================

    df_clean = pd.DataFrame()

    # --------------------------------------------------------
    # IDENTIFICATIVI
    # --------------------------------------------------------

    df_clean["player_id"] = (
        pd.to_numeric(
            df_player["player_id"],
            errors="coerce"
        ).astype("Int64")
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
    # PRESENZE / MINUTI
    # --------------------------------------------------------

    df_clean["matches_played"] = (
        to_numeric(
            df_player["matches"]
        ).astype(int)
    )

    df_clean["minutes_played"] = (
        to_numeric(
            df_player["minutes"]
        ).astype(int)
    )

    # --------------------------------------------------------
    # GOL / ASSIST
    # --------------------------------------------------------

    df_clean["goals"] = (
        to_numeric(
            df_player["goals"]
        ).astype(int)
    )

    df_clean["assists"] = (
        to_numeric(
            df_player["assists"]
        ).astype(int)
    )

    # --------------------------------------------------------
    # xG / xA
    # --------------------------------------------------------

    df_clean["xg"] = (
        to_numeric(
            df_player["xg"]
        ).round(2)
    )

    df_clean["xa"] = (
        to_numeric(
            df_player["xa"]
        ).round(2)
    )

    # --------------------------------------------------------
    # NON-PENALTY
    # --------------------------------------------------------

    df_clean["np_goals"] = (
        to_numeric(
            df_player["np_goals"]
        ).astype(int)
    )

    df_clean["np_xg"] = (
        to_numeric(
            df_player["np_xg"]
        ).round(2)
    )

    # --------------------------------------------------------
    # TIRI / KEY PASSES
    # --------------------------------------------------------

    df_clean["shots_total"] = (
        to_numeric(
            df_player["shots"]
        ).astype(int)
    )

    df_clean["key_passes"] = (
        to_numeric(
            df_player["key_passes"]
        ).astype(int)
    )

    # --------------------------------------------------------
    # CARTELLINI
    # --------------------------------------------------------

    df_clean["yellow_cards"] = (
        to_numeric(
            df_player["yellow_cards"]
        ).astype(int)
    )

    df_clean["red_cards"] = (
        to_numeric(
            df_player["red_cards"]
        ).astype(int)
    )

    # --------------------------------------------------------
    # METRICHE AVANZATE
    # --------------------------------------------------------

    df_clean["xg_chain"] = (
        to_numeric(
            df_player["xg_chain"]
        ).round(2)
    )

    df_clean["xg_buildup"] = (
        to_numeric(
            df_player["xg_buildup"]
        ).round(2)
    )

    # ========================================================
    # METRICHE PER 90
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

    # ========================================================
    # ID UNIVOCO
    # ========================================================

    df_clean["id"] = (
        df_clean["player_id"].astype(str)
        + "_"
        + df_clean["season"].astype(str)
    )

    # ========================================================
    # ORDINE COLONNE
    # ========================================================

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
    # RIMOZIONE DUPLICATI
    # --------------------------------------------------------

    df_clean = df_clean.drop_duplicates(
        subset=[
            "player_id",
            "season"
        ]
    )

    print(
        f"DataFrame finale stagione {season}: "
        f"{len(df_clean)} giocatori."
    )

    return df_clean


# ============================================================
# UPLOAD SUPABASE
# ============================================================

def upload_to_supabase(
    df,
    batch_size=500
):
    """
    Esegue l'upsert dei record su Supabase.
    """

    if df is None or df.empty:

        print(
            "Nessun dato valido da caricare."
        )

        return False

    records = df.to_dict(
        orient="records"
    )

    # --------------------------------------------------------
    # Conversione tipi Pandas -> Python
    # --------------------------------------------------------

    for record in records:

        for key, value in record.items():

            if pd.isna(value):

                record[key] = None

            elif hasattr(value, "item"):

                record[key] = value.item()

    total = len(records)

    print(
        f"Inizio caricamento di "
        f"{total} record su Supabase..."
    )

    try:

        for start in range(
            0,
            total,
            batch_size
        ):

            end = min(
                start + batch_size,
                total
            )

            batch = records[
                start:end
            ]

            print(
                f"Upload record "
                f"{start + 1}-{end} "
                f"di {total}..."
            )

            (
                supabase
                .table("player_stats")
                .upsert(
                    batch,
                    on_conflict="player_id,season"
                )
                .execute()
            )

            print(
                f"Batch {start + 1}-{end} "
                f"completato."
            )

        print(
            "Caricamento completato con successo!"
        )

        return True

    except Exception as e:

        print(
            f"Errore durante l'upsert su Supabase: {e}"
        )

        raise


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print("\n")
    print("=" * 70)
    print("FANTA-AI - INGESTION STORICA UNDERSTAT")
    print("=" * 70)

    print(
        f"Stagioni da importare: {SEASONS}"
    )

    total_records = 0
    successful_seasons = []
    failed_seasons = []

    # --------------------------------------------------------
    # ELABORAZIONE UNA STAGIONE ALLA VOLTA
    # --------------------------------------------------------

    for season in SEASONS:

        try:

            df_processed = fetch_and_process_data(
                season
            )

            if df_processed is None:

                failed_seasons.append(
                    season
                )

                continue

            success = upload_to_supabase(
                df_processed
            )

            if success:

                successful_seasons.append(
                    season
                )

                total_records += len(
                    df_processed
                )

        except Exception as e:

            print(
                f"\nERRORE STAGIONE {season}: {e}"
            )

            failed_seasons.append(
                season
            )

    # ========================================================
    # RIEPILOGO
    # ========================================================

    print("\n")
    print("=" * 70)
    print("RIEPILOGO INGESTION")
    print("=" * 70)

    print(
        f"Stagioni completate: "
        f"{successful_seasons}"
    )

    print(
        f"Stagioni fallite: "
        f"{failed_seasons}"
    )

    print(
        f"Totale record elaborati: "
        f"{total_records}"
    )

    if failed_seasons:

        print(
            "\nATTENZIONE: alcune stagioni "
            "non sono state caricate."
        )

        raise RuntimeError(
            "Ingestion completata parzialmente. "
            f"Stagioni fallite: {failed_seasons}"
        )

    print(
        "\nINGESTION STORICA COMPLETATA "
        "CON SUCCESSO!"
    )
