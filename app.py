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

# Dark theme + accent color are set natively via .streamlit/config.toml
# (see the file shipped alongside this script). The CSS below only
# restyles Streamlit's own native elements (st.metric, st.radio,
# st.container(border=True), inputs) — it never injects custom
# <div>/<span> markup, so there is nothing for it to conflict with.
#
# IMPORTANT: every line here is flush-left with no leading indentation.
# Streamlit's st.markdown() runs text through a CommonMark parser first;
# a line indented by 4+ spaces that follows a blank line is treated as
# an "indented code block" and rendered as literal text instead of CSS.
# Keeping this block unindented avoids that failure mode entirely.
_CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

:root {
  --bg:#0d1119; --panel:#151a24; --panel2:#1b202b; --panel3:#222834;
  --line:rgba(255,255,255,.075); --text:#e7ebf4; --muted:#8791a1;
  --green:#50e0a5; --orange:#ffb85c; --blue:#9db9ff; --red:#ff8e87;
}
html, body, [class*="css"], .stApp, [data-testid="stAppViewContainer"] {
  font-family:'Plus Jakarta Sans',sans-serif !important;
  background:var(--bg) !important; color:var(--text) !important;
}
[data-testid="stHeader"] { background:var(--bg) !important; }
[data-testid="stAppViewBlockContainer"] { max-width:1600px !important; padding:14px 18px 28px !important; }
[data-testid="stVerticalBlock"] { gap:.42rem !important; }
[data-testid="stHorizontalBlock"] { gap:.65rem !important; align-items:flex-start !important; }
[data-testid="stVerticalBlockBorderWrapper"] {
  background:var(--panel) !important; border:1px solid var(--line) !important;
  border-radius:10px !important; box-shadow:none !important;
}
hr { margin:5px 0 !important; border-color:var(--line) !important; }
h1 { font-size:1.45rem !important; line-height:1.1 !important; margin:0 !important; }
h2 { font-size:1.12rem !important; margin:0 !important; }
h3 { font-size:.92rem !important; margin:.15rem 0 !important; }
p { line-height:1.35 !important; }
[data-testid="stCaptionContainer"] { color:var(--muted) !important; font-size:.66rem !important; }

