import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from supabase import create_client, ClientOptions


# ============================================================
# CONFIGURAZIONE STREAMLIT
# ============================================================

st.set_page_config(
    page_title="FantaAI",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# STILE
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 2.4rem;
        font-weight: 700;
        margin-bottom: 0;
    }

    .subtitle {
        color: #777;
        font-size: 1rem;
        margin-bottom: 25px;
    }

    .section-title {
        font-size: 1.4rem;
        font-weight: 600;
        margin-top: 20px;
        margin-bottom: 10px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">⚽ FantaAI</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Serie A Analytics · Historical Player Performance'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# SUPABASE
# ============================================================

SUPABASE_URL = (
    os.getenv("SUPABASE_URL")
    or st.secrets.get("SUPABASE_URL")
)

SUPABASE_KEY = (
    os.getenv("SUPABASE_KEY")
    or st.secrets.get("SUPABASE_KEY")
)


if not SUPABASE_URL or not SUPABASE_KEY:

    st.error(
        "⚠️ Credenziali Supabase non trovate."
    )

    st.stop()


@st.cache_resource
def init_supabase():

    headers = {
        "apiKey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    return create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
        options=ClientOptions(
            headers=headers
        )
    )


try:

    supabase = init_supabase()

except Exception as e:

    st.error(
        f"Errore di connessione a Supabase: {e}"
    )

    st.stop()


# ============================================================
# CARICAMENTO DATI
# ============================================================

@st.cache_data(
    ttl=600,
    show_spinner="Caricamento dati da Supabase..."
)
def load_data():

    response = (
        supabase
        .table("player_stats")
        .select("*")
        .execute()
    )

    df = pd.DataFrame(
        response.data
    )

    return df


try:

    df = load_data()

except Exception as e:

    st.error(
        f"Errore durante la lettura dei dati: {e}"
    )

    st.stop()


if df.empty:

    st.warning(
        "Nessun dato trovato nella tabella player_stats."
    )

    st.stop()


# ============================================================
# PREPARAZIONE DATI
# ============================================================

numeric_columns = [
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


for column in numeric_columns:

    if column in df.columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        ).fillna(0)


df["season"] = (
    df["season"]
    .astype(str)
)


# ------------------------------------------------------------
# Nome leggibile stagione
# ------------------------------------------------------------

def season_label(season):

    try:

        year = int(season)

        return f"{year}/{str(year + 1)[-2:]}"

    except:

        return str(season)


df["season_label"] = df["season"].apply(
    season_label
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("⚙️ Filtri")


# ------------------------------------------------------------
# Stagione
# ------------------------------------------------------------

available_seasons = sorted(
    df["season"].unique(),
    reverse=True
)

season_options = [
    "Tutte"
] + available_seasons


selected_season = st.sidebar.selectbox(
    "Stagione",
    season_options,
    format_func=lambda x:
        "Tutte le stagioni"
        if x == "Tutte"
        else season_label(x)
)


# ------------------------------------------------------------
# Squadra
# ------------------------------------------------------------

available_teams = sorted(
    df["team"]
    .dropna()
    .unique()
    .tolist()
)

selected_team = st.sidebar.selectbox(
    "Squadra",
    ["Tutte"] + available_teams
)


# ------------------------------------------------------------
# Ruolo
# ------------------------------------------------------------

if "position" in df.columns:

    available_positions = sorted(
        df["position"]
        .dropna()
        .replace("", "N/A")
        .unique()
        .tolist()
    )

else:

    available_positions = []


selected_positions = st.sidebar.multiselect(
    "Ruolo",
    available_positions,
    default=available_positions
)


# ------------------------------------------------------------
# Minuti
# ------------------------------------------------------------

max_minutes = int(
    df["minutes_played"].max()
)

min_minutes = st.sidebar.slider(
    "Minuti minimi",
    min_value=0,
    max_value=max_minutes,
    value=min(900, max_minutes),
    step=90
)


# ============================================================
# FILTRAGGIO
# ============================================================

df_filtered = df.copy()


if selected_season != "Tutte":

    df_filtered = df_filtered[
        df_filtered["season"] == selected_season
    ]


if selected_team != "Tutte":

    df_filtered = df_filtered[
        df_filtered["team"] == selected_team
    ]


if selected_positions:

    df_filtered = df_filtered[
        df_filtered["position"].isin(
            selected_positions
        )
    ]


df_filtered = df_filtered[
    df_filtered["minutes_played"] >= min_minutes
]


# ============================================================
# SIDEBAR INFO
# ============================================================

st.sidebar.markdown("---")

st.sidebar.caption(
    f"Record database: {len(df):,}"
)

st.sidebar.caption(
    f"Record filtrati: {len(df_filtered):,}"
)

st.sidebar.caption(
    f"Stagioni: {df['season'].nunique()}"
)


# ============================================================
# TABS PRINCIPALI
# ============================================================

tab_overview, tab_player, tab_compare, tab_scouting, tab_database = st.tabs(
    [
        "📊 Overview",
        "👤 Player Analysis",
        "⚔️ Confronto",
        "🔎 Scouting",
        "🗄️ Database"
    ]
)


# ============================================================
# TAB 1 — OVERVIEW
# ============================================================

with tab_overview:

    st.subheader(
        "📊 Overview"
    )

    # --------------------------------------------------------
    # KPI
    # --------------------------------------------------------

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "Giocatori",
        f"{len(df_filtered):,}"
    )

    col2.metric(
        "Gol",
        f"{int(df_filtered['goals'].sum()):,}"
    )

    col3.metric(
        "Assist",
        f"{int(df_filtered['assists'].sum()):,}"
    )

    col4.metric(
        "xG",
        f"{df_filtered['xg'].sum():,.1f}"
    )

    col5.metric(
        "xA",
        f"{df_filtered['xa'].sum():,.1f}"
    )

    st.markdown("---")

    # --------------------------------------------------------
    # TOP SCORER
    # --------------------------------------------------------

    col_left, col_right = st.columns(2)

    with col_left:

        st.markdown(
            "### 🥅 Top scorer"
        )

        top_goals = (
            df_filtered
            .sort_values(
                "goals",
                ascending=False
            )
            .head(15)
        )

        fig = px.bar(
            top_goals,
            x="goals",
            y="player_name",
            orientation="h",
            color="team",
            hover_data=[
                "matches_played",
                "minutes_played",
                "xg"
            ],
            labels={
                "goals": "Gol",
                "player_name": "Giocatore"
            }
        )

        fig.update_layout(
            yaxis=dict(
                categoryorder="total ascending"
            ),
            height=500
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    # --------------------------------------------------------
    # GOALS VS XG
    # --------------------------------------------------------

    with col_right:

        st.markdown(
            "### 🎯 Gol vs xG"
        )

        fig = px.scatter(
            df_filtered,
            x="xg",
            y="goals",
            size="minutes_played",
            color="team",
            hover_name="player_name",
            hover_data=[
                "matches_played",
                "goals_per_90",
                "xg_per_90"
            ],
            labels={
                "xg": "Expected Goals",
                "goals": "Gol"
            }
        )

        # linea xG = gol
        max_value = max(
            df_filtered["xg"].max(),
            df_filtered["goals"].max()
        )

        fig.add_shape(
            type="line",
            x0=0,
            y0=0,
            x1=max_value,
            y1=max_value,
            line=dict(
                dash="dash"
            )
        )

        fig.update_layout(
            height=500
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    # --------------------------------------------------------
    # TOP PER 90
    # --------------------------------------------------------

    st.markdown(
        "### 🚀 Migliori giocatori per rendimento offensivo"
    )

    top90 = (
        df_filtered
        .assign(
            goal_xa_per90=lambda x:
            x["goals_per_90"]
            + x["assists_per_90"]
        )
        .sort_values(
            "goal_xa_per90",
            ascending=False
        )
        .head(20)
    )

    display_cols = [
        "player_name",
        "team",
        "position",
        "minutes_played",
        "goals",
        "assists",
        "xg",
        "xa",
        "goals_per_90",
        "assists_per_90"
    ]

    st.dataframe(
        top90[display_cols],
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# TAB 2 — PLAYER ANALYSIS
# ============================================================

with tab_player:

    st.subheader(
        "👤 Analisi giocatore"
    )

    player_names = sorted(
        df["player_name"]
        .dropna()
        .unique()
        .tolist()
    )

    selected_player = st.selectbox(
        "Seleziona giocatore",
        player_names
    )

    player_df = (
        df[
            df["player_name"]
            == selected_player
        ]
        .sort_values("season")
    )

    if not player_df.empty:

        latest = player_df.iloc[-1]

        # ----------------------------------------------------
        # PLAYER HEADER
        # ----------------------------------------------------

        st.markdown(
            f"### {selected_player}"
        )

        info1, info2, info3, info4, info5 = st.columns(5)

        info1.metric(
            "Ultima squadra",
            latest["team"]
        )

        info2.metric(
            "Ruolo",
            latest["position"]
        )

        info3.metric(
            "Gol ultima stagione",
            int(latest["goals"])
        )

        info4.metric(
            "xG ultima stagione",
            round(latest["xg"], 2)
        )

        info5.metric(
            "Gol/90",
            round(latest["goals_per_90"], 2)
        )

        st.markdown("---")

        # ----------------------------------------------------
        # EVOLUZIONE GOL / ASSIST
        # ----------------------------------------------------

        col1, col2 = st.columns(2)

        with col1:

            fig = px.line(
                player_df,
                x="season_label",
                y=["goals", "assists"],
                markers=True,
                title="Gol e assist per stagione",
                labels={
                    "value": "Totale",
                    "season_label": "Stagione",
                    "variable": "Metrica"
                }
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        with col2:

            fig = px.line(
                player_df,
                x="season_label",
                y=["xg", "xa"],
                markers=True,
                title="xG e xA per stagione",
                labels={
                    "value": "Valore",
                    "season_label": "Stagione",
                    "variable": "Metrica"
                }
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        # ----------------------------------------------------
        # PER 90
        # ----------------------------------------------------

        st.markdown(
            "### 📈 Evoluzione rendimento per 90"
        )

        per90_cols = [
            "goals_per_90",
            "assists_per_90",
            "xg_per_90",
            "xa_per_90"
        ]

        fig = px.line(
            player_df,
            x="season_label",
            y=per90_cols,
            markers=True,
            labels={
                "value": "Per 90",
                "season_label": "Stagione",
                "variable": "Metrica"
            }
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        # ----------------------------------------------------
        # STORICO
        # ----------------------------------------------------

        st.markdown(
            "### 📋 Storico stagionale"
        )

        history_cols = [
            "season_label",
            "team",
            "position",
            "matches_played",
            "minutes_played",
            "goals",
            "assists",
            "xg",
            "xa",
            "shots_total",
            "key_passes",
            "goals_per_90",
            "xg_per_90"
        ]

        st.dataframe(
            player_df[history_cols],
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# TAB 3 — CONFRONTO
# ============================================================

with tab_compare:

    st.subheader(
        "⚔️ Confronto giocatori"
    )

    compare_players = st.multiselect(
        "Seleziona 2-5 giocatori",
        sorted(
            df["player_name"]
            .dropna()
            .unique()
        ),
        max_selections=5
    )

    if len(compare_players) >= 2:

        compare_df = df[
            df["player_name"]
            .isin(compare_players)
        ]

        # ----------------------------------------------------
        # STAGIONE
        # ----------------------------------------------------

        compare_season = st.selectbox(
            "Stagione confronto",
            ["Tutte"] + sorted(
                compare_df["season"].unique(),
                reverse=True
            ),
            format_func=lambda x:
                "Tutte le stagioni"
                if x == "Tutte"
                else season_label(x)
        )

        if compare_season != "Tutte":

            compare_df = compare_df[
                compare_df["season"]
                == compare_season
            ]

        # ----------------------------------------------------
        # METRICA
        # ----------------------------------------------------

        metric = st.selectbox(
            "Metrica",
            [
                "goals_per_90",
                "assists_per_90",
                "xg_per_90",
                "xa_per_90",
                "shots_per_90",
                "key_passes_per_90"
            ],
            format_func=lambda x: {
                "goals_per_90": "Gol / 90",
                "assists_per_90": "Assist / 90",
                "xg_per_90": "xG / 90",
                "xa_per_90": "xA / 90",
                "shots_per_90": "Tiri / 90",
                "key_passes_per_90": "Key passes / 90"
            }[x]
        )

        fig = px.bar(
            compare_df,
            x="player_name",
            y=metric,
            color="team",
            text_auto=".2f",
            labels={
                "player_name": "Giocatore",
                metric: metric
            }
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        # ----------------------------------------------------
        # RADAR
        # ----------------------------------------------------

        st.markdown(
            "### 🕸️ Profilo comparativo"
        )

        radar_metrics = [
            "goals_per_90",
            "assists_per_90",
            "xg_per_90",
            "xa_per_90",
            "shots_per_90",
            "key_passes_per_90"
        ]

        labels = [
            "Gol/90",
            "Assist/90",
            "xG/90",
            "xA/90",
            "Tiri/90",
            "Key Pass/90"
        ]

        fig = go.Figure()

        for _, row in compare_df.iterrows():

            values = [
                row[m]
                for m in radar_metrics
            ]

            # normalizzazione rispetto al massimo
            max_values = [
                max(
                    df[m].max(),
                    0.01
                )
                for m in radar_metrics
            ]

            normalized = [
                min(
                    value / max_value,
                    1
                )
                for value, max_value
                in zip(values, max_values)
            ]

            normalized.append(
                normalized[0]
            )

            fig.add_trace(
                go.Scatterpolar(
                    r=normalized,
                    theta=labels + [labels[0]],
                    fill="toself",
                    name=row["player_name"]
                )
            )

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1]
                )
            ),
            showlegend=True
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    else:

        st.info(
            "Seleziona almeno 2 giocatori per iniziare il confronto."
        )


# ============================================================
# TAB 4 — SCOUTING
# ============================================================

with tab_scouting:

    st.subheader(
        "🔎 Scouting giocatori"
    )

    st.markdown(
        "Trova i giocatori più interessanti in base "
        "alle metriche che ti interessano."
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        min_goals90 = st.number_input(
            "Minimo Gol/90",
            min_value=0.0,
            max_value=5.0,
            value=0.0,
            step=0.05
        )

    with col2:

        min_xg90 = st.number_input(
            "Minimo xG/90",
            min_value=0.0,
            max_value=5.0,
            value=0.0,
            step=0.05
        )

    with col3:

        min_assists90 = st.number_input(
            "Minimo Assist/90",
            min_value=0.0,
            max_value=5.0,
            value=0.0,
            step=0.05
        )

    scouting = df_filtered.copy()

    scouting = scouting[
        scouting["goals_per_90"]
        >= min_goals90
    ]

    scouting = scouting[
        scouting["xg_per_90"]
        >= min_xg90
    ]

    scouting = scouting[
        scouting["assists_per_90"]
        >= min_assists90
    ]

    # --------------------------------------------------------
    # INDICE OFFENSIVO
    # --------------------------------------------------------

    if not scouting.empty:

        scouting = scouting.copy()

        scouting["attacking_index"] = (
            scouting["goals_per_90"] * 0.35
            + scouting["assists_per_90"] * 0.20
            + scouting["xg_per_90"] * 0.30
            + scouting["xa_per_90"] * 0.15
        )

        scouting = scouting.sort_values(
            "attacking_index",
            ascending=False
        )

    st.markdown(
        f"### {len(scouting)} giocatori trovati"
    )

    scouting_cols = [
        "player_name",
        "team",
        "position",
        "minutes_played",
        "goals",
        "assists",
        "xg",
        "xa",
        "goals_per_90",
        "assists_per_90",
        "xg_per_90",
        "xa_per_90",
        "attacking_index"
    ]

    if not scouting.empty:

        st.dataframe(
            scouting[scouting_cols],
            use_container_width=True,
            hide_index=True
        )

        # ----------------------------------------------------
        # SCATTER SCOUTING
        # ----------------------------------------------------

        fig = px.scatter(
            scouting,
            x="xg_per_90",
            y="goals_per_90",
            size="minutes_played",
            color="position",
            hover_name="player_name",
            hover_data=[
                "team",
                "assists_per_90",
                "xa_per_90"
            ],
            labels={
                "xg_per_90": "xG / 90",
                "goals_per_90": "Gol / 90"
            },
            title="Efficienza realizzativa"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    else:

        st.info(
            "Nessun giocatore soddisfa i criteri selezionati."
        )


# ============================================================
# TAB 5 — DATABASE
# ============================================================

with tab_database:

    st.subheader(
        "🗄️ Database giocatori"
    )

    st.caption(
        f"{len(df_filtered):,} record visualizzati"
    )

    database_columns = [
        "player_name",
        "team",
        "season_label",
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
        "goals_per_90",
        "assists_per_90",
        "xg_per_90",
        "xa_per_90",
        "shots_per_90",
        "key_passes_per_90"
    ]

    database_columns = [
        c
        for c in database_columns
        if c in df_filtered.columns
    ]

    st.dataframe(
        df_filtered[
            database_columns
        ].sort_values(
            "goals",
            ascending=False
        ),
        use_container_width=True,
        hide_index=True,
        height=600
    )
