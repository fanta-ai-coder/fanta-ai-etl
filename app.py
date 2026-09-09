import os
import html
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from supabase import create_client


# ==========================================
# 1. PAGE CONFIG
# ==========================================

st.set_page_config(
    page_title="FantaAI Analytics Pro — Dashboard",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ==========================================
# 2. DESIGN SYSTEM — M3 DARK
# ==========================================

_CUSTOM_CSS = """
<style>

@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');


/* =========================================================
   GLOBAL
   ========================================================= */

html,
body,
[class*="css"],
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stHeader"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    background-color: #0B0F19 !important;
    color: #F8FAFC !important;
}


section.main,
[data-testid="stMainBlockContainer"],
[data-testid="stAppViewBlockContainer"] {
    background-color: #0B0F19 !important;
    padding-top: 1.5rem !important;
    padding-bottom: 2rem !important;
}


/* =========================================================
   SCROLLBAR
   ========================================================= */

::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}

::-webkit-scrollbar-track {
    background: transparent;
}

::-webkit-scrollbar-thumb {
    background: #334155;
    border-radius: 9999px;
}

::-webkit-scrollbar-thumb:hover {
    background: #10B981;
}


/* =========================================================
   INPUTS
   ========================================================= */

.stTextInput input,
.stSelectbox [data-baseweb="select"] {
    background-color: #111827 !important;
    border: 1px solid rgba(255, 255, 255, 0.10) !important;
    border-radius: 8px !important;
    color: #F9FAFB !important;
    font-size: 0.85rem !important;
}

.stTextInput input::placeholder {
    color: #64748B !important;
}


/* =========================================================
   RADIO RUOLI
   ========================================================= */

#role-filter-anchor + div[data-testid="stRadio"] label:nth-child(1) p {
    color: #FFFFFF !important;
    font-weight: 700 !important;
}

#role-filter-anchor + div[data-testid="stRadio"] label:nth-child(2) p {
    color: #F59E0B !important;
    font-weight: 700 !important;
}

#role-filter-anchor + div[data-testid="stRadio"] label:nth-child(3) p {
    color: #3B82F6 !important;
    font-weight: 700 !important;
}

#role-filter-anchor + div[data-testid="stRadio"] label:nth-child(4) p {
    color: #10B981 !important;
    font-weight: 700 !important;
}

#role-filter-anchor + div[data-testid="stRadio"] label:nth-child(5) p {
    color: #EF4444 !important;
    font-weight: 700 !important;
}


/* =========================================================
   PANELS
   ========================================================= */

.glass-panel {
    background: #111827;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 20px;
    box-sizing: border-box;
}


/* =========================================================
   TOP HEADER
   ========================================================= */

.top-header {
    background: #111827;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding: 12px 20px;
    border-radius: 12px;
    margin-bottom: 16px;
}


/* =========================================================
   ROSTER BUTTON
   ========================================================= */

/*
   IMPORTANTE:

   Il vecchio codice passava HTML direttamente a st.button().
   Streamlit NON deve ricevere <div>, <span>, ecc. nella label
   del pulsante.

   Adesso la label è solamente testo/Markdown.
*/

div[data-testid="stButton"] > button.roster-player-button {
    width: 100% !important;

    background: #111827 !important;

    border: 1px solid rgba(255, 255, 255, 0.08) !important;

    border-radius: 12px !important;

    padding: 10px 12px !important;

    margin-bottom: 6px !important;

    min-height: 72px !important;

    text-align: left !important;

    color: #FFFFFF !important;

    transition:
        background 0.15s ease-in-out,
        border-color 0.15s ease-in-out,
        transform 0.15s ease-in-out !important;

    box-shadow: none !important;
}


div[data-testid="stButton"] > button.roster-player-button:hover {
    background: #161F33 !important;

    border-color: rgba(16, 185, 129, 0.45) !important;

    color: #FFFFFF !important;

    transform: translateY(-1px);

    box-shadow:
        0 4px 14px rgba(0, 0, 0, 0.20) !important;
}


div[data-testid="stButton"] > button.roster-player-button:focus {
    background: #182238 !important;

    border-color: #10B981 !important;

    color: #FFFFFF !important;

    box-shadow:
        0 0 0 1px #10B981,
        0 0 12px rgba(16, 185, 129, 0.20) !important;
}


/*
   Tutto il testo interno del pulsante deve rimanere bianco.
*/

div[data-testid="stButton"] > button.roster-player-button p,
div[data-testid="stButton"] > button.roster-player-button span,
div[data-testid="stButton"] > button.roster-player-button div {
    color: #FFFFFF !important;
}


/* =========================================================
   GENERIC STREAMLIT BUTTON RESET
   ========================================================= */

div[data-testid="stButton"] > button {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}


/* =========================================================
   METRICS
   ========================================================= */

[data-testid="stMetric"] {
    background: #111827 !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 12px !important;
    padding: 14px !important;
}

[data-testid="stMetricLabel"] {
    color: #94A3B8 !important;
}

[data-testid="stMetricValue"] {
    color: #F8FAFC !important;
}


/* =========================================================
   CHECKBOX
   ========================================================= */

[data-testid="stCheckbox"] label p {
    color: #CBD5E1 !important;
    font-size: 0.78rem !important;
}


/* =========================================================
   SLIDER
   ========================================================= */

[data-testid="stSlider"] label p {
    color: #CBD5E1 !important;
    font-size: 0.78rem !important;
}


/* =========================================================
   SELECTBOX LABEL
   ========================================================= */

[data-testid="stSelectbox"] label p {
    color: #94A3B8 !important;
    font-size: 0.75rem !important;
    font-weight: 600 !important;
}


/* =========================================================
   DIVIDER
   ========================================================= */

hr {
    border-color: rgba(255, 255, 255, 0.06) !important;
}


/* =========================================================
   DATAFRAME / TABLE
   ========================================================= */

[data-testid="stDataFrame"] {
    border-radius: 12px !important;
    overflow: hidden !important;
}


/* =========================================================
   ALERTS
   ========================================================= */

[data-testid="stAlert"] {
    border-radius: 10px !important;
}


/* =========================================================
   HIDE EMPTY STREAMLIT ELEMENT SPACING
   ========================================================= */

.element-container {
    margin-bottom: 0.25rem;
}

</style>
"""

st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)


