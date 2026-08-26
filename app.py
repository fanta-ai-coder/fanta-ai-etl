import os
import re
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from supabase import create_client


# ============================================================
# CONFIGURAZIONE
# ============================================================

st.set_page_config(
    page_title="FantaAI",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

    /* Layout generale */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1500px;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        min-width: 320px;
        max-width: 360px;
    }

    /* Titolo */
    .main-title {
        font-size: 42px;
        font-weight: 800;
        margin-bottom: 0;
    }

    .subtitle {
        color: #6b7280;
        font-size: 16px;
        margin-top: -5px;
        margin-bottom: 30px;
    }

    /* Player header */
    .player-header {
        padding: 20px 0 25px 0;
        border-bottom: 1px solid #e5e7eb;
        margin-bottom: 25px;
    }

    .player-name {
        font-size: 34px;
        font-weight: 800;
        line-height: 1.1;
    }

    .player-meta {
        color: #6b7280;
        font-size: 16px;
        margin-top: 8px;
    }

    /* KPI */
    div[data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 15px;
    }

    div[data-testid="stMetricLabel"] {
        font-size: 13px;
    }

    div[data-testid="stMetricValue"] {
        font-size: 27px;
        font-weight: 700;
    }

    /* Sezioni */
    .section-title {
        font-size: 22px;
        font-weight: 750;
        margin-top: 25px;
        margin-bottom: 12px;
    }

    /* Player list */
    .player-count {
        color: #6b7280;
        font-size: 13px;
        margin-bottom: 10px;
    }

    /* Info box */
    .info-box {
        background: #f8fafc;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 15px;
    }

    /* Tabella */
    .dataframe {
        font-size: 13px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SUPABASE
# ============================================================

def get_secret(name):
    """
    Recupera una variabile prima dall'ambiente e poi dagli
    Streamlit Secrets.
    """
    value = os.getenv(name)

    if value:
        return value

    try:
        return st.secrets.get(name)
    except Exception:
        return None


SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_KEY")


if not SUPABASE_URL or not SUPABASE_KEY:
    st.error(
        "⚠️ Credenziali Supabase non trovate. "
        "Configura SUPABASE_URL e SUPABASE_KEY."
    )
    st.stop()


@st.cache_resource
def init_supabase():
    return create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
    )


try:
    supabase = init_supabase()
except Exception as e:
    st.error(f"Errore nella connessione a Supabase: {e}")
    st.stop()


# ============================================================
# LETTURA SUPABASE
# ============================================================

@st.cache_data(ttl=600, show_spinner=False)
def load_player_stats():

    all_rows = []

    page_size = 1000
    start = 0

    while True:

        response = (
            supabase
            .table("player_stats")
            .select("*")
            .range(start, start + page_size - 1)
            .execute()
        )

        rows = response.data or []

        if not rows:
            break

        all_rows.extend(rows)

        if len(rows) < page_size:
            break

        start += page_size

    return pd.DataFrame(all_rows)


with st.spinner("Caricamento statistiche giocatori..."):

    try:
        df = load_player_stats()

    except Exception as e:
        st.error(f"Errore durante la lettura di player_stats: {e}")
        st.stop()


if df.empty:
    st.warning("La tabella `player_stats` non contiene dati.")
    st.stop()


# ============================================================
# NORMALIZZAZIONE DATI
# ============================================================

# Colonne numeriche attese
numeric_columns = [
    "player_id",
    "matches_played",
    "minutes_played",
    "goals",
    "assists",
    "xg",
    "xa",
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
    "key_passes_per_90",
    "np_goals",
    "np_xg",
]


for col in numeric_columns:

    if col not in df.columns:
        df[col] = 0

    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    ).fillna(0)


# ------------------------------------------------------------
# Stagione
# ------------------------------------------------------------

