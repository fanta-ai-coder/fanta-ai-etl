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
    return create_client(SUPABASE_URL, SUPABASE_KEY)


supabase = init_supabase()


# ============================================================
# CARICAMENTO DATI
# ============================================================

@st.cache_data(ttl=600)
def load_stats():
    """Carica tutte le statistiche storiche."""
    res = (
        supabase
        .table("player_stats_history")
        .select("*")
        .execute()
    )

    return pd.DataFrame(res.data)


@st.cache_data(ttl=600)
def load_quotazioni():
    """
    Carica le quotazioni.
    
    La tabella contiene la rosa attuale.
    Se dovessero essere presenti più stagioni,
    viene utilizzata automaticamente quella più recente.
    """
    res = (
        supabase
        .table("giocatori_quotazioni")
        .select("*")
        .execute()
    )

    return pd.DataFrame(res.data)


# ============================================================
# FUNZIONI UTILITY
# ============================================================

def safe_sum(df, column):
    if column not in df.columns:
        return 0

    return int(
        pd.to_numeric(df[column], errors="coerce")
        .fillna(0)
        .sum()
    )


def safe_mean(df, column):
    if column not in df.columns:
        return 0

    value = pd.to_numeric(df[column], errors="coerce").mean()

    if pd.isna(value):
        return 0

    return round(float(value), 2)


def safe_std(df, column):
    if column not in df.columns:
        return None

    value = pd.to_numeric(df[column], errors="coerce").std()

    if pd.isna(value):
        return None

    return round(float(value), 2)


def format_season(season):
    """
    Mantiene la stagione così come presente nel DB.
    """
    return str(season)


def get_latest_quote_row(quot_player):
    """
    Restituisce la quotazione più recente disponibile
    per il giocatore.
    """

    if quot_player.empty:
        return None

    if "stagione" in quot_player.columns:
        try:
            quot_player = quot_player.sort_values("stagione")
        except Exception:
            pass

    return quot_player.iloc[-1]


# ============================================================
# PROFILO GIOCATORE
# ============================================================

