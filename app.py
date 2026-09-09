import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from supabase import create_client


# ============================================================
# 1. PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="FantaAI Analytics Pro — Dashboard",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# 2. DESIGN SYSTEM
# ============================================================
#
# IMPORTANTE:
# In questa versione NON viene usato HTML per costruire:
# - roster
# - card giocatore
# - dossier
# - KPI
#
# L'unico HTML presente è questo blocco CSS.
# Questo evita che Streamlit mostri <div>, <span>, <h1>, ecc.
# come testo nell'interfaccia.
# ============================================================

_CUSTOM_CSS = """
<style>

html,
body,
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMainBlockContainer"],
[data-testid="stAppViewBlockContainer"] {
    background: #0B0F19 !important;
    color: #F8FAFC !important;
    font-family: "Plus Jakarta Sans", "Inter", sans-serif !important;
}

[data-testid="stHeader"] {
    background: #0B0F19 !important;
}

section.main {
    background: #0B0F19 !important;
}

.block-container {
    padding-top: 1.2rem !important;
    padding-bottom: 2rem !important;
}


/* ============================================================
   SCROLLBAR
   ============================================================ */

::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}

::-webkit-scrollbar-track {
    background: #0B0F19;
}

::-webkit-scrollbar-thumb {
    background: #334155;
    border-radius: 999px;
}


/* ============================================================
   INPUT
   ============================================================ */

.stTextInput input {
    background: #111827 !important;
    color: #F8FAFC !important;
    border: 1px solid rgba(255,255,255,0.10) !important;
    border-radius: 9px !important;
}

.stTextInput input::placeholder {
    color: #64748B !important;
}

[data-baseweb="select"] {
    background: #111827 !important;
    color: #F8FAFC !important;
}

[data-baseweb="select"] * {
    color: #F8FAFC !important;
}


/* ============================================================
   RADIO RUOLO
   ============================================================ */

div[data-testid="stRadio"] label p {
    color: #CBD5E1 !important;
    font-weight: 700 !important;
}

div[data-testid="stRadio"] label:nth-child(2) p {
    color: #F59E0B !important;
}

div[data-testid="stRadio"] label:nth-child(3) p {
    color: #60A5FA !important;
}

div[data-testid="stRadio"] label:nth-child(4) p {
    color: #34D399 !important;
}

div[data-testid="stRadio"] label:nth-child(5) p {
    color: #F87171 !important;
}


/* ============================================================
   ROSTER
   ============================================================ */

/*
   Nel codice Python i giocatori sono normali st.button().
   Non viene passato HTML al pulsante.

   Tutti i pulsanti dell'app sono quindi roster buttons.
*/

div[data-testid="stButton"] {
    margin-bottom: 6px !important;
}

div[data-testid="stButton"] > button {
    width: 100% !important;
    min-height: 74px !important;

    background: #111827 !important;

    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 12px !important;

    color: #FFFFFF !important;

    text-align: left !important;

    padding: 10px 14px !important;

    box-shadow: none !important;

    transition:
        background 0.15s ease,
        border-color 0.15s ease,
        transform 0.15s ease !important;
}

div[data-testid="stButton"] > button:hover {
    background: #182238 !important;
    border-color: rgba(16,185,129,0.45) !important;
    color: #FFFFFF !important;
    transform: translateY(-1px);
}

div[data-testid="stButton"] > button:focus {
    color: #FFFFFF !important;
    box-shadow: none !important;
}

/*
   Giocatore selezionato:
   ROSSO sempre, non solo al passaggio del mouse.
*/

div[data-testid="stButton"] > button[kind="primary"],
div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"] {
    background: #EF4444 !important;
    border-color: #EF4444 !important;
    color: #FFFFFF !important;
}

div[data-testid="stButton"] > button[kind="primary"]:hover,
div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"]:hover {
    background: #DC2626 !important;
    border-color: #DC2626 !important;
    color: #FFFFFF !important;
}


/* testo interno dei pulsanti */

div[data-testid="stButton"] > button p,
div[data-testid="stButton"] > button span,
div[data-testid="stButton"] > button div {
    color: #FFFFFF !important;
}


/* ============================================================
   PANEL
   ============================================================ */

[data-testid="stVerticalBlockBorderWrapper"] {
    background: #111827 !important;
    border-color: rgba(255,255,255,0.08) !important;
    border-radius: 16px !important;
}


/* ============================================================
   METRIC
   ============================================================ */

[data-testid="stMetric"] {
    background: #111827 !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 12px !important;
    padding: 14px !important;
}

[data-testid="stMetricLabel"] {
    color: #94A3B8 !important;
}

[data-testid="stMetricValue"] {
    color: #F8FAFC !important;
}


/* ============================================================
   CHECKBOX / SLIDER
   ============================================================ */

[data-testid="stCheckbox"] label p,
[data-testid="stSlider"] label p {
    color: #CBD5E1 !important;
    font-size: 0.78rem !important;
}


/* ============================================================
   DATAFRAME
   ============================================================ */

[data-testid="stDataFrame"] {
    border-radius: 12px !important;
    overflow: hidden !important;
}


/* ============================================================
   HEADINGS
   ============================================================ */

h1, h2, h3 {
    color: #F8FAFC !important;
}


/* ============================================================
   INFO / WARNING
   ============================================================ */

[data-testid="stAlert"] {
    border-radius: 10px !important;
}

</style>
"""

st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)


