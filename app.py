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

    .section-title {
        margin-top: 28px;
        margin-bottom: 12px;
        font-size: 20px;
        font-weight: 650;
    }

    .player-subtitle {
        color: #64748b;
        font-size: 16px;
        margin-top: -10px;
        margin-bottom: 20px;
    }

    .quote-container {
        background: linear-gradient(135deg, #111827, #1f2937);
        color: white;
        border-radius: 16px;
        padding: 18px 20px;
        text-align: center;
        min-height: 125px;
    }

    .quote-label {
        font-size: 12px;
        opacity: 0.75;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .quote-value {
        font-size: 38px;
        font-weight: 700;
        line-height: 1.1;
        margin-top: 7px;
    }

    .quote-fvm {
        font-size: 14px;
        opacity: 0.8;
        margin-top: 5px;
    }

    .continuity-good {
        color: #16a34a;
        font-weight: 700;
    }

    .continuity-medium {
        color: #ca8a04;
        font-weight: 700;
    }

    .continuity-bad {
        color: #dc2626;
        font-weight: 700;
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
        SUPABASE_KEY,
    )


supabase = init_supabase()


# ============================================================
# CARICAMENTO PAGINATO
# ============================================================

def fetch_all_rows(
    table_name,
    page_size=1000,
):
    """
    Scarica tutte le righe della tabella usando paginazione.

    Evita il limite delle prime 1000 righe di Supabase/PostgREST.
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
# LOAD STATS
# ============================================================

@st.cache_data(ttl=600)
def load_stats():

    rows = fetch_all_rows(
        "player_stats_history"
    )

    return pd.DataFrame(rows)


# ============================================================
# LOAD QUOTAZIONI
# ============================================================

@st.cache_data(ttl=600)
def load_quotazioni():

    rows = fetch_all_rows(
        "giocatori_quotazioni"
    )

    return pd.DataFrame(rows)


# ============================================================
# UTILITY
# ============================================================

def normalize_player_id(df):

    if df.empty:
        return df

    df = df.copy()

    if "player_id" in df.columns:

        df["player_id"] = pd.to_numeric(
            df["player_id"],
            errors="coerce",
        )

    return df


def safe_numeric(
    df,
    column,
):

    if column not in df.columns:

        return pd.Series(
            0,
            index=df.index,
            dtype="float64",
        )

    return pd.to_numeric(
        df[column],
        errors="coerce",
    ).fillna(0)


def safe_sum(
    df,
    column,
):

    if column not in df.columns:
        return 0

    return int(
        safe_numeric(
            df,
            column,
        ).sum()
    )


def safe_mean(
    df,
    column,
):

    if column not in df.columns:
        return 0

    values = pd.to_numeric(
        df[column],
        errors="coerce",
    )

    value = values.mean()

    if pd.isna(value):
        return 0

    return float(value)


def safe_std(
    df,
    column,
):

    if column not in df.columns:
        return None

    values = pd.to_numeric(
        df[column],
        errors="coerce",
    )

    value = values.std()

    if pd.isna(value):
        return None

    return float(value)


def season_sort_key(value):

    value = str(value).strip()

    try:

        first_part = value.split("/")[0]

        return int(first_part)

    except Exception:

        return 0


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
        key=season_sort_key,
    )


def get_latest_quote_row(
    quotations,
):

    if quotations.empty:
        return None

    result = quotations.copy()

    if "stagione" in result.columns:

        result["_season_sort"] = (
            result["stagione"]
            .apply(season_sort_key)
        )

        result = result.sort_values(
            "_season_sort"
        )

    return result.iloc[-1]


def format_value(
    value,
    decimals=2,
):

    if value is None:
        return "-"

    try:

        value = float(value)

        return f"{value:.{decimals}f}"

    except Exception:

        return str(value)


# ============================================================
# CONTINUITÀ
# ============================================================

def calculate_continuity(
    stats,
):

    std = safe_std(
        stats,
        "voto",
    )

    if std is None:
        return None, "-"

    if std < 0.60:

        return (
            round(std, 2),
            "🟢 Molto continuo",
        )

    elif std < 0.90:

        return (
            round(std, 2),
            "🟡 Abbastanza continuo",
        )

    else:

        return (
            round(std, 2),
            "🔴 Altalenante",
        )


# ============================================================
# MEDIA MOBILE
# ============================================================

def build_rolling_data(
    player_stats,
    window=5,
):

    if player_stats.empty:
        return pd.DataFrame()

    required = [
        "stagione",
        "giornata",
    ]

    for column in required:

        if column not in player_stats.columns:
            return pd.DataFrame()

    result = player_stats.copy()

    result["giornata"] = pd.to_numeric(
        result["giornata"],
        errors="coerce",
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

    result = result.sort_values(
        [
            "stagione",
            "giornata",
        ]
    )

    # --------------------------------------------------------
    # MEDIA MOBILE PER STAGIONE
    # --------------------------------------------------------

    if "voto" in result.columns:

        result["voto"] = pd.to_numeric(
            result["voto"],
            errors="coerce",
        )

        result["media_mobile_voto"] = (
            result
            .groupby("stagione")["voto"]
            .transform(
                lambda x: x.rolling(
                    window=window,
                    min_periods=1,
                ).mean()
            )
        )

    if "fanta_voto" in result.columns:

        result["fanta_voto"] = pd.to_numeric(
            result["fanta_voto"],
            errors="coerce",
        )

        result["media_mobile_fanta"] = (
            result
            .groupby("stagione")["fanta_voto"]
            .transform(
                lambda x: x.rolling(
                    window=window,
                    min_periods=1,
                ).mean()
            )
        )

    result["periodo"] = (
        result["stagione"]
        + " • G"
        + result["giornata"].astype(str)
    )

    return result


# ============================================================
# PROFILO GIOCATORE
# ============================================================

def render_player_detail(
    player_id,
    stats,
    quotations,
):

    # ========================================================
    # QUOTAZIONI
    # ========================================================

    p_quotes = quotations[
        quotations["player_id"] == player_id
    ].copy()

    current_quote = get_latest_quote_row(
        p_quotes
    )

    # ========================================================
    # STORICO
    # ========================================================

    p_stats = stats[
        stats["player_id"] == player_id
    ].copy()

    # ========================================================
    # DATI ANAGRAFICI
    # ========================================================

    if current_quote is not None:

        nome = current_quote.get(
            "nome",
            "Giocatore",
        )

        ruolo = current_quote.get(
            "ruolo",
            "-",
        )

        squadra = current_quote.get(
            "squadra",
            "-",
        )

    elif not p_stats.empty:

        nome = p_stats.iloc[-1].get(
            "nome",
            "Giocatore",
        )

        ruolo = p_stats.iloc[-1].get(
            "ruolo",
            "-",
        )

        squadra = p_stats.iloc[-1].get(
            "squadra",
            "-",
        )

    else:

        nome = "Giocatore"
        ruolo = "-"
        squadra = "-"

    # ========================================================
    # HEADER
    # ========================================================

    header_left, header_right = st.columns(
        [3.5, 1]
    )

    with header_left:

        st.title(nome)

        st.markdown(
            f"""
            <div class="player-subtitle">
                {squadra} &nbsp; • &nbsp; {ruolo}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with header_right:

        if current_quote is not None:

            quota = current_quote.get(
                "quotazione_attuale",
                "-",
            )

            fvm = current_quote.get(
                "fvm",
                "-",
            )

            st.markdown(
                f"""
                <div class="quote-container">
                    <div class="quote-label">
                        Quotazione attuale
                    </div>

                    <div class="quote-value">
                        {quota}
                    </div>

                    <div class="quote-fvm">
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
            False,
        )

        if (
            ceduto is True
            or str(ceduto).lower() == "true"
        ):

            st.warning(
                "⚠️ Questo giocatore risulta marcato "
                "come ceduto nella tabella delle quotazioni."
            )

    # ========================================================
    # NESSUNO STORICO
    # ========================================================

    if p_stats.empty:

        st.info(
            "Non sono presenti statistiche storiche "
            "per questo giocatore."
        )

        return

    # ========================================================
    # NORMALIZZAZIONE STORICO
    # ========================================================

    if "stagione" in p_stats.columns:

        p_stats["stagione"] = (
            p_stats["stagione"]
            .astype(str)
            .str.strip()
        )

    if "giornata" in p_stats.columns:

        p_stats["giornata"] = pd.to_numeric(
            p_stats["giornata"],
            errors="coerce",
        )

    # ========================================================
    # KPI PRINCIPALI
    # ========================================================

    st.markdown(
        '<div class="section-title">'
        '📊 Rendimento storico'
        '</div>',
        unsafe_allow_html=True,
    )

    # Presenze

    if "voto" in p_stats.columns:

        presenze = int(
            pd.to_numeric(
                p_stats["voto"],
                errors="coerce",
            ).count()
        )

    else:

        presenze = 0

    # Media voto

    media_voto = safe_mean(
        p_stats,
        "voto",
    )

    # Fantamedia

    fantamedia = safe_mean(
        p_stats,
        "fanta_voto",
    )

    # Gol

    gol = safe_sum(
        p_stats,
        "gf",
    )

    # Assist

    assist = safe_sum(
        p_stats,
        "ass",
    )

    # Continuità

    std,
    continuita = calculate_continuity(
        p_stats
    )

    k1, k2, k3, k4, k5, k6 = st.columns(6)

    with k1:

        st.metric(
            "Presenze",
            presenze,
        )

    with k2:

        st.metric(
            "Media voto",
            format_value(
                media_voto
            ),
        )

    with k3:

        st.metric(
            "Fantamedia",
            format_value(
                fantamedia
            ),
        )

    with k4:

        if std is not None:

            st.metric(
                "Continuità",
                format_value(
                    std
                ),
                help=(
                    "Deviazione standard del voto. "
                    "Più è bassa, più il rendimento è continuo."
                ),
            )

            st.caption(
                continuita
            )

        else:

            st.metric(
                "Continuità",
                "-",
            )

    with k5:

        st.metric(
            "Gol",
            gol,
        )

    with k6:

        st.metric(
            "Assist",
            assist,
        )

    # ========================================================
    # MEDIA MOBILE 5 GIORNATE
    # ========================================================

    st.markdown(
        '<div class="section-title">'
        '📈 Andamento della forma'
        '</div>',
        unsafe_allow_html=True,
    )

    rolling_df = build_rolling_data(
        p_stats,
        window=5,
    )

    if rolling_df.empty:

        st.info(
            "Non sono disponibili dati sufficienti "
            "per calcolare l'andamento della forma."
        )

    else:

        fig = go.Figure()

        if "media_mobile_voto" in rolling_df.columns:

            fig.add_trace(
                go.Scatter(
                    x=rolling_df["periodo"],
                    y=rolling_df["media_mobile_voto"],
                    mode="lines",
                    name="Media voto — 5 giornate",
                    line=dict(
                        width=3
                    ),
                    hovertemplate=(
                        "%{x}<br>"
                        "Media voto: %{y:.2f}"
                        "<extra></extra>"
                    ),
                )
            )

        if "media_mobile_fanta" in rolling_df.columns:

            fig.add_trace(
                go.Scatter(
                    x=rolling_df["periodo"],
                    y=rolling_df["media_mobile_fanta"],
                    mode="lines",
                    name="Fantamedia — 5 giornate",
                    line=dict(
                        width=3
                    ),
                    hovertemplate=(
                        "%{x}<br>"
                        "Fantamedia: %{y:.2f}"
                        "<extra></extra>"
                    ),
                )
            )

        fig.update_layout(
            title="Media mobile a 5 giornate",
            xaxis_title="Stagione / Giornata",
            yaxis_title="Media",
            hovermode="x unified",
            height=430,
            margin=dict(
                l=20,
                r=20,
                t=60,
                b=20,
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
            ),
        )

        fig.update_xaxes(
            rangeslider_visible=False
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    # ========================================================
    # RENDIMENTO PER STAGIONE
    # ========================================================

    st.markdown(
        '<div class="section-title">'
        '📅 Rendimento per stagione'
        '</div>',
        unsafe_allow_html=True,
    )

    if "stagione" in p_stats.columns:

        aggregation = {}

        if "voto" in p_stats.columns:

            aggregation["Presenze"] = (
                "voto",
                "count",
            )

            aggregation["Media voto"] = (
                "voto",
                "mean",
            )

        if "fanta_voto" in p_stats.columns:

            aggregation["Fantamedia"] = (
                "fanta_voto",
                "mean",
            )

        if "gf" in p_stats.columns:

            aggregation["Gol"] = (
                "gf",
                "sum",
            )

        if "ass" in p_stats.columns:

            aggregation["Assist"] = (
                "ass",
                "sum",
            )

        if aggregation:

            season_agg = (
                p_stats
                .groupby("stagione")
                .agg(**aggregation)
                .reset_index()
            )

            if "Media voto" in season_agg.columns:

                season_agg["Media voto"] = (
                    season_agg["Media voto"]
                    .round(2)
                )

            if "Fantamedia" in season_agg.columns:

                season_agg["Fantamedia"] = (
                    season_agg["Fantamedia"]
                    .round(2)
                )

            season_agg["_sort"] = (
                season_agg["stagione"]
                .apply(season_sort_key)
            )

            season_agg = (
                season_agg
                .sort_values("_sort")
                .drop(columns="_sort")
            )

            st.dataframe(
                season_agg,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "Non sono disponibili statistiche "
                "stagionali sufficienti."
            )

    else:

        st.info(
            "La colonna stagione non è disponibile."
        )

    # ========================================================
    # BONUS / MALUS SECONDARI
    # ========================================================

    st.markdown(
        '<div class="section-title">'
        '⚽ Bonus e malus'
        '</div>',
        unsafe_allow_html=True,
    )

    b1, b2, b3, b4 = st.columns(4)

    with b1:

        st.metric(
            "Rigori segnati",
            safe_sum(
                p_stats,
                "rf",
            ),
        )

    with b2:

        st.metric(
            "Ammonizioni",
            safe_sum(
                p_stats,
                "amm",
            ),
        )

    with b3:

        st.metric(
            "Espulsioni",
            safe_sum(
                p_stats,
                "esp",
            ),
        )

    with b4:

        st.metric(
            "Autogol",
            safe_sum(
                p_stats,
                "au",
            ),
        )

    # ========================================================
    # DATI STORICI COMPLETI
    # ========================================================

    with st.expander(
        "📄 Visualizza statistiche storiche complete"
    ):

        display_df = p_stats.copy()

        if "_season_sort" in display_df.columns:

            display_df = display_df.drop(
                columns="_season_sort"
            )

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
        )

        csv = display_df.to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            "⬇️ Scarica CSV",
            data=csv,
            file_name=f"{nome}_storico.csv",
            mime="text/csv",
        )


# ============================================================
# CARICAMENTO DATI
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

    st.error(
        "❌ La tabella giocatori_quotazioni è vuota."
    )

    st.stop()


# ============================================================
# NORMALIZZAZIONE
# ============================================================

df = normalize_player_id(
    df
)

quot = normalize_player_id(
    quot
)


# ============================================================
# CONTROLLO player_id
# ============================================================

if "player_id" not in df.columns:

    st.error(
        "❌ player_stats_history non contiene player_id."
    )

    st.stop()


if "player_id" not in quot.columns:

    st.error(
        "❌ giocatori_quotazioni non contiene player_id."
    )

    st.stop()


df = df[
    df["player_id"].notna()
].copy()

quot = quot[
    quot["player_id"].notna()
].copy()


# ============================================================
# DIAGNOSTICA
# ============================================================

with st.expander(
    "🔎 Diagnostica database",
    expanded=False,
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

    cutrone_stats = df[
        df["player_id"] == 2155
    ]

    cutrone_quote = quot[
        quot["player_id"] == 2155
    ]

    if not cutrone_stats.empty:

        st.success(
            f"✅ Cutrone (2155) nello storico: "
            f"{len(cutrone_stats)} righe"
        )

    else:

        st.error(
            "❌ Cutrone (2155) NON trovato nello storico."
        )

    if not cutrone_quote.empty:

        st.success(
            f"✅ Cutrone (2155) nelle quotazioni: "
            f"{len(cutrone_quote)} righe"
        )

    else:

        st.error(
            "❌ Cutrone (2155) NON trovato nelle quotazioni."
        )


# ============================================================
# STAGIONE QUOTAZIONI PIÙ RECENTE
# ============================================================

latest_season = get_latest_season(
    quot
)


if latest_season is not None:

    current_quot = quot[
        quot["stagione"]
        .astype(str)
        .str.strip()
        == str(latest_season).strip()
    ].copy()

else:

    current_quot = quot.copy()


# ============================================================
# HEADER APP
# ============================================================

st.title(
    "⚽ FantaAI"
)

if latest_season:

    st.markdown(
        f"""
        ### Analisi dei giocatori della rosa attuale

        Stagione quotazioni: **{latest_season}**

        Seleziona un ruolo e un giocatore per visualizzare
        **quotazione, FVM e rendimento storico completo**.
        """
    )

else:

    st.markdown(
        """
        ### Analisi dei giocatori della rosa attuale

        Seleziona un ruolo e un giocatore per visualizzare
        **quotazione, FVM e rendimento storico completo**.
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
        quot_view["ruolo"]
        == selected_role
    ]


if "nome" in quot_view.columns:

    quot_view = quot_view.sort_values(
        "nome",
        na_position="last",
    )


# ============================================================
# LAYOUT PRINCIPALE
# ============================================================

col_players, col_detail = st.columns(
    [1, 3.2],
    gap="large",
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

        required_columns = [
            "player_id",
            "nome",
            "squadra",
            "ruolo",
            "quotazione_attuale",
        ]

        available_columns = [
            column
            for column in required_columns
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
                "Giocatore",
            )

            squadra = getattr(
                row,
                "squadra",
                "-",
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