def render_player_detail(player_id, stats, quotations):

    # --------------------------------------------------------
    # DATI QUOTAZIONE
    # --------------------------------------------------------

    p_quotes = quotations[
        quotations["player_id"] == player_id
    ].copy()

    current_quote = get_latest_quote_row(p_quotes)

    # --------------------------------------------------------
    # DATI STORICI
    # --------------------------------------------------------

    p_stats = stats[
        stats["player_id"] == player_id
    ].copy()

    if "giornata" in p_stats.columns:
        p_stats["giornata"] = pd.to_numeric(
            p_stats["giornata"],
            errors="coerce"
        )

    if "stagione" in p_stats.columns:
        p_stats["stagione"] = p_stats["stagione"].astype(str)

    p_stats = p_stats.sort_values(
        ["stagione", "giornata"]
    )

    # --------------------------------------------------------
    # NOME
    # --------------------------------------------------------

    if current_quote is not None:
        nome = current_quote.get("nome", "Giocatore")
        ruolo = current_quote.get("ruolo", "-")
        squadra = current_quote.get("squadra", "-")
    elif not p_stats.empty:
        nome = p_stats.iloc[-1].get("nome", "Giocatore")
        ruolo = p_stats.iloc[-1].get("ruolo", "-")
        squadra = p_stats.iloc[-1].get("squadra", "-")
    else:
        nome = "Giocatore"
        ruolo = "-"
        squadra = "-"

    # ========================================================
    # HEADER
    # ========================================================

    left, right = st.columns([2.4, 1])

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

            quota = current_quote.get("quotazione_attuale", "-")
            fvm = current_quote.get("fvm", "-")

            st.markdown(
                f"""
                <div class="quote-card">
                    <div class="quote-label">Quotazione attuale</div>
                    <div class="quote-value">{quota}</div>
                    <div class="quote-sub">FVM: {fvm}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ========================================================
    # CEDUTO
    # ========================================================

    if current_quote is not None:

        ceduto = current_quote.get("ceduto", False)

        if bool(ceduto):
            st.warning(
                "⚠️ Questo giocatore risulta marcato come ceduto "
                "nella tabella delle quotazioni."
            )

    # ========================================================
    # NESSUNA STATISTICA
    # ========================================================

    if p_stats.empty:

        st.info(
            "Non sono presenti statistiche storiche per questo giocatore."
        )

        return

    # ========================================================
    # STATISTICHE PRINCIPALI
    # ========================================================

    st.markdown(
        '<div class="section-title">📊 Rendimento storico</div>',
        unsafe_allow_html=True,
    )

    partite = int(p_stats["voto"].count())

    media_voto = safe_mean(p_stats, "voto")

    media_fanta = safe_mean(p_stats, "fanta_voto")

    gol = safe_sum(p_stats, "gf")

    assist = safe_sum(p_stats, "ass")

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.metric("Presenze", partite)

    with c2:
        st.metric("Media voto", f"{media_voto:.2f}")

    with c3:
        st.metric("Media fantavoto", f"{media_fanta:.2f}")

    with c4:
        st.metric("Gol", gol)

    with c5:
        st.metric("Assist", assist)

    # ========================================================
    # BONUS / MALUS
    # ========================================================

    st.markdown(
        '<div class="section-title">⚽ Bonus e malus</div>',
        unsafe_allow_html=True,
    )

    b1, b2, b3, b4, b5, b6 = st.columns(6)

    with b1:
        st.metric("Gol", safe_sum(p_stats, "gf"))

    with b2:
        st.metric("Assist", safe_sum(p_stats, "ass"))

    with b3:
        st.metric("Rigori segnati", safe_sum(p_stats, "rf"))

    with b4:
        st.metric("Ammonizioni", safe_sum(p_stats, "amm"))

    with b5:
        st.metric("Espulsioni", safe_sum(p_stats, "esp"))

    with b6:
        st.metric("Autogol", safe_sum(p_stats, "au"))

    # ========================================================
    # ANDAMENTO NEL TEMPO
    # ========================================================

    st.markdown(
        '<div class="section-title">📈 Andamento nel tempo</div>',
        unsafe_allow_html=True,
    )

    chart_df = p_stats.copy()

    chart_df["periodo"] = (
        chart_df["stagione"].astype(str)
        + " • G"
        + chart_df["giornata"].astype(int).astype(str)
    )

    fig = go.Figure()

    if "voto" in chart_df.columns:

        fig.add_trace(
            go.Scatter(
                x=chart_df["periodo"],
                y=chart_df["voto"],
                mode="lines+markers",
                name="Voto",
                line=dict(width=2),
            )
        )

    if "fanta_voto" in chart_df.columns:

        fig.add_trace(
            go.Scatter(
                x=chart_df["periodo"],
                y=chart_df["fanta_voto"],
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
        margin=dict(l=20, r=20, t=60, b=20),
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
        '<div class="section-title">📅 Rendimento per stagione</div>',
        unsafe_allow_html=True,
    )

    season_agg = (
        p_stats
        .groupby("stagione")
        .agg(
            Presenze=("voto", "count"),
            Media_Voto=("voto", "mean"),
            Media_Fantavoto=("fanta_voto", "mean"),
            Gol=("gf", "sum"),
            Assist=("ass", "sum"),
            Ammonizioni=("amm", "sum"),
            Espulsioni=("esp", "sum"),
        )
        .reset_index()
    )

    season_agg[
        [
            "Media_Voto",
            "Media_Fantavoto",
        ]
    ] = season_agg[
        [
            "Media_Voto",
            "Media_Fantavoto",
        ]
    ].round(2)

    st.dataframe(
        season_agg,
        use_container_width=True,
        hide_index=True,
    )

    # ========================================================
    # GRAFICO MEDIA VOTO PER STAGIONE
    # ========================================================

    fig_season = go.Figure()

    fig_season.add_trace(
        go.Bar(
            x=season_agg["stagione"],
            y=season_agg["Media_Voto"],
            name="Media voto",
        )
    )

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
        margin=dict(l=20, r=20, t=60, b=20),
    )

    st.plotly_chart(
        fig_season,
        use_container_width=True,
    )

    # ========================================================
    # CONTINUITÀ
    # ========================================================

    st.markdown(
        '<div class="section-title">🎯 Continuità di rendimento</div>',
        unsafe_allow_html=True,
    )

    std = safe_std(p_stats, "voto")

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
            '<div class="section-title">💰 Quotazione attuale</div>',
            unsafe_allow_html=True,
        )

        q1, q2, q3, q4 = st.columns(4)

        q1.metric(
            "Quotazione",
            current_quote.get("quotazione_attuale", "-")
        )

        q2.metric(
            "FVM",
            current_quote.get("fvm", "-")
        )

        q3.metric(
            "Ruolo",
            current_quote.get("ruolo", "-")
        )

        q4.metric(
            "Squadra",
            current_quote.get("squadra", "-")
        )

    # ========================================================
    # DATI GREZZI
    # ========================================================

    with st.expander("📄 Visualizza statistiche storiche complete"):

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
        f"Errore nel caricamento dei dati da Supabase: {e}"
    )

    st.stop()


if quot.empty:

    st.warning(
        "La tabella giocatori_quotazioni è vuota."
    )

    st.stop()


# ============================================================
# NORMALIZZAZIONE
# ============================================================

quot["player_id"] = pd.to_numeric(
    quot["player_id"],
    errors="coerce"
)

df["player_id"] = pd.to_numeric(
    df["player_id"],
    errors="coerce"
)


# ============================================================
# ROSA ATTUALE
# ============================================================

if "stagione" in quot.columns:

    seasons = quot["stagione"].dropna().unique()

    if len(seasons) > 1:

        try:
            latest_season = sorted(
                seasons,
                key=lambda x: str(x)
            )[-1]

            current_quot = quot[
                quot["stagione"] == latest_season
            ].copy()

        except Exception:

            current_quot = quot.copy()

    else:

        current_quot = quot.copy()

else:

    current_quot = quot.copy()


# ============================================================
# HEADER APP
# ============================================================

st.title("⚽ FantaAI")

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

role_col, info_col = st.columns([1, 3])

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

if selected_role != "Tutti":

    quot_view = quot_view[
        quot_view["ruolo"] == selected_role
    ]


quot_view = quot_view.sort_values(
    "nome"
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

    st.markdown("### 👥 Giocatori")

    st.caption(
        f"{len(quot_view)} giocatori disponibili"
    )

    if quot_view.empty:

        st.info(
            "Nessun giocatore trovato per questo ruolo."
        )

        selected_id = None

    else:

        options_df = (
            quot_view[
                [
                    "player_id",
                    "nome",
                    "squadra",
                    "ruolo",
                    "quotazione_attuale",
                ]
            ]
            .drop_duplicates(
                subset="player_id"
            )
        )

        labels = []

        for row in options_df.itertuples():

            labels.append(
                f"{row.nome}  •  {row.squadra}"
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