def season_start(value):
    """
    Restituisce l'anno di inizio della stagione.

    Supporta:

    2021      -> 2021
    2024      -> 2024
    2025      -> 2025

    2122      -> 2021
    2425      -> 2024
    2526      -> 2025

    2425/26   -> 2024
    """

    if pd.isna(value):
        return np.nan

    s = str(value).strip()

    # Caso YYYY/YY
    match = re.match(r"^(\d{4})/(\d{2})$", s)

    if match:

        first = int(match.group(1))
        second = int(match.group(2))

        # stagione corretta, es. 2025/26
        if (
            1900 <= first <= 2100
            and second == (first + 1) % 100
        ):
            return first

        # caso errato 2425/26
        if first >= 2100:
            return 2000 + int(str(first)[:2])

    # Elimina eventuali caratteri
    digits = re.sub(r"\D", "", s)

    if len(digits) == 4:

        number = int(digits)

        # YYYY
        if 1900 <= number <= 2100:
            return number

        # YYXX
        return 2000 + int(digits[:2])

    return np.nan


def format_season(value):
    """
    Converte qualsiasi formato conosciuto in:

    2021/22
    2022/23
    2023/24
    2024/25
    2025/26
    """

    start = season_start(value)

    if pd.isna(start):
        return str(value)

    start = int(start)

    return f"{start}/{str(start + 1)[-2:]}"


df["season_start"] = df["season"].apply(season_start)

df["season_label"] = df["season"].apply(format_season)


# ------------------------------------------------------------
# Ruolo
# ------------------------------------------------------------

def normalize_role(position):

    if pd.isna(position):
        return "N/D"

    position = str(position).upper()

    # Understat può restituire combinazioni:
    # GK
    # D S
    # M S
    # F M S

    if "GK" in position:
        return "P"

    if "D" in position:
        return "D"

    if "M" in position:
        return "C"

    if "F" in position or "S" in position:
        return "A"

    return "N/D"


if "position" not in df.columns:
    df["position"] = ""

df["role"] = df["position"].apply(normalize_role)


# ============================================================
# GESTIONE DUPLICATI
# ============================================================

# In teoria player_stats contiene una riga per:
#
# player_id + season
#
# ma gestiamo comunque eventuali duplicati.

aggregation = {}

sum_columns = [
    "matches_played",
    "minutes_played",
    "goals",
    "assists",
    "xg",
    "xa",
    "shots_total",
    "key_passes",
    "yellow_cards",
    "red_cards",
    "xg_chain",
    "xg_buildup",
    "np_goals",
    "np_xg",
]

for col in sum_columns:
    if col in df.columns:
        aggregation[col] = "sum"


for col in ["player_name", "team", "position", "role"]:
    if col in df.columns:
        aggregation[col] = "first"


df = (
    df
    .sort_values(
        ["season_start", "player_name"],
        ascending=[True, True]
    )
    .groupby(
        ["player_id", "season_start"],
        as_index=False
    )
    .agg(aggregation)
)


# ============================================================
# RICALCOLO METRICHE DERIVATE
# ============================================================

minutes = df["minutes_played"].replace(0, np.nan)


df["goals_per_90"] = (
    df["goals"] / (minutes / 90)
).fillna(0)


df["assists_per_90"] = (
    df["assists"] / (minutes / 90)
).fillna(0)


df["xg_per_90"] = (
    df["xg"] / (minutes / 90)
).fillna(0)


df["xa_per_90"] = (
    df["xa"] / (minutes / 90)
).fillna(0)


df["shots_per_90"] = (
    df["shots_total"] / (minutes / 90)
).fillna(0)


df["key_passes_per_90"] = (
    df["key_passes"] / (minutes / 90)
).fillna(0)


# Conversione tiri -> gol
df["shot_conversion"] = (
    df["goals"] / df["shots_total"].replace(0, np.nan)
).fillna(0) * 100


# Over / under performance
df["goal_xg_diff"] = df["goals"] - df["xg"]


# ============================================================
# IDENTIFICAZIONE STAGIONE PIÙ RECENTE
# ============================================================

latest_season = int(
    df["season_start"].dropna().max()
)


# ============================================================
# LISTA GIOCATORI
# ============================================================

# Per la lista principale mostriamo i giocatori presenti
# nella stagione più recente disponibile.