/* Top status bar */
.st-key-topbar [data-testid="stVerticalBlockBorderWrapper"] { background:#10151e !important; border-radius:8px !important; }
.st-key-topbar p { font-size:.61rem !important; text-transform:uppercase; letter-spacing:.04em; }

/* Inputs */
.stTextInput input, .stSelectbox [data-baseweb="select"] {
  background:#10151e !important; color:var(--text) !important; border:1px solid var(--line) !important;
  border-radius:7px !important; min-height:32px !important; font-size:.72rem !important;
}
[data-testid="stWidgetLabel"] p { color:#8f99a9 !important; font-size:.60rem !important; font-weight:700 !important; text-transform:uppercase; letter-spacing:.06em; }
.stSlider [data-baseweb="slider"] { padding-top:0 !important; }

/* Role chips */
.st-key-role_filter_radio div[role="radiogroup"] { display:grid !important; grid-template-columns:repeat(5,1fr); gap:4px !important; }
.st-key-role_filter_radio label { background:#10151e !important; border:1px solid var(--line) !important; border-radius:7px !important; padding:5px 2px !important; min-height:42px !important; }
.st-key-role_filter_radio label:has(input:checked) { background:rgba(80,224,165,.12) !important; border-color:var(--green) !important; box-shadow:0 0 14px rgba(80,224,165,.12); }
.st-key-role_filter_radio label p { font-size:.58rem !important; line-height:1.05 !important; }

/* Player list */
.st-key-player_radio div[role="radiogroup"] {
  display:flex !important; flex-direction:column !important; gap:4px !important;
  max-height:600px !important; overflow-y:auto !important; overflow-x:hidden !important;
  background:#10151e !important; border:1px solid var(--line) !important; border-radius:9px !important; padding:5px !important;
}
.st-key-player_radio label { display:flex !important; width:100% !important; background:#171c26 !important; border:1px solid transparent !important; border-radius:7px !important; padding:6px 8px !important; margin:0 !important; }
.st-key-player_radio label:hover { background:#202631 !important; border-color:rgba(80,224,165,.25) !important; }
.st-key-player_radio label:has(input:checked) { background:rgba(80,224,165,.12) !important; border-color:var(--green) !important; }
.st-key-player_radio label > div:first-child, .st-key-player_radio input { display:none !important; }
.st-key-player_radio label p { font-size:.62rem !important; line-height:1.25 !important; margin:0 !important; }
.st-key-player_radio label code { font-size:.52rem !important; padding:1px 4px !important; }

/* Metrics */
[data-testid="stMetric"] { background:#171c26 !important; border:1px solid var(--line) !important; border-radius:9px !important; padding:9px 11px !important; min-height:72px !important; }
[data-testid="stMetricLabel"] p { color:#8993a3 !important; font-size:.58rem !important; text-transform:uppercase; font-weight:700 !important; letter-spacing:.04em; }
[data-testid="stMetricValue"] { color:var(--text) !important; font-size:1.18rem !important; font-weight:800 !important; line-height:1.1 !important; }
[data-testid="stMetricDelta"] { font-size:.58rem !important; }
[data-testid="stProgress"] { margin-top:4px !important; height:4px !important; }
[data-testid="stProgress"] > div > div { border-radius:99px !important; }
.st-key-kpi_fantamedia [data-testid="stMetricValue"] { color:var(--green) !important; }
.st-key-kpi_voto [data-testid="stMetricValue"] { color:var(--blue) !important; }
.st-key-kpi_presenze [data-testid="stMetricValue"] { color:var(--orange) !important; }
.st-key-kpi_gol [data-testid="stMetricValue"] { color:var(--red) !important; }
.st-key-kpi_fantamedia [data-testid="stProgress"] > div > div { background:var(--green) !important; }
.st-key-kpi_voto [data-testid="stProgress"] > div > div { background:var(--blue) !important; }
.st-key-kpi_presenze [data-testid="stProgress"] > div > div { background:var(--orange) !important; }
.st-key-kpi_gol [data-testid="stProgress"] > div > div { background:var(--red) !important; }

/* Hero auction card */
.st-key-hero_card [data-testid="stVerticalBlockBorderWrapper"] { background:linear-gradient(145deg,#1b202b,#151a24) !important; border-color:rgba(255,184,92,.18) !important; }
.st-key-hero_card [data-testid="stMetric"] { min-height:76px !important; background:#10151e !important; }
.st-key-hero_card [data-testid="stMetricValue"] { color:var(--orange) !important; font-size:1.32rem !important; }

/* Detail header */
.st-key-detail_header [data-testid="stVerticalBlockBorderWrapper"] { background:linear-gradient(145deg,#18202a,#141923) !important; }
.st-key-detail_header h1 { font-size:1.42rem !important; }

/* Section cards */
.st-key-section_card [data-testid="stVerticalBlockBorderWrapper"] { padding:10px !important; }

/* Tables */
[data-testid="stDataFrame"] { border:1px solid var(--line) !important; border-radius:8px !important; overflow:hidden !important; }

/* Buttons */
button[kind="secondary"] { border-color:var(--line) !important; background:#171c26 !important; }

::-webkit-scrollbar { width:5px; height:5px; }
::-webkit-scrollbar-thumb { background:#303746; border-radius:99px; }
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
    return pd.DataFrame(
        fetch_all_rows("player_stats_history")
    )


@st.cache_data(ttl=600)
def load_quotazioni():
    return pd.DataFrame(
        fetch_all_rows("giocatori_quotazioni")
    )


# ==========================================
# NUOVO V3.1
# Ranking Asta
# ==========================================

@st.cache_data(ttl=600)
def load_ranking():
    try:
        return pd.DataFrame(
            fetch_all_rows("player_ranking")
        )
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def load_rigoristi():

    url = (
        "https://raw.githubusercontent.com/"
        "fanta-ai-coder/fanta-ai-etl/"
        "refs/heads/main/rigoristi.csv"
    )

    try:
        df = pd.read_csv(url)

        df["giocatore"] = (
            df["giocatore"]
            .astype(str)
            .str.upper()
            .str.strip()
        )

        df["squadra"] = (
            df["squadra"]
            .astype(str)
            .str.upper()
            .str.strip()
        )

        return df

    except Exception:
        return pd.DataFrame(
            columns=[
                "giocatore",
                "squadra",
                "posizione",
            ]
        )


@st.cache_data(ttl=600)
def load_punizioni():

    url = (
        "https://raw.githubusercontent.com/"
        "fanta-ai-coder/fanta-ai-etl/"
        "refs/heads/main/punizioni.csv"
    )

    try:
        df = pd.read_csv(url)

        df["giocatore"] = (
            df["giocatore"]
            .astype(str)
            .str.upper()
            .str.strip()
        )

        df["squadra"] = (
            df["squadra"]
            .astype(str)
            .str.upper()
            .str.strip()
        )

        return df

    except Exception:
        return pd.DataFrame(
            columns=[
                "giocatore",
                "squadra",
                "posizione",
            ]
        )


@st.cache_data(ttl=300)
def load_titolari_infortuni():

    url = (
        "https://raw.githubusercontent.com/"
        "fanta-ai-coder/fanta-ai-etl/"
        "refs/heads/main/titolari_infortuni"
    )

    try:
        df = pd.read_csv(url)

        df["nome_giocatore"] = (
            df["nome_giocatore"]
            .astype(str)
            .str.upper()
            .str.strip()
        )

        df["squadra"] = (
            df["squadra"]
            .astype(str)
            .str.upper()
            .str.strip()
        )

        df["titolarita"] = (
            df["titolarita"]
            .astype(str)
            .str.lower()
            .str.strip()
        )

        df["squalificato"] = (
            df["squalificato"]
            .astype(str)
            .str.lower()
            .str.strip()
        )

        df["infortunato"] = (
            df["infortunato"]
            .astype(str)
            .str.lower()
            .str.strip()
        )

        df["desc_infortunio"] = (
            df["desc_infortunio"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        return df

    except Exception:
        return pd.DataFrame(
            columns=[
                "nome_giocatore",
                "squadra",
                "titolarita",
                "squalificato",
                "infortunato",
                "desc_infortunio",
            ]
        )


rigoristi_df = load_rigoristi()
punizioni_df = load_punizioni()
titolari_df = load_titolari_infortuni()


# ==========================================
# 3. STATISTICAL UTILITIES
# ==========================================

def normalize_player_id_series(series):

    numeric = pd.to_numeric(
        series,
        errors="coerce"
    )

    return numeric.round().astype("Int64")


def normalize_dataframe(df):

    if df.empty:
        return df.copy()

    result = df.copy()

    if "player_id" in result.columns:
        result["player_id"] = normalize_player_id_series(
            result["player_id"]
        )

    return result


def numeric_series(df, column):

    if column not in df.columns:
        return pd.Series(
            float("nan"),
            index=df.index,
            dtype="float64"
        )

    return pd.to_numeric(
        df[column],
        errors="coerce"
    )


def safe_sum(df, column):

    if column not in df.columns:
        return 0.0

    return float(
        numeric_series(df, column)
        .fillna(0)
        .sum()
    )


def safe_mean(df, column):

    if column not in df.columns:
        return 0.0

    values = (
        numeric_series(df, column)
        .dropna()
    )

    return (
        float(values.mean())
        if not values.empty
        else 0.0
    )


def safe_variance(df, column):

    if column not in df.columns:
        return None

    values = (
        numeric_series(df, column)
        .dropna()
    )

    if len(values) < 2:
        return None

    val = values.var(ddof=1)

    return (
        None
        if pd.isna(val)
        else float(val)
    )


def format_number(value, decimals=2):

    if value is None or pd.isna(value):
        return "N/D"

    return f"{value:.{decimals}f}"


def remove_starred_vote_rows(df):

    if df.empty or "voto" not in df.columns:
        return df.copy()

    raw_vote = (
        df["voto"]
        .astype(str)
        .str.strip()
    )

    starred = raw_vote.str.contains(
        r"\*",
        regex=True,
        na=False
    )

    return (
        df.loc[~starred].copy()
        if starred.any()
        else df.copy()
    )


def calculate_fantavoto(df):

    result = df.copy()

    if "voto" not in result.columns:
        result["fanta_voto_calcolato"] = float("nan")
        return result

    voto = numeric_series(
        result,
        "voto"
    ).fillna(0)

    gf = numeric_series(
        result,
        "gf"
    ).fillna(0)

    ass = numeric_series(
        result,
        "ass"
    ).fillna(0)

    rf = numeric_series(
        result,
        "rf"
    ).fillna(0)

    au = numeric_series(
        result,
        "au"
    ).fillna(0)

    esp = numeric_series(
        result,
        "esp"
    ).fillna(0)

    amm = numeric_series(
        result,
        "amm"
    ).fillna(0)

    clean_sheet = pd.Series(
        0.0,
        index=result.index
    )

    penalty_saved = pd.Series(
        0.0,
        index=result.index
    )

    gol_subiti = pd.Series(
        0.0,
        index=result.index
    )

    for c in [
        "pi",
        "porta_inviolata",
        "clean_sheet",
        "imbattuto"
    ]:

        if c in result.columns:
            clean_sheet = (
                numeric_series(result, c)
                .fillna(0)
            )
            break

    for c in [
        "rp",
        "rigori_parati",
        "rigore_parato"
    ]:

        if c in result.columns:
            penalty_saved = (
                numeric_series(result, c)
                .fillna(0)
            )
            break

    for c in [
        "gs",
        "gol_subiti"
    ]:

        if c in result.columns:
            gol_subiti = (
                numeric_series(result, c)
                .fillna(0)
            )
            break

    if "ruolo" in result.columns:

        is_p = (
            result["ruolo"]
            .astype(str)
            .str.strip()
            .str.upper()
            .eq("P")
        )

        clean_sheet = clean_sheet.where(
            is_p,
            0
        )

        gol_subiti = gol_subiti.where(
            is_p,
            0
        )

    result["fanta_voto_calcolato"] = (
        voto
        + (gf * 3)
        + ass
        + (rf * 3)
        - (au * 2)
        - esp
        - (amm * 0.5)
        + clean_sheet
        + (penalty_saved * 3)
        - gol_subiti
    )

    result.loc[
        numeric_series(
            result,
            "voto"
        ).isna(),
        "fanta_voto_calcolato"
    ] = float("nan")

    return result


def calculate_bonus_malus(df):

    res = calculate_fantavoto(df)

    res["bonus_malus"] = (
        res["fanta_voto_calcolato"]
        - numeric_series(res, "voto")
    )

    return res


def calculate_relative_metrics(
    p_stats,
    is_goalkeeper=False
):

    seasons = (
        p_stats["stagione"]
        .dropna()
        .astype(str)
        .str.strip()
        .nunique()
        if "stagione" in p_stats.columns
        else 0
    )

    if seasons <= 0:

        return {
            "stagioni": 0,
            "presenze_medie": 0.0,
            "presenza_pct": 0.0,
            "gol_stagione": 0.0,
            "assist_stagione": 0.0,
            "rigori_segnati": 0.0,
            "rigori_sbagliati": 0.0,
            "ammonizioni": 0.0,
            "espulsioni": 0.0,
            "gs_stagione": 0.0,
            "rigori_parati": 0.0,
        }

    presenze_totali = (
        numeric_series(
            p_stats,
            "voto"
        ).count()
    )

    presenze_medie = (
        presenze_totali / seasons
    )

    presenza_pct = min(
        100.0,
        (presenze_medie / 38) * 100
    )

    if is_goalkeeper:

        gs_tot = safe_sum(
            p_stats,
            "gs"
        )

        rp_tot = safe_sum(
            p_stats,
            "rp"
        )

        gf_tot = 0
        rf_tot = 0

    else:

        gf_tot = (
            safe_sum(p_stats, "gf")
            + safe_sum(p_stats, "rf")
        )

        rf_tot = safe_sum(
            p_stats,
            "rf"
        )

        gs_tot = 0
        rp_tot = 0

    return {
        "stagioni": seasons,
        "presenze_medie": presenze_medie,
        "presenza_pct": presenza_pct,
        "assist_stagione": safe_sum(
            p_stats,
            "ass"
        ) / seasons,
        "rigori_sbagliati": safe_sum(
            p_stats,
            "rs"
        ) / seasons,
        "ammonizioni": safe_sum(
            p_stats,
            "amm"
        ) / seasons,
        "espulsioni": safe_sum(
            p_stats,
            "esp"
        ) / seasons,
        "gol_stagione": gf_tot / seasons,
        "rigori_segnati": rf_tot / seasons,
        "gs_stagione": gs_tot / seasons,
        "rigori_parati": rp_tot / seasons,
    }


def varianza_gol_binaria(p_stats):

    if (
        p_stats.empty
        or "giornata" not in p_stats.columns
    ):
        return 0.0

    gol_g = (
        p_stats
        .groupby("giornata")
        .apply(
            lambda df:
            1
            if (
                safe_sum(df, "gf")
                + safe_sum(df, "rf")
            ) > 0
            else 0
        )
    )

    return (
        0.0
        if len(gol_g) <= 1
        else float(gol_g.var(ddof=1))
    )


def season_sort_key(value):

    try:
        return int(
            str(value)
            .strip()
            .split("/")[0]
        )

    except Exception:
        return -1


def build_rolling_data(
    player_stats,
    window=5
):

    if (
        player_stats.empty
        or any(
            c not in player_stats.columns
            for c in [
                "stagione",
                "giornata"
            ]
        )
    ):
        return pd.DataFrame()

    res = player_stats.copy()

    res["giornata"] = pd.to_numeric(
        res["giornata"],
        errors="coerce"
    )

    res = res[
        res["giornata"].notna()
    ].copy()

    if res.empty:
        return pd.DataFrame()

    res["giornata"] = (
        res["giornata"]
        .astype(int)
    )

    res["stagione"] = (
        res["stagione"]
        .astype(str)
        .str.strip()
    )

    res["_season_sort"] = (
        res["stagione"]
        .apply(season_sort_key)
    )

    res = (
        res
        .sort_values(
            [
                "_season_sort",
                "giornata"
            ]
        )
        .reset_index(drop=True)
    )

    res = calculate_fantavoto(res)

    if "voto" in res.columns:

        res["voto"] = pd.to_numeric(
            res["voto"],
            errors="coerce"
        )

        res["media_mobile_voto"] = (
            res
            .groupby(
                "stagione",
                sort=False
            )["voto"]
            .transform(
                lambda x:
                x.rolling(
                    window=window,
                    min_periods=1
                ).mean()
            )
        )

    res["media_mobile_fanta"] = (
        res
        .groupby(
            "stagione",
            sort=False
        )["fanta_voto_calcolato"]
        .transform(
            lambda x:
            x.rolling(
                window=window,
                min_periods=1
            ).mean()
        )
    )

    res["periodo"] = (
        res["stagione"]
        + " G"
        + res["giornata"].astype(str)
    )

    return res


def get_latest_season(df):

    if (
        df.empty
        or "stagione" not in df.columns
    ):
        return None

    seasons = (
        df["stagione"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    seasons = seasons[
        seasons != ""
    ]

    return (
        max(
            seasons.unique(),
            key=season_sort_key
        )
        if not seasons.empty
        else None
    )


def get_latest_quote_row(player_quotes):

    if player_quotes.empty:
        return None

    res = player_quotes.copy()

    if "stagione" in res.columns:

        res["_season_sort"] = (
            res["stagione"]
            .apply(season_sort_key)
        )

        res = (
            res
            .sort_values("_season_sort")
        )

    return res.iloc[-1]


# ==========================================
# NUOVO V3.1
# Recupero ranking giocatore
# ==========================================

def get_player_ranking(
    ranking_df,
    player_id,
    stagione=None
):

    if ranking_df.empty:
        return None

    if "player_id" not in ranking_df.columns:
        return None

    ranking = ranking_df.copy()

    ranking["player_id"] = normalize_player_id_series(
        ranking["player_id"]
    )

    try:
        pid = int(float(player_id))
    except Exception:
        return None

    ranking = ranking[
        ranking["player_id"] == pid
    ].copy()

    if ranking.empty:
        return None

    # Prima prova: stagione corrente
    if stagione is not None and "stagione" in ranking.columns:

        current = ranking[
            ranking["stagione"]
            .astype(str)
            .str.strip()
            == str(stagione).strip()
        ].copy()

        if not current.empty:
            ranking = current

    # Se non disponibile, prende l'ultima versione
    if len(ranking) > 1:

        if "calculated_at" in ranking.columns:

            ranking["calculated_at"] = pd.to_datetime(
                ranking["calculated_at"],
                errors="coerce"
            )

            ranking = (
                ranking
                .sort_values(
                    "calculated_at"
                )
            )

        elif "stagione" in ranking.columns:

            ranking["_season_sort"] = (
                ranking["stagione"]
                .apply(season_sort_key)
            )

            ranking = (
                ranking
                .sort_values(
                    "_season_sort"
                )
            )

    return ranking.iloc[-1]



# ==========================================
# PRECALCOLO METRICHE & SUMMARY GIOCATORI
# ==========================================

@st.cache_data(ttl=600)
def compute_player_summaries(stats_df, quot_df, ranking_df, titolari_df):
    """
    Combina quotazioni, ranking e statistiche storiche aggregate
    per consentire filtraggio per squadra/titolari/partite e ordinamento
    per Indice Ranking o Fantamedia in tempo reale.
    """
    if quot_df.empty:
        return quot_df.copy()

    base = quot_df.copy()
    base["player_id"] = normalize_player_id_series(base["player_id"])

    # 1. Unione con tabella ranking
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
        base["is_titolare"] = (
            base["titolarita"]
            .astype(str)
            .str.lower()
            .str.strip()
            == "titolare"
        )
    else:
        base["is_titolare"] = False

    # 3. Aggregazione storico voti e fantamedia
    if not stats_df.empty and "player_id" in stats_df.columns:
        sdf = stats_df.copy()
        sdf["player_id"] = normalize_player_id_series(sdf["player_id"])

        if "stagione" in sdf.columns:
            sdf_hist = sdf[
                sdf["stagione"].astype(str).str.strip() != "2026-27"
            ].copy()
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
            voto
            + (gf * 3)
            + ass
            + (rf * 3)
            - (au * 2)
            - esp
            - (amm * 0.5)
            + clean_sheet
            + (rp * 3)
            - gs
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
# 4. REUSABLE UI COMPONENTS
# ==========================================

ROLE_COLORS = {

    "P": {
        "bg": "rgba(255, 185, 95, 0.15)",
        "text": "#FFB95F",
        "border": "rgba(255, 185, 95, 0.4)",
        "label": "Portiere",
    },

    "D": {
        "bg": "rgba(173, 198, 255, 0.15)",
        "text": "#ADC6FF",
        "border": "rgba(173, 198, 255, 0.4)",
        "label": "Difensore",
    },

    "C": {
        "bg": "rgba(78, 222, 163, 0.15)",
        "text": "#4EDEA3",
        "border": "rgba(78, 222, 163, 0.4)",
        "label": "Centrocampista",
    },

    "A": {
        "bg": "rgba(255, 180, 171, 0.15)",
        "text": "#FFB4AB",
        "border": "rgba(255, 180, 171, 0.4)",
        "label": "Attaccante",
    },
}

# Colori nativi supportati dal markdown di Streamlit (":red[testo]" ecc.),
# usati per colorare i badge di ruolo senza CSS posizionale: P=arancio,
# D=blu, C=verde, A=rosso — coerenti con la palette del mockup.
ROLE_MD_COLOR = {
    "P": "orange",
    "D": "blue",
    "C": "green",
    "A": "red",
}


def role_badge_md(ruolo):
    """Badge di ruolo colorato in Markdown nativo (nessun HTML custom)."""
    r = str(ruolo).upper().strip()
    color = ROLE_MD_COLOR.get(r)
    return f":{color}[**{r}**]" if color else f"**{r}**"


def render_section_header(title, subtitle=None):
    """Native replacement for the old custom HTML section header."""
    st.subheader(title)
    if subtitle:
        st.caption(subtitle)


def render_kpi_card(
    title,
    value,
    subtext="",
    highlight=False,
    icon="",
    progress=None,
    key=None,
):
    """KPI card nativa con icona, metrica e barra di progresso opzionale
    (colorata via CSS in base alla `key`, vedi .st-key-kpi_* nel CSS)."""
    with st.container(border=True, key=key):
        label = f"{icon} {title}".strip() if icon else title
        if highlight:
            label = "⭐ " + label
        st.metric(label=label, value=value)
        if subtext:
            st.caption(subtext)
        if progress is not None:
            st.progress(max(0.0, min(float(progress), 1.0)))


def risk_badge_md(varianza_v):
    """Etichetta di rischio (colore nativo) dedotta dalla varianza voto."""
    if varianza_v is None:
        return ":gray[**Rischio N/D**]"
    if varianza_v < 0.5:
        return ":green[**Basso Rischio**]"
    if varianza_v < 1.0:
        return ":orange[**Rischio Medio**]"
    return ":red[**Rischio Alto**]"


def format_ranking_badge(ranking):
    """Indice ranking, da mostrare inline accanto al nome del giocatore
    (unica fonte del dato: non viene più replicato nella card a destra)."""
    if ranking is None:
        return None
    indice_finale = ranking.get("indice_finale")
    if indice_finale is None or pd.isna(indice_finale):
        return None
    return f":orange[👑 {float(indice_finale):.1f}]"


def ranking_tier_label(indice_finale):
    """Fascia di merito dedotta dall'Indice Ranking (0-100), per dare un
    colpo d'occhio immediato sul valore del giocatore in asta."""
    if indice_finale is None or pd.isna(indice_finale):
        return None
    v = float(indice_finale)
    if v >= 90:
        return ":green[**TIER S+ · MUST-BUY**]"
    if v >= 80:
        return ":green[**TIER S · TOP TARGET**]"
    if v >= 65:
        return ":orange[**TIER A · SOLIDO**]"
    if v >= 45:
        return ":blue[**TIER B · ROTAZIONE**]"
    return ":gray[**TIER C · SCOMMESSA**]"


# ==========================================
# CARD ASTA V3.1
# ==========================================

def render_quote_hero_card(quota, fvm):
    """Solo Quotazione e FVM: le due cifre che servono al volo durante
    l'asta. Il ranking (indice) vive ora accanto al nome del giocatore,
    quindi non viene più replicato qui."""

    with st.container(border=True, key="hero_card"):
        st.caption("💰 VALUTAZIONE ASTA")

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Quotazione", f"{quota} FM")
        with c2:
            st.metric("FVM Consigliato", f"{fvm} FM")


# ==========================================
# 5. PLAYER DETAIL VIEW
# ==========================================

def render_player_detail(
    player_id,
    stats,
    quotations,
    ranking_df
):

    try:

        player_id = int(
            float(player_id)
        )

    except Exception:

        st.error(
            f"Player ID non valido: {player_id}"
        )

        return

    # --------------------------------------
    # Quotazioni
    # --------------------------------------

    p_quotes = quotations[
        quotations["player_id"]
        == player_id
    ].copy()

    current_quote = get_latest_quote_row(
        p_quotes
    )

    # --------------------------------------
    # Stats
    # --------------------------------------

    p_stats = stats[
        stats["player_id"]
        == player_id
    ].copy()

    # --------------------------------------
    # Informazioni giocatore
    # --------------------------------------

    if current_quote is not None:

        nome = current_quote.get(
            "nome",
            "Giocatore"
        )

        ruolo = str(
            current_quote.get(
                "ruolo",
                "-"
            )
        ).upper().strip()

        squadra = current_quote.get(
            "squadra",
            "-"
        )

    elif not p_stats.empty:

        nome = p_stats.iloc[-1].get(
            "nome",
            "Giocatore"
        )

        ruolo = str(
            p_stats.iloc[-1].get(
                "ruolo",
                "-"
            )
        ).upper().strip()

        squadra = p_stats.iloc[-1].get(
            "squadra",
            "-"
        )

    else:

        nome = "Giocatore"
        ruolo = "-"
        squadra = "-"

    nome_upper = (
        str(nome)
        .upper()
        .strip()
    )

    squadra_upper = (
        str(squadra)
        .upper()
        .strip()
    )

    # --------------------------------------
    # Ranking V3.1
    # --------------------------------------

    ranking_row = get_player_ranking(
        ranking_df,
        player_id
    )

    # --------------------------------------
    # Lookup dati aggiuntivi
    # --------------------------------------

    rigor_info = rigoristi_df[
        (
            rigoristi_df["giocatore"]
            == nome_upper
        )
        &
        (
            rigoristi_df["squadra"]
            == squadra_upper
        )
    ]

    puniz_info = punizioni_df[
        (
            punizioni_df["giocatore"]
            == nome_upper
        )
        &
        (
            punizioni_df["squadra"]
            == squadra_upper
        )
    ]

    titolare_info = titolari_df[
        (
            titolari_df["nome_giocatore"]
            == nome_upper
        )
        &
        (
            titolari_df["squadra"]
            == squadra_upper
        )
    ]

    role_meta = ROLE_COLORS.get(
        ruolo,
        {"label": ruolo}
    )

    # --------------------------------------
    # Tag informativi (ruolo, squadra, rigorista, punizioni)
    # --------------------------------------

    tags = [
        f"{role_badge_md(ruolo)} — {role_meta['label']}",
        f"🛡️ {squadra}",
    ]

    if not rigor_info.empty:
        pos_r = int(rigor_info["posizione"].values[0])
        tags.append(f"🎯 Rigorista #{pos_r}")

    if not puniz_info.empty:
        pos_p = int(puniz_info["posizione"].values[0])
        tags.append(f"⚡ Punizioni #{pos_p}")

    # --------------------------------------
    # Stato giocatore (titolare / infortunato / squalificato / panchina)
    # --------------------------------------

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
            # "##" = titolo grande: stato più critico, massima visibilità
            status_text = " 🟥 Squalificato"

        elif infortunato == "si":
            desc_short = (
                ("  \n" + desc[:80] + ("…" if len(desc) > 80 else ""))
                if desc else ""
            )
            status_kind = "warning"
            # "##" per il titolo, descrizione su riga separata in testo normale
            status_text = f" 🤕 Infortunato{desc_short}"

        elif tit == "titolare":
            status_kind = "info"
            # "###" = titolo medio: informazione positiva ma meno urgente
            status_text = " ✅ Titolare"

        elif tit == "panchina":
            status_kind = "info"
            # solo grassetto: informazione meno critica, testo normale
            status_text = "**🪑 Panchina**"

    # --------------------------------------
    # HEADER
    # --------------------------------------

    header_col1, header_col2 = st.columns([2.5, 1.5])

    with header_col1:

        # Badge Indice Ranking + Tier, sopra al nome (come nel mockup):
        # unica fonte del dato, non replicato altrove nella pagina.
        ind_val = (
            ranking_row.get("indice_finale")
            if ranking_row is not None
            else None
        )
        rank_badge = format_ranking_badge(ranking_row)
        tier_badge = ranking_tier_label(ind_val)
        badge_line = "&nbsp;&nbsp;".join(
            b for b in [rank_badge, tier_badge] if b
        )
        if badge_line:
            st.markdown(badge_line)

        st.header(nome)
        st.write(" &nbsp;|&nbsp; ".join(tags))

        # st.error/warning/success/info interpretano il Markdown nel testo:
        # "##"/"###" produce un titolo più grande, utile per dare più
        # risalto agli stati critici (squalificato/infortunato) rispetto
        # a quelli neutri (panchina).
        if status_kind == "error":
            st.error(status_text)
        elif status_kind == "warning":
            st.warning(status_text)
        elif status_kind == "success":
            st.success(status_text)
        elif status_kind == "info":
            st.markdown(status_text)

    with header_col2:

        quota_val = (
            current_quote.get("quotazione_attuale", "-")
            if current_quote is not None
            else "-"
        )

        fvm_val = (
            current_quote.get("fvm", "-")
            if current_quote is not None
            else "-"
        )

        render_quote_hero_card(
            quota_val,
            fvm_val,
        )

    # --------------------------------------
    # Nessuna statistica
    # --------------------------------------

    if p_stats.empty:

        (
            "ℹ️ Nessuna statistica storica disponibile per questo giocatore."
        )

        return

    # --------------------------------------
    # Normalizzazione stats
    # --------------------------------------

    if "stagione" in p_stats.columns:

        p_stats["stagione"] = (
            p_stats["stagione"]
            .astype(str)
            .str.strip()
        )

    if "giornata" in p_stats.columns:

        p_stats["giornata"] = pd.to_numeric(
            p_stats["giornata"],
            errors="coerce"
        )

    p_stats = remove_starred_vote_rows(
        p_stats
    )

    if p_stats.empty:

        (
            "ℹ️ Nessuna prestazione valida registrata."
        )

        return

    p_stats = calculate_bonus_malus(
        p_stats
    )

    is_goalkeeper = (
        ruolo == "P"
    )

    # ======================================
    # Escludi stagione corrente 2026-27
    # ======================================

    p_stats_hist = (
        p_stats[
            p_stats["stagione"]
            .astype(str)
            .str.strip()
            != "2026-27"
        ].copy()
        if "stagione" in p_stats.columns
        else p_stats.copy()
    )

    if p_stats_hist.empty:
        p_stats_hist = p_stats.copy()

    # ======================================
    # RENDIMENTO
    # ======================================

    render_section_header(
        "📊 Rendimento Complessivo",
        "Medie pesate e metriche chiave calcolate sulle stagioni concluse"
    )

    rel = calculate_relative_metrics(
        p_stats_hist,
        is_goalkeeper=is_goalkeeper
    )

    media_voto = safe_mean(
        p_stats_hist,
        "voto"
    )

    fantamedia = safe_mean(
        p_stats_hist,
        "fanta_voto_calcolato"
    )

    varianza_bin = varianza_gol_binaria(
        p_stats_hist
    )

    varianza_v = safe_variance(
        p_stats_hist,
        "voto"
    )

    # ======================================
    # KPI
    # ======================================

    k1, k2, k3, k4 = st.columns(4)

    with k1:

        render_kpi_card(
            "Fantamedia",
            f"{fantamedia:.2f}",
            "Bonus/Malus inclusi",
            highlight=True,
            icon="📈",
            progress=fantamedia / 12,
            key="kpi_fantamedia",
        )

    with k2:

        render_kpi_card(
            "Media Voto Pura",
            f"{media_voto:.2f}",
            "Stabilità redazionale",
            icon="🎯",
            progress=media_voto / 10,
            key="kpi_voto",
        )

    with k3:

        render_kpi_card(
            "% Presenze",
            f"{rel['presenza_pct']:.1f}%",
            f"{rel['presenze_medie']:.1f} partite / anno",
            icon="🏃",
            progress=rel['presenza_pct'] / 100,
            key="kpi_presenze",
        )

    with k4:

        if is_goalkeeper:

            render_kpi_card(
                "Media GS / Stagione",
                f"{rel['gs_stagione']:.2f}",
                highlight=True,
                icon="🧤",
                key="kpi_gol",
            )

        else:

            render_kpi_card(
                "Gol Medi / Anno",
                f"{rel['gol_stagione']:.1f}",
                f"👟 {rel['assist_stagione']:.1f} assist medi",
                icon="⚽",
                progress=rel['gol_stagione'] / 30,
                key="kpi_gol",
            )

    # ======================================
    # PORTIERI
    # ======================================

    if is_goalkeeper:

        var_col1, var_col2, var_col3 = st.columns(3)

        varianza_gs = safe_variance(
            p_stats_hist,
            "gs"
        )

        totale_presenze = (
            numeric_series(
                p_stats_hist,
                "voto"
            ).count()
        )

        media_clean_sheet = (
            (
                numeric_series(
                    p_stats_hist,
                    "gs"
                ) == 0
            ).sum()
            / totale_presenze
            * 100
            if totale_presenze > 0
            else 0
        )

        with var_col1:

            render_kpi_card(
                "Varianza GS / Partita",
                format_number(
                    varianza_gs
                ),
                icon="📉",
            )

        with var_col2:

            render_kpi_card(
                "Media Clean Sheet (%)",
                f"{media_clean_sheet:.1f}%",
                icon="🧼",
                progress=media_clean_sheet / 100,
            )

        with var_col3:

            st.markdown("")

    else:

        # ==================================
        # CONTINUITÀ
        # ==================================

        sec_c1, sec_c2 = st.columns([3, 1])
        with sec_c1:
            render_section_header(
                "🎯 Continuità & Analisi del Rischio"
            )
        with sec_c2:
            st.markdown(risk_badge_md(varianza_v))

        var_col1, var_col2 = st.columns(2)

        with var_col1:

            st.metric(
                "Varianza Voto",
                format_number(varianza_v),
                help=(
                    "Minore è il valore, "
                    "più costante è il rendimento "
                    "(valore < 0.5 = ottimo)"
                )
            )

        with var_col2:

            st.metric(
                "Varianza Gol",
                format_number(varianza_bin),
                help=(
                    "Frequenza con cui va a segno "
                    "su più giornate diverse"
                )
            )

        st.caption("MALUS MEDI / STAGIONE")

        malus_col1, malus_col2, malus_col3 = st.columns(3)

        with malus_col1:
            st.metric(
                "Ammonizioni",
                f"{rel['ammonizioni']:.1f}",
                help="Media cartellini gialli a stagione"
            )

        with malus_col2:
            st.metric(
                "Espulsioni",
                f"{rel['espulsioni']:.1f}",
                help="Media cartellini rossi a stagione"
            )

        with malus_col3:
            st.metric(
                "Rigori Errati",
                f"{rel['rigori_sbagliati']:.1f}",
                help="Media rigori sbagliati a stagione"
            )

    # ======================================
    # TREND
    # ======================================

    render_section_header(
        "📈 Trend di Forma (Rolling 5 Giornate)",
        "Evoluzione della media mobile su voto puro vs fantavoto"
    )

    rolling_df = build_rolling_data(
        p_stats,
        window=5
    )

    if not rolling_df.empty:

        fig = go.Figure()

        if "media_mobile_fanta" in rolling_df.columns:

            fig.add_trace(
                go.Scatter(
                    x=rolling_df["periodo"],
                    y=rolling_df["media_mobile_fanta"],
                    mode="lines",
                    name="Fantamedia (5G)",
                    line=dict(
                        color="#4EDEA3",
                        width=3,
                        shape="spline"
                    ),
                    fill="tozeroy",
                    fillcolor="rgba(78, 222, 163, 0.10)",
                    hovertemplate=(
                        "<b>%{x}</b><br>"
                        "Fantamedia: "
                        "<b>%{y:.2f}</b>"
                        "<extra></extra>"
                    ),
                )
            )

        if "media_mobile_voto" in rolling_df.columns:

            fig.add_trace(
                go.Scatter(
                    x=rolling_df["periodo"],
                    y=rolling_df["media_mobile_voto"],
                    mode="lines",
                    name="Media Voto (5G)",
                    line=dict(
                        color="#ADC6FF",
                        width=2,
                        dash="dot",
                        shape="spline"
                    ),
                    hovertemplate=(
                        "<b>%{x}</b><br>"
                        "Media Voto: "
                        "<b>%{y:.2f}</b>"
                        "<extra></extra>"
                    ),
                )
            )

        fig.add_hline(
            y=6.0,
            line_dash="dash",
            line_color="rgba(255,255,255,0.2)",
            annotation_text="Sufficienza (6.0)",
            annotation_position="bottom right"
        )

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(24, 27, 37, 0.6)",
            font=dict(
                family="Plus Jakarta Sans",
                color="#BBCABF"
            ),
            hovermode="x unified",
            height=380,
            margin=dict(
                l=10,
                r=10,
                t=30,
                b=10
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                bgcolor="rgba(0,0,0,0)"
            ),
            xaxis=dict(
                gridcolor="rgba(255,255,255,0.05)",
                showgrid=True
            ),
            yaxis=dict(
                gridcolor="rgba(255,255,255,0.05)",
                showgrid=True,
                range=[4.5, 10]
            ),
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    # ======================================
    # STORICO
    # ======================================

    render_section_header(
        "📅 Storico Dettagliato per Stagione"
    )

    if "stagione" in p_stats.columns:

        rows = []

        for s, g in p_stats.groupby(
            "stagione"
        ):

            gfanta = calculate_fantavoto(
                g
            )

            if is_goalkeeper:

                gol_subiti = int(
                    safe_sum(g, "gs")
                )

                clean_sheet_count = (
                    numeric_series(
                        g,
                        "gs"
                    ) == 0
                ).sum()

                rows.append(
                    {
                        "Stagione": s,
                        "Presenze": int(
                            numeric_series(
                                g,
                                "voto"
                            ).count()
                        ),
                        "Media Voto": round(
                            safe_mean(
                                g,
                                "voto"
                            ),
                            2
                        ),
                        "Fantamedia": round(
                            safe_mean(
                                gfanta,
                                "fanta_voto_calcolato"
                            ),
                            2
                        ),
                        "Gol Subiti": gol_subiti,
                        "Clean Sheet": clean_sheet_count,
                        "Amm": int(
                            safe_sum(
                                g,
                                "amm"
                            )
                        ),
                        "Esp": int(
                            safe_sum(
                                g,
                                "esp"
                            )
                        ),
                        "Malus/Bonus Medio": round(
                            safe_mean(
                                calculate_bonus_malus(g),
                                "bonus_malus"
                            ),
                            2
                        ),
                    }
                )

            else:

                rows.append(
                    {
                        "Stagione": s,
                        "Presenze": int(
                            numeric_series(
                                g,
                                "voto"
                            ).count()
                        ),
                        "Media Voto": round(
                            safe_mean(
                                g,
                                "voto"
                            ),
                            2
                        ),
                        "Fantamedia": round(
                            safe_mean(
                                gfanta,
                                "fanta_voto_calcolato"
                            ),
                            2
                        ),
                        "Gol": int(
                            safe_sum(
                                g,
                                "gf"
                            )
                            +
                            safe_sum(
                                g,
                                "rf"
                            )
                        ),
                        "Assist": int(
                            safe_sum(
                                g,
                                "ass"
                            )
                        ),
                        "Amm": int(
                            safe_sum(
                                g,
                                "amm"
                            )
                        ),
                        "Esp": int(
                            safe_sum(
                                g,
                                "esp"
                            )
                        ),
                        "Malus/Bonus Medio": round(
                            safe_mean(
                                calculate_bonus_malus(g),
                                "bonus_malus"
                            ),
                            2
                        ),
                    }
                )

        season_df = pd.DataFrame(rows)

        if not season_df.empty:

            season_df["_sort"] = (
                season_df["Stagione"]
                .apply(season_sort_key)
            )

            season_df = (
                season_df
                .sort_values(
                    "_sort",
                    ascending=False
                )
                .drop(columns="_sort")
            )

            st.dataframe(
                season_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Fantamedia":
                        st.column_config.NumberColumn(
                            format="%.2f ⭐"
                        ),

                    "Media Voto":
                        st.column_config.NumberColumn(
                            format="%.2f"
                        ),

                    "Presenze":
                        st.column_config.ProgressColumn(
                            min_value=0,
                            max_value=38,
                            format="%d / 38"
                        ),
                }
            )


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
current_quot = (
    quot[quot["stagione"].astype(str).str.strip() == str(latest_s).strip()].copy()
    if latest_s and "stagione" in quot.columns else quot.copy()
)

# ---------- TOP BAR ----------
with st.container(border=True, key="topbar"):
    top1, top2, top3 = st.columns([2.1, 1.2, 1.2])
    with top1:
        st.markdown("**⚽ FANTA AI ANALYTICS PRO**")
    with top2:
        st.markdown(f"🟢 **INTELLIGENCE ENGINE ACTIVE** · Archivio {latest_s or 'storico'}")
    with top3:
        st.markdown(f"**{len(current_quot)}** Calciatori Analizzati")

# ---------- DATA / FILTER HELPERS ----------
squadre_raw = (
    current_quot["squadra"].dropna().astype(str).str.strip().unique()
    if "squadra" in current_quot.columns else []
)
squadre_list = ["Tutte"] + sorted(list(squadre_raw))
role_counts = (
    current_quot["ruolo"].astype(str).str.upper().str.strip().value_counts()
    if "ruolo" in current_quot.columns else pd.Series(dtype=int)
)
role_order = ["Tutti", "P", "D", "C", "A"]
role_labels = []
for r in role_order:
    if r == "Tutti":
        role_labels.append(f"**TUTTI**  \n{len(current_quot)}")
    else:
        color = ROLE_MD_COLOR.get(r, "gray")
        role_labels.append(f":{color}[**{r}**]  \n{int(role_counts.get(r, 0))}")

# ---------- FILTER + PLAYER SUMMARY ----------
summary_df = compute_player_summaries(df, current_quot, ranking_df, titolari_df)
quot_view = summary_df.copy()

# ---------- MAIN 2-COLUMN LAYOUT ----------
col_players, col_detail = st.columns([1.05, 2.95], gap="medium")

with col_players:
    st.markdown("### 🧭 Roster & Filtri")
    search_query = st.text_input("Cerca", placeholder="🔍 Filtra per nome o squadra", key="search_left")

    selected_role_label = st.radio(
        "Ruolo", role_labels, horizontal=True, key="role_filter_radio", label_visibility="collapsed"
    )
    selected_role = role_order[role_labels.index(selected_role_label)]

    f1, f2 = st.columns(2)
    with f1:
        selected_team = st.selectbox("Squadra", squadre_list, index=0, key="team_filter")
    with f2:
        selected_sort = st.selectbox(
            "Ordina",
            ["👑 Ranking", "⭐ Fantamedia", "🔤 Nome", "💰 Quotazione"],
            index=0,
            key="sort_filter",
        )

    only_titolari = st.checkbox(
        "Solo titolari / formazione tipo", value=True,
        help="Mostra solo i giocatori indicati come titolari nella formazione tipo."
    )
    min_partite = st.slider("Presenze minime storico", 0, 38, 0, 1)

    if selected_role != "Tutti" and "ruolo" in quot_view.columns:
        quot_view = quot_view[quot_view["ruolo"].astype(str).str.upper().str.strip() == selected_role]
    if selected_team != "Tutte" and "squadra" in quot_view.columns:
        quot_view = quot_view[quot_view["squadra"].astype(str).str.upper().str.strip() == selected_team.upper().strip()]
    if search_query.strip():
        q = search_query.upper().strip()
        mn = quot_view["nome"].astype(str).str.upper().str.contains(q, na=False) if "nome" in quot_view else False
        ms = quot_view["squadra"].astype(str).str.upper().str.contains(q, na=False) if "squadra" in quot_view else False
        quot_view = quot_view[mn | ms]
    if only_titolari and "is_titolare" in quot_view.columns:
        quot_view = quot_view[quot_view["is_titolare"] == True]
    if min_partite > 0 and "presenze_totali" in quot_view.columns:
        quot_view = quot_view[quot_view["presenze_totali"] >= min_partite]

    if selected_sort == "👑 Ranking":
        quot_view = quot_view.sort_values(["indice_finale", "quotazione_attuale", "nome"], ascending=[False, False, True], na_position="last")
    elif selected_sort == "⭐ Fantamedia":
        quot_view = quot_view.sort_values(["fantamedia", "presenze_totali", "nome"], ascending=[False, False, True], na_position="last")
    elif selected_sort == "🔤 Nome":
        quot_view = quot_view.sort_values(["nome"], ascending=[True], na_position="last")
    else:
        quot_view = quot_view.sort_values(["quotazione_attuale", "fvm", "nome"], ascending=[False, False, True], na_position="last")

    st.caption(f"**{len(quot_view)} GIOCATORI** · lista scouting")

    if quot_view.empty:
        st.info("Nessun giocatore trovato.")
        selected_id = None
    else:
        options_df = quot_view.drop_duplicates(subset="player_id").copy()
        labels, ids = [], []
        for row in options_df.itertuples():
            n = getattr(row, "nome", "Giocatore")
            team = getattr(row, "squadra", "-")
            role = str(getattr(row, "ruolo", "")).upper().strip()
            pid = getattr(row, "player_id")
            ind = getattr(row, "indice_finale", None)
            fm = getattr(row, "fantamedia", None)
            qv = getattr(row, "quotazione_attuale", None)
            fv = getattr(row, "fvm", None)
            ind_txt = f"{float(ind):.1f}" if pd.notna(ind) else "—"
            fm_txt = f"{float(fm):.2f}" if pd.notna(fm) else "—"
            q_txt = f"{qv:g}" if isinstance(qv, (int, float)) and pd.notna(qv) else "—"
            fvm_txt = f"{fv:g}" if isinstance(fv, (int, float)) and pd.notna(fv) else "—"
            lbl = f"{role_badge_md(role)} **{n}** · `{team}`  \n👑 {ind_txt} · FM {fm_txt} · Q {q_txt} · FVM {fvm_txt}"
            labels.append(lbl); ids.append(int(pid))

        label_to_id = dict(zip(labels, ids))
        radio_key = "player_radio"
        prev = st.session_state.get(radio_key)
        if prev not in labels:
            active = st.session_state.get("active_player_id")
            st.session_state[radio_key] = labels[ids.index(active)] if active in ids else labels[0]
        selected_label = st.radio("Seleziona giocatore", labels, key=radio_key, label_visibility="collapsed")
        selected_id = label_to_id.get(selected_label)
        st.session_state["active_player_id"] = selected_id

with col_detail:
    if selected_id is None:
        st.info("👈 Seleziona un giocatore dalla lista a sinistra.")
    else:
        render_player_detail(selected_id, df, quot, ranking_df)

