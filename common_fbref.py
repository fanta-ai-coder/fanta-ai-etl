"""
Modulo condiviso tra etl_ingestion_full.py e etl_update_weekly.py.

Contiene:
  - lettura del listone quotazioni (SENZA colonne Mantra)
  - download statistiche giocatori da FBref (movimento + portieri)
  - matching nomi listone <-> FBref (normalizzazione accenti + fuzzy match,
    con tie-break su ruolo/squadra)
  - helper per svuotare/caricare tabelle su Supabase
"""

import os
import re
import unicodedata
import difflib

import pandas as pd
import soccerdata as sd
from supabase import Client, create_client

# ============================================================
# CONFIGURAZIONE
# ============================================================

QUOTAZIONI_XLSX_PATH = "Quotazioni_Fantacalcio_Stagione_2026_27.xlsx"
QUOTAZIONI_SHEET_NAME = "Tutti"

FBREF_LEAGUE = "ITA-Serie A"

# Mappa ruolo listone -> possibili valori "position" restituiti da FBref
RUOLO_TO_FBREF_POS = {
    "P": {"GK"},
    "D": {"DF"},
    "C": {"MF"},
    "A": {"FW"},
}

MATCH_CONFIDENCE_THRESHOLD = 80  # sotto questa soglia -> match_method = manual_review


def get_supabase_client() -> Client:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        raise ValueError(
            "Credenziali SUPABASE_URL o SUPABASE_KEY non trovate "
            "nei GitHub Secrets / variabili d'ambiente!"
        )
    return create_client(supabase_url, supabase_key)


def to_numeric(series, default=0):
    return pd.to_numeric(series, errors="coerce").fillna(default)


# ============================================================
# NORMALIZZAZIONE NOMI
# ============================================================

def normalize_name(name: str) -> str:
    """
    Rimuove accenti, converte in maiuscolo, elimina punteggiatura
    e spazi multipli. Es: "Martìnez L." -> "MARTINEZ L"
    """
    if not isinstance(name, str):
        return ""
    # rimuove accenti (NFKD + filtro caratteri combinanti)
    nfkd = unicodedata.normalize("NFKD", name)
    senza_accenti = "".join(c for c in nfkd if not unicodedata.combining(c))
    senza_accenti = senza_accenti.upper()
    senza_accenti = re.sub(r"[^A-Z\s]", " ", senza_accenti)
    senza_accenti = re.sub(r"\s+", " ", senza_accenti).strip()
    return senza_accenti


def name_tokens_sorted(name: str) -> str:
    """
    Ordina alfabeticamente i token del nome normalizzato, per rendere
    il confronto insensibile all'ordine (es. 'MARTINEZ LAUTARO' vs
    'LAUTARO MARTINEZ' diventano identici).
    """
    norm = normalize_name(name)
    return " ".join(sorted(norm.split()))


def similarity(a: str, b: str) -> float:
    """Punteggio di similarità 0-100 tra due stringhe già normalizzate."""
    return difflib.SequenceMatcher(None, a, b).ratio() * 100


# ============================================================
# QUOTAZIONI (listone classico, SENZA Mantra)
# ============================================================

def load_quotazioni_classic(
    path=QUOTAZIONI_XLSX_PATH,
    sheet_name=QUOTAZIONI_SHEET_NAME,
    stagione="2026/27",
):
    """
    Legge il foglio 'Tutti' del listone e mantiene SOLO le colonne
    classiche (nessuna colonna Mantra).
    """
    print("\n" + "=" * 70)
    print(f"LETTURA LISTONE QUOTAZIONI (classico) · foglio '{sheet_name}'")
    print("=" * 70)

    if not os.path.exists(path):
        raise FileNotFoundError(f"File non trovato: {path}")

    df_raw = pd.read_excel(path, sheet_name=sheet_name, skiprows=1)

    required_columns = ["Id", "R", "Nome", "Squadra", "Qt.A", "Qt.I", "Diff.", "FVM"]
    missing = [c for c in required_columns if c not in df_raw.columns]
    if missing:
        raise ValueError(
            "Colonne mancanti nel foglio 'Tutti': " + ", ".join(missing)
        )

    df = pd.DataFrame()
    df["id"] = pd.to_numeric(df_raw["Id"], errors="coerce").astype("Int64")
    df["stagione"] = stagione
    df["ruolo"] = df_raw["R"].fillna("").astype(str).str.strip().str.upper()
    df["nome"] = df_raw["Nome"].fillna("").astype(str).str.strip()
    df["squadra"] = df_raw["Squadra"].fillna("").astype(str).str.strip()
    df["quotazione_attuale"] = to_numeric(df_raw["Qt.A"]).astype(int)
    df["quotazione_iniziale"] = to_numeric(df_raw["Qt.I"]).astype(int)
    df["differenza"] = to_numeric(df_raw["Diff."]).astype(int)
    df["fvm"] = to_numeric(df_raw["FVM"]).astype(int)

    df = df.dropna(subset=["id"])
    df = df.drop_duplicates(subset=["id", "stagione"])

    print(f"Listone caricato: {len(df)} giocatori (colonne Mantra escluse).")
    return df