latest_players = (
    df[df["season_start"] == latest_season]
    .copy()
)


# Se per qualche motivo non esiste la stagione più recente
# per alcuni record, fallback a tutti i giocatori.

if latest_players.empty:

    latest_players = df.copy()


# Ordine ruoli Fantacalcio
role_order = {
    "P": 0,
    "D": 1,
    "C": 2,
    "A": 3,
    "N/D": 4,
}


latest_players["role_order"] = (
    latest_players["role"]
    .map(role_order)
    .fillna(4)
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">⚽ FantaAI</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">'
    'Serie A Analytics · Player Performance & Historical Data'
    '</div>',
    unsafe_allow_html=True,
)


# ============================================================
# SIDEBAR — LISTA GIOCATORI
# ============================================================

with st.sidebar:

    st.markdown("## 🔎 Giocatori")

    search = st.text_input(
        "Cerca giocatore",
        placeholder="Es. Lautaro, Barella...",
        label_visibility="collapsed",
    )

    sort_option = st.selectbox(
        "Ordina giocatori",
        [
            "Ruolo → Nome",
            "Nome",
            "Gol",
            "xG",
            "Minuti",
        ],
    )


    # --------------------------------------------------------
    # Ricerca
    # --------------------------------------------------------

    players_list = latest_players.copy()

    if search:

        search_lower = search.lower()

        players_list = players_list[
            players_list["player_name"]
            .astype(str)
            .str.lower()
            .str.contains(
                search_lower,
                na=False
            )
        ]


    # --------------------------------------------------------
    # Ordinamento
    # --------------------------------------------------------

    if sort_option == "Ruolo → Nome":

        players_list = players_list.sort_values(
            ["role_order", "player_name"]
        )

    elif sort_option == "Nome":

        players_list = players_list.sort_values(
            "player_name"
        )

    elif sort_option == "Gol":

        players_list = players_list.sort_values(
            "goals",
            ascending=False
        )

    elif sort_option == "xG":

        players_list = players_list.sort_values(
            "xg",
            ascending=False
        )

    elif sort_option == "Minuti":

        players_list = players_list.sort_values(
            "minutes_played",
            ascending=False
        )


    st.caption(
        f"{len(players_list)} giocatori · "
        f"stagione {format_season(latest_season)}"
    )


    # --------------------------------------------------------
    # Creazione label
    # --------------------------------------------------------

    player_options = []

    player_map = {}

    for _, row in players_list.iterrows():

        player_id = row["player_id"]

        name = str(row["player_name"])

        team = str(row["team"])

        role = str(row["role"])

        label = f"{name} · {team} · {role}"

        player_options.append(label)

        player_map[label] = player_id


    if not player_options:

        st.warning(
            "Nessun giocatore trovato."
        )

        st.stop()


    # --------------------------------------------------------
    # Mantieni giocatore selezionato
    # --------------------------------------------------------

    if (
        "selected_player_id" not in st.session_state
        or st.session_state.selected_player_id
        not in player_map.values()
    ):

        st.session_state.selected_player_id = (
            players_list.iloc[0]["player_id"]
        )


    current_index = 0

    for i, label in enumerate(player_options):

        if (
            player_map[label]
            == st.session_state.selected_player_id
        ):

            current_index = i
            break


    selected_label = st.selectbox(
        "Giocatore",
        player_options,
        index=current_index,
        key="player_selector",
        label_visibility="collapsed",
    )


    selected_player_id = player_map[selected_label]

    st.session_state.selected_player_id = selected_player_id


# ============================================================
# PLAYER DATA
# ============================================================

player_history = (
    df[
        df["player_id"]
        == selected_player_id
    ]
    .sort_values(
        "season_start"
    )
    .copy()
)


if player_history.empty:

    st.error(
        "Statistiche del giocatore non trovate."
    )

    st.stop()


# Ultima stagione disponibile per il giocatore
player_latest = player_history.iloc[-1]


player_name = str(
    player_latest["player_name"]
)

team = str(
    player_latest["team"]
)

role = str(
    player_latest["role"]
)