# ============================================================
# 3. SUPABASE
# ============================================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ SUPABASE_URL e/o SUPABASE_KEY non configurate.")
    st.stop()


@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


supabase = init_supabase()


# ============================================================
# 4. DATA FETCH
# ============================================================

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


@st.cache_data(ttl=600)
def load_ranking():
    try:
        return pd.DataFrame(
            fetch_all_rows("player_ranking")
        )
    except Exception:
        return pd.DataFrame()


# ============================================================
# 5. EXTERNAL CSV
# ============================================================

@st.cache_data(ttl=600)
def load_rigoristi():
    url = (
        "https://raw.githubusercontent.com/"
        "fanta-ai-coder/fanta-ai-etl/"
        "refs/heads/main/rigoristi.csv"
    )

    try:
        df = pd.read_csv(url)

        if "giocatore" in df.columns:
            df["giocatore"] = (
                df["giocatore"]
                .astype(str)
                .str.upper()
                .str.strip()
            )

        if "squadra" in df.columns:
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
                "posizione"
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

        if "giocatore" in df.columns:
            df["giocatore"] = (
                df["giocatore"]
                .astype(str)
                .str.upper()
                .str.strip()
            )

        if "squadra" in df.columns:
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
                "posizione"
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

        for col in [
            "nome_giocatore",
            "squadra"
        ]:
            if col in df.columns:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.upper()
                    .str.strip()
                )

        for col in [
            "titolarita",
            "squalificato",
            "infortunato"
        ]:
            if col in df.columns:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.lower()
                    .str.strip()
                )

        if "desc_infortunio" in df.columns:
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
                "desc_infortunio"
            ]
        )


rigoristi_df = load_rigoristi()
punizioni_df = load_punizioni()
titolari_df = load_titolari_infortuni()


# ============================================================
# 6. UTILITIES
# ============================================================

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
        result["player_id"] = (
            normalize_player_id_series(
                result["player_id"]
            )
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

    if values.empty:
        return 0.0

    return float(values.mean())


def safe_variance(df, column):
    if column not in df.columns:
        return None

    values = (
        numeric_series(df, column)
        .dropna()
    )

    if len(values) < 2:
        return None

    value = values.var(ddof=1)

    if pd.isna(value):
        return None

    return float(value)


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

    if starred.any():
        return df.loc[~starred].copy()

    return df.copy()


def calculate_fantavoto(df):
    result = df.copy()

    if "voto" not in result.columns:
        result["fanta_voto_calcolato"] = float("nan")
        return result

    voto = numeric_series(
        result,
        "voto"
    )

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

    for column in [
        "pi",
        "porta_inviolata",
        "clean_sheet",
        "imbattuto"
    ]:
        if column in result.columns:
            clean_sheet = (
                numeric_series(
                    result,
                    column
                )
                .fillna(0)
            )
            break

    for column in [
        "rp",
        "rigori_parati",
        "rigore_parato"
    ]:
        if column in result.columns:
            penalty_saved = (
                numeric_series(
                    result,
                    column
                )
                .fillna(0)
            )
            break

    for column in [
        "gs",
        "gol_subiti"
    ]:
        if column in result.columns:
            gol_subiti = (
                numeric_series(
                    result,
                    column
                )
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
        voto.isna(),
        "fanta_voto_calcolato"
    ] = float("nan")

    return result


def calculate_bonus_malus(df):
    result = calculate_fantavoto(df)

    result["bonus_malus"] = (
        result["fanta_voto_calcolato"]
        - numeric_series(result, "voto")
    )

    return result


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
            "rigori_parati": 0.0
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
        "assist_stagione": (
            safe_sum(
                p_stats,
                "ass"
            ) / seasons
        ),
        "rigori_sbagliati": (
            safe_sum(
                p_stats,
                "rs"
            ) / seasons
        ),
        "ammonizioni": (
            safe_sum(
                p_stats,
                "amm"
            ) / seasons
        ),
        "espulsioni": (
            safe_sum(
                p_stats,
                "esp"
            ) / seasons
        ),
        "gol_stagione": (
            gf_tot / seasons
        ),
        "rigori_segnati": (
            rf_tot / seasons
        ),
        "gs_stagione": (
            gs_tot / seasons
        ),
        "rigori_parati": (
            rp_tot / seasons
        ),
    }


