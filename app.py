import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from supabase import create_client


# ============================================================
# CONFIGURAZIONE
# ============================================================

st.set_page_config(
    page_title="FantaAI Analytics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


if not SUPABASE_URL or not SUPABASE_KEY:
    st.error(
        "❌ Variabili SUPABASE_URL e/o SUPABASE_KEY non configurate."
    )
    st.stop()


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

    /* ---------- GENERALE ---------- */

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1600px;
    }

    h1 {
        font-weight: 700;
        letter-spacing: -0.5px;
    }

    h2, h3 {
        font-weight: 600;
    }

    /* ---------- CARD ---------- */

    .info-card {
        background: #f8fafc;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 18px 20px;
        margin-bottom: 14px;
    }

    .player-name {
        font-size: 30px;
        font-weight: 700;
        margin-bottom: 3px;
    }

    .player-team {
        color: #64748b;
        font-size: 16px;
    }

    .quote-card {
        background: linear-gradient(135deg, #111827, #1f2937);
        color: white;
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        height: 100%;
    }

    .quote-label {
        font-size: 13px;
        opacity: 0.75;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .quote-value {
        font-size: 36px;
        font-weight: 700;
        margin-top: 5px;
    }

    .quote-sub {
        font-size: 14px;
        opacity: 0.8;
    }

    /* ---------- STAT BOX ---------- */

    .stat-box {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 15px;
        min-height: 100px;
    }

    .stat-label {
        color: #64748b;
        font-size: 13px;
        margin-bottom: 7px;
    }

    .stat-value {
        font-size: 25px;
        font-weight: 700;
    }

    /* ---------- PLAYER LIST ---------- */

    div[data-testid="stRadio"] label {
        padding: 8px 10px;
        border-radius: 8px;
    }

    /* ---------- SEPARATOR ---------- */

    .section-title {
        margin-top: 25px;
        margin-bottom: 10px;
        font-size: 20px;
        font-weight: 650;
    }

    /* ---------- BADGE ---------- */

    .role-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 20px;
        background: #eef2ff;
        color: #4338ca;
        font-size: 13px;
        font-weight: 600;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SUPABASE
# ============================================================

@st.cache_resource
def init_supabase():
    return create_client(
        SUPABASE_URL,
        SUPABASE_KEY
    )


supabase = init_supabase()


# ============================================================
# CARICAMENTO PAGINATO DA SUPABASE
# ============================================================

def fetch_all_rows(table_name, page_size=1000):
    """
    Scarica tutte le righe di una tabella Supabase.

    Supabase/PostgREST può limitare il numero di righe restituite
    da una singola richiesta. Per questo utilizziamo .range()
    e scarichiamo i dati a blocchi da 1000.
    """

    all_rows = []
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

        rows = response.data or []

        if not rows:
            break

        all_rows.extend(rows)

        if len(rows) < page_size:
            break

        start += page_size

    return all_rows


# ============================================================
# CARICAMENTO DATI
# ============================================================

@st.cache_data(ttl=600)
def load_stats():
    """
    Carica TUTTO lo storico dei giocatori.
    """

    rows = fetch_all_rows(
        "player_stats_history"
    )

    return pd.DataFrame(rows)


@st.cache_data(ttl=600)
def load_quotazioni():
    """
    Carica TUTTE le quotazioni.
    """

    rows = fetch_all_rows(
        "giocatori_quotazioni"
    )

    return pd.DataFrame(rows)


# ============================================================
# FUNZIONI UTILITY
# ============================================================

def safe_sum(df, column):

    if column not in df.columns:
        return 0

    values = pd.to_numeric(
        df[column],
        errors="coerce"
    )

    return int(
        values
        .fillna(0)
        .sum()
    )


def safe_mean(df, column):

    if column not in df.columns:
        return 0

    values = pd.to_numeric(
        df[column],
        errors="coerce"
    )

    value = values.mean()

    if pd.isna(value):
        return 0

    return round(
        float(value),
        2
    )


def safe_std(df, column):

    if column not in df.columns:
        return None

    values = pd.to_numeric(
        df[column],
        errors="coerce"
    )

    value = values.std()

    if pd.isna(value):
        return None

    return round(
        float(value),
        2
    )


def normalize_player_id(df):

    if "player_id" not in df.columns:
        return df

    df = df.copy()

    df["player_id"] = pd.to_numeric(
        df["player_id"],
        errors="coerce"
    )

    return df


def season_sort_key(value):
    """
    Permette di ordinare correttamente le stagioni.

    Gestisce ad esempio:

    2021/22
    2022/23
    2023/24
    2024/25
    2025/26
    2026/27

    e anche valori come:

    2021
    2022
    """

    value = str(value).strip()

    try:

        first_part = value.split("/")[0]

        return int(first_part)

    except Exception:

        return 0


def get_latest_season(df):

    if df.empty:
        return None

    if "stagione" not in df.columns:
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


def get_latest_quote_row(quot_player):

    if quot_player.empty:
        return None

    quot_player = quot_player.copy()

    if "stagione" in quot_player.columns:

        quot_player["_season_sort"] = (
            quot_player["stagione"]
            .apply(season_sort_key)
        )

        quot_player = quot_player.sort_values(
            "_season_sort"
        )

    return quot_player.iloc[-1]


# ============================================================
# PROFILO GIOCATORE
# ============================================================

def render_player_detail(
    player_id,
    stats,
    quotations
):

    # --------------------------------------------------------
    # DATI QUOTAZIONE
    # --------------------------------------------------------

    p_quotes = quotations[
        quotations["player_id"] == player_id
    ].copy()

    current_quote = get_latest_quote_row(
        p_quotes
    )

    # --------------------------------------------------------
    # DATI STORICI
    # --------------------------------------------------------

    p_stats = stats[
        stats["player_id"] == player_id
    ].copy()

    # --------------------------------------------------------
    # GIORNATA
    # --------------------------------------------------------

    if "giornata" in p_stats.columns:

        p_stats["giornata"] = pd.to_numeric(
            p_stats["giornata"],
            errors="coerce"
        )

    # --------------------------------------------------------
    # STAGIONE
    # --------------------------------------------------------

    if "stagione" in p_stats.columns:

        p_stats["stagione"] = (
            p_stats["stagione"]
            .astype(str)
            .str.strip()
        )

    # --------------------------------------------------------
    # ORDINAMENTO
    # --------------------------------------------------------

    sort_columns = []

    if "stagione" in p_stats.columns:
        p_stats["_season_sort"] = (
            p_stats["stagione"]
            .apply(season_sort_key)
        )
        sort_columns.append("_season_sort")

    if "giornata" in p_stats.columns:
        sort_columns.append("giornata")

    if sort_columns:

        p_stats = p_stats.sort_values(
            sort_columns
        )

    # --------------------------------------------------------
    # NOME / RUOLO / SQUADRA
    # --------------------------------------------------------

    if current_quote is not None:

        nome = current_quote.get(
            "nome",
            "Giocatore"
        )

        ruolo = current_quote.get(
            "ruolo",
            "-"
        )

        squadra = current_quote.get(
            "squadra",
            "-"
        )

    elif not p_stats.empty:

        nome = p_stats.iloc[-1].get(
            "nome",
            "Giocatore"
        )

        ruolo = p_stats.iloc[-1].get(
            "ruolo",
            "-"
        )

        squadra = p_stats.iloc[-1].get(
            "squadra",
            "-"
        )

    else:

        nome = "Giocatore"
        ruolo = "-"
        squadra = "-"

    # ========================================================
    # HEADER
    # ========================================================

    left, right = st.columns(
        [2.4, 1]
    )

    with left:

        st.markdown(
            f"""
            <div class="info-card">
                <div class="player-name">{nome}</div>
                <div class="player-team">
                    {squadra} &nbsp; • &nbsp;
                    <span class="role-badge">{ruolo}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:

        if current_quote is not None:

            quota = current_quote.get(
                "quotazione_attuale",
                "-"
            )

            fvm = current_quote.get(
                "fvm",
                "-"
            )

            st.markdown(
                f"""
                <div class="quote-card">
                    <div class="quote-label">
                        Quotazione attuale
                    </div>

                    <div class="quote-value">
                        {quota}
                    </div>

                    <div class="quote-sub">
                        FVM: {fvm}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ========================================================
    # CEDUTO
    # ========================================================

    if current_quote is not None:

        ceduto = current_quote.get(
            "ceduto",
            False
        )

        if bool(ceduto):

            st.warning(
                "⚠️ Questo giocatore risulta marcato "
                "come ceduto nella tabella delle quotazioni."
            )

    # ========================================================
    # NESSUNA STATISTICA
    # ========================================================

    if p_stats.empty:

        st.info(
            "Non sono presenti statistiche storiche "
            "per questo giocatore."
        )

        return

    # ========================================================
    # STATISTICHE PRINCIPALI
    # ========================================================

    st.markdown(
        '<div class="section-title">'
        '📊 Rendimento storico'
        '</div>',
        unsafe_allow_html=True,
    )

    if "voto" in p_stats.columns:

        partite = int(
            pd.to_numeric(
                p_stats["voto"],
                errors="coerce"
            ).count()
        )

    else:

        partite = 0

    media_voto = safe_mean(
        p_stats,
        "voto"
    )

    media_fanta = safe_mean(
        p_stats,
        "fanta_voto"
    )

    gol = safe_sum(
        p_stats,
        "gf"
    )

    assist = safe_sum(
        p_stats,
        "ass"
    )

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.metric(
            "Presenze",
            partite
        )

    with c2:
        st.metric(
            "Media voto",
            f"{media_voto:.2f}"
        )

    with c3:
        st.metric(
            "Media fantavoto",
            f"{media_fanta:.2f}"
        )

    with c4:
        st.metric(
            "Gol",
            gol
        )

    with c5:
        st.metric(
            "Assist",
            assist
        )

    # ========================================================
    # BONUS / MALUS
    # ========================================================

    st.markdown(
        '<div class="section-title">'
        '⚽ Bonus e malus'
        '</div>',
        unsafe_allow_html=True,
    )

    b1, b2, b3, b4, b5, b6 = st.columns(6)

    with b1:
        st.metric(
            "Gol",
            safe_sum(p_stats, "gf")
        )

    with b2:
        st.metric(
            "Assist",
            safe_sum(p_stats, "ass")
        )

    with b3:
        st.metric(
            "Rigori segnati",
            safe_sum(p_stats, "rf")
        )

    with b4:
        st.metric(
            "Ammonizioni",
            safe_sum(p_stats, "amm")
        )

    with b5:
        st.metric(
            "Espulsioni",
            safe_sum(p_stats, "esp")
        )

    with b6:
        st.metric(
            "Autogol",
            safe_sum(p_stats, "au")
        )

    # ========================================================
    # ANDAMENTO NEL TEMPO
    # ========================================================

    st.markdown(
        '<div class="section-title">'
        '📈 Andamento nel tempo'
        '</div>',
        unsafe_allow_html=True,
    )

    chart_df = p_stats.copy()

    if (
        "stagione" in chart_df.columns
        and "giornata" in chart_df.columns
    ):

        chart_df = chart_df[
            chart_df["giornata"].notna()
        ].copy()

        chart_df["periodo"] = (
            chart_df["stagione"].astype(str)
            + " • G"
            + chart_df["giornata"].astype(int).astype(str)
        )

    else:

        chart_df["periodo"] = (
            chart_df.index.astype(str)
        )

    fig = go.Figure()

    if "voto" in chart_df.columns:

        fig.add_trace(
            go.Scatter(
                x=chart_df["periodo"],
                y=pd.to_numeric(
                    chart_df["voto"],
                    errors="coerce"
                ),
                mode="lines+markers",
                name="Voto",
                line=dict(width=2),
            )
        )

    if "fanta_voto" in chart_df.columns:

        fig.add_trace(
            go.Scatter(
                x=chart_df["periodo"],
                y=pd.to_numeric(
                    chart_df["fanta_voto"],
                    errors="coerce"
                ),
                mode="lines+markers",
                name="Fantavoto",
                line=dict(width=2),
            )
        )

    fig.update_layout(
        title="Voto e Fantavoto giornata per giornata",
        xaxis_title="Stagione / Giornata",
        yaxis_title="Valutazione",
        hovermode="x unified",
        height=450,
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=20
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # ========================================================
    # MEDIA PER STAGIONE
    # ========================================================

    st.markdown(
        '<div class="section-title">'
        '📅 Rendimento per stagione'
        '</div>',
        unsafe_allow_html=True,
    )

    agg_dict = {}

    if "voto" in p_stats.columns:
        agg_dict["Presenze"] = (
            "voto",
            "count"
        )

        agg_dict["Media_Voto"] = (
            "voto",
            "mean"
        )

    if "fanta_voto" in p_stats.columns:
        agg_dict["Media_Fantavoto"] = (
            "fanta_voto",
            "mean"
        )

    if "gf" in p_stats.columns:
        agg_dict["Gol"] = (
            "gf",
            "sum"
        )

    if "ass" in p_stats.columns:
        agg_dict["Assist"] = (
            "ass",
            "sum"
        )

    if "amm" in p_stats.columns:
        agg_dict["Ammonizioni"] = (
            "amm",
            "sum"
        )

    if "esp" in p_stats.columns:
        agg_dict["Espulsioni"] = (
            "esp",
            "sum"
        )

    if "stagione" in p_stats.columns and agg_dict:

        season_agg = (
            p_stats
            .groupby("stagione")
            .agg(**agg_dict)
            .reset_index()
        )

        if "Media_Voto" in season_agg.columns:
            season_agg["Media_Voto"] = (
                season_agg["Media_Voto"]
                .round(2)
            )

        if "Media_Fantavoto" in season_agg.columns:
            season_agg["Media_Fantavoto"] = (
                season_agg["Media_Fantavoto"]
                .round(2)
            )

        season_agg["_season_sort"] = (
            season_agg["stagione"]
            .apply(season_sort_key)
        )

        season_agg = (
            season_agg
            .sort_values("_season_sort")
            .drop(columns="_season_sort")
        )

        st.dataframe(
            season_agg,
            use_container_width=True,
            hide_index=True,
        )

    else:

        season_agg = pd.DataFrame()

        st.info(
            "Non sono disponibili dati sufficienti "
            "per creare il riepilogo stagionale."
        )

    # ========================================================
    # GRAFICO MEDIA VOTO PER STAGIONE
    # ========================================================

    if not season_agg.empty:

        fig_season = go.Figure()

        if "Media_Voto" in season_agg.columns:

            fig_season.add_trace(
                go.Bar(
                    x=season_agg["stagione"],
                    y=season_agg["Media_Voto"],
                    name="Media voto",
                )
            )

        if "Media_Fantavoto" in season_agg.columns:

            fig_season.add_trace(
                go.Scatter(
                    x=season_agg["stagione"],
                    y=season_agg["Media_Fantavoto"],
                    name="Media fantavoto",
                    mode="lines+markers",
                )
            )

        fig_season.update_layout(
            title="Evoluzione del rendimento medio",
            xaxis_title="Stagione",
            yaxis_title="Media",
            height=400,
            margin=dict(
                l=20,
                r=20,
                t=60,
                b=20
            ),
        )

        st.plotly_chart(
            fig_season,
            use_container_width=True,
        )

    # ========================================================
    # CONTINUITÀ
    # ========================================================

    st.markdown(
        '<div class="section-title">'
        '🎯 Continuità di rendimento'
        '</div>',
        unsafe_allow_html=True,
    )

    std = safe_std(
        p_stats,
        "voto"
    )

    if std is not None:

        if std < 0.6:
            giudizio = "🟢 Molto continuo"

        elif std < 0.9:
            giudizio = "🟡 Abbastanza continuo"

        else:
            giudizio = "🔴 Altalenante"

        c1, c2 = st.columns(2)

        with c1:

            st.metric(
                "Deviazione standard voto",
                f"{std:.2f}"
            )

        with c2:

            st.metric(
                "Valutazione",
                giudizio
            )

    # ========================================================
    # DETTAGLIO QUOTAZIONE
    # ========================================================

    if current_quote is not None:

        st.markdown(
            '<div class="section-title">'
            '💰 Quotazione attuale'
            '</div>',
            unsafe_allow_html=True,
        )

        q1, q2, q3, q4 = st.columns(4)

        q1.metric(
            "Quotazione",
            current_quote.get(
                "quotazione_attuale",
                "-"
            )
        )

        q2.metric(
            "FVM",
            current_quote.get(
                "fvm",
                "-"
            )
        )

        q3.metric(
            "Ruolo",
            current_quote.get(
                "ruolo",
                "-"
            )
        )

        q4.metric(
            "Squadra",
            current_quote.get(
                "squadra",
                "-"
            )
        )

    # ========================================================
    # DATI GREZZI
    # ========================================================

    with st.expander(
        "📄 Visualizza statistiche storiche complete"
    ):

        st.dataframe(
            p_stats,
            use_container_width=True,
            hide_index=True,
        )

        csv = p_stats.to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            "⬇️ Scarica CSV",
            data=csv,
            file_name=f"{nome}_storico.csv",
            mime="text/csv",
        )


# ============================================================
# CARICAMENTO
# ============================================================

try:

    df = load_stats()

    quot = load_quotazioni()

except Exception as e:

    st.error(
        "❌ Errore nel caricamento dei dati da Supabase:"
    )

    st.code(
        str(e)
    )

    st.stop()


# ============================================================
# CONTROLLO TABELLE
# ============================================================

if df.empty:

    st.error(
        "❌ La tabella player_stats_history è vuota "
        "oppure non contiene dati accessibili."
    )

    st.stop()


if quot.empty:

    st.warning(
        "⚠️ La tabella giocatori_quotazioni è vuota."
    )

    st.stop()


# ============================================================
# NORMALIZZAZIONE
# ============================================================

df = normalize_player_id(df)

quot = normalize_player_id(quot)


# ============================================================
# CONTROLLO player_id
# ============================================================

if "player_id" not in df.columns:

    st.error(
        "❌ La tabella player_stats_history "
        "non contiene la colonna player_id."
    )

    st.stop()


if "player_id" not in quot.columns:

    st.error(
        "❌ La tabella giocatori_quotazioni "
        "non contiene la colonna player_id."
    )

    st.stop()


# Elimina eventuali ID nulli

df = df[
    df["player_id"].notna()
].copy()

quot = quot[
    quot["player_id"].notna()
].copy()


# ============================================================
# DEBUG DATI
# ============================================================

with st.expander(
    "🔎 Diagnostica database",
    expanded=False
):

    st.write(
        f"**Righe storico caricate:** {len(df):,}"
    )

    st.write(
        f"**Righe quotazioni caricate:** {len(quot):,}"
    )

    st.write(
        f"**Giocatori distinti nello storico:** "
        f"{df['player_id'].nunique():,}"
    )

    st.write(
        f"**Giocatori distinti nelle quotazioni:** "
        f"{quot['player_id'].nunique():,}"
    )

    common_ids = set(
        df["player_id"].unique()
    ).intersection(
        set(quot["player_id"].unique())
    )

    st.write(
        f"**Player ID presenti in entrambe:** "
        f"{len(common_ids):,}"
    )

    if 2155 in set(
        df["player_id"].astype(int).unique()
    ):

        cutrone_stats = df[
            df["player_id"] == 2155
        ]

        st.success(
            f"✅ Cutrone (2155) trovato nello storico: "
            f"{len(cutrone_stats)} righe"
        )

    else:

        st.error(
            "❌ Cutrone (2155) NON trovato nello storico."
        )

    if 2155 in set(
        quot["player_id"].astype(int).unique()
    ):

        cutrone_quote = quot[
            quot["player_id"] == 2155
        ]

        st.success(
            f"✅ Cutrone (2155) trovato nelle quotazioni: "
            f"{len(cutrone_quote)} righe"
        )

    else:

        st.error(
            "❌ Cutrone (2155) NON trovato nelle quotazioni."
        )


# ============================================================
# ROSA ATTUALE
# ============================================================

if "stagione" in quot.columns:

    latest_season = get_latest_season(
        quot
    )

    if latest_season is not None:

        current_quot = quot[
            quot["stagione"].astype(str).str.strip()
            == str(latest_season).strip()
        ].copy()

    else:

        current_quot = quot.copy()

else:

    latest_season = None

    current_quot = quot.copy()


# ============================================================
# HEADER APP
# ============================================================

st.title("⚽ FantaAI")

if latest_season:

    st.markdown(
        f"""
        ### Analisi dei giocatori della rosa attuale

        Stagione quotazioni: **{latest_season}**

        Seleziona un ruolo e un giocatore per visualizzare
        **quotazione attuale, FVM e rendimento storico completo**.
        """
    )

else:

    st.markdown(
        """
        ### Analisi dei giocatori della rosa attuale

        Seleziona un ruolo e un giocatore per visualizzare
        **quotazione attuale, FVM e rendimento storico completo**.
        """
    )


# ============================================================
# FILTRO RUOLO
# ============================================================

role_col, info_col = st.columns(
    [1, 3]
)

with role_col:

    selected_role = st.selectbox(
        "Filtra per ruolo",
        options=[
            "Tutti",
            "P",
            "D",
            "C",
            "A",
        ],
    )


with info_col:

    st.markdown(
        f"""
        **Rosa attuale:** {len(current_quot)} giocatori
        """
    )


# ============================================================
# FILTRO ROSA
# ============================================================

quot_view = current_quot.copy()


if (
    selected_role != "Tutti"
    and "ruolo" in quot_view.columns
):

    quot_view = quot_view[
        quot_view["ruolo"] == selected_role
    ]


if "nome" in quot_view.columns:

    quot_view = quot_view.sort_values(
        "nome",
        na_position="last"
    )


# ============================================================
# LAYOUT PRINCIPALE
# ============================================================

col_players, col_detail = st.columns(
    [1, 3.2],
    gap="large"
)


# ============================================================
# LISTA GIOCATORI
# ============================================================

with col_players:

    st.markdown(
        "### 👥 Giocatori"
    )

    st.caption(
        f"{len(quot_view)} giocatori disponibili"
    )

    if quot_view.empty:

        st.info(
            "Nessun giocatore trovato per questo ruolo."
        )

        selected_id = None

    else:

        columns_needed = [
            "player_id",
            "nome",
            "squadra",
            "ruolo",
            "quotazione_attuale",
        ]

        available_columns = [
            column
            for column in columns_needed
            if column in quot_view.columns
        ]

        options_df = (
            quot_view[
                available_columns
            ]
            .drop_duplicates(
                subset="player_id"
            )
        )

        labels = []

        for row in options_df.itertuples():

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

            labels.append(
                f"{nome}  •  {squadra}"
            )

        label_to_id = dict(
            zip(
                labels,
                options_df["player_id"]
            )
        )

        selected_label = st.radio(
            "Seleziona giocatore",
            options=labels,
            label_visibility="collapsed",
        )

        selected_id = label_to_id[
            selected_label
        ]


# ============================================================
# DETTAGLIO
# ============================================================

with col_detail:

    if selected_id is None:

        st.info(
            "Seleziona un giocatore."
        )

    else:

        render_player_detail(
            selected_id,
            df,
            quot,
        )