position = str(
    player_latest["position"]
)

player_latest_season = int(
    player_latest["season_start"]
)


# ============================================================
# HEADER GIOCATORE
# ============================================================

st.markdown(
    '<div class="player-header">',
    unsafe_allow_html=True,
)

st.markdown(
    f'<div class="player-name">{player_name}</div>',
    unsafe_allow_html=True,
)

st.markdown(
    f'<div class="player-meta">'
    f'⚽ {team} &nbsp; · &nbsp; '
    f'Ruolo: <b>{role}</b> &nbsp; · &nbsp; '
    f'{position} &nbsp; · &nbsp; '
    f'Stagione: <b>{format_season(player_latest_season)}</b>'
    f'</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '</div>',
    unsafe_allow_html=True,
)


# ============================================================
# KPI PRINCIPALI
# ============================================================

col1, col2, col3, col4, col5 = st.columns(5)


col1.metric(
    "⚽ Gol",
    int(player_latest["goals"])
)

col2.metric(
    "🎯 Assist",
    int(player_latest["assists"])
)

col3.metric(
    "xG",
    f'{player_latest["xg"]:.2f}'
)

col4.metric(
    "xG / 90",
    f'{player_latest["xg_per_90"]:.2f}'
)

col5.metric(
    "⏱ Minuti",
    f'{int(player_latest["minutes_played"]):,}'.replace(",", ".")
)


# ============================================================
# SECONDA RIGA KPI
# ============================================================

st.markdown("")

col1, col2, col3, col4, col5 = st.columns(5)


col1.metric(
    "Presenze",
    int(player_latest["matches_played"])
)

col2.metric(
    "Gol / 90",
    f'{player_latest["goals_per_90"]:.2f}'
)

col3.metric(
    "xA",
    f'{player_latest["xa"]:.2f}'
)

col4.metric(
    "xA / 90",
    f'{player_latest["xa_per_90"]:.2f}'
)

col5.metric(
    "Tiri",
    int(player_latest["shots_total"])
)


# ============================================================
# STORICO STAGIONI
# ============================================================

st.markdown(
    '<div class="section-title">'
    '📈 Evoluzione storica'
    '</div>',
    unsafe_allow_html=True,
)


history_display = player_history.copy()

history_display["Stagione"] = (
    history_display["season_start"]
    .apply(format_season)
)


# ------------------------------------------------------------
# Grafico Gol / xG
# ------------------------------------------------------------

fig_history = go.Figure()


fig_history.add_trace(
    go.Scatter(
        x=history_display["Stagione"],
        y=history_display["goals"],
        mode="lines+markers",
        name="Gol",
        line=dict(width=3),
    )
)


fig_history.add_trace(
    go.Scatter(
        x=history_display["Stagione"],
        y=history_display["xg"],
        mode="lines+markers",
        name="xG",
        line=dict(width=3, dash="dash"),
    )
)


fig_history.update_layout(
    title="Gol vs Expected Goals",
    xaxis_title="Stagione",
    yaxis_title="Valore",
    hovermode="x unified",
    height=400,
    margin=dict(l=20, r=20, t=60, b=20),
)


st.plotly_chart(
    fig_history,
    use_container_width=True,
)


# ============================================================
# GOL - XG
# ============================================================

col_left, col_right = st.columns(2)


with col_left:

    fig_over = px.bar(
        history_display,
        x="Stagione",
        y="goal_xg_diff",
        title="Over / Underperformance · Gol − xG",
        labels={
            "goal_xg_diff": "Gol − xG",
            "Stagione": "Stagione",
        },
        text_auto=".2f",
    )

    fig_over.add_hline(
        y=0,
        line_dash="dash",
    )

    fig_over.update_layout(
        height=380,
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=20,
        ),
    )

    st.plotly_chart(
        fig_over,
        use_container_width=True,
    )