# ==========================================
# 3. SUPABASE
# ==========================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ SUPABASE_URL e/o SUPABASE_KEY non configurate.")
    st.stop()


@st.cache_resource
def init_supabase():
    return create_client(
        SUPABASE_URL,
        SUPABASE_KEY
    )


supabase = init_supabase()


# ==========================================
# 4. GENERIC DATA FETCH
# ==========================================

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


# ==========================================
# 5. LOAD DATABASE TABLES
# ==========================================

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


# ==========================================
# 6. LOAD RIGORISTI
# ==========================================

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


# ==========================================
# 7. LOAD TIRATORI PUNIZIONI
# ==========================================

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


# ==========================================
# 8. LOAD TITOLARI / INFORTUNI
# ==========================================

@st.cache_data(ttl=300)
def load_titolari_infortuni():

    url = (
        "https://raw.githubusercontent.com/"
        "fanta-ai-coder/fanta-ai-etl/"
        "refs/heads/main/titolari_infortuni"
    )

    try:

        df = pd.read_csv(url)

        if "nome_giocatore" in df.columns:
            df["nome_giocatore"] = (
                df["nome_giocatore"]
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

        if "titolarita" in df.columns:
            df["titolarita"] = (
                df["titolarita"]
                .astype(str)
                .str.lower()
                .str.strip()
            )

        if "squalificato" in df.columns:
            df["squalificato"] = (
                df["squalificato"]
                .astype(str)
                .str.lower()
                .str.strip()
            )

        if "infortunato" in df.columns:
            df["infortunato"] = (
                df["infortunato"]
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


# ==========================================
# 9. LOAD ALL DATA
# ==========================================

rigoristi_df = load_rigoristi()
punizioni_df = load_punizioni()
titolari_df = load_titolari_infortuni()


# ==========================================
# 10. STATISTICAL UTILITIES
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

        result["player_id"] = (
            normalize_player_id_series(
                result["player_id"]
            )
        )

    return result


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


def season_sort_key(value):

    try:

        return int(
            str(value)
            .strip()
            .split("/")[0]
        )

    except Exception:

        return -1


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


# ==========================================
# 11. PLAYER SUMMARY
# ==========================================

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

    # --------------------------------------
    # RANKING
    # --------------------------------------

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

        available_rank_cols = [
            c
            for c in rank_cols
            if c in rdf.columns
        ]

        rdf_unique = (
            rdf
            .drop_duplicates(
                subset=["player_id"]
            )[available_rank_cols]
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

    # --------------------------------------
    # TITOLARI / INFORTUNI
    # --------------------------------------

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

        merge_columns = [
            "nome_norm",
            "squadra_norm",
            "titolarita",
            "squalificato",
            "infortunato"
        ]

        merge_columns = [
            c
            for c in merge_columns
            if c in tdf_unique.columns
        ]

        base = pd.merge(
            base,
            tdf_unique[merge_columns],
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

    # --------------------------------------
    # STATISTICHE
    # --------------------------------------

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

        voto = pd.to_numeric(
            sdf.get("voto"),
            errors="coerce"
        )

        gf = pd.to_numeric(
            sdf.get("gf", 0),
            errors="coerce"
        ).fillna(0)

        rf = pd.to_numeric(
            sdf.get("rf", 0),
            errors="coerce"
        ).fillna(0)

        ass = pd.to_numeric(
            sdf.get("ass", 0),
            errors="coerce"
        ).fillna(0)

        au = pd.to_numeric(
            sdf.get("au", 0),
            errors="coerce"
        ).fillna(0)

        esp = pd.to_numeric(
            sdf.get("esp", 0),
            errors="coerce"
        ).fillna(0)

        amm = pd.to_numeric(
            sdf.get("amm", 0),
            errors="coerce"
        ).fillna(0)

        gs = pd.to_numeric(
            sdf.get("gs", 0),
            errors="coerce"
        ).fillna(0)

        rp = pd.to_numeric(
            sdf.get("rp", 0),
            errors="coerce"
        ).fillna(0)

        clean_sheet = pd.Series(
            0.0,
            index=sdf.index
        )

        for column in [
            "pi",
            "porta_inviolata",
            "clean_sheet",
            "imbattuto"
        ]:

            if column in sdf.columns:

                clean_sheet = pd.to_numeric(
                    sdf[column],
                    errors="coerce"
                ).fillna(0)

                break

        # ----------------------------------
        # FANTAVOTO
        # ----------------------------------

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

        sdf["_fanta_calc"] = fv
        sdf["_voto_num"] = voto

        valid = sdf[
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


# ==========================================
# 12. HEADER
# ==========================================

st.markdown(
    """
    <div class="top-header"
         style="
            display:flex;
            align-items:center;
            justify-content:space-between;
         ">

        <div style="
            display:flex;
            align-items:center;
            gap:12px;
        ">

            <div style="
                background:#10B981;
                color:#0B0F19;
                border-radius:8px;
                width:36px;
                height:36px;
                display:flex;
                align-items:center;
                justify-content:center;
                font-weight:800;
            ">
                ⚡
            </div>

            <div>

                <div style="
                    font-weight:800;
                    font-size:1.1rem;
                    color:#F8FAFC;
                    letter-spacing:-0.02em;
                ">
                    FantaAI
                    <span style="color:#34D399;">
                        Analytics Pro
                    </span>
                </div>

                <div style="
                    font-size:0.72rem;
                    color:#94A3B8;
                ">
                    SERIE A — ASTA LIVE READY
                </div>

            </div>

        </div>


        <div style="
            display:flex;
            align-items:center;
            gap:16px;
        ">

            <div style="
                background:rgba(255,255,255,0.05);
                padding:6px 14px;
                border-radius:8px;
                border:1px solid rgba(255,255,255,0.08);
                text-align:right;
            ">

                <div style="
                    font-size:0.65rem;
                    color:#64748B;
                ">
                    BUDGET FANTAMEDIA
                </div>

                <div style="
                    font-size:0.85rem;
                    font-weight:700;
                    color:#F8FAFC;
                ">
                    342 / 500 FM
                </div>

            </div>


            <div style="
                background:rgba(16,185,129,0.10);
                padding:6px 12px;
                border-radius:8px;
                border:1px solid rgba(16,185,129,0.20);
                color:#34D399;
                font-size:0.75rem;
                font-weight:600;
            ">
                ● Supabase Live
            </div>

        </div>

    </div>
    """,
    unsafe_allow_html=True
)


# ==========================================
# 13. DATA LOADING
# ==========================================

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


# ==========================================
# 14. NORMALIZATION
# ==========================================

df = normalize_dataframe(df)
quot = normalize_dataframe(quot)
ranking_df = normalize_dataframe(ranking_df)

df = remove_starred_vote_rows(df)


# ==========================================
# 15. CURRENT SEASON
# ==========================================

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


# ==========================================
# 16. SUMMARY
# ==========================================

summary_df = compute_player_summaries(
    df,
    current_quot,
    ranking_df,
    titolari_df
)


# ==========================================
# 17. MAIN LAYOUT
# ==========================================

col_roster, col_dossier = st.columns(
    [0.35, 0.65],
    gap="medium"
)


# ==========================================
# 18. LEFT — ROSTER
# ==========================================

with col_roster:

    st.markdown(
        """
        <div style="margin-bottom:12px;">

            <div style="
                font-size:0.95rem;
                font-weight:800;
                color:#F8FAFC;
            ">
                🔍 FILTRI SCOUTING
            </div>

            <div style="
                font-size:0.72rem;
                color:#64748B;
            ">
                Trova e ordina i calciatori nel listone
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )


    search_query = st.text_input(
        "Ricerca",
        placeholder="Cerca giocatore o squadra...",
        label_visibility="collapsed"
    )


    st.markdown(
        '<div id="role-filter-anchor"></div>',
        unsafe_allow_html=True
    )


    selected_role = st.radio(
        "Seleziona Ruolo",
        ["Tutti", "P", "D", "C", "A"],
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
        + sorted(list(squadre_raw))
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


    st.markdown(
        """
        <hr style="
            border-color:rgba(255,255,255,0.06);
            margin:12px 0;
        ">
        """,
        unsafe_allow_html=True
    )


    # ======================================
    # FILTER DATAFRAME
    # ======================================

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
            quot_view["is_titolare"] == True
        ]


    if (
        min_partite > 0
        and "presenze_totali" in quot_view.columns
    ):

        quot_view = quot_view[
            quot_view["presenze_totali"]
            >= min_partite
        ]


    # ======================================
    # SORT
    # ======================================

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
            by=["nome"],
            ascending=[True],
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


    # ======================================
    # ROSTER TITLE
    # ======================================

    st.markdown(
        f"""
        <div style="
            font-size:0.75rem;
            color:#94A3B8;
            font-weight:700;
            margin-bottom:8px;
        ">
            ROSTER SELEZIONATO ({len(quot_view)})
        </div>
        """,
        unsafe_allow_html=True
    )


    # ======================================
    # EMPTY
    # ======================================

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


        role_colors = {
            "P": "🟨",
            "D": "🟦",
            "C": "🟩",
            "A": "🟥"
        }


        role_names = {
            "P": "PORTIERI",
            "D": "DIFENSORI",
            "C": "CENTROCAMPO",
            "A": "ATTACCANTI"
        }


        # ==================================
        # ACTIVE PLAYER
        # ==================================

        current_active = (
            st.session_state.get(
                "active_player_id"
            )
        )


        available_ids = (
            options_df["player_id"]
            .dropna()
            .astype(int)
            .tolist()
        )


        if (
            current_active is None
            or current_active not in available_ids
        ):

            st.session_state[
                "active_player_id"
            ] = available_ids[0]


        # ==================================
        # SCROLLABLE ROSTER
        # ==================================

        with st.container(height=650):

            for row in options_df.itertuples():

                pid = int(
                    getattr(
                        row,
                        "player_id"
                    )
                )


                n = getattr(
                    row,
                    "nome",
                    "Giocatore"
                )


                s = getattr(
                    row,
                    "squadra",
                    "-"
                )


                r = str(
                    getattr(
                        row,
                        "ruolo",
                        ""
                    )
                ).upper().strip()


                ind = getattr(
                    row,
                    "indice_finale",
                    None
                )


                fm = getattr(
                    row,
                    "fantamedia",
                    None
                )


                pg = getattr(
                    row,
                    "presenze_totali",
                    0
                )


                q_att = getattr(
                    row,
                    "quotazione_attuale",
                    0
                )


                fvm = getattr(
                    row,
                    "fvm",
                    0
                )


                rk_r = getattr(
                    row,
                    "rank_ruolo",
                    None
                )


                # --------------------------
                # FORMAT VALUES
                # --------------------------

                ind_str = (
                    f"{float(ind):.1f}"
                    if pd.notna(ind)
                    else "N/D"
                )


                fm_str = (
                    f"{float(fm):.2f}"
                    if pd.notna(fm)
                    else "N/D"
                )


                rk_str = (
                    f"#{int(rk_r)}"
                    if pd.notna(rk_r)
                    else "-"
                )


                # --------------------------
                # ROLE
                # --------------------------

                role_icon = role_colors.get(
                    r,
                    "⚪"
                )


                role_name = role_names.get(
                    r,
                    "GIOCATORI"
                )


                # --------------------------
                # RIGORISTI / PUNIZIONI
                # --------------------------

                n_norm = (
                    str(n)
                    .upper()
                    .strip()
                )

                s_norm = (
                    str(s)
                    .upper()
                    .strip()
                )


                is_rig = False

                if not rigoristi_df.empty:

                    is_rig = not rigoristi_df[
                        (
                            rigoristi_df["giocatore"]
                            == n_norm
                        )
                        &
                        (
                            rigoristi_df["squadra"]
                            == s_norm
                        )
                    ].empty


                is_pun = False

                if not punizioni_df.empty:

                    is_pun = not punizioni_df[
                        (
                            punizioni_df["giocatore"]
                            == n_norm
                        )
                        &
                        (
                            punizioni_df["squadra"]
                            == s_norm
                        )
                    ].empty


                # --------------------------
                # BADGES — SOLO TESTO
                # --------------------------

                badges = []

                if is_rig:
                    badges.append(
                        "🎯 Rigorista"
                    )

                if is_pun:
                    badges.append(
                        "⚡ Punizioni"
                    )

                badges_text = (
                    " · ".join(badges)
                    if badges
                    else ""
                )


                # --------------------------
                # ACTIVE
                # --------------------------

                is_active = (
                    st.session_state[
                        "active_player_id"
                    ] == pid
                )


                # ==================================================
                # IMPORTANTISSIMO:
                #
                # NIENTE HTML.
                #
                # La label del pulsante contiene solamente testo
                # e Markdown supportato da Streamlit.
                # ==================================================

                button_label = (
                    f"{role_icon}  "
                    f"**{n}**  ·  "
                    f"{s}  ·  "
                    f"{role_name}\n\n"
                    f"📊 Indice **{ind_str}**  "
                    f"·  ⭐ FM **{fm_str}**  "
                    f"·  PG **{pg}**  "
                    f"·  Q **{q_att}**  "
                    f"·  FVM **{fvm}**"
                )


                if badges_text:

                    button_label += (
                        f"\n{badges_text}"
                    )


                # ----------------------------------------------
                # BUTTON
                # ----------------------------------------------

                if st.button(
                    button_label,
                    key=f"card_btn_{pid}",
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


        selected_id = (
            st.session_state
            .get("active_player_id")
        )


# ==========================================
# 19. RIGHT — DOSSIER
# ==========================================

with col_dossier:

    if selected_id is None:

        st.info(
            "👈 Seleziona un giocatore dalla lista "
            "a sinistra per aprire la scheda analitica."
        )

    else:

        player_id = int(
            float(selected_id)
        )


        # ==================================
        # PLAYER QUOTES
        # ==================================

        p_quotes = quot[
            quot["player_id"]
            == player_id
        ].copy()


        current_quote = (
            get_latest_quote_row(
                p_quotes
            )
        )


        # ==================================
        # PLAYER STATS
        # ==================================

        p_stats = df[
            df["player_id"]
            == player_id
        ].copy()


        # ==================================
        # BASIC PLAYER INFO
        # ==================================

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


        # ==================================
        # NORMALIZED NAMES
        # ==================================

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


        # ==================================
        # RANKING
        # ==================================

        ranking_row = get_player_ranking(
            ranking_df,
            player_id
        )


        # ==================================
        # TITOLARI / INFORTUNI
        # ==================================

        if not titolari_df.empty:

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

        else:

            titolare_info = pd.DataFrame()


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


        # ==================================
        # STATUS TAGS
        # ==================================

        tags_html = ""


        if "titolare" in titolarita_val:

            tags_html += """
            <span style="
                background:rgba(16,185,129,0.15);
                color:#34D399;
                border:1px solid rgba(16,185,129,0.30);
                padding:4px 10px;
                border-radius:9999px;
                font-size:0.72rem;
                font-weight:700;
                text-transform:uppercase;
                display:inline-block;
                margin-right:4px;
            ">
                🟢 Titolare
            </span>
            """

        elif (
            "panchina" in titolarita_val
            or "riserva" in titolarita_val
        ):

            tags_html += """
            <span style="
                background:rgba(245,158,11,0.15);
                color:#FBBF24;
                border:1px solid rgba(245,158,11,0.30);
                padding:4px 10px;
                border-radius:9999px;
                font-size:0.72rem;
                font-weight:700;
                text-transform:uppercase;
                display:inline-block;
                margin-right:4px;
            ">
                🟠 Panchina
            </span>
            """


        if infortunato_val in [
            "sì",
            "si",
            "true",
            "1",
            "yes"
        ]:

            tags_html += """
            <span style="
                background:rgba(239,68,68,0.15);
                color:#F87171;
                border:1px solid rgba(239,68,68,0.30);
                padding:4px 10px;
                border-radius:9999px;
                font-size:0.72rem;
                font-weight:700;
                text-transform:uppercase;
                display:inline-block;
                margin-right:4px;
            ">
                🚑 Infortunato
            </span>
            """


        # ==================================
        # INJURY DESCRIPTION
        # ==================================

        desc_html = ""


        if (
            desc_infortunio
            and desc_infortunio.lower()
            != "nan"
        ):

            safe_desc = html.escape(
                desc_infortunio
            )

            desc_html = f"""
            <div style="
                font-size:0.8rem;
                color:#FCA5A5;
                margin-top:8px;
                font-weight:600;
                background:rgba(239,68,68,0.10);
                padding:6px 12px;
                border-radius:6px;
                display:inline-block;
            ">
                ⚠️ {safe_desc}
            </div>
            """


        # ==================================
        # RANKING VALUES
        # ==================================

        if (
            ranking_row is not None
            and pd.notna(
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
            and pd.notna(
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


        # ==================================
        # QUOTE
        # ==================================

        if current_quote is not None:

            quota_val = current_quote.get(
                "quotazione_attuale",
                38
            )

            fvm_val = current_quote.get(
                "fvm",
                320
            )

        else:

            quota_val = 38
            fvm_val = 320


        # ==========================================
        # DOSSIER HEADER
        #
        # Questo HTML è CORRETTO perché viene
        # passato a st.markdown(..., unsafe_allow_html=True)
        #
        # NON viene passato a st.button().
        # ==========================================

        dossier_header_html = f"""
        <div class="glass-panel">

            <div style="
                display:flex;
                justify-content:space-between;
                align-items:flex-start;
                gap:20px;
            ">

                <div style="
                    min-width:0;
                    flex:1;
                ">

                    <div style="
                        display:flex;
                        align-items:center;
                        gap:8px;
                        margin-bottom:6px;
                    ">

                        <span style="
                            background:#10B981;
                            color:#0B0F19;
                            font-weight:800;
                            font-size:0.8rem;
                            padding:2px 8px;
                            border-radius:6px;
                        ">
                            {html.escape(str(ruolo))}
                        </span>

                        <span style="
                            color:#94A3B8;
                            font-size:0.9rem;
                            font-weight:600;
                        ">
                            {html.escape(str(squadra))}
                        </span>

                    </div>


                    <h1 style="
                        margin:0;
                        font-size:2.2rem;
                        font-weight:800;
                        color:#F8FAFC;
                        letter-spacing:-0.03em;
                        line-height:1.15;
                        overflow-wrap:anywhere;
                    ">
                        {html.escape(str(nome))}
                    </h1>


                    <div style="
                        margin-top:10px;
                    ">
                        {tags_html}
                    </div>


                    {desc_html}

                </div>


                <div style="
                    text-align:right;
                    background:rgba(255,255,255,0.03);
                    padding:12px 18px;
                    border-radius:12px;
                    border:1px solid rgba(255,255,255,0.06);
                    flex-shrink:0;
                ">

                    <div style="
                        font-size:0.7rem;
                        color:#94A3B8;
                        font-weight:700;
                        text-transform:uppercase;
                    ">
                        RANKING RUOLO
                    </div>


                    <div style="
                        font-size:1.8rem;
                        font-weight:800;
                        color:#34D399;
                        line-height:1.2;
                    ">
                        #{rk_ruolo}

                        <span style="
                            font-size:0.9rem;
                            color:#64748B;
                        ">
                            / {tot_ruolo}
                        </span>
                    </div>


                    <div style="
                        font-size:0.75rem;
                        color:#CBD5E1;
                        margin-top:4px;
                    ">
                        Quotazione:
                        <b>{quota_val}</b>

                        &nbsp;|&nbsp;

                        FVM:
                        <b style="
                            color:#F59E0B;
                        ">
                            {fvm_val} FM
                        </b>
                    </div>

                </div>

            </div>

        </div>
        """


        # ==================================
        # RENDER DOSSIER
        # ==================================

        st.markdown(
            dossier_header_html,
            unsafe_allow_html=True
        )


        # ==========================================
        # STATISTICHE BASE
        #
        # Anche qui usiamo HTML SOLO dentro
        # st.markdown(), mai dentro st.button().
        # ==========================================

        player_summary = summary_df[
            summary_df["player_id"]
            == player_id
        ]


        if not player_summary.empty:

            summary_row = (
                player_summary.iloc[0]
            )


            fantamedia_val = summary_row.get(
                "fantamedia",
                None
            )


            media_voto_val = summary_row.get(
                "media_voto",
                None
            )


            presenze_val = summary_row.get(
                "presenze_totali",
                0
            )


            indice_val = summary_row.get(
                "indice_finale",
                None
            )


            fantamedia_display = (
                f"{float(fantamedia_val):.2f}"
                if pd.notna(fantamedia_val)
                else "N/D"
            )


            media_display = (
                f"{float(media_voto_val):.2f}"
                if pd.notna(media_voto_val)
                else "N/D"
            )


            indice_display = (
                f"{float(indice_val):.1f}"
                if pd.notna(indice_val)
                else "N/D"
            )


        else:

            fantamedia_display = "N/D"
            media_display = "N/D"
            presenze_val = 0
            indice_display = "N/D"


        # ==================================
        # STATS CARDS
        # ==================================

        stats_html = f"""
        <div style="
            display:grid;
            grid-template-columns:
                repeat(4, minmax(0, 1fr));
            gap:10px;
            margin-top:14px;
        ">

            <div style="
                background:#111827;
                border:1px solid rgba(255,255,255,0.08);
                border-radius:12px;
                padding:14px;
            ">

                <div style="
                    font-size:0.68rem;
                    color:#64748B;
                    font-weight:700;
                    text-transform:uppercase;
                ">
                    INDICE
                </div>

                <div style="
                    font-size:1.55rem;
                    color:#34D399;
                    font-weight:800;
                    margin-top:4px;
                ">
                    {indice_display}
                </div>

            </div>


            <div style="
                background:#111827;
                border:1px solid rgba(255,255,255,0.08);
                border-radius:12px;
                padding:14px;
            ">

                <div style="
                    font-size:0.68rem;
                    color:#64748B;
                    font-weight:700;
                    text-transform:uppercase;
                ">
                    FANTAMEDIA
                </div>

                <div style="
                    font-size:1.55rem;
                    color:#34D399;
                    font-weight:800;
                    margin-top:4px;
                ">
                    {fantamedia_display}
                </div>

            </div>


            <div style="
                background:#111827;
                border:1px solid rgba(255,255,255,0.08);
                border-radius:12px;
                padding:14px;
            ">

                <div style="
                    font-size:0.68rem;
                    color:#64748B;
                    font-weight:700;
                    text-transform:uppercase;
                ">
                    MEDIA VOTO
                </div>

                <div style="
                    font-size:1.55rem;
                    color:#F8FAFC;
                    font-weight:800;
                    margin-top:4px;
                ">
                    {media_display}
                </div>

            </div>


            <div style="
                background:#111827;
                border:1px solid rgba(255,255,255,0.08);
                border-radius:12px;
                padding:14px;
            ">

                <div style="
                    font-size:0.68rem;
                    color:#64748B;
                    font-weight:700;
                    text-transform:uppercase;
                ">
                    PRESENZE
                </div>

                <div style="
                    font-size:1.55rem;
                    color:#F8FAFC;
                    font-weight:800;
                    margin-top:4px;
                ">
                    {presenze_val}
                </div>

            </div>

        </div>
        """


        st.markdown(
            stats_html,
            unsafe_allow_html=True
        )
