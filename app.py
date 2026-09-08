import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from supabase import create_client

# ==========================================
# 1. PAGE CONFIG & DESIGN SYSTEM
# ==========================================

st.set_page_config(
    page_title="FantaAI Analytics Pro",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------- CSS personalizzato (design system dal mockup) ----------
_CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Geist:wght@100..900&family=Space+Grotesk:wght@100..900&family=JetBrains+Mono:wght@100..900&display=swap');

/* VARIABILI COLORE (allineate al mockup) */
:root {
  --surface: #0b1326;
  --surface-dim: #0b1326;
  --surface-bright: #31394d;
  --surface-container-lowest: #060e20;
  --surface-container-low: #131b2e;
  --surface-container: #171f33;
  --surface-container-high: #222a3d;
  --surface-container-highest: #2d3449;
  --surface-variant: #2d3449;
  --on-surface: #dae2fd;
  --on-surface-variant: #bbcabf;
  --outline: #86948a;
  --outline-variant: #3c4a42;
  --primary: #4edea3;
  --on-primary: #003824;
  --primary-container: #10b981;
  --on-primary-container: #00422b;
  --primary-fixed: #6ffbbe;
  --primary-fixed-dim: #4edea3;
  --secondary: #4cd7f6;
  --on-secondary: #003640;
  --secondary-container: #03b5d3;
  --on-secondary-container: #00424e;
  --secondary-fixed: #acedff;
  --secondary-fixed-dim: #4cd7f6;
  --tertiary: #ffb95f;
  --on-tertiary: #472a00;
  --tertiary-container: #e29100;
  --on-tertiary-container: #523200;
  --tertiary-fixed: #ffddb8;
  --tertiary-fixed-dim: #ffb95f;
  --error: #ffb4ab;
  --on-error: #690005;
  --error-container: #93000a;
  --on-error-container: #ffdad6;
  --background: #0b1326;
  --on-background: #dae2fd;
  --surface-tint: #4edea3;
  --inverse-surface: #dae2fd;
  --inverse-on-surface: #283044;
  --inverse-primary: #006c49;
}

html, body, .stApp, [data-testid="stAppViewContainer"] {
  background-color: var(--surface) !important;
  color: var(--on-surface) !important;
  font-family: 'Geist', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Nascondi scrollbar */
::-webkit-scrollbar { display: none; }

/* Container principale */
[data-testid="stMainBlockContainer"], [data-testid="stAppViewBlockContainer"] {
  background-color: transparent !important;
  padding-top: 0 !important;
}

/* ---- HEADER fisso (non nativo, lo replicheremo con un container) ---- */
.fixed-header {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  z-index: 1000;
  background-color: rgba(6, 14, 32, 0.9);
  backdrop-filter: blur(20px);
  box-shadow: 0 1px 8px rgba(0,0,0,0.04);
  padding: 0 1.5rem;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}

/* ---- SIDEBAR SINISTRA (lista giocatori) ---- */
.player-sidebar {
  background-color: var(--surface-container-low);
  border-radius: 12px;
  padding: 0.75rem;
  box-shadow: 0 4px 20px rgba(0,0,0,0.3);
  border: 1px solid rgba(255,255,255,0.05);
  height: calc(100vh - 100px);
  overflow-y: auto;
  position: sticky;
  top: 76px;
}

/* ---- Card giocatore nella lista ---- */
.player-card {
  background-color: var(--surface-container-lowest);
  border-radius: 8px;
  padding: 0.5rem 0.75rem;
  margin-bottom: 0.25rem;
  border-left: 3px solid var(--primary);
  transition: all 0.15s ease;
  cursor: pointer;
}
.player-card:hover {
  background-color: var(--surface-container-high);
}
.player-card.selected {
  background-color: rgba(16, 185, 129, 0.15);
  border-left-color: var(--secondary);
}

/* ---- Badge di ruolo ---- */
.role-badge {
  display: inline-block;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.role-P { background: rgba(245, 158, 11, 0.2); color: #FBBF24; }
.role-D { background: rgba(59, 130, 246, 0.2); color: #60A5FA; }
.role-C { background: rgba(16, 185, 129, 0.2); color: #34D399; }
.role-A { background: rgba(239, 68, 68, 0.2); color: #F87171; }

/* ---- Metriche custom ---- */
.metric-card {
  background-color: var(--surface-container-low);
  border-radius: 12px;
  padding: 0.75rem 1rem;
  border: 1px solid rgba(255,255,255,0.05);
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
  height: 100%;
}

/* ---- Widget Streamlit ---- */
.stTextInput > div > div > input,
.stSelectbox > div > div {
  background-color: var(--surface-container-lowest) !important;
  border: 1px solid var(--surface-variant) !important;
  border-radius: 8px !important;
  color: var(--on-surface) !important;
  font-family: 'Geist', sans-serif !important;
  padding: 0.5rem 0.75rem !important;
}
.stTextInput > div > div > input:focus,
.stSelectbox > div > div:focus-within {
  border-color: var(--secondary) !important;
  box-shadow: 0 0 0 2px rgba(76, 215, 246, 0.3) !important;
}

/* Radio (lista giocatori) */
div[data-testid="stRadio"] > div[role="radiogroup"] {
  display: flex !important;
  flex-direction: column !important;
  gap: 4px !important;
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
  max-height: none !important;
  overflow: visible !important;
}
div[data-testid="stRadio"] label {
  background-color: var(--surface-container-lowest) !important;
  border: 1px solid rgba(255,255,255,0.05) !important;
  border-radius: 8px !important;
  padding: 0.6rem 0.8rem !important;
  margin: 0 !important;
  transition: all 0.1s ease !important;
  cursor: pointer !important;
}
div[data-testid="stRadio"] label:hover {
  background-color: var(--surface-container-high) !important;
  border-color: rgba(78, 222, 163, 0.3) !important;
}
div[data-testid="stRadio"] label:has(input:checked) {
  background-color: rgba(16, 185, 129, 0.12) !important;
  border-color: var(--primary) !important;
  border-left: 3px solid var(--primary) !important;
}
div[data-testid="stRadio"] label p {
  color: var(--on-surface) !important;
  font-size: 0.9rem !important;
  font-weight: 500 !important;
  margin: 0 !important;
}

/* Checkbox, Slider */
.stCheckbox label, .stSlider label {
  color: var(--on-surface-variant) !important;
  font-size: 0.8rem !important;
  font-weight: 500 !important;
}
.stSlider div[data-baseweb="slider"] div[role="slider"] {
  background-color: var(--primary) !important;
}
.stSlider div[data-baseweb="slider"] div[data-testid="stSliderTrack"] {
  background-color: var(--surface-variant) !important;
}

/* Metriche st.metric */
[data-testid="stMetric"] {
  background-color: var(--surface-container-low) !important;
  border: 1px solid rgba(255,255,255,0.05) !important;
  border-radius: 12px !important;
  padding: 0.75rem 1rem !important;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
}
[data-testid="stMetricLabel"] {
  color: var(--on-surface-variant) !important;
  font-size: 0.75rem !important;
  font-weight: 500 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.04em !important;
}
[data-testid="stMetricValue"] {
  color: var(--on-surface) !important;
  font-size: 1.6rem !important;
  font-weight: 700 !important;
}

/* Container con bordo (usato per card) */
div[data-testid="stVerticalBlockBorderWrapper"] {
  background-color: var(--surface-container-low) !important;
  border: 1px solid rgba(255,255,255,0.05) !important;
  border-radius: 12px !important;
  padding: 0.75rem !important;
}

/* Plotly chart container */
.js-plotly-plot .plotly .main-svg {
  background-color: transparent !important;
}
.js-plotly-plot .plotly .cartesianlayer {
  background-color: transparent !important;
}

/* Tabella storica */
.dataframe-container {
  background-color: var(--surface-container-low);
  border-radius: 12px;
  padding: 0.5rem;
  border: 1px solid rgba(255,255,255,0.05);
}
.dataframe-container table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}
.dataframe-container th {
  background-color: var(--surface-container-lowest);
  color: var(--on-surface-variant);
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 0.5rem 0.75rem;
  text-align: left;
}
.dataframe-container td {
  padding: 0.4rem 0.75rem;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}
.dataframe-container tr:hover td {
  background-color: var(--surface-container-high);
}
.dataframe-container .progress-bar {
  display: inline-block;
  height: 6px;
  border-radius: 9999px;
  background-color: var(--surface-variant);
  overflow: hidden;
  width: 60px;
}
.dataframe-container .progress-bar span {
  display: block;
  height: 100%;
  background-color: var(--primary);
}

/* ---- TITOLI ---- */
h1, h2, h3, h4, h5, h6 {
  font-family: 'Space Grotesk', sans-serif !important;
  font-weight: 700 !important;
  letter-spacing: -0.02em !important;
  color: var(--on-surface) !important;
}

/* ---- Badge di stato (titolare, infortunato, ecc.) ---- */
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.15rem 0.6rem;
  border-radius: 9999px;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
}
.status-badge.titolare { background: rgba(16, 185, 129, 0.2); color: #34D399; }
.status-badge.infortunato { background: rgba(245, 158, 11, 0.2); color: #FBBF24; }
.status-badge.squalificato { background: rgba(239, 68, 68, 0.2); color: #F87171; }
.status-badge.panchina { background: rgba(148, 163, 184, 0.2); color: #94A3B8; }

/* ---- Layout colonne ---- */
.stHorizontalBlock {
  align-items: stretch !important;
}
</style>
"""
st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)

# ==========================================
# 2. SUPABASE & DATA FETCHING
# ==========================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ SUPABASE_URL e/o SUPABASE_KEY non configurate.")
    st.stop()

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

def fetch_all_rows(table_name, page_size=1000):
    rows = []
    start = 0
    while True:
        end = start + page_size - 1
        response = (
            supabase
            .table(table_name)
            .select("*")
            .range(start, end)
            .execute()
        )
        page = response.data or []
        if not page:
            break
        rows.extend(page)
        if len(page) < page_size:
            break
        start += page_size
    return rows

@st.cache_data(ttl=600)
def load_stats():
    return pd.DataFrame(fetch_all_rows("player_stats_history"))

@st.cache_data(ttl=600)
def load_quotazioni():
    return pd.DataFrame(fetch_all_rows("giocatori_quotazioni"))

@st.cache_data(ttl=600)
def load_ranking():
    try:
        return pd.DataFrame(fetch_all_rows("player_ranking"))
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=600)
def load_rigoristi():
    url = "https://raw.githubusercontent.com/fanta-ai-coder/fanta-ai-etl/refs/heads/main/rigoristi.csv"
    try:
        df = pd.read_csv(url)
        df["giocatore"] = df["giocatore"].astype(str).str.upper().str.strip()
        df["squadra"] = df["squadra"].astype(str).str.upper().str.strip()
        return df
    except Exception:
        return pd.DataFrame(columns=["giocatore", "squadra", "posizione"])

@st.cache_data(ttl=600)
def load_punizioni():
    url = "https://raw.githubusercontent.com/fanta-ai-coder/fanta-ai-etl/refs/heads/main/punizioni.csv"
    try:
        df = pd.read_csv(url)
        df["giocatore"] = df["giocatore"].astype(str).str.upper().str.strip()
        df["squadra"] = df["squadra"].astype(str).str.upper().str.strip()
        return df
    except Exception:
        return pd.DataFrame(columns=["giocatore", "squadra", "posizione"])

@st.cache_data(ttl=300)
def load_titolari_infortuni():
    url = "https://raw.githubusercontent.com/fanta-ai-coder/fanta-ai-etl/refs/heads/main/titolari_infortuni"
    try:
        df = pd.read_csv(url)
        df["nome_giocatore"] = df["nome_giocatore"].astype(str).str.upper().str.strip()
        df["squadra"] = df["squadra"].astype(str).str.upper().str.strip()
        df["titolarita"] = df["titolarita"].astype(str).str.lower().str.strip()
        df["squalificato"] = df["squalificato"].astype(str).str.lower().str.strip()
        df["infortunato"] = df["infortunato"].astype(str).str.lower().str.strip()
        df["desc_infortunio"] = df["desc_infortunio"].fillna("").astype(str).str.strip()
        return df
    except Exception:
        return pd.DataFrame(columns=["nome_giocatore", "squadra", "titolarita", "squalificato", "infortunato", "desc_infortunio"])

rigoristi_df = load_rigoristi()
punizioni_df = load_punizioni()
titolari_df = load_titolari_infortuni()

# ==========================================
# 3. STATISTICAL UTILITIES (invariato)
# ==========================================

def normalize_player_id_series(series):
    numeric = pd.to_numeric(series, errors="coerce")
    return numeric.round().astype("Int64")

def normalize_dataframe(df):
    if df.empty:
        return df.copy()
    result = df.copy()
    if "player_id" in result.columns:
        result["player_id"] = normalize_player_id_series(result["player_id"])
    return result

def numeric_series(df, column):
    if column not in df.columns:
        return pd.Series(float("nan"), index=df.index, dtype="float64")
    return pd.to_numeric(df[column], errors="coerce")

def safe_sum(df, column):
    if column not in df.columns:
        return 0.0
    return float(numeric_series(df, column).fillna(0).sum())

def safe_mean(df, column):
    if column not in df.columns:
        return 0.0
    values = numeric_series(df, column).dropna()
    return float(values.mean()) if not values.empty else 0.0

def safe_variance(df, column):
    if column not in df.columns:
        return None
    values = numeric_series(df, column).dropna()
    if len(values) < 2:
        return None
    val = values.var(ddof=1)
    return None if pd.isna(val) else float(val)

def format_number(value, decimals=2):
    if value is None or pd.isna(value):
        return "N/D"
    return f"{value:.{decimals}f}"

def remove_starred_vote_rows(df):
    if df.empty or "voto" not in df.columns:
        return df.copy()
    raw_vote = df["voto"].astype(str).str.strip()
    starred = raw_vote.str.contains(r"\*", regex=True, na=False)
    return df.loc[~starred].copy() if starred.any() else df.copy()

def calculate_fantavoto(df):
    result = df.copy()
    if "voto" not in result.columns:
        result["fanta_voto_calcolato"] = float("nan")
        return result
    voto = numeric_series(result, "voto").fillna(0)
    gf = numeric_series(result, "gf").fillna(0)
    ass = numeric_series(result, "ass").fillna(0)
    rf = numeric_series(result, "rf").fillna(0)
    au = numeric_series(result, "au").fillna(0)
    esp = numeric_series(result, "esp").fillna(0)
    amm = numeric_series(result, "amm").fillna(0)
    clean_sheet = pd.Series(0.0, index=result.index)
    penalty_saved = pd.Series(0.0, index=result.index)
    gol_subiti = pd.Series(0.0, index=result.index)
    for c in ["pi", "porta_inviolata", "clean_sheet", "imbattuto"]:
        if c in result.columns:
            clean_sheet = numeric_series(result, c).fillna(0)
            break
    for c in ["rp", "rigori_parati", "rigore_parato"]:
        if c in result.columns:
            penalty_saved = numeric_series(result, c).fillna(0)
            break
    for c in ["gs", "gol_subiti"]:
        if c in result.columns:
            gol_subiti = numeric_series(result, c).fillna(0)
            break
    if "ruolo" in result.columns:
        is_p = result["ruolo"].astype(str).str.strip().str.upper().eq("P")
        clean_sheet = clean_sheet.where(is_p, 0)
        gol_subiti = gol_subiti.where(is_p, 0)
    result["fanta_voto_calcolato"] = (
        voto + (gf * 3) + ass + (rf * 3) - (au * 2) - esp - (amm * 0.5)
        + clean_sheet + (penalty_saved * 3) - gol_subiti
    )
    result.loc[numeric_series(result, "voto").isna(), "fanta_voto_calcolato"] = float("nan")
    return result

def calculate_bonus_malus(df):
    res = calculate_fantavoto(df)
    res["bonus_malus"] = res["fanta_voto_calcolato"] - numeric_series(res, "voto")
    return res

def calculate_relative_metrics(p_stats, is_goalkeeper=False):
    seasons = p_stats["stagione"].dropna().astype(str).str.strip().nunique() if "stagione" in p_stats.columns else 0
    if seasons <= 0:
        return {
            "stagioni": 0, "presenze_medie": 0.0, "presenza_pct": 0.0,
            "gol_stagione": 0.0, "assist_stagione": 0.0, "rigori_segnati": 0.0,
            "rigori_sbagliati": 0.0, "ammonizioni": 0.0, "espulsioni": 0.0,
            "gs_stagione": 0.0, "rigori_parati": 0.0,
        }
    presenze_totali = numeric_series(p_stats, "voto").count()
    presenze_medie = presenze_totali / seasons
    presenza_pct = min(100.0, (presenze_medie / 38) * 100)
    if is_goalkeeper:
        gs_tot = safe_sum(p_stats, "gs")
        rp_tot = safe_sum(p_stats, "rp")
        gf_tot = 0
        rf_tot = 0
    else:
        gf_tot = safe_sum(p_stats, "gf") + safe_sum(p_stats, "rf")
        rf_tot = safe_sum(p_stats, "rf")
        gs_tot = 0
        rp_tot = 0
    return {
        "stagioni": seasons,
        "presenze_medie": presenze_medie,
        "presenza_pct": presenza_pct,
        "assist_stagione": safe_sum(p_stats, "ass") / seasons,
        "rigori_sbagliati": safe_sum(p_stats, "rs") / seasons,
        "ammonizioni": safe_sum(p_stats, "amm") / seasons,
        "espulsioni": safe_sum(p_stats, "esp") / seasons,
        "gol_stagione": gf_tot / seasons,
        "rigori_segnati": rf_tot / seasons,
        "gs_stagione": gs_tot / seasons,
        "rigori_parati": rp_tot / seasons,
    }

def varianza_gol_binaria(p_stats):
    if p_stats.empty or "giornata" not in p_stats.columns:
        return 0.0
    gol_g = p_stats.groupby("giornata").apply(
        lambda df: 1 if (safe_sum(df, "gf") + safe_sum(df, "rf")) > 0 else 0
    )
    return 0.0 if len(gol_g) <= 1 else float(gol_g.var(ddof=1))

def season_sort_key(value):
    try:
        return int(str(value).strip().split("/")[0])
    except Exception:
        return -1

def build_rolling_data(player_stats, window=5):
    if player_stats.empty or any(c not in player_stats.columns for c in ["stagione", "giornata"]):
        return pd.DataFrame()
    res = player_stats.copy()
    res["giornata"] = pd.to_numeric(res["giornata"], errors="coerce")
    res = res[res["giornata"].notna()].copy()
    if res.empty:
        return pd.DataFrame()
    res["giornata"] = res["giornata"].astype(int)
    res["stagione"] = res["stagione"].astype(str).str.strip()
    res["_season_sort"] = res["stagione"].apply(season_sort_key)
    res = res.sort_values(["_season_sort", "giornata"]).reset_index(drop=True)
    res = calculate_fantavoto(res)
    if "voto" in res.columns:
        res["voto"] = pd.to_numeric(res["voto"], errors="coerce")
        res["media_mobile_voto"] = res.groupby("stagione", sort=False)["voto"].transform(
            lambda x: x.rolling(window=window, min_periods=1).mean()
        )
    res["media_mobile_fanta"] = res.groupby("stagione", sort=False)["fanta_voto_calcolato"].transform(
        lambda x: x.rolling(window=window, min_periods=1).mean()
    )
    res["periodo"] = res["stagione"] + " G" + res["giornata"].astype(str)
    return res

def get_latest_season(df):
    if df.empty or "stagione" not in df.columns:
        return None
    seasons = df["stagione"].dropna().astype(str).str.strip()
    seasons = seasons[seasons != ""]
    return max(seasons.unique(), key=season_sort_key) if not seasons.empty else None

def get_latest_quote_row(player_quotes):
    if player_quotes.empty:
        return None
    res = player_quotes.copy()
    if "stagione" in res.columns:
        res["_season_sort"] = res["stagione"].apply(season_sort_key)
        res = res.sort_values("_season_sort")
    return res.iloc[-1]

def get_player_ranking(ranking_df, player_id, stagione=None):
    if ranking_df.empty or "player_id" not in ranking_df.columns:
        return None
    ranking = ranking_df.copy()
    ranking["player_id"] = normalize_player_id_series(ranking["player_id"])
    try:
        pid = int(float(player_id))
    except Exception:
        return None
    ranking = ranking[ranking["player_id"] == pid].copy()
    if ranking.empty:
        return None
    if stagione is not None and "stagione" in ranking.columns:
        current = ranking[ranking["stagione"].astype(str).str.strip() == str(stagione).strip()].copy()
        if not current.empty:
            ranking = current
    if len(ranking) > 1:
        if "calculated_at" in ranking.columns:
            ranking["calculated_at"] = pd.to_datetime(ranking["calculated_at"], errors="coerce")
            ranking = ranking.sort_values("calculated_at")
        elif "stagione" in ranking.columns:
            ranking["_season_sort"] = ranking["stagione"].apply(season_sort_key)
            ranking = ranking.sort_values("_season_sort")
    return ranking.iloc[-1]

# ==========================================
# PRECALCOLO METRICHE & SUMMARY GIOCATORI
# ==========================================

@st.cache_data(ttl=600)
def compute_player_summaries(stats_df, quot_df, ranking_df, titolari_df):
    if quot_df.empty:
        return quot_df.copy()
    base = quot_df.copy()
    base["player_id"] = normalize_player_id_series(base["player_id"])

    # 1. Unione con ranking
    if not ranking_df.empty and "player_id" in ranking_df.columns:
        rdf = ranking_df.copy()
        rdf["player_id"] = normalize_player_id_series(rdf["player_id"])
        rank_cols = [
            "player_id", "indice_finale", "rank_ruolo", "totale_ruolo",
            "rank_generale", "totale_generale", "titolarita_score",
            "presenze_pesate", "forma_attuale_score", "performance_score"
        ]
        avail_rank_cols = [c for c in rank_cols if c in rdf.columns]
        rdf_unique = rdf.drop_duplicates(subset=["player_id"])[avail_rank_cols]
        base = pd.merge(base, rdf_unique, on="player_id", how="left")
    else:
        for c in ["indice_finale", "rank_ruolo", "totale_ruolo", "rank_generale", "totale_generale", "titolarita_score", "presenze_pesate"]:
            base[c] = None

    # 2. Unione con stato titolari/infortuni
    if not titolari_df.empty:
        tdf = titolari_df.copy()
        tdf["nome_norm"] = tdf["nome_giocatore"].astype(str).str.upper().str.strip()
        tdf["squadra_norm"] = tdf["squadra"].astype(str).str.upper().str.strip()
        base["nome_norm"] = base["nome"].astype(str).str.upper().str.strip()
        base["squadra_norm"] = base["squadra"].astype(str).str.upper().str.strip()
        tdf_unique = tdf.drop_duplicates(subset=["nome_norm", "squadra_norm"])
        base = pd.merge(
            base,
            tdf_unique[["nome_norm", "squadra_norm", "titolarita", "squalificato", "infortunato"]],
            on=["nome_norm", "squadra_norm"],
            how="left"
        )
        base["is_titolare"] = base["titolarita"].astype(str).str.lower().str.strip() == "titolare"
    else:
        base["is_titolare"] = False

    # 3. Aggregazione storico voti e fantamedia
    if not stats_df.empty and "player_id" in stats_df.columns:
        sdf = stats_df.copy()
        sdf["player_id"] = normalize_player_id_series(sdf["player_id"])
        if "stagione" in sdf.columns:
            sdf_hist = sdf[sdf["stagione"].astype(str).str.strip() != "2026-27"].copy()
            if sdf_hist.empty:
                sdf_hist = sdf.copy()
        else:
            sdf_hist = sdf.copy()

        voto = numeric_series(sdf_hist, "voto")
        gf = numeric_series(sdf_hist, "gf").fillna(0)
        rf = numeric_series(sdf_hist, "rf").fillna(0)
        ass = numeric_series(sdf_hist, "ass").fillna(0)
        au = numeric_series(sdf_hist, "au").fillna(0)
        esp = numeric_series(sdf_hist, "esp").fillna(0)
        amm = numeric_series(sdf_hist, "amm").fillna(0)
        gs = numeric_series(sdf_hist, "gs").fillna(0)
        rp = numeric_series(sdf_hist, "rp").fillna(0)

        clean_sheet = pd.Series(0.0, index=sdf_hist.index)
        for c in ["pi", "porta_inviolata", "clean_sheet", "imbattuto"]:
            if c in sdf_hist.columns:
                clean_sheet = numeric_series(sdf_hist, c).fillna(0)
                break
        if "ruolo" in sdf_hist.columns:
            is_p = sdf_hist["ruolo"].astype(str).str.strip().str.upper().eq("P")
            clean_sheet = clean_sheet.where(is_p, 0)
            gs = gs.where(is_p, 0)

        fv = (
            voto + (gf * 3) + ass + (rf * 3) - (au * 2) - esp - (amm * 0.5)
            + clean_sheet + (rp * 3) - gs
        )
        sdf_hist["_fanta_calc"] = fv
        sdf_hist["_voto_num"] = voto

        valid = sdf_hist[voto.notna()]
        agg = valid.groupby("player_id").agg(
            presenze_totali=("_voto_num", "count"),
            fantamedia=("_fanta_calc", "mean"),
            media_voto=("_voto_num", "mean")
        ).reset_index()

        base = pd.merge(base, agg, on="player_id", how="left")
    else:
        base["presenze_totali"] = 0
        base["fantamedia"] = None
        base["media_voto"] = None

    base["presenze_totali"] = base["presenze_totali"].fillna(0).astype(int)
    return base

# ==========================================
# 4. REUSABLE UI COMPONENTS (adattati allo stile mockup)
# ==========================================

ROLE_COLORS = {
    "P": {"bg": "rgba(245, 158, 11, 0.15)", "text": "#FBBF24", "border": "rgba(245, 158, 11, 0.4)", "label": "Portiere"},
    "D": {"bg": "rgba(59, 130, 246, 0.15)", "text": "#60A5FA", "border": "rgba(59, 130, 246, 0.4)", "label": "Difensore"},
    "C": {"bg": "rgba(16, 185, 129, 0.15)", "text": "#34D399", "border": "rgba(16, 185, 129, 0.4)", "label": "Centrocampista"},
    "A": {"bg": "rgba(239, 68, 68, 0.15)", "text": "#F87171", "border": "rgba(239, 68, 68, 0.4)", "label": "Attaccante"},
}

def render_section_header(title, subtitle=None):
    st.subheader(title)
    if subtitle:
        st.caption(subtitle)

def render_kpi_card(title, value, subtext="", highlight=False):
    with st.container(border=True):
        label = f"⭐ {title}" if highlight else title
        st.metric(label=label, value=value)
        if subtext:
            st.caption(subtext)

def render_quote_hero_card(quota, fvm, ranking=None):
    if ranking is not None:
        indice_finale = ranking.get("indice_finale")
        rank_generale = ranking.get("rank_generale")
        totale_generale = ranking.get("totale_generale")
        rank_ruolo = ranking.get("rank_ruolo")
        totale_ruolo = ranking.get("totale_ruolo")
    else:
        indice_finale = rank_generale = totale_generale = rank_ruolo = totale_ruolo = None

    ranking_score = None if indice_finale is None or pd.isna(indice_finale) else f"{float(indice_finale):.1f}"
    generale_txt = f"#{int(rank_generale)} / {int(totale_generale)}" if (rank_generale is not None and not pd.isna(rank_generale) and totale_generale is not None and not pd.isna(totale_generale)) else "N/D"
    ruolo_txt = f"#{int(rank_ruolo)} / {int(totale_ruolo)}" if (rank_ruolo is not None and not pd.isna(rank_ruolo) and totale_ruolo is not None and not pd.isna(totale_ruolo)) else "N/D"

    with st.container(border=True, key="hero_card"):
        st.caption("⭐ VALUTAZIONI ASTA — GUIDA ASTA")
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Quotazione", f"{quota} FM")
        with c2:
            st.metric("FVM Consigliato", f"{fvm} FM")
        st.markdown("**👑 RANKING ASTA V3.1**")
        st.metric(
            "Indice",
            ranking_score if ranking_score is not None else "N/D",
            delta=("su 100" if ranking_score is not None else None),
            delta_color="off",
        )
        with st.container(key="hero_rank_small"):
            r1, r2 = st.columns(2)
            with r1:
                st.metric("Generale", generale_txt)
            with r2:
                st.metric("Ruolo", ruolo_txt)

# ==========================================
# 5. PLAYER DETAIL VIEW (stilizzata come mockup)
# ==========================================

def render_player_detail(player_id, stats, quotations, ranking_df):
    try:
        player_id = int(float(player_id))
    except Exception:
        st.error(f"Player ID non valido: {player_id}")
        return

    p_quotes = quotations[quotations["player_id"] == player_id].copy()
    current_quote = get_latest_quote_row(p_quotes)
    p_stats = stats[stats["player_id"] == player_id].copy()

    if current_quote is not None:
        nome = current_quote.get("nome", "Giocatore")
        ruolo = str(current_quote.get("ruolo", "-")).upper().strip()
        squadra = current_quote.get("squadra", "-")
    elif not p_stats.empty:
        nome = p_stats.iloc[-1].get("nome", "Giocatore")
        ruolo = str(p_stats.iloc[-1].get("ruolo", "-")).upper().strip()
        squadra = p_stats.iloc[-1].get("squadra", "-")
    else:
        nome = "Giocatore"
        ruolo = "-"
        squadra = "-"

    nome_upper = str(nome).upper().strip()
    squadra_upper = str(squadra).upper().strip()

    ranking_row = get_player_ranking(ranking_df, player_id)

    # Lookup dati aggiuntivi
    rigor_info = rigoristi_df[(rigoristi_df["giocatore"] == nome_upper) & (rigoristi_df["squadra"] == squadra_upper)]
    puniz_info = punizioni_df[(punizioni_df["giocatore"] == nome_upper) & (punizioni_df["squadra"] == squadra_upper)]
    titolare_info = titolari_df[(titolari_df["nome_giocatore"] == nome_upper) & (titolari_df["squadra"] == squadra_upper)]

    role_meta = ROLE_COLORS.get(ruolo, {"label": ruolo})

    # Tag
    tags = [f"{ruolo} — {role_meta['label']}", f"🛡️ {squadra}"]
    if not rigor_info.empty:
        pos_r = int(rigor_info["posizione"].values[0])
        tags.append(f"🎯 Rigorista #{pos_r}")
    if not puniz_info.empty:
        pos_p = int(puniz_info["posizione"].values[0])
        tags.append(f"⚡ Punizioni #{pos_p}")

    # Status
    status_kind = None
    status_text = None
    if not titolare_info.empty:
        row = titolare_info.iloc[0]
        tit = row.get("titolarita", "")
        squalificato = str(row.get("squalificato", "no")).lower()
        infortunato = str(row.get("infortunato", "no")).lower()
        desc = str(row.get("desc_infortunio", "")).strip()
        if squalificato == "si":
            status_kind = "error"
            status_text = "🟥 Squalificato"
        elif infortunato == "si":
            desc_short = ("  \n" + desc[:80] + ("…" if len(desc) > 80 else "")) if desc else ""
            status_kind = "warning"
            status_text = f"🤕 Infortunato{desc_short}"
        elif tit == "titolare":
            status_kind = "success"
            status_text = "✅ Titolare"
        elif tit == "panchina":
            status_kind = "info"
            status_text = "🪑 Panchina"

    # HEADER
    header_col1, header_col2 = st.columns([2.5, 1.5])
    with header_col1:
        st.header(nome)
        st.write(" | ".join(tags))
        if status_kind == "error":
            st.error(status_text)
        elif status_kind == "warning":
            st.warning(status_text)
        elif status_kind == "success":
            st.success(status_text)
        elif status_kind == "info":
            st.info(status_text)

    with header_col2:
        quota_val = current_quote.get("quotazione_attuale", "-") if current_quote is not None else "-"
        fvm_val = current_quote.get("fvm", "-") if current_quote is not None else "-"
        render_quote_hero_card(quota_val, fvm_val, ranking_row)

    if p_stats.empty:
        st.info("ℹ️ Nessuna statistica storica disponibile per questo giocatore.")
        return

    # Pulizia e calcoli
    if "stagione" in p_stats.columns:
        p_stats["stagione"] = p_stats["stagione"].astype(str).str.strip()
    if "giornata" in p_stats.columns:
        p_stats["giornata"] = pd.to_numeric(p_stats["giornata"], errors="coerce")
    p_stats = remove_starred_vote_rows(p_stats)
    if p_stats.empty:
        st.info("ℹ️ Nessuna prestazione valida registrata.")
        return
    p_stats = calculate_bonus_malus(p_stats)
    is_goalkeeper = (ruolo == "P")

    # Escludi stagione 2026-27 per le medie storiche
    p_stats_hist = p_stats[p_stats["stagione"].astype(str).str.strip() != "2026-27"].copy() if "stagione" in p_stats.columns else p_stats.copy()
    if p_stats_hist.empty:
        p_stats_hist = p_stats.copy()

    # ---- RENDIMENTO ----
    render_section_header("📊 Rendimento Complessivo", "Medie pesate e metriche chiave calcolate sulle stagioni concluse")
    rel = calculate_relative_metrics(p_stats_hist, is_goalkeeper=is_goalkeeper)
    media_voto = safe_mean(p_stats_hist, "voto")
    fantamedia = safe_mean(p_stats_hist, "fanta_voto_calcolato")
    varianza_bin = varianza_gol_binaria(p_stats_hist)
    varianza_v = safe_variance(p_stats_hist, "voto")

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi_card("Fantamedia", f"{fantamedia:.2f}", "Bonus/Malus inclusi", highlight=True)
    with k2:
        render_kpi_card("Media Voto Pura", f"{media_voto:.2f}", "Stabilità redazionale")
    with k3:
        render_kpi_card("% Presenze", f"{rel['presenza_pct']:.1f}%", f"{rel['presenze_medie']:.1f} partite / anno")
    with k4:
        if is_goalkeeper:
            render_kpi_card("Media GS / Stagione", f"{rel['gs_stagione']:.2f}", highlight=True)
        else:
            render_kpi_card("Gol Medi / Anno", f"{rel['gol_stagione']:.1f}", f"{rel['assist_stagione']:.1f} assist medi")

    # ---- Portieri extra ----
    if is_goalkeeper:
        var_col1, var_col2, var_col3 = st.columns(3)
        varianza_gs = safe_variance(p_stats_hist, "gs")
        totale_presenze = numeric_series(p_stats_hist, "voto").count()
        media_clean_sheet = ((numeric_series(p_stats_hist, "gs") == 0).sum() / totale_presenze * 100) if totale_presenze > 0 else 0
        with var_col1:
            render_kpi_card("Varianza GS / Partita", format_number(varianza_gs))
        with var_col2:
            render_kpi_card("Media Clean Sheet (%)", f"{media_clean_sheet:.1f}%")
        with var_col3:
            st.markdown("")  # placeholder

    else:
        # ---- CONTINUITÀ ----
        render_section_header("🎯 Continuità & Analisi del Rischio")
        var_col1, var_col2, var_col3, var_col4 = st.columns(4)
        with var_col1:
            st.metric("Varianza Voto", format_number(varianza_v), help="Minore è il valore, più costante è il rendimento (valore < 0.5 = ottimo)")
        with var_col2:
            st.metric("Varianza Gol", format_number(varianza_bin), help="Frequenza con cui va a segno su più giornate diverse")
        with var_col3:
            st.metric("Ammonizioni / anno", f"{rel['ammonizioni']:.1f}", help="Media cartellini gialli a stagione")
        with var_col4:
            st.metric("Espulsioni / anno", f"{rel['espulsioni']:.1f}", help="Media cartellini rossi a stagione")

    # ---- TREND ----
    render_section_header("📈 Trend di Forma (Rolling 5 Giornate)", "Evoluzione della media mobile su voto puro vs fantavoto")
    rolling_df = build_rolling_data(p_stats, window=5)
    if not rolling_df.empty:
        fig = go.Figure()
        if "media_mobile_fanta" in rolling_df.columns:
            fig.add_trace(go.Scatter(
                x=rolling_df["periodo"],
                y=rolling_df["media_mobile_fanta"],
                mode="lines",
                name="Fantamedia (5G)",
                line=dict(color="#10B981", width=3, shape="spline"),
                fill="tozeroy",
                fillcolor="rgba(16, 185, 129, 0.08)",
                hovertemplate="<b>%{x}</b><br>Fantamedia: <b>%{y:.2f}</b><extra></extra>"
            ))
        if "media_mobile_voto" in rolling_df.columns:
            fig.add_trace(go.Scatter(
                x=rolling_df["periodo"],
                y=rolling_df["media_mobile_voto"],
                mode="lines",
                name="Media Voto (5G)",
                line=dict(color="#60A5FA", width=2, dash="dot", shape="spline"),
                hovertemplate="<b>%{x}</b><br>Media Voto: <b>%{y:.2f}</b><extra></extra>"
            ))
        fig.add_hline(y=6.0, line_dash="dash", line_color="rgba(255,255,255,0.2)", annotation_text="Sufficienza (6.0)", annotation_position="bottom right")
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(17, 24, 39, 0.6)",
            font=dict(family="Geist", color="#94A3B8"),
            hovermode="x unified",
            height=380,
            margin=dict(l=10, r=10, t=30, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)", showgrid=True),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)", showgrid=True, range=[4.5, 10])
        )
        st.plotly_chart(fig, use_container_width=True)

    # ---- STORICO ----
    render_section_header("📅 Storico Dettagliato per Stagione")
    if "stagione" in p_stats.columns:
        rows = []
        for s, g in p_stats.groupby("stagione"):
            gfanta = calculate_fantavoto(g)
            if is_goalkeeper:
                gol_subiti = int(safe_sum(g, "gs"))
                clean_sheet_count = (numeric_series(g, "gs") == 0).sum()
                rows.append({
                    "Stagione": s,
                    "Presenze": int(numeric_series(g, "voto").count()),
                    "Media Voto": round(safe_mean(g, "voto"), 2),
                    "Fantamedia": round(safe_mean(gfanta, "fanta_voto_calcolato"), 2),
                    "Gol Subiti": gol_subiti,
                    "Clean Sheet": clean_sheet_count,
                    "Amm": int(safe_sum(g, "amm")),
                    "Esp": int(safe_sum(g, "esp")),
                    "Malus/Bonus Medio": round(safe_mean(calculate_bonus_malus(g), "bonus_malus"), 2)
                })
            else:
                rows.append({
                    "Stagione": s,
                    "Presenze": int(numeric_series(g, "voto").count()),
                    "Media Voto": round(safe_mean(g, "voto"), 2),
                    "Fantamedia": round(safe_mean(gfanta, "fanta_voto_calcolato"), 2),
                    "Gol": int(safe_sum(g, "gf") + safe_sum(g, "rf")),
                    "Assist": int(safe_sum(g, "ass")),
                    "Amm": int(safe_sum(g, "amm")),
                    "Esp": int(safe_sum(g, "esp")),
                    "Malus/Bonus Medio": round(safe_mean(calculate_bonus_malus(g), "bonus_malus"), 2)
                })
        season_df = pd.DataFrame(rows)
        if not season_df.empty:
            season_df["_sort"] = season_df["Stagione"].apply(season_sort_key)
            season_df = season_df.sort_values("_sort", ascending=False).drop(columns="_sort")
            # Personalizzazione colonne
            col_config = {
                "Fantamedia": st.column_config.NumberColumn(format="%.2f ⭐"),
                "Media Voto": st.column_config.NumberColumn(format="%.2f"),
                "Presenze": st.column_config.ProgressColumn(min_value=0, max_value=38, format="%d / 38"),
            }
            st.dataframe(season_df, use_container_width=True, hide_index=True, column_config=col_config)

# ==========================================
# 6. APP CONTROLLER & MAIN UI
# ==========================================

try:
    df = load_stats()
    quot = load_quotazioni()
    ranking_df = load_ranking()
except Exception as e:
    st.error(f"❌ Errore nel caricamento dei dati: {e}")
    st.stop()

if df.empty or quot.empty:
    st.warning("⚠️ Tabelle statistiche o quotazioni vuote.")
    st.stop()

df = normalize_dataframe(df)
quot = normalize_dataframe(quot)
ranking_df = normalize_dataframe(ranking_df)
df = remove_starred_vote_rows(df)

latest_s = get_latest_season(quot)
current_quot = quot[quot["stagione"].astype(str).str.strip() == str(latest_s).strip()].copy() if latest_s else quot.copy()

# ==========================================
# HEADER (fisso replicato con un container)
# ==========================================
st.markdown(
    """
    <div class="fixed-header">
        <div style="display:flex;align-items:center;gap:0.5rem;">
            <span style="font-size:1.8rem;">⚽</span>
            <span style="font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:1.2rem;letter-spacing:-0.02em;color:#dae2fd;">FantaAI Analytics Pro</span>
            <span style="background:rgba(3,181,211,0.2);color:#4cd7f6;padding:0.1rem 0.5rem;border-radius:4px;font-size:0.6rem;font-weight:700;text-transform:uppercase;letter-spacing:0.04em;">v2.4 PRO</span>
        </div>
        <div style="display:flex;align-items:center;gap:1rem;font-size:0.75rem;color:#bbcabf;">
            <span><span style="display:inline-block;width:8px;height:8px;background:#10b981;border-radius:50%;margin-right:6px;"></span>Opta Live Feed</span>
            <span style="color:#86948a;">•</span>
            <span>Serie A 2024/25</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Spazio per evitare sovrapposizione con header fisso
st.markdown("<div style='height:80px;'></div>", unsafe_allow_html=True)

# ==========================================
# FILTRI & ORDINAMENTO (stile mockup)
# ==========================================

squadre_raw = current_quot["squadra"].dropna().astype(str).str.strip().unique() if "squadra" in current_quot.columns else []
squadre_list = ["Tutte"] + sorted(list(squadre_raw))

filter_c1, filter_c2, filter_c3, filter_c4 = st.columns([1, 1.2, 1.5, 1.8])
with filter_c1:
    selected_role = st.selectbox("Ruolo", ["Tutti", "P", "D", "C", "A"], index=0)
with filter_c2:
    selected_team = st.selectbox("Squadra", squadre_list, index=0)
with filter_c3:
    sort_options = ["👑 Indice Ranking (Decrescente)", "⭐ Fantamedia (Decrescente)", "🔤 Nome (A-Z)", "💰 Quotazione (Decrescente)"]
    selected_sort = st.selectbox("Ordina per", sort_options, index=0)
with filter_c4:
    search_query = st.text_input("Cerca giocatore o squadra", placeholder="🔍 Cerca per nome o squadra...")

adv_c1, adv_c2 = st.columns([1.5, 2.5])
with adv_c1:
    only_titolari = st.checkbox("✅ Mostra solo titolari (formazione tipo)", value=False, help="Se selezionato, mostra solo i titolari della formazione tipo.")
with adv_c2:
    min_partite = st.slider("Partite minime giocate (con voto)", min_value=0, max_value=38, value=0, step=1, help="Filtra i giocatori che hanno disputato almeno questo numero di partite nello storico")

st.divider()

# ==========================================
# CALCOLO SUMMARY PER FILTRI
# ==========================================

summary_df = compute_player_summaries(df, current_quot, ranking_df, titolari_df)
quot_view = summary_df.copy()

# Applica filtri
if isinstance(selected_role, str) and selected_role != "Tutti" and "ruolo" in quot_view.columns:
    quot_view = quot_view[quot_view["ruolo"].astype(str).str.upper().str.strip() == selected_role]
if isinstance(selected_team, str) and selected_team != "Tutte" and "squadra" in quot_view.columns:
    quot_view = quot_view[quot_view["squadra"].astype(str).str.upper().str.strip() == selected_team.upper().strip()]
if isinstance(search_query, str) and search_query.strip():
    q = search_query.upper().strip()
    match_nome = quot_view["nome"].astype(str).str.upper().str.contains(q, na=False) if "nome" in quot_view.columns else False
    match_squadra = quot_view["squadra"].astype(str).str.upper().str.contains(q, na=False) if "squadra" in quot_view.columns else False
    quot_view = quot_view[match_nome | match_squadra]
if bool(only_titolari) is True and "is_titolare" in quot_view.columns:
    quot_view = quot_view[quot_view["is_titolare"] == True]
if isinstance(min_partite, (int, float)) and min_partite > 0 and "presenze_totali" in quot_view.columns:
    quot_view = quot_view[quot_view["presenze_totali"] >= min_partite]

# Ordinamento
if selected_sort == "👑 Indice Ranking (Decrescente)":
    quot_view = quot_view.sort_values(by=["indice_finale", "quotazione_attuale", "nome"], ascending=[False, False, True], na_position="last")
elif selected_sort == "⭐ Fantamedia (Decrescente)":
    quot_view = quot_view.sort_values(by=["fantamedia", "presenze_totali", "nome"], ascending=[False, False, True], na_position="last")
elif selected_sort == "🔤 Nome (A-Z)":
    quot_view = quot_view.sort_values(by=["nome"], ascending=[True], na_position="last")
elif selected_sort == "💰 Quotazione (Decrescente)":
    quot_view = quot_view.sort_values(by=["quotazione_attuale", "fvm", "nome"], ascending=[False, False, True], na_position="last")

# ==========================================
# LAYOUT DUE COLONNE (SIDEBAR + DETAIL)
# ==========================================

col_players, col_detail = st.columns([1.1, 2.9], gap="medium")

with col_players:
    st.caption(f"**GIOCATORI{' TITOLARI' if only_titolari else ''} ({len(quot_view)})**")
    if quot_view.empty:
        st.info("Nessun giocatore trovato con questi filtri.")
        selected_id = None
    else:
        options_df = quot_view.drop_duplicates(subset="player_id").copy()
        labels = []
        ids = []
        for row in options_df.itertuples():
            n = getattr(row, "nome", "Giocatore")
            s = getattr(row, "squadra", "-")
            pid = getattr(row, "player_id")
            if selected_sort == "👑 Indice Ranking (Decrescente)":
                ind = getattr(row, "indice_finale", None)
                rk = getattr(row, "rank_ruolo", None)
                r = getattr(row, "ruolo", "")
                if pd.notna(ind):
                    rk_txt = f" (#{int(float(rk))} {r})" if pd.notna(rk) else ""
                    lbl = f"{n} [{s}] • Ind: {float(ind):.1f}{rk_txt}"
                else:
                    lbl = f"{n} [{s}] • Ind: N/D"
            elif selected_sort == "⭐ Fantamedia (Decrescente)":
                fm = getattr(row, "fantamedia", None)
                pz = getattr(row, "presenze_totali", 0)
                if pd.notna(fm):
                    lbl = f"{n} [{s}] • FM: {float(fm):.2f} ({int(float(pz))}P)"
                else:
                    lbl = f"{n} [{s}] • FM: N/D"
            elif selected_sort == "💰 Quotazione (Decrescente)":
                q_val = getattr(row, "quotazione_attuale", "-")
                f_val = getattr(row, "fvm", "-")
                lbl = f"{n} [{s}] • Q: {q_val} | FVM: {f_val}"
            else:
                lbl = f"{n} [{s}]"
            if lbl in labels:
                lbl = f"{lbl} #{int(pid)}"
            labels.append(lbl)
            ids.append(int(pid))

        label_to_id = dict(zip(labels, ids))
        radio_key = "player_radio"
        prev_label = st.session_state.get(radio_key)
        if prev_label not in labels:
            default_idx = 0
            if "active_player_id" in st.session_state and st.session_state["active_player_id"] in ids:
                default_idx = ids.index(st.session_state["active_player_id"])
            st.session_state[radio_key] = labels[default_idx]

        selected_label = st.radio(
            "Seleziona giocatore",
            options=labels,
            key=radio_key,
            label_visibility="collapsed"
        )
        selected_id = label_to_id.get(selected_label)
        st.session_state["active_player_id"] = selected_id

with col_detail:
    if selected_id is None:
        st.info("👈 Seleziona un giocatore dalla lista a sinistra per visualizzare la scheda analitica.")
    else:
        render_player_detail(selected_id, df, quot, ranking_df)
