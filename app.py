import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from supabase import create_client


# ==========================================
# 1. PAGE CONFIG & DESIGN SYSTEM (M3 DARK)
# ==========================================

st.set_page_config(
    page_title="FantaAI Analytics Pro — Dashboard",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

_CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

/* GLOBAL RESET */
html, body, [class*="css"], .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    background-color: #0B0F19 !important;
    color: #F8FAFC !important;
}

section.main, [data-testid="stMainBlockContainer"], [data-testid="stAppViewBlockContainer"] {
    background-color: #0B0F19 !important;
    padding-top: 1.5rem !important;
    padding-bottom: 2rem !important;
}

/* SCROLLBAR CUSTOM */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #334155; border-radius: 9999px; }
::-webkit-scrollbar-thumb:hover { background: #10B981; }

/* INPUT & SELECT */
.stTextInput input, .stSelectbox [data-baseweb="select"] {
    background-color: #111827 !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 8px !important;
    color: #F9FAFB !important;
    font-size: 0.85rem !important;
}

/* 1. FILTRO RUOLI COLORATO (ORIZZONTALE) */
#role-filter-anchor + div[data-testid="stRadio"] label:nth-child(1) p { color: #FFFFFF !important; font-weight: 700 !important; }
#role-filter-anchor + div[data-testid="stRadio"] label:nth-child(2) p { color: #F59E0B !important; font-weight: 700 !important; }
#role-filter-anchor + div[data-testid="stRadio"] label:nth-child(3) p { color: #3B82F6 !important; font-weight: 700 !important; }
#role-filter-anchor + div[data-testid="stRadio"] label:nth-child(4) p { color: #10B981 !important; font-weight: 700 !important; }
#role-filter-anchor + div[data-testid="stRadio"] label:nth-child(5) p { color: #EF4444 !important; font-weight: 700 !important; }

/* 2. ROSTER LIST SCROLLABILE CON CARDS SEPARATE */
#roster-anchor + div[data-testid="stRadio"] div[role="radiogroup"] {
    display: flex !important;
    flex-direction: column !important;
    gap: 8px !important;
    max-height: 680px !important;
    overflow-y: auto !important;
    padding-right: 6px !important;
}

#roster-anchor + div[data-testid="stRadio"] label > div:first-child,
#roster-anchor + div[data-testid="stRadio"] input[type="radio"] {
    display: none !important;
}

#roster-anchor + div[data-testid="stRadio"] label {
    display: flex !important;
    align-items: center !important;
    background: #111827 !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 10px !important;
    padding: 12px 16px !important;
    margin: 0 !important;
    cursor: pointer !important;
    transition: all 0.2s ease-in-out !important;
}

#roster-anchor + div[data-testid="stRadio"] label:hover {
    background: #1E293B !important;
    border-color: rgba(16, 185, 129, 0.4) !important;
}

#roster-anchor + div[data-testid="stRadio"] label:has(input:checked) {
    background: rgba(16, 185, 129, 0.15) !important;
    border: 1px solid #10B981 !important;
}

#roster-anchor + div[data-testid="stRadio"] label p {
    color: #FFFFFF !important;
    font-size: 0.98rem !important;
    font-weight: 600 !important;
    margin: 0 !important;
}

#roster-anchor + div[data-testid="stRadio"] label:has(input:checked) p {
    color: #34D399 !important;
    font-weight: 700 !important;
}