with col_right:

    fig_efficiency = px.line(
        history_display,
        x="Stagione",
        y=[
            "goals_per_90",
            "xg_per_90",
        ],
        markers=True,
        title="Produzione offensiva per 90'",
        labels={
            "value": "Per 90'",
            "variable": "Metrica",
            "Stagione": "Stagione",
        },
    )

    fig_efficiency.update_layout(
        height=380,
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=20,
        ),
    )

    st.plotly_chart(
        fig_efficiency,
        use_container_width=True,
    )


# ============================================================
# STATISTICHE VOLUME / QUALITÀ
# ============================================================

st.markdown(
    '<div class="section-title">'
    '📊 Metriche di volume e qualità'
    '</div>',
    unsafe_allow_html=True,
)


volume_cols = [
    "Stagione",
    "matches_played",
    "minutes_played",
    "shots_total",
    "key_passes",
    "xg",
    "xa",
    "xg_chain",
    "xg_buildup",
]


available_volume_cols = [
    col
    for col in volume_cols
    if col in history_display.columns
]


volume_table = history_display[
    available_volume_cols
].copy()


volume_table = volume_table.rename(
    columns={
        "Stagione": "Stagione",
        "matches_played": "Presenze",
        "minutes_played": "Minuti",
        "shots_total": "Tiri",
        "key_passes": "Key Passes",
        "xg": "xG",
        "xa": "xA",
        "xg_chain": "xG Chain",
        "xg_buildup": "xG Buildup",
    }
)