def varianza_gol_binaria(p_stats):
    if (
        p_stats.empty
        or "giornata" not in p_stats.columns
    ):
        return 0.0

    gol_g = p_stats.groupby(
        "giornata"
    ).apply(
        lambda data: (
            1
            if (
                safe_sum(data, "gf")
                + safe_sum(data, "rf")
            ) > 0
            else 0
        ),
        include_groups=False
    )

    if len(gol_g) <= 1:
        return 0.0

    return float(
        gol_g.var(ddof=1)
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
    required = [
        "stagione",
        "giornata"
    ]

    if (
        player_stats.empty
        or any(
            c not in player_stats.columns
            for c in required
        )
    ):
        return pd.DataFrame()

    result = player_stats.copy()

    result["giornata"] = pd.to_numeric(
        result["giornata"],
        errors="coerce"
    )

    result = result[
        result["giornata"].notna()
    ].copy()

    if result.empty:
        return pd.DataFrame()

    result["giornata"] = (
        result["giornata"]
        .astype(int)
    )

    result["stagione"] = (
        result["stagione"]
        .astype(str)
        .str.strip()
    )

    result["_season_sort"] = (
        result["stagione"]
        .apply(season_sort_key)
    )

    result = (
        result
        .sort_values(
            [
                "_season_sort",
                "giornata"
            ]
        )
        .reset_index(drop=True)
    )

    result = calculate_fantavoto(
        result
    )

    if "voto" in result.columns:
        result["voto"] = pd.to_numeric(
            result["voto"],
            errors="coerce"
        )

        result["media_mobile_voto"] = (
            result
            .groupby(
                "stagione",
                sort=False
            )["voto"]
            .transform(
                lambda x: x.rolling(
                    window=window,
                    min_periods=1
                ).mean()
            )
        )

    result["media_mobile_fanta"] = (
        result
        .groupby(
            "stagione",
            sort=False
        )["fanta_voto_calcolato"]
        .transform(
            lambda x: x.rolling(
                window=window,
                min_periods=1
            ).mean()
        )
    )

    result["periodo"] = (
        result["stagione"]
        + " G"
        + result["giornata"].astype(str)
    )

    return result


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

    if seasons.empty:
        return None

    return max(
        seasons.unique(),
        key=season_sort_key
    )


def get_latest_quote_row(player_quotes):
    if player_quotes.empty:
        return None

    result = player_quotes.copy()

    if "stagione" in result.columns:
        result["_season_sort"] = (
            result["stagione"]
            .apply(season_sort_key)
        )

        result = result.sort_values(
            "_season_sort"
        )

    return result.iloc[-1]


def get_player_ranking(
    ranking_df,
    player_id,
    stagione=None
):
    if (
        ranking_df.empty
        or "player_id" not in ranking_df.columns
    ):
        return None

    ranking = ranking_df.copy()

    ranking["player_id"] = (
        normalize_player_id_series(
            ranking["player_id"]
        )
    )

    try:
        pid = int(
            float(player_id)
        )
    except Exception:
        return None

    ranking = ranking[
        ranking["player_id"] == pid
    ].copy()

    if ranking.empty:
        return None

    if (
        stagione is not None
        and "stagione" in ranking.columns
    ):
        current = ranking[
            ranking["stagione"]
            .astype(str)
            .str.strip()
            ==
            str(stagione).strip()
        ].copy()

        if not current.empty:
            ranking = current

    if len(ranking) > 1:
        if "calculated_at" in ranking.columns:
            ranking["calculated_at"] = (
                pd.to_datetime(
                    ranking["calculated_at"],
                    errors="coerce"
                )
            )

            ranking = ranking.sort_values(
                "calculated_at"
            )

        elif "stagione" in ranking.columns:
            ranking["_season_sort"] = (
                ranking["stagione"]
                .apply(season_sort_key)
            )

            ranking = ranking.sort_values(
                "_season_sort"
            )

    return ranking.iloc[-1]


# ============================================================
# 7. SUMMARY DATAFRAME
# ============================================================

@st.cache_data(ttl=600)
def compute_player_summaries(
    stats_df,
    quot_df,
    ranking_df,
    titolari_df
):
    if quot_df.empty:
        return quot_df.copy()

    base = quot_df.copy()

    base["player_id"] = (
        normalize_player_id_series(
            base["player_id"]
        )
    )

    # --------------------------------------------------------
    # Ranking
    # --------------------------------------------------------

    if (
        not ranking_df.empty
        and "player_id" in ranking_df.columns
    ):
        rdf = ranking_df.copy()

        rdf["player_id"] = (
            normalize_player_id_series(
                rdf["player_id"]
            )
        )

        rank_cols = [
            "player_id",
            "indice_finale",
            "rank_ruolo",
            "totale_ruolo",
            "rank_generale",
            "totale_generale",
            "titolarita_score",
            "presenze_pesate",
            "forma_attuale_score",
            "performance_score"
        ]

        available = [
            c
            for c in rank_cols
            if c in rdf.columns
        ]

        rdf_unique = (
            rdf
            .drop_duplicates(
                subset=["player_id"]
            )[available]
        )

        base = pd.merge(
            base,
            rdf_unique,
            on="player_id",
            how="left"
        )

    else:
        for column in [
            "indice_finale",
            "rank_ruolo",
            "totale_ruolo",
            "rank_generale",
            "totale_generale",
            "titolarita_score",
            "presenze_pesate"
        ]:
            base[column] = None

    # --------------------------------------------------------
    # Titolari / infortuni
    # --------------------------------------------------------

    if not titolari_df.empty:

        tdf = titolari_df.copy()

        tdf["nome_norm"] = (
            tdf["nome_giocatore"]
            .astype(str)
            .str.upper()
            .str.strip()
        )

        tdf["squadra_norm"] = (
            tdf["squadra"]
            .astype(str)
            .str.upper()
            .str.strip()
        )

        base["nome_norm"] = (
            base["nome"]
            .astype(str)
            .str.upper()
            .str.strip()
        )

        base["squadra_norm"] = (
            base["squadra"]
            .astype(str)
            .str.upper()
            .str.strip()
        )

        tdf_unique = (
            tdf
            .drop_duplicates(
                subset=[
                    "nome_norm",
                    "squadra_norm"
                ]
            )
        )

        columns = [
            "nome_norm",
            "squadra_norm",
            "titolarita",
            "squalificato",
            "infortunato"
        ]

        columns = [
            c
            for c in columns
            if c in tdf_unique.columns
        ]

        base = pd.merge(
            base,
            tdf_unique[columns],
            on=[
                "nome_norm",
                "squadra_norm"
            ],
            how="left"
        )

        base["is_titolare"] = (
            base["titolarita"]
            .astype(str)
            .str.lower()
            .str.strip()
            ==
            "titolare"
        )

    else:
        base["is_titolare"] = False

    # --------------------------------------------------------
    # Historical statistics
    # --------------------------------------------------------

    if (
        not stats_df.empty
        and "player_id" in stats_df.columns
    ):
        sdf = stats_df.copy()

        sdf["player_id"] = (
            normalize_player_id_series(
                sdf["player_id"]
            )
        )

        if "stagione" in sdf.columns:

            sdf_hist = sdf[
                sdf["stagione"]
                .astype(str)
                .str.strip()
                != "2026-27"
            ].copy()

            if sdf_hist.empty:
                sdf_hist = sdf.copy()

        else:
            sdf_hist = sdf.copy()

        voto = numeric_series(
            sdf_hist,
            "voto"
        )

        gf = numeric_series(
            sdf_hist,
            "gf"
        ).fillna(0)

        rf = numeric_series(
            sdf_hist,
            "rf"
        ).fillna(0)

        ass = numeric_series(
            sdf_hist,
            "ass"
        ).fillna(0)

        au = numeric_series(
            sdf_hist,
            "au"
        ).fillna(0)

        esp = numeric_series(
            sdf_hist,
            "esp"
        ).fillna(0)

        amm = numeric_series(
            sdf_hist,
            "amm"
        ).fillna(0)

        gs = numeric_series(
            sdf_hist,
            "gs"
        ).fillna(0)

        rp = numeric_series(
            sdf_hist,
            "rp"
        ).fillna(0)

        clean_sheet = pd.Series(
            0.0,
            index=sdf_hist.index
        )

        for column in [
            "pi",
            "porta_inviolata",
            "clean_sheet",
            "imbattuto"
        ]:
            if column in sdf_hist.columns:
                clean_sheet = (
                    numeric_series(
                        sdf_hist,
                        column
                    )
                    .fillna(0)
                )
                break

        if "ruolo" in sdf_hist.columns:

            is_p = (
                sdf_hist["ruolo"]
                .astype(str)
                .str.strip()
                .str.upper()
                .eq("P")
            )

            clean_sheet = clean_sheet.where(
                is_p,
                0
            )

            gs = gs.where(
                is_p,
                0
            )

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

        valid = sdf_hist[
            voto.notna()
        ]

        agg = (
            valid
            .groupby("player_id")
            .agg(
                presenze_totali=(
                    "_voto_num",
                    "count"
                ),
                fantamedia=(
                    "_fanta_calc",
                    "mean"
                ),
                media_voto=(
                    "_voto_num",
                    "mean"
                )
            )
            .reset_index()
        )

        base = pd.merge(
            base,
            agg,
            on="player_id",
            how="left"
        )

    else:
        base["presenze_totali"] = 0
        base["fantamedia"] = None
        base["media_voto"] = None

    base["presenze_totali"] = (
        base["presenze_totali"]
        .fillna(0)
        .astype(int)
    )

    return base


# ============================================================
# 8. LOAD DATA
# ============================================================

try:
    df = load_stats()
    quot = load_quotazioni()
    ranking_df = load_ranking()

except Exception as e:
    st.error(
        f"❌ Errore nel caricamento dei dati: {e}"
    )
    st.stop()


if df.empty or quot.empty:
    st.warning(
        "⚠️ Tabelle statistiche o quotazioni vuote."
    )
    st.stop()


df = normalize_dataframe(df)
quot = normalize_dataframe(quot)
ranking_df = normalize_dataframe(ranking_df)

df = remove_starred_vote_rows(df)


# ============================================================
# 9. CURRENT SEASON
# ============================================================

latest_s = get_latest_season(
    quot
)

if latest_s:
    current_quot = quot[
        quot["stagione"]
        .astype(str)
        .str.strip()
        ==
        str(latest_s).strip()
    ].copy()
else:
    current_quot = quot.copy()


summary_df = compute_player_summaries(
    df,
    current_quot,
    ranking_df,
    titolari_df
)


# ============================================================
# 10. TOP HEADER
# ============================================================

header_left, header_right = st.columns(
    [2.8, 1.2]
)

with header_left:
    st.markdown(
        "# ⚡ FantaAI Analytics Pro"
    )

    st.caption(
        "SERIE A — ASTA LIVE READY"
    )

with header_right:
    st.metric(
        "Budget Fantamedia",
        "342 / 500 FM"
    )

st.divider()


# ============================================================
# 11. MASTER DETAIL
# ============================================================

col_roster, col_dossier = st.columns(
    [0.34, 0.66],
    gap="medium"
)


# ============================================================
# 12. LEFT COLUMN — ROSTER
# ============================================================

with col_roster:

    st.markdown(
        "### 🔍 Filtri Scouting"
    )

    st.caption(
        "Trova e ordina i calciatori nel listone"
    )

    search_query = st.text_input(
        "Ricerca",
        placeholder="Cerca giocatore o squadra...",
        label_visibility="collapsed"
    )

    selected_role = st.radio(
        "Seleziona Ruolo",
        [
            "Tutti",
            "P",
            "D",
            "C",
            "A"
        ],
        horizontal=True,
        key="role_filter_btn"
    )

    if "squadra" in current_quot.columns:
        squadre_raw = (
            current_quot["squadra"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
        )
    else:
        squadre_raw = []

    squadre_list = (
        ["Tutte"]
        + sorted(
            list(squadre_raw)
        )
    )

    c1, c2 = st.columns(2)

    with c1:
        selected_team = st.selectbox(
            "Squadra",
            squadre_list,
            index=0
        )

    with c2:
        selected_sort = st.selectbox(
            "Ordina per",
            [
                "👑 Indice Ranking",
                "⭐ Fantamedia",
                "🔤 Nome (A-Z)",
                "💰 Quotazione"
            ],
            index=0
        )

    f1, f2 = st.columns(
        [1.1, 1.9]
    )

    with f1:
        only_titolari = st.checkbox(
            "Solo Titolari",
            value=False
        )

    with f2:
        min_partite = st.slider(
            "Partite minime",
            0,
            38,
            0,
            step=1
        )

    st.divider()

    # --------------------------------------------------------
    # FILTER
    # --------------------------------------------------------

    quot_view = summary_df.copy()

    if (
        selected_role != "Tutti"
        and "ruolo" in quot_view.columns
    ):
        quot_view = quot_view[
            quot_view["ruolo"]
            .astype(str)
            .str.upper()
            .str.strip()
            ==
            selected_role
        ]

    if (
        selected_team != "Tutte"
        and "squadra" in quot_view.columns
    ):
        quot_view = quot_view[
            quot_view["squadra"]
            .astype(str)
            .str.upper()
            .str.strip()
            ==
            selected_team.upper().strip()
        ]

    if search_query.strip():

        q = (
            search_query
            .upper()
            .strip()
        )

        if "nome" in quot_view.columns:
            match_nome = (
                quot_view["nome"]
                .astype(str)
                .str.upper()
                .str.contains(
                    q,
                    na=False
                )
            )
        else:
            match_nome = False

        if "squadra" in quot_view.columns:
            match_squadra = (
                quot_view["squadra"]
                .astype(str)
                .str.upper()
                .str.contains(
                    q,
                    na=False
                )
            )
        else:
            match_squadra = False

        quot_view = quot_view[
            match_nome | match_squadra
        ]

    if (
        only_titolari
        and "is_titolare" in quot_view.columns
    ):
        quot_view = quot_view[
            quot_view["is_titolare"]
            == True
        ]

    if (
        min_partite > 0
        and "presenze_totali"
        in quot_view.columns
    ):
        quot_view = quot_view[
            quot_view["presenze_totali"]
            >= min_partite
        ]

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    if selected_sort == "👑 Indice Ranking":

        quot_view = quot_view.sort_values(
            by=[
                "indice_finale",
                "quotazione_attuale",
                "nome"
            ],
            ascending=[
                False,
                False,
                True
            ],
            na_position="last"
        )

    elif selected_sort == "⭐ Fantamedia":

        quot_view = quot_view.sort_values(
            by=[
                "fantamedia",
                "presenze_totali",
                "nome"
            ],
            ascending=[
                False,
                False,
                True
            ],
            na_position="last"
        )

    elif selected_sort == "🔤 Nome (A-Z)":

        quot_view = quot_view.sort_values(
            by=[
                "nome"
            ],
            ascending=[
                True
            ],
            na_position="last"
        )

    elif selected_sort == "💰 Quotazione":

        quot_view = quot_view.sort_values(
            by=[
                "quotazione_attuale",
                "fvm",
                "nome"
            ],
            ascending=[
                False,
                False,
                True
            ],
            na_position="last"
        )

    st.caption(
        f"ROSTER SELEZIONATO ({len(quot_view)})"
    )

    # --------------------------------------------------------
    # EMPTY
    # --------------------------------------------------------

    if quot_view.empty:

        st.info(
            "Nessun giocatore trovato con questi filtri."
        )

        selected_id = None

    else:

        options_df = (
            quot_view
            .drop_duplicates(
                subset="player_id"
            )
            .copy()
        )

        player_ids = (
            options_df["player_id"]
            .dropna()
            .astype(int)
            .tolist()
        )

        # ----------------------------------------------------
        # ACTIVE PLAYER
        # ----------------------------------------------------

        active_id = st.session_state.get(
            "active_player_id"
        )

        if (
            active_id is None
            or active_id not in player_ids
        ):
            active_id = player_ids[0]

            st.session_state[
                "active_player_id"
            ] = active_id

        # ----------------------------------------------------
        # SCROLLABLE ROSTER
        # ----------------------------------------------------

        with st.container(
            height=650,
            border=False
        ):

            for row in options_df.itertuples():

                pid = int(
                    getattr(
                        row,
                        "player_id"
                    )
                )

                nome = getattr(
                    row,
                    "nome",
                    "Giocatore"
                )

                squadra = getattr(
                    row,
                    "squadra",
                    "-"
                )

                ruolo = str(
                    getattr(
                        row,
                        "ruolo",
                        ""
                    )
                ).upper().strip()

                indice = getattr(
                    row,
                    "indice_finale",
                    None
                )

                fantamedia = getattr(
                    row,
                    "fantamedia",
                    None
                )

                presenze = getattr(
                    row,
                    "presenze_totali",
                    0
                )

                quota = getattr(
                    row,
                    "quotazione_attuale",
                    0
                )

                fvm = getattr(
                    row,
                    "fvm",
                    0
                )

                # --------------------------------------------
                # ROLE ICON
                # --------------------------------------------

                role_icon = {
                    "P": "🟨",
                    "D": "🟦",
                    "C": "🟩",
                    "A": "🟥"
                }.get(
                    ruolo,
                    "⚪"
                )

                # --------------------------------------------
                # RIGORISTA / PUNIZIONI
                # --------------------------------------------

                nome_norm = (
                    str(nome)
                    .upper()
                    .strip()
                )

                squadra_norm = (
                    str(squadra)
                    .upper()
                    .strip()
                )

                is_rigorista = False

                if not rigoristi_df.empty:
                    is_rigorista = not (
                        rigoristi_df[
                            (
                                rigoristi_df[
                                    "giocatore"
                                ]
                                ==
                                nome_norm
                            )
                            &
                            (
                                rigoristi_df[
                                    "squadra"
                                ]
                                ==
                                squadra_norm
                            )
                        ].empty
                    )

                is_punizioni = False

                if not punizioni_df.empty:
                    is_punizioni = not (
                        punizioni_df[
                            (
                                punizioni_df[
                                    "giocatore"
                                ]
                                ==
                                nome_norm
                            )
                            &
                            (
                                punizioni_df[
                                    "squadra"
                                ]
                                ==
                                squadra_norm
                            )
                        ].empty
                    )

                badges = []

                if is_rigorista:
                    badges.append(
                        "🎯 Rigorista"
                    )

                if is_punizioni:
                    badges.append(
                        "⚡ Punizioni"
                    )

                badge_text = (
                    " · ".join(badges)
                    if badges
                    else ""
                )

                # --------------------------------------------
                # FORMAT
                # --------------------------------------------

                indice_text = (
                    f"{float(indice):.1f}"
                    if pd.notna(indice)
                    else "N/D"
                )

                fm_text = (
                    f"{float(fantamedia):.2f}"
                    if pd.notna(fantamedia)
                    else "N/D"
                )

                # --------------------------------------------
                # BUTTON LABEL
                #
                # SOLO TESTO / MARKDOWN.
                # NESSUN HTML.
                # --------------------------------------------

                label = (
                    f"{role_icon} **{nome}** · "
                    f"{squadra} · {ruolo}\n\n"
                    f"📊 Indice **{indice_text}** · "
                    f"⭐ FM **{fm_text}** · "
                    f"PG **{presenze}** · "
                    f"Q **{quota}** · "
                    f"FVM **{fvm}**"
                )

                if badge_text:
                    label += (
                        f" · {badge_text}"
                    )

                is_active = (
                    st.session_state[
                        "active_player_id"
                    ]
                    == pid
                )

                if st.button(
                    label,
                    key=f"player_{pid}",
                    use_container_width=True,
                    type=(
                        "primary"
                        if is_active
                        else "secondary"
                    )
                ):
                    st.session_state[
                        "active_player_id"
                    ] = pid

                    st.rerun()

        selected_id = st.session_state.get(
            "active_player_id"
        )


# ============================================================
# 13. RIGHT COLUMN — DOSSIER
# ============================================================

with col_dossier:

    if selected_id is None:

        st.info(
            "👈 Seleziona un giocatore dalla lista "
            "a sinistra."
        )

    else:

        player_id = int(
            float(selected_id)
        )

        p_quotes = quot[
            quot["player_id"]
            == player_id
        ].copy()

        current_quote = (
            get_latest_quote_row(
                p_quotes
            )
        )

        p_stats = df[
            df["player_id"]
            == player_id
        ].copy()

        # ----------------------------------------------------
        # PLAYER INFO
        # ----------------------------------------------------

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

        ranking_row = get_player_ranking(
            ranking_df,
            player_id
        )

        rigor_info = rigoristi_df[
            (
                rigoristi_df["giocatore"]
                ==
                nome_upper
            )
            &
            (
                rigoristi_df["squadra"]
                ==
                squadra_upper
            )
        ]

        punizioni_info = punizioni_df[
            (
                punizioni_df["giocatore"]
                ==
                nome_upper
            )
            &
            (
                punizioni_df["squadra"]
                ==
                squadra_upper
            )
        ]

        titolare_info = titolari_df[
            (
                titolari_df[
                    "nome_giocatore"
                ]
                ==
                nome_upper
            )
            &
            (
                titolari_df[
                    "squadra"
                ]
                ==
                squadra_upper
            )
        ]

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        titolarita_val = ""
        infortunato_val = ""
        desc_infortunio = ""

        if not titolare_info.empty:

            t_row = titolare_info.iloc[0]

            titolarita_val = str(
                t_row.get(
                    "titolarita",
                    ""
                )
            ).lower().strip()

            infortunato_val = str(
                t_row.get(
                    "infortunato",
                    ""
                )
            ).lower().strip()

            desc_infortunio = str(
                t_row.get(
                    "desc_infortunio",
                    ""
                )
            ).strip()

        # ----------------------------------------------------
        # HEADER DOSSIER
        #
        # SOLO COMPONENTI STREAMLIT.
        # NIENTE HTML.
        # ----------------------------------------------------

        with st.container(
            border=True
        ):

            head_left, head_right = st.columns(
                [3.0, 1.0]
            )

            with head_left:

                st.markdown(
                    f"### {nome}"
                )

                st.caption(
                    f"{ruolo} · {squadra}"
                )

                status_parts = []

                if "titolare" in titolarita_val:
                    status_parts.append(
                        "🟢 Titolare"
                    )

                elif (
                    "panchina"
                    in titolarita_val
                    or
                    "riserva"
                    in titolarita_val
                ):
                    status_parts.append(
                        "🟠 Panchina"
                    )

                if infortunato_val in [
                    "sì",
                    "si",
                    "true",
                    "1",
                    "yes"
                ]:
                    status_parts.append(
                        "🚑 Infortunato"
                    )

                if status_parts:
                    st.write(
                        " · ".join(status_parts)
                    )

                if (
                    desc_infortunio
                    and
                    desc_infortunio.lower()
                    != "nan"
                ):
                    st.warning(
                        f"⚠️ {desc_infortunio}"
                    )

            with head_right:

                if (
                    ranking_row is not None
                    and
                    pd.notna(
                        ranking_row.get(
                            "rank_ruolo"
                        )
                    )
                ):
                    rk_ruolo = int(
                        ranking_row.get(
                            "rank_ruolo"
                        )
                    )
                else:
                    rk_ruolo = 1

                if (
                    ranking_row is not None
                    and
                    pd.notna(
                        ranking_row.get(
                            "totale_ruolo"
                        )
                    )
                ):
                    tot_ruolo = int(
                        ranking_row.get(
                            "totale_ruolo"
                        )
                    )
                else:
                    tot_ruolo = 68

                st.metric(
                    "Ranking Ruolo",
                    f"#{rk_ruolo} / {tot_ruolo}"
                )

        # ----------------------------------------------------
        # QUOTAZIONE
        # ----------------------------------------------------

        if current_quote is not None:

            quota_val = current_quote.get(
                "quotazione_attuale",
                0
            )

            fvm_val = current_quote.get(
                "fvm",
                0
            )

        else:

            quota_val = 0
            fvm_val = 0

        q1, q2 = st.columns(2)

        with q1:
            st.metric(
                "Quotazione Listino",
                f"{quota_val} FM"
            )

        with q2:
            st.metric(
                "FVM suggerito",
                f"{fvm_val} FM"
            )

        # ----------------------------------------------------
        # STATS PREPARATION
        # ----------------------------------------------------

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

            st.info(
                "Nessuna statistica storica disponibile "
                "per questo calciatore."
            )

        else:

            p_stats = calculate_bonus_malus(
                p_stats
            )

            is_goalkeeper = (
                ruolo == "P"
            )

            if "stagione" in p_stats.columns:

                p_stats_hist = p_stats[
                    p_stats["stagione"]
                    .astype(str)
                    .str.strip()
                    != "2026-27"
                ].copy()

                if p_stats_hist.empty:
                    p_stats_hist = p_stats.copy()

            else:
                p_stats_hist = p_stats.copy()

            # ------------------------------------------------
            # RELATIVE METRICS
            # ------------------------------------------------

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

            varianza_bin = (
                varianza_gol_binaria(
                    p_stats_hist
                )
            )

            varianza_v = safe_variance(
                p_stats_hist,
                "voto"
            )

            # ------------------------------------------------
            # KPI
            # ------------------------------------------------

            st.markdown(
                "### 📊 Indicatori principali"
            )

            k1, k2, k3, k4 = st.columns(4)

            with k1:
                st.metric(
                    "Fantamedia",
                    f"{fantamedia:.2f}"
                )

            with k2:
                st.metric(
                    "Media Voto",
                    f"{media_voto:.2f}"
                )

            with k3:
                st.metric(
                    "Presenze medie",
                    f"{rel['presenze_medie']:.1f}"
                )

            with k4:

                if is_goalkeeper:

                    st.metric(
                        "Gol subiti / stagione",
                        f"{rel['gs_stagione']:.1f}"
                    )

                else:

                    st.metric(
                        "Gol / stagione",
                        f"{rel['gol_stagione']:.1f}"
                    )

            # ------------------------------------------------
            # SECOND ROW KPI
            # ------------------------------------------------

            r1, r2, r3, r4 = st.columns(4)

            with r1:
                st.metric(
                    "Varianza Voto",
                    format_number(
                        varianza_v
                    ),
                    help=(
                        "Più è bassa, più il rendimento "
                        "è regolare."
                    )
                )

            with r2:
                st.metric(
                    "Varianza Gol",
                    format_number(
                        varianza_bin
                    )
                )

            with r3:

                if is_goalkeeper:
                    st.metric(
                        "Rigori parati / anno",
                        f"{rel['rigori_parati']:.1f}"
                    )
                else:
                    st.metric(
                        "Assist / stagione",
                        f"{rel['assist_stagione']:.1f}"
                    )

            with r4:

                st.metric(
                    "Presenze %",
                    f"{rel['presenza_pct']:.1f}%"
                )

            # ------------------------------------------------
            # SET PIECES
            # ------------------------------------------------

            sp1, sp2 = st.columns(2)

            with sp1:

                if not rigor_info.empty:

                    position = (
                        rigor_info[
                            "posizione"
                        ]
                        .iloc[0]
                        if "posizione"
                        in rigor_info.columns
                        else None
                    )

                    if pd.notna(position):
                        st.success(
                            f"🎯 Rigorista — posizione #{int(position)}"
                        )
                    else:
                        st.success(
                            "🎯 Rigorista"
                        )

                else:
                    st.caption(
                        "🎯 Non indicato come rigorista"
                    )

            with sp2:

                if not punizioni_info.empty:
                    st.success(
                        "⚡ Tiratore di punizioni"
                    )
                else:
                    st.caption(
                        "⚡ Non indicato come tiratore di punizioni"
                    )

            # ------------------------------------------------
            # TREND
            # ------------------------------------------------

            st.markdown(
                "### 📈 Trend di Forma — Rolling 5 Giornate"
            )

            rolling_df = build_rolling_data(
                p_stats,
                window=5
            )

            if not rolling_df.empty:

                fig = go.Figure()

                upper_y = 12.0

                if (
                    "media_mobile_fanta"
                    in rolling_df.columns
                ):

                    max_fanta = (
                        rolling_df[
                            "media_mobile_fanta"
                        ].max()
                    )

                    if (
                        pd.notna(max_fanta)
                        and
                        max_fanta > 11.0
                    ):
                        upper_y = (
                            max_fanta + 1.0
                        )

                if (
                    "media_mobile_fanta"
                    in rolling_df.columns
                ):

                    fig.add_trace(
                        go.Scatter(
                            x=rolling_df[
                                "periodo"
                            ],
                            y=rolling_df[
                                "media_mobile_fanta"
                            ],
                            mode="lines",
                            name="Fantamedia 5G",
                            line=dict(
                                color="#10B981",
                                width=3,
                                shape="spline"
                            ),
                            fill="tozeroy",
                            fillcolor=(
                                "rgba("
                                "16,185,129,0.08)"
                            ),
                            hovertemplate=(
                                "<b>%{x}</b><br>"
                                "Fantamedia: "
                                "<b>%{y:.2f}</b>"
                                "<extra></extra>"
                            )
                        )
                    )

                if (
                    "media_mobile_voto"
                    in rolling_df.columns
                ):

                    fig.add_trace(
                        go.Scatter(
                            x=rolling_df[
                                "periodo"
                            ],
                            y=rolling_df[
                                "media_mobile_voto"
                            ],
                            mode="lines",
                            name="Media Voto 5G",
                            line=dict(
                                color="#60A5FA",
                                width=2,
                                dash="dot",
                                shape="spline"
                            ),
                            hovertemplate=(
                                "<b>%{x}</b><br>"
                                "Media Voto: "
                                "<b>%{y:.2f}</b>"
                                "<extra></extra>"
                            )
                        )
                    )

                fig.add_hline(
                    y=6.0,
                    line_dash="dash",
                    line_color=(
                        "rgba("
                        "255,255,255,0.20)"
                    ),
                    annotation_text="Sufficienza"
                )

                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor=(
                        "rgba("
                        "17,24,39,0.60)"
                    ),
                    font=dict(
                        family="Plus Jakarta Sans",
                        color="#94A3B8"
                    ),
                    hovermode="x unified",
                    height=400,
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
                        gridcolor=(
                            "rgba("
                            "255,255,255,0.05)"
                        ),
                        showgrid=True
                    ),
                    yaxis=dict(
                        gridcolor=(
                            "rgba("
                            "255,255,255,0.05)"
                        ),
                        showgrid=True,
                        range=[
                            4.0,
                            upper_y
                        ]
                    )
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

            else:

                st.info(
                    "Dati insufficienti per costruire "
                    "il trend."
                )

            # ------------------------------------------------
            # HISTORICAL TABLE
            # ------------------------------------------------

            st.markdown(
                "### 📅 Storico Prestazioni per Stagione"
            )

            if "stagione" in p_stats.columns:

                rows = []

                for season, group in (
                    p_stats
                    .groupby("stagione")
                ):

                    gfanta = calculate_fantavoto(
                        group
                    )

                    if is_goalkeeper:

                        rows.append(
                            {
                                "Stagione": season,
                                "Presenze": int(
                                    numeric_series(
                                        group,
                                        "voto"
                                    ).count()
                                ),
                                "Media Voto": round(
                                    safe_mean(
                                        group,
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
                                "Gol Subiti": int(
                                    safe_sum(
                                        group,
                                        "gs"
                                    )
                                ),
                                "Clean Sheet": int(
                                    (
                                        numeric_series(
                                            group,
                                            "gs"
                                        ) == 0
                                    ).sum()
                                ),
                                "Amm": int(
                                    safe_sum(
                                        group,
                                        "amm"
                                    )
                                ),
                                "Esp": int(
                                    safe_sum(
                                        group,
                                        "esp"
                                    )
                                )
                            }
                        )

                    else:

                        rows.append(
                            {
                                "Stagione": season,
                                "Presenze": int(
                                    numeric_series(
                                        group,
                                        "voto"
                                    ).count()
                                ),
                                "Media Voto": round(
                                    safe_mean(
                                        group,
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
                                        group,
                                        "gf"
                                    )
                                    +
                                    safe_sum(
                                        group,
                                        "rf"
                                    )
                                ),
                                "Assist": int(
                                    safe_sum(
                                        group,
                                        "ass"
                                    )
                                ),
                                "Amm": int(
                                    safe_sum(
                                        group,
                                        "amm"
                                    )
                                ),
                                "Esp": int(
                                    safe_sum(
                                        group,
                                        "esp"
                                    )
                                )
                            }
                        )

                season_df = pd.DataFrame(
                    rows
                )

                if not season_df.empty:

                    season_df["_sort"] = (
                        season_df[
                            "Stagione"
                        ].apply(
                            season_sort_key
                        )
                    )

                    season_df = (
                        season_df
                        .sort_values(
                            "_sort",
                            ascending=False
                        )
                        .drop(
                            columns="_sort"
                        )
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
                                )
                        }
                    )