/* CARDS & PANELS */
.glass-panel { background: #111827; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 20px; }
.kpi-card { background: #111827; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 16px; display: flex; flex-direction: column; }
.kpi-card .kpi-label { color: #94A3B8; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
.kpi-card .kpi-value { color: #F8FAFC; font-size: 1.6rem; font-weight: 800; margin: 4px 0; font-family: 'Inter', sans-serif; }
.kpi-card .kpi-sub { color: #64748B; font-size: 0.75rem; }

.top-header { background: #111827; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding: 12px 20px; border-radius: 12px; margin-bottom: 16px; }
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
            supabase.table(table_name)
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
        return pd.DataFrame(
            columns=["nome_giocatore", "squadra", "titolarita", "squalificato", "infortunato", "desc_infortunio"]
        )


rigoristi_df = load_rigoristi()
punizioni_df = load_punizioni()
titolari_df = load_titolari_infortuni()


# ==========================================
# 3. STATISTICAL UTILITIES
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
        voto + (gf * 3) + ass + (rf * 3) - (au * 2) - esp - (amm * 0.5) + clean_sheet + (penalty_saved * 3) - gol_subiti
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
            "gs_stagione": 0.0, "rigori_parati": 0.0
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


@st.cache_data(ttl=600)
def compute_player_summaries(stats_df, quot_df, ranking_df, titolari_df):
    if quot_df.empty:
        return quot_df.copy()

    base = quot_df.copy()
    base["player_id"] = normalize_player_id_series(base["player_id"])

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

        fv = voto + (gf * 3) + ass + (rf * 3) - (au * 2) - esp - (amm * 0.5) + clean_sheet + (rp * 3) - gs
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
# 4. APP TOP BARS & HEADERS
# ==========================================

# Top Application Header
st.markdown("""
<div class="top-header" style="display: flex; align-items: center; justify-content: space-between;">
    <div style="display: flex; align-items: center; gap: 12px;">
        <div style="background: #10B981; color: #0B0F19; border-radius: 8px; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; font-weight: 800;">
            ⚡
        </div>
        <div>
            <div style="font-weight: 800; font-size: 1.1rem; color: #F8FAFC; letter-spacing: -0.02em;">
                FantaAI <span style="color: #34D399;">Analytics Pro</span>
            </div>
            <div style="font-size: 0.72rem; color: #94A3B8;">SERIE A 2024/25 — ASTA LIVE READY</div>
        </div>
    </div>
    <div style="display: flex; align-items: center; gap: 16px;">
        <div style="background: rgba(255,255,255,0.05); padding: 6px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08); text-align: right;">
            <div style="font-size: 0.65rem; color: #64748B;">BUDGET FANTAMEDIA</div>
            <div style="font-size: 0.85rem; font-weight: 700; color: #F8FAFC;">342 / 500 FM</div>
        </div>
        <div style="background: rgba(16, 185, 129, 0.1); padding: 6px 12px; border-radius: 8px; border: 1px solid rgba(16, 185, 129, 0.2); color: #34D399; font-size: 0.75rem; font-weight: 600;">
            ● Supabase Live
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ==========================================
# 5. DATA LOADING & FILTER PREPARATION
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

summary_df = compute_player_summaries(df, current_quot, ranking_df, titolari_df)


# ==========================================
# 6. MAIN MASTER-DETAIL LAYOUT
# ==========================================

col_roster, col_dossier = st.columns([0.33, 0.67], gap="medium")

# ------------------------------------------
# COLONNA SINISTRA: ROSTER & FILTRI
# ------------------------------------------
with col_roster:
    st.markdown("""
    <div style="margin-bottom: 12px;">
        <div style="font-size: 0.95rem; font-weight: 800; color: #F8FAFC;">🔍 FILTRI SCOUTING</div>
        <div style="font-size: 0.72rem; color: #64748B;">Trova e ordina i calciatori nel listone</div>
    </div>
    """, unsafe_allow_html=True)

    search_query = st.text_input("Ricerca", placeholder="Cerca giocatore o squadra...", label_visibility="collapsed")

    st.markdown('<div id="role-filter-anchor"></div>', unsafe_allow_html=True)
    
    selected_role = st.radio(
        "Seleziona Ruolo",
        ["Tutti", "P", "D", "C", "A"],
        horizontal=True,
        key="role_filter_btn"
    )

    squadre_raw = current_quot["squadra"].dropna().astype(str).str.strip().unique() if "squadra" in current_quot.columns else []
    squadre_list = ["Tutte"] + sorted(list(squadre_raw))

    c1, c2 = st.columns(2)
    with c1: selected_team = st.selectbox("Squadra", squadre_list, index=0)
    with c2: selected_sort = st.selectbox("Ordina per", ["👑 Indice Ranking", "⭐ Fantamedia", "🔤 Nome (A-Z)", "💰 Quotazione"], index=0)

    f1, f2 = st.columns([1.1, 1.9])
    with f1: only_titolari = st.checkbox("Solo Titolari", value=False)
    with f2: min_partite = st.slider("Partite minime", 0, 38, 0, step=1)

    st.markdown("<hr style='border-color: rgba(255,255,255,0.06); margin: 12px 0;'>", unsafe_allow_html=True)

    quot_view = summary_df.copy()

    if selected_role != "Tutti" and "ruolo" in quot_view.columns:
        quot_view = quot_view[quot_view["ruolo"].astype(str).str.upper().str.strip() == selected_role]
    if selected_team != "Tutte" and "squadra" in quot_view.columns:
        quot_view = quot_view[quot_view["squadra"].astype(str).str.upper().str.strip() == selected_team.upper().strip()]
    if search_query.strip():
        q = search_query.upper().strip()
        match_nome = quot_view["nome"].astype(str).str.upper().str.contains(q, na=False) if "nome" in quot_view.columns else False
        match_squadra = quot_view["squadra"].astype(str).str.upper().str.contains(q, na=False) if "squadra" in quot_view.columns else False
        quot_view = quot_view[match_nome | match_squadra]
    if only_titolari and "is_titolare" in quot_view.columns:
        quot_view = quot_view[quot_view["is_titolare"] == True]
    if min_partite > 0 and "presenze_totali" in quot_view.columns:
        quot_view = quot_view[quot_view["presenze_totali"] >= min_partite]

    if selected_sort == "👑 Indice Ranking":
        quot_view = quot_view.sort_values(by=["indice_finale", "quotazione_attuale", "nome"], ascending=[False, False, True], na_position="last")
    elif selected_sort == "⭐ Fantamedia":
        quot_view = quot_view.sort_values(by=["fantamedia", "presenze_totali", "nome"], ascending=[False, False, True], na_position="last")
    elif selected_sort == "🔤 Nome (A-Z)":
        quot_view = quot_view.sort_values(by=["nome"], ascending=[True], na_position="last")
    elif selected_sort == "💰 Quotazione":
        quot_view = quot_view.sort_values(by=["quotazione_attuale", "fvm", "nome"], ascending=[False, False, True], na_position="last")

    st.markdown(f"<div style='font-size: 0.75rem; color: #94A3B8; font-weight: 700; margin-bottom: 8px;'>ROSTER SELEZIONATO ({len(quot_view)})</div>", unsafe_allow_html=True)

    if quot_view.empty:
        st.info("Nessun giocatore trovato con questi filtri.")
        selected_id = None
    else:
        options_df = quot_view.drop_duplicates(subset="player_id").copy()
        labels, ids = [], []
        for row in options_df.itertuples():
            n = getattr(row, "nome", "Giocatore")
            s = getattr(row, "squadra", "-")
            pid = getattr(row, "player_id")
            r = getattr(row, "ruolo", "")
            ind = getattr(row, "indice_finale", None)
            fm = getattr(row, "fantamedia", None)

            if pd.notna(ind): lbl = f"{n} [{s}] • {r} | Ind: {float(ind):.1f}"
            elif pd.notna(fm): lbl = f"{n} [{s}] • {r} | FM: {float(fm):.2f}"
            else: lbl = f"{n} [{s}] • {r}"

            if lbl in labels: lbl = f"{lbl} #{int(pid)}"
            labels.append(lbl)
            ids.append(int(pid))

        label_to_id = dict(zip(labels, ids))
        radio_key = "roster_radio"
        prev_label = st.session_state.get(radio_key)
        if prev_label not in labels:
            default_idx = 0
            if "active_player_id" in st.session_state and st.session_state["active_player_id"] in ids:
                default_idx = ids.index(st.session_state["active_player_id"])
            st.session_state[radio_key] = labels[default_idx]

        # ==========================================
        # ROSTER SCROLLABILE
        # ==========================================
        st.markdown('<div id="roster-anchor"></div>', unsafe_allow_html=True)

        selected_label = st.radio(
            "Giocatori",
            options=labels,
            key=radio_key,
            label_visibility="collapsed"
        )

        selected_id = label_to_id.get(selected_label)

        # Mantiene il giocatore selezionato tra i rerun
        st.session_state["active_player_id"] = selected_id


# ------------------------------------------
# COLONNA DESTRA: DOSSIER ANALITICO
# ------------------------------------------
with col_dossier:
    if selected_id is None:
        st.info("👈 Seleziona un giocatore dalla lista a sinistra per aprire la scheda analitica.")
    else:
        player_id = int(float(selected_id))
        p_quotes = quot[quot["player_id"] == player_id].copy()
        current_quote = get_latest_quote_row(p_quotes)
        p_stats = df[df["player_id"] == player_id].copy()

        if current_quote is not None:
            nome = current_quote.get("nome", "Giocatore")
            ruolo = str(current_quote.get("ruolo", "-")).upper().strip()
            squadra = current_quote.get("squadra", "-")
        elif not p_stats.empty:
            nome = p_stats.iloc[-1].get("nome", "Giocatore")
            ruolo = str(p_stats.iloc[-1].get("ruolo", "-")).upper().strip()
            squadra = p_stats.iloc[-1].get("squadra", "-")
        else:
            nome, ruolo, squadra = "Giocatore", "-", "-"

        nome_upper, squadra_upper = str(nome).upper().strip(), str(squadra).upper().strip()
        ranking_row = get_player_ranking(ranking_df, player_id)
        rigor_info = rigoristi_df[(rigoristi_df["giocatore"] == nome_upper) & (rigoristi_df["squadra"] == squadra_upper)]
        titolare_info = titolari_df[(titolari_df["nome_giocatore"] == nome_upper) & (titolari_df["squadra"] == squadra_upper)]

        # --- GESTIONE TAG TITOLARITA E INFORTUNIO ---
        titolarita_val, infortunato_val, desc_infortunio = "", "", ""
        if not titolare_info.empty:
            t_row = titolare_info.iloc[0]
            titolarita_val = str(t_row.get("titolarita", "")).lower().strip()
            infortunato_val = str(t_row.get("infortunato", "")).lower().strip()
            desc_infortunio = str(t_row.get("desc_infortunio", "")).strip()

        tags_html = ""
        if "titolare" in titolarita_val:
            tags_html += '<span style="background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3); padding: 4px 10px; border-radius: 9999px; font-size: 0.72rem; font-weight: 700; text-transform: uppercase;">🟢 Titolare</span> '
        elif "panchina" in titolarita_val or "riserva" in titolarita_val:
            tags_html += '<span style="background: rgba(245, 158, 11, 0.15); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.3); padding: 4px 10px; border-radius: 9999px; font-size: 0.72rem; font-weight: 700; text-transform: uppercase;">🟠 Panchina</span> '
        
        if infortunato_val in ["sì", "si", "true", "1", "yes"]:
            tags_html += '<span style="background: rgba(239, 68, 68, 0.15); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.3); padding: 4px 10px; border-radius: 9999px; font-size: 0.72rem; font-weight: 700; text-transform: uppercase;">🚑 Infortunato</span> '

        desc_html = ""
        if desc_infortunio and desc_infortunio.lower() != "nan":
            desc_html = f'<div style="font-size: 0.8rem; color: #FCA5A5; margin-top: 8px; font-weight: 600; background: rgba(239, 68, 68, 0.1); padding: 6px 12px; border-radius: 6px; display: inline-block;">⚠️ {desc_infortunio}</div>'

        # --- METRICHE E ASTA ---
        rk_ruolo = int(ranking_row.get("rank_ruolo")) if ranking_row is not None and pd.notna(ranking_row.get("rank_ruolo")) else 1
        tot_ruolo = int(ranking_row.get("totale_ruolo")) if ranking_row is not None and pd.notna(ranking_row.get("totale_ruolo")) else 68
        quota_val = current_quote.get("quotazione_attuale", 38) if current_quote is not None else 38
        fvm_val = current_quote.get("fvm", 320) if current_quote is not None else 320

        st.markdown(f"""
        <div class="glass-panel" style="margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                <div style="display: flex; gap: 16px; align-items: center;">
                    <div style="width: 72px; height: 72px; border-radius: 50%; background: #1E293B; border: 2px solid #10B981; display: flex; align-items: center; justify-content: center; font-size: 2rem;">
                        👤
                    </div>
                    <div>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span class="badge-tier badge-role-{ruolo}">{ruolo} — {squadra}</span>
                        </div>
                        <div style="font-size: 1.8rem; font-weight: 800; color: #F8FAFC; margin-top: 4px; display: flex; align-items: center; gap: 10px;">
                            {nome} 
                            <div style="display: inline-flex; align-items: center; gap: 6px; margin-top: 2px;">{tags_html}</div>
                        </div>{desc_html}
                        <div style="font-size: 0.8rem; color: #94A3B8; display: flex; gap: 12px; margin-top: 6px;">
                            <span>🏆 Rank Ruolo: <b>#{rk_ruolo} / {tot_ruolo}</b></span>
                            <span>🎯 Rigorista: <b>{'Sì (#' + str(int(rigor_info['posizione'].values[0])) + ')' if not rigor_info.empty else 'No'}</b></span>
                        </div>
                    </div>
                </div>
                <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2); border-radius: 12px; padding: 12px 18px; text-align: right;">
                    <div style="font-size: 0.7rem; color: #34D399; font-weight: 700; letter-spacing: 0.05em;">VALUTAZIONE ASTA RECOMENDED</div>
                    <div style="font-size: 1.5rem; font-weight: 800; color: #F8FAFC; margin: 2px 0;">{fvm_val} <span style="font-size: 0.9rem; color: #94A3B8;">FM</span></div>
                    <div style="font-size: 0.72rem; color: #94A3B8;">Quotazione Listino: <b style="color: #F8FAFC;">{quota_val} FM</b></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if "stagione" in p_stats.columns: p_stats["stagione"] = p_stats["stagione"].astype(str).str.strip()
        if "giornata" in p_stats.columns: p_stats["giornata"] = pd.to_numeric(p_stats["giornata"], errors="coerce")
        p_stats = remove_starred_vote_rows(p_stats)

        if not p_stats.empty:
            p_stats = calculate_bonus_malus(p_stats)
            is_goalkeeper = (ruolo == "P")
            p_stats_hist = p_stats[p_stats["stagione"].astype(str).str.strip() != "2026-27"].copy() if "stagione" in p_stats.columns else p_stats.copy()
            if p_stats_hist.empty: p_stats_hist = p_stats.copy()

            rel = calculate_relative_metrics(p_stats_hist, is_goalkeeper=is_goalkeeper)
            media_voto = safe_mean(p_stats_hist, "voto")
            fantamedia = safe_mean(p_stats_hist, "fanta_voto_calcolato")
            varianza_bin = varianza_gol_binaria(p_stats_hist)
            varianza_v = safe_variance(p_stats_hist, "voto")

            # --- MATRICE KPI ---
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">Fantamedia Pesata</div>
                    <div class="kpi-value" style="color: #34D399;">{fantamedia:.2f}</div>
                    <div class="kpi-sub">Bonus/Malus Inclusi</div>
                </div>
                """, unsafe_allow_html=True)
            with k2:
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">Media Voto Pura</div>
                    <div class="kpi-value">{media_voto:.2f}</div>
                    <div class="kpi-sub">Stabilità Redazionale</div>
                </div>
                """, unsafe_allow_html=True)
            with k3:
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">% Presenze Medie</div>
                    <div class="kpi-value">{rel['presenza_pct']:.1f}%</div>
                    <div class="kpi-sub">{rel['presenze_medie']:.1f} P/Stagione</div>
                </div>
                """, unsafe_allow_html=True)
            with k4:
                val_label = "GS | RIG. PARATI MEDI" if is_goalkeeper else "GOL | ASSIST MEDI"
                val_num_1 = f"{rel['gs_stagione']:.1f}" if is_goalkeeper else f"{rel['gol_stagione']:.1f}"
                val_num_2 = f"{rel['rigori_parati']:.1f}" if is_goalkeeper else f"{rel['assist_stagione']:.1f}"
                
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">{val_label}</div>
                    <div class="kpi-value" style="color: #60A5FA;">{val_num_1} <span style="font-size: 1.15rem; color: #94A3B8; font-weight: 600;">| {val_num_2}</span></div>
                    <div class="kpi-sub">Media per stagione</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

            # --- SEZIONE CONTINUITÀ E RISCHIO ---
            r1, r2, r3, r4 = st.columns(4)
            with r1: st.metric("Varianza Voto", format_number(varianza_v), help="Valore < 0.5 indica altissima regolarità")
            with r2: st.metric("Varianza Gol", format_number(varianza_bin), help="Frequenza di bonus distribuiti")
            with r3: st.metric("Ammonizioni / Anno", f"{rel['ammonizioni']:.1f}")
            with r4: st.metric("Espulsioni / Anno", f"{rel['espulsioni']:.1f}")

            st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

            # --- GRAFICO TREND (ALTEZZA AUMENTATA E RANGE DINAMICO) ---
            st.markdown("""
            <div style="font-weight: 700; font-size: 1rem; color: #F8FAFC; margin-bottom: 8px;">
                📈 Trend di Forma (Rolling 5 Giornate)
            </div>
            """, unsafe_allow_html=True)

            rolling_df = build_rolling_data(p_stats, window=5)
            if not rolling_df.empty:
                fig = go.Figure()
                
                # Calcola dinamicamente il limite Y (Scala Minima 12.0)
                upper_y = 12.0
                if "media_mobile_fanta" in rolling_df.columns:
                    max_fanta = rolling_df["media_mobile_fanta"].max()
                    if pd.notna(max_fanta) and max_fanta > 11.0:
                        upper_y = max_fanta + 1.0

                if "media_mobile_fanta" in rolling_df.columns:
                    fig.add_trace(go.Scatter(x=rolling_df["periodo"], y=rolling_df["media_mobile_fanta"], mode="lines", name="Fantamedia (5G)", line=dict(color="#10B981", width=3, shape="spline"), fill="tozeroy", fillcolor="rgba(16, 185, 129, 0.08)", hovertemplate="<b>%{x}</b><br>Fantamedia: <b>%{y:.2f}</b><extra></extra>"))
                if "media_mobile_voto" in rolling_df.columns:
                    fig.add_trace(go.Scatter(x=rolling_df["periodo"], y=rolling_df["media_mobile_voto"], mode="lines", name="Media Voto (5G)", line=dict(color="#60A5FA", width=2, dash="dot", shape="spline"), hovertemplate="<b>%{x}</b><br>Media Voto: <b>%{y:.2f}</b><extra></extra>"))

                fig.add_hline(y=6.0, line_dash="dash", line_color="rgba(255,255,255,0.2)", annotation_text="Sufficienza", annotation_position="bottom right")

                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(17, 24, 39, 0.6)",
                    font=dict(family="Plus Jakarta Sans", color="#94A3B8"),
                    hovermode="x unified",
                    height=400,
                    margin=dict(l=10, r=10, t=30, b=10),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"),
                    xaxis=dict(gridcolor="rgba(255,255,255,0.05)", showgrid=True),
                    yaxis=dict(gridcolor="rgba(255,255,255,0.05)", showgrid=True, range=[4.0, upper_y]),
                )
                st.plotly_chart(fig, use_container_width=True)

            # --- TABELLA STORICO ---
            st.markdown("""
            <div style="font-weight: 700; font-size: 1rem; color: #F8FAFC; margin-top: 12px; margin-bottom: 8px;">
                📅 Storico Prestazioni per Stagione
            </div>
            """, unsafe_allow_html=True)

            if "stagione" in p_stats.columns:
                rows = []
                for s, g in p_stats.groupby("stagione"):
                    gfanta = calculate_fantavoto(g)
                    if is_goalkeeper:
                        rows.append({"Stagione": s, "Presenze": int(numeric_series(g, "voto").count()), "Media Voto": round(safe_mean(g, "voto"), 2), "Fantamedia": round(safe_mean(gfanta, "fanta_voto_calcolato"), 2), "Gol Subiti": int(safe_sum(g, "gs")), "Clean Sheet": (numeric_series(g, "gs") == 0).sum(), "Amm": int(safe_sum(g, "amm")), "Esp": int(safe_sum(g, "esp"))})
                    else:
                        rows.append({"Stagione": s, "Presenze": int(numeric_series(g, "voto").count()), "Media Voto": round(safe_mean(g, "voto"), 2), "Fantamedia": round(safe_mean(gfanta, "fanta_voto_calcolato"), 2), "Gol": int(safe_sum(g, "gf") + safe_sum(g, "rf")), "Assist": int(safe_sum(g, "ass")), "Amm": int(safe_sum(g, "amm")), "Esp": int(safe_sum(g, "esp"))})

                season_df = pd.DataFrame(rows)
                if not season_df.empty:
                    season_df["_sort"] = season_df["Stagione"].apply(season_sort_key)
                    season_df = season_df.sort_values("_sort", ascending=False).drop(columns="_sort")
                    st.dataframe(season_df, use_container_width=True, hide_index=True, column_config={"Fantamedia": st.column_config.NumberColumn(format="%.2f ⭐"), "Media Voto": st.column_config.NumberColumn(format="%.2f"), "Presenze": st.column_config.ProgressColumn(min_value=0, max_value=38, format="%d / 38")})
        else:
            st.info("Nessuna statistica storica disponibile per questo calciatore.")