st.dataframe(
    volume_table,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# METRICHE PER 90
# ============================================================

st.markdown(
    '<div class="section-title">'
    '⚡ Metriche per 90 minuti'
    '</div>',
    unsafe_allow_html=True,
)


per90_cols = [
    "Stagione",
    "goals_per_90",
    "assists_per_90",
    "xg_per_90",
    "xa_per_90",
    "shots_per_90",
    "key_passes_per_90",
]


per90_table = history_display[
    [
        col
        for col in per90_cols
        if col in history_display.columns
    ]
].copy()


per90_table = per90_table.rename(
    columns={
        "Stagione": "Stagione",
        "goals_per_90": "Gol / 90",
        "assists_per_90": "Assist / 90",
        "xg_per_90": "xG / 90",
        "xa_per_90": "xA / 90",
        "shots_per_90": "Tiri / 90",
        "key_passes_per_90": "Key Passes / 90",
    }
)


for col in per90_table.columns:

    if col != "Stagione":

        per90_table[col] = (
            pd.to_numeric(
                per90_table[col],
                errors="coerce"
            )
            .fillna(0)
            .round(2)
        )


st.dataframe(
    per90_table,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# CONFRONTO CON IL RUOLO
# ============================================================

st.markdown(
    '<div class="section-title">'
    '🎯 Confronto con i pari ruolo'
    '</div>',
    unsafe_allow_html=True,
)


role_players = df[
    (
        df["season_start"]
        == player_latest_season
    )
    &
    (
        df["role"]
        == role
    )
].copy()


if len(role_players) >= 5:

    metrics_for_percentile = {
        "goals_per_90": "Gol / 90",
        "xg_per_90": "xG / 90",
        "xa_per_90": "xA / 90",
        "shots_per_90": "Tiri / 90",
        "key_passes_per_90": "Key Passes / 90",
    }


    percentile_data = []


    for metric, label in metrics_for_percentile.items():

        if metric not in role_players.columns:
            continue

        values = pd.to_numeric(
            role_players[metric],
            errors="coerce"
        ).fillna(0)

        player_value = float(
            player_latest[metric]
        )

        percentile = (
            (values < player_value).mean()
            * 100
        )

        percentile_data.append(
            {
                "Metrica": label,
                "Valore": round(player_value, 2),
                "Percentile": round(percentile, 0),
            }
        )


    percentile_df = pd.DataFrame(
        percentile_data
    )


    if not percentile_df.empty:

        fig_percentile = px.bar(
            percentile_df,
            x="Percentile",
            y="Metrica",
            orientation="h",
            text="Percentile",
            range_x=[0, 100],
            title=(
                f"Percentile rispetto ai {role} "
                f"della Serie A · "
                f"{format_season(player_latest_season)}"
            ),
        )

        fig_percentile.update_traces(
            texttemplate="%{text}°",
            textposition="inside",
        )

        fig_percentile.update_layout(
            height=350,
            margin=dict(
                l=20,
                r=20,
                t=60,
                b=20,
            ),
        )

        st.plotly_chart(
            fig_percentile,
            use_container_width=True,
        )


else:

    st.info(
        "Non ci sono abbastanza giocatori dello stesso "
        "ruolo per calcolare un confronto significativo."
    )


# ============================================================
# GIOCATORI SIMILI
# ============================================================

st.markdown(
    '<div class="section-title">'
    '🔄 Giocatori simili'
    '</div>',
    unsafe_allow_html=True,
)


similar_metrics = [
    "goals_per_90",
    "assists_per_90",
    "xg_per_90",
    "xa_per_90",
    "shots_per_90",
    "key_passes_per_90",
]


similar_pool = df[
    (
        df["season_start"]
        == player_latest_season
    )
    &
    (
        df["role"]
        == role
    )
    &
    (
        df["player_id"]
        != selected_player_id
    )
].copy()


if len(similar_pool) >= 3:

    features = similar_pool[
        similar_metrics
    ].fillna(0).astype(float)

    target = np.array(
        [
            float(player_latest[m])
            for m in similar_metrics
        ]
    )


    # Standardizzazione
    means = features.mean()

    stds = features.std().replace(
        0,
        1
    )


    features_scaled = (
        features - means
    ) / stds


    target_scaled = (
        target - means.values
    ) / stds.values


    distances = np.sqrt(
        (
            (
                features_scaled
                - target_scaled
            ) ** 2
        ).sum(axis=1)
    )


    similar_pool["distance"] = distances


    similar_players = (
        similar_pool
        .sort_values("distance")
        .head(3)
        .copy()
    )


    similar_display = similar_players[
        [
            "player_name",
            "team",
            "role",
            "goals_per_90",
            "xg_per_90",
            "xa_per_90",
            "minutes_played",
        ]
    ].copy()


    similar_display = similar_display.rename(
        columns={
            "player_name": "Giocatore",
            "team": "Squadra",
            "role": "Ruolo",
            "goals_per_90": "Gol / 90",
            "xg_per_90": "xG / 90",
            "xa_per_90": "xA / 90",
            "minutes_played": "Minuti",
        }
    )


    for col in [
        "Gol / 90",
        "xG / 90",
        "xA / 90",
    ]:

        similar_display[col] = (
            similar_display[col]
            .round(2)
        )


    st.dataframe(
        similar_display,
        use_container_width=True,
        hide_index=True,
    )

else:

    st.info(
        "Non ci sono abbastanza giocatori "
        "per calcolare similitudini."
    )


# ============================================================
# DETTAGLIO STAGIONALE
# ============================================================

st.markdown(
    '<div class="section-title">'
    '📋 Dettaglio stagionale'
    '</div>',
    unsafe_allow_html=True,
)


detail = history_display[
    [
        "Stagione",
        "team",
        "role",
        "matches_played",
        "minutes_played",
        "goals",
        "assists",
        "xg",
        "xa",
        "shots_total",
        "key_passes",
        "yellow_cards",
        "red_cards",
    ]
].copy()


detail = detail.rename(
    columns={
        "Stagione": "Stagione",
        "team": "Squadra",
        "role": "Ruolo",
        "matches_played": "Presenze",
        "minutes_played": "Minuti",
        "goals": "Gol",
        "assists": "Assist",
        "xg": "xG",
        "xa": "xA",
        "shots_total": "Tiri",
        "key_passes": "Key Passes",
        "yellow_cards": "Gialli",
        "red_cards": "Rossi",
    }
)


detail["xG"] = detail["xG"].round(2)
detail["xA"] = detail["xA"].round(2)


st.dataframe(
    detail,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    f"FantaAI · Database: {len(df):,} record stagionali · "
    f"{df['player_id'].nunique():,} giocatori · "
    f"Ultima stagione disponibile: "
    f"{format_season(latest_season)}"
)