# ============================================================
# FBREF: DOWNLOAD STATISTICHE GIOCATORI
# ============================================================

def flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Appiattisce colonne MultiIndex tipiche delle tabelle FBref."""
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = [
            "_".join(
                str(level) for level in col
                if level and "Unnamed" not in str(level)
            ).strip("_")
            for col in df.columns
        ]
    return df


def pick_column(df: pd.DataFrame, candidates, required=True, default=None):
    """
    Ritorna il nome della prima colonna esistente tra `candidates`.

    NOTA: i nomi esatti delle colonne FBref non sono documentati in modo
    stabile da soccerdata. Se questa funzione solleva un errore, guarda
    la lista di colonne disponibili stampata nel messaggio ed aggiungi
    il nome corretto alla lista `candidates` nella chiamata corrispondente.
    """
    for c in candidates:
        if c in df.columns:
            return c
    if required:
        raise ValueError(
            f"Nessuna colonna trovata tra i candidati {candidates}.\n"
            f"Colonne disponibili: {list(df.columns)}"
        )
    return default


def _safe_col(df, candidates, cast=None, default=0):
    col = pick_column(df, candidates, required=False)
    if col is None:
        return pd.Series([default] * len(df))
    series = to_numeric(df[col], default=default)
    return series.astype(cast) if cast else series


def fetch_fbref_player_stats(season: str) -> pd.DataFrame:
    """
    Scarica e unisce le statistiche stagionali dei giocatori da FBref
    (standard + shooting + misc + keeper) per la Serie A.

    Ritorna un DataFrame con una riga per giocatore/stagione, comprese
    le metriche da portiere (NULL per i non-portieri).
    """
    print("\n" + "=" * 70)
    print(f"DOWNLOAD FBREF · STAGIONE {season}")
    print("=" * 70)

    fbref = sd.FBref(leagues=FBREF_LEAGUE, seasons=[season], headless=True)

    df_std = flatten_columns(fbref.read_player_season_stats(stat_type="standard").reset_index())
    df_shoot = flatten_columns(fbref.read_player_season_stats(stat_type="shooting").reset_index())
    df_misc = flatten_columns(fbref.read_player_season_stats(stat_type="misc").reset_index())
    df_keeper = flatten_columns(fbref.read_player_season_stats(stat_type="keeper").reset_index())

    # --------------------------------------------------------
    # Colonne chiave per il merge tra i 4 stat_type
    # --------------------------------------------------------
    player_col = pick_column(df_std, ["player", "Player"])
    team_col = pick_column(df_std, ["team", "Team", "squad", "Squad"])
    season_col = pick_column(df_std, ["season", "Season"])

    key_cols = [player_col, team_col, season_col]

    df = df_std.copy()
    for other in (df_shoot, df_misc, df_keeper):
        # rinomina le chiavi dell'altro df sugli stessi nomi, se diverse
        other_player = pick_column(other, ["player", "Player"])
        other_team = pick_column(other, ["team", "Team", "squad", "Squad"])
        other_season = pick_column(other, ["season", "Season"])
        other = other.rename(columns={
            other_player: player_col,
            other_team: team_col,
            other_season: season_col,
        })
        cols_to_merge = [c for c in other.columns if c not in df.columns] + key_cols
        df = df.merge(other[cols_to_merge], on=key_cols, how="left")

    print(f"Ricevuti {len(df)} record da FBref (dopo merge standard+shooting+misc+keeper).")

    # --------------------------------------------------------
    # COSTRUZIONE DATAFRAME PULITO
    # --------------------------------------------------------
    df_clean = pd.DataFrame()

    df_clean["player_name"] = df[player_col].fillna("").astype(str).str.strip()
    df_clean["team"] = df[team_col].fillna("").astype(str).str.strip()
    df_clean["season"] = df[season_col].fillna("").astype(str).str.strip()

    position_col = pick_column(df, ["pos", "Pos", "position", "Position"], required=False)
    df_clean["position"] = (
        df[position_col].fillna("").astype(str).str.strip() if position_col else ""
    )

    df_clean["matches_played"] = _safe_col(df, ["games", "MP", "Playing Time_MP"], cast=int)
    df_clean["minutes_played"] = _safe_col(df, ["minutes", "Min", "Playing Time_Min"], cast=int)
    df_clean["goals"] = _safe_col(df, ["goals", "Gls", "Performance_Gls"], cast=int)
    df_clean["assists"] = _safe_col(df, ["assists", "Ast", "Performance_Ast"], cast=int)
    df_clean["xg"] = _safe_col(df, ["xg", "xG", "Expected_xG"]).round(2)
    df_clean["xa"] = _safe_col(df, ["xg_assist", "xAG", "Expected_xAG"]).round(2)
    df_clean["shots_total"] = _safe_col(df, ["shots", "Sh", "Standard_Sh"], cast=int)
    df_clean["shots_on_target"] = _safe_col(df, ["shots_on_target", "SoT", "Standard_SoT"], cast=int)
    df_clean["yellow_cards"] = _safe_col(df, ["cards_yellow", "CrdY", "Performance_CrdY"], cast=int)
    df_clean["red_cards"] = _safe_col(df, ["cards_red", "CrdR", "Performance_CrdR"], cast=int)

    # metriche da portiere (rimarranno 0/NaN per i non-portieri: le
    # trasformiamo in NULL più sotto)
    df_clean["saves"] = _safe_col(df, ["saves", "Saves", "Performance_Saves"], cast=int, default=None)
    df_clean["goals_against"] = _safe_col(df, ["goals_against", "GA", "Performance_GA"], cast=int, default=None)
    df_clean["clean_sheets"] = _safe_col(df, ["clean_sheets", "CS", "Performance_CS"], cast=int, default=None)
    df_clean["penalty_saved"] = _safe_col(df, ["pens_saved", "PKsv", "Penalty Kicks_PKsv"], cast=int, default=None)

    # per i non-portieri, azzeriamo i valori "finti" 0 introdotti da _safe_col
    is_gk = df_clean["position"].str.contains("GK", na=False)
    for col in ["saves", "goals_against", "clean_sheets", "penalty_saved"]:
        df_clean.loc[~is_gk, col] = None

    # --------------------------------------------------------
    # ID FBREF: fbref non espone sempre un id numerico stabile in
    # questo formato di export, quindi costruiamo uno slug basato su
    # nome normalizzato + squadra, unico per stagione.
    # --------------------------------------------------------
    df_clean["fbref_id"] = (
        df_clean["player_name"].apply(normalize_name).str.replace(" ", "_")
        + "__"
        + df_clean["team"].apply(normalize_name).str.replace(" ", "_")
    )

    df_clean = df_clean.drop_duplicates(subset=["fbref_id", "season"])

    print(f"DataFrame FBref pulito: {len(df_clean)} giocatori (stagione {season}).")
    return df_clean


# ============================================================
# MATCHING NOMI: LISTONE <-> FBREF
# ============================================================

def build_player_mapping(df_quotazioni: pd.DataFrame, df_fbref: pd.DataFrame) -> pd.DataFrame:
    """
    Crea il mapping tra i giocatori del listone (Excel) e i giocatori
    FBref, usando:
      1. normalizzazione accenti/maiuscole
      2. confronto token ordinati alfabeticamente (gestisce sia
         "Cognome Nome" che "Nome Cognome")
      3. filtro/tie-break su ruolo e squadra quando ci sono più candidati
    """
    print("\n" + "=" * 70)
    print("MATCHING NOMI: listone <-> FBref")
    print("=" * 70)

    # un candidato FBref per (nome_normalizzato_ordinato, squadra) evitando
    # duplicati inutili tra stagioni diverse: usiamo solo la stagione più
    # recente disponibile per ogni giocatore come riferimento del match
    df_fbref_latest = (
        df_fbref.sort_values("season")
        .drop_duplicates(subset=["fbref_id"], keep="last")
        .copy()
    )
    df_fbref_latest["name_key"] = df_fbref_latest["player_name"].apply(name_tokens_sorted)
    df_fbref_latest["team_norm"] = df_fbref_latest["team"].apply(normalize_name)

    righe = []
    for _, riga in df_quotazioni.drop_duplicates(subset=["id"]).iterrows():
        nome_key = name_tokens_sorted(riga["nome"])
        squadra_norm = normalize_name(riga["squadra"])
        ruolo = riga["ruolo"]
        posizioni_attese = RUOLO_TO_FBREF_POS.get(ruolo, set())

        candidati = df_fbref_latest.copy()

        # 1) prova a restringere per squadra (se normalizzazioni combaciano)
        stessa_squadra = candidati[candidati["team_norm"] == squadra_norm]
        pool = stessa_squadra if len(stessa_squadra) > 0 else candidati

        # 2) calcola similarità sul nome per ogni candidato nel pool
        pool = pool.copy()
        pool["score"] = pool["name_key"].apply(lambda k: similarity(nome_key, k))

        # 3) bonus se la posizione FBref è coerente col ruolo del listone
        if posizioni_attese:
            pool["score"] += pool["position"].apply(
                lambda p: 5 if any(pos in str(p) for pos in posizioni_attese) else 0
            )

        pool = pool.sort_values("score", ascending=False)

        if len(pool) == 0:
            righe.append({
                "id_excel": riga["id"], "nome_excel": riga["nome"], "ruolo": ruolo,
                "squadra_excel": riga["squadra"], "fbref_id": None, "fbref_name": None,
                "match_confidence": 0, "match_method": "manual_review",
            })
            continue

        best = pool.iloc[0]
        method = "exact" if best["score"] >= 99 else "fuzzy"
        if best["score"] < MATCH_CONFIDENCE_THRESHOLD:
            method = "manual_review"

        righe.append({
            "id_excel": riga["id"],
            "nome_excel": riga["nome"],
            "ruolo": ruolo,
            "squadra_excel": riga["squadra"],
            "fbref_id": best["fbref_id"],
            "fbref_name": best["player_name"],
            "match_confidence": round(float(best["score"]), 1),
            "match_method": method,
        })

    df_mapping = pd.DataFrame(righe)

    n_ok = (df_mapping["match_method"] != "manual_review").sum()
    print(f"Match totali: {len(df_mapping)} | affidabili: {n_ok} | da rivedere: {len(df_mapping) - n_ok}")

    return df_mapping


# ============================================================
# HELPER SUPABASE
# ============================================================

def wipe_table(supabase: Client, table_name: str, id_column: str = "id"):
    """Svuota completamente una tabella (equivalente pratico a un TRUNCATE)."""
    print(f"Svuoto la tabella '{table_name}'...")
    supabase.table(table_name).delete().gte(id_column, -2147483648).execute()


def upload_to_supabase(df, table_name, on_conflict, batch_size=500):
    if df is None or df.empty:
        print(f"Nessun dato da caricare su '{table_name}'.")
        return False

    supabase = get_supabase_client()
    records = df.to_dict(orient="records")
    for record in records:
        for key, value in record.items():
            if pd.isna(value):
                record[key] = None
            elif hasattr(value, "item"):
                record[key] = value.item()

    total = len(records)
    print(f"Upload di {total} record su '{table_name}'...")
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        batch = records[start:end]
        supabase.table(table_name).upsert(batch, on_conflict=on_conflict).execute()
        print(f"  batch {start + 1}-{end}/{total} caricato.")

    print(f"Caricamento '{table_name}' completato.")
    return True
