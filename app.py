```python
import os

import pandas as pd
import streamlit as st
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
        "❌ SUPABASE_URL e/o SUPABASE_KEY non configurate."
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

    .section-title {
        margin-top: 28px;
        margin-bottom: 12px;
        font-size: 20px;
        font-weight: 650;
    }

    .player-subtitle {
        color: #64748b;
        font-size: 16px;
        margin-top: -12px;
        margin-bottom: 20px;
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
# LETTURA SUPABASE
# ============================================================

def fetch_all_rows(
    table_name,
    page_size=1000,
):
    """
    Scarica tutte le righe della tabella usando paginazione.
    """

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


# ============================================================
# LOAD STORICO
# ============================================================

@st.cache_data(ttl=600)
def load_stats():

    data = fetch_all_rows(
        "player_stats_history"
    )

    return pd.DataFrame(data)


# ============================================================
# LOAD QUOTAZIONI
# ============================================================

@st.cache_data(ttl=600)
def load_quotazioni():

    data = fetch_all_rows(
        "giocatori_quotazioni"
    )

    return pd.DataFrame(data)


# ============================================================
# NORMALIZZAZIONE PLAYER ID
# ============================================================

def normalize_player_id(value):
    """
    Trasforma:

        2155
        "2155"
        2155.0
        "2155.0"

    nello stesso identificativo intero.
    """

    if pd.isna(value):
        return pd.NA

    try:
        return int(float(str(value).strip()))
    except Exception:
        return pd.NA


def normalize_player_ids(df):

    result = df.copy()

    if "player_id" not in result.columns:
        return result

    result["player_id"] = (
        result["player_id"]
        .apply(normalize_player_id)
        .astype("Int64")
    )

    return result


# ============================================================
# UTILITY
# ============================================================

def numeric_series(
    df,
    column,
):

    if column not in df.columns:
        return pd.Series(
            0.0,
            index=df.index,
            dtype="float64",
        )

    return pd.to_numeric(
        df[column],
        errors="coerce",
    )


def safe_sum(
    df,
    column,
):

    if column not in df.columns:
        return 0

    values = numeric_series(
        df,
        column,
    )

    return int(
        values.fillna(0).sum()
    )


def safe_mean(
    df,
    column,
):

    if column not in df.columns:
        return 0.0

    values = numeric_series(
        df,
        column,
    )

    value = values.mean()

    if pd.isna(value):
        return 0.0

    return float(value)


def safe_std(
    df,
    column,
):

    if column not in df.columns:
        return None

    values = numeric_series(
        df,
        column,
    ).dropna()

    if len(values) < 2:
        return None

    value = values.std()

    if pd.isna(value):
        return None

    return float(value)


# ============================================================
# STAGIONE
# ============================================================

def season_sort_key(value):

    if pd.isna(value):
        return -1

    value = str(value).strip()

    try:

        first = value.split("/")[0]

        return int(first)

    except Exception:

        return -1


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
        key=season_sort_key,
    )


# ============================================================
# VALORI QUOTAZIONE
# ============================================================

def get_quote_value(row):

    """
    Cerca il valore della quotazione attuale
    anche se la colonna ha un nome leggermente diverso.
    """

    possible_columns = [
        "quotazione_attuale",
        "quotazione",
        "quota",
        "quotazione_corrente",
    ]

    for column in possible_columns:

        if column in row.index:

            value = row.get(column)

            if pd.notna(value):
                return value

    return "-"


def get_fvm_value(row):

    """
    Cerca i fantamilioni suggeriti.

    Supporta diversi possibili nomi della colonna.
    """

    possible_columns = [
        "fvm",
        "fantamilioni_suggeriti",
        "fantamilioni",
        "fm_suggeriti",
        "prezzo_suggerito",
        "offerta_suggerita",
    ]

    for column in possible_columns:

        if column in row.index:

            value = row.get(column)

            if pd.notna(value):
                return value

    return "-"


# ============================================================
# ULTIMA QUOTAZIONE DEL GIOCATORE
# ============================================================

def get_latest_quote_row(
    player_quotes,
):

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


# ============================================================
# CONTINUITÀ
# ============================================================

def get_continuity(
    player_stats,
):

    std = safe_std(
        player_stats,
        "voto",
    )

    if std is None:
        return None, "N/D"

    if std < 0.60:
        return std, "🟢 Molto continuo"

    if std < 0.90:
        return std, "🟡 Abbastanza continuo"

    return std, "🔴 Altalenante"


# ============================================================
# MEDIA MOBILE
# ============================================================

def build_rolling_data(
    player_stats,
    window=5,
):

    if player_stats.empty:
        return pd.DataFrame()

    if "stagione" not in player_stats.columns:
        return pd.DataFrame()

    if "giornata" not in player_stats.columns:
        return pd.DataFrame()

    result = player_stats.copy()

    # --------------------------------------------------------
    # GIORNATA
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # STAGIONE
    # --------------------------------------------------------

    result["stagione"] = (
        result["stagione"]
        .astype(str)
        .str.strip()
    )

    result["_season_sort"] = (
        result["stagione"]
        .apply(season_sort_key)
    )

    result = result.sort_values(
        [
            "_season_sort",
            "giornata",
        ]
    ).copy()

    # --------------------------------------------------------
    # MEDIA MOBILE VOTO
    # --------------------------------------------------------

    if "voto" in result.columns:

        result["voto"] = pd.to_numeric(
            result["voto"],
            errors="coerce",
        )

        result["media_mobile_voto"] = (
            result
            .groupby(
                "stagione",
                sort=False,
            )["voto"]
            .transform(
                lambda x:
                x.rolling(
                    window=window,
                    min_periods=1,
                ).mean()
            )
        )

    # --------------------------------------------------------
    # MEDIA MOBILE FANTAVOTO
    # --------------------------------------------------------

    if "fanta_voto" in result.columns:

        result["fanta_voto"] = pd.to_numeric(
            result["fanta_voto"],
            errors="coerce",
        )

        result["media_mobile_fanta"] = (
            result
            .groupby(
                "stagione",
                sort=False,
            )["fanta_voto"]
            .transform(
                lambda x:
                x.rolling(
                    window=window,
                    min_periods=1,
                ).mean()
            )
        )

    # --------------------------------------------------------
    # LABEL
    # --------------------------------------------------------

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
    # NORMALIZZAZIONE ID
    # ========================================================

    player_id = normalize_player_id(
        player_id
    )

    if pd.isna(player_id):

        st.error(
            "❌ Player ID non valido."
        )

        return

    player_id = int(player_id)

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
    # DIAGNOSTICA
    # ========================================================

    with st.expander(
        "🔎 Diagnostica giocatore",
        expanded=False,
    ):

        st.write(
            f"**Player ID selezionato:** `{player_id}`"
        )

        st.write(
            f"**Righe quotazioni:** `{len(p_quotes)}`"
        )

        st.write(
            f"**Righe storico:** `{len(p_stats)}`"
        )

        if current_quote is not None:

            st.success(
                "✅ Quotazione trovata."
            )

            st.write(
                "**Nome:**",
                current_quote.get(
                    "nome",
                    "-"
                ),
            )

            st.write(
                "**Stagione quotazione:**",
                current_quote.get(
                    "stagione",
                    "-"
                ),
            )

            st.write(
                "**Quotazione:**",
                get_quote_value(
                    current_quote
                ),
            )

            st.write(
                "**Fantamilioni suggeriti:**",
                get_fvm_value(
                    current_quote
                ),
            )

        else:

            st.error(
                f"❌ Nessuna quotazione per "
                f"player_id {player_id}."
            )

        if not p_stats.empty:

            st.success(
                "✅ Storico trovato."
            )

            if "stagione" in p_stats.columns:

                st.write(
                    "**Stagioni presenti:**",
                    sorted(
                        p_stats["stagione"]
                        .dropna()
                        .astype(str)
                        .unique(),
                        key=season_sort_key,
                    ),
                )

        else:

            st.error(
                f"❌ Nessuno storico per "
                f"player_id {player_id}."
            )

    # ========================================================
    # ANAGRAFICA
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
        [3, 1.4]
    )

    with header_left:

        st.header(
            nome
        )

        st.markdown(
            f"""
            <div class="player-subtitle">
                {squadra} • {ruolo}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with header_right:

        if current_quote is not None:

            quota = get_quote_value(
                current_quote
            )

            fvm = get_fvm_value(
                current_quote
            )

            q1, q2 = st.columns(2)

            with q1:

                st.metric(
                    "Quotazione attuale",
                    quota,
                )

            with q2:

                st.metric(
                    "Fantamilioni suggeriti",
                    fvm,
                )

    # ========================================================
    # CEDUTO
    # ========================================================

    if current_quote is not None:

        ceduto = current_quote.get(
            "ceduto",
            False,
        )

        ceduto_string = str(
            ceduto
        ).strip().lower()

        if (
            ceduto is True
            or ceduto_string in [
                "true",
                "1",
                "yes",
                "si",
            ]
        ):

            st.warning(
                "⚠️ Il giocatore risulta marcato "
                "come ceduto."
            )

    # ========================================================
    # NESSUNO STORICO
    # ========================================================

    if p_stats.empty:

        st.error(
            "❌ Nessuna statistica storica trovata "
            f"per player_id {player_id}."
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
    # KPI
    # ========================================================

    st.markdown(
        '<div class="section-title">'
        '📊 Rendimento storico complessivo'
        '</div>',
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # PRESENZE
    # --------------------------------------------------------

    if "voto" in p_stats.columns:

        presenze = int(
            numeric_series(
                p_stats,
                "voto",
            ).count()
        )

    else:

        presenze = 0

    # --------------------------------------------------------
    # MEDIA VOTO
    # --------------------------------------------------------

    media_voto = safe_mean(
        p_stats,
        "voto",
    )

    # --------------------------------------------------------
    # FANTAMEDIA
    # --------------------------------------------------------

    fantamedia = safe_mean(
        p_stats,
        "fanta_voto",
    )

    # --------------------------------------------------------
    # GOL
    # --------------------------------------------------------

    gol = safe_sum(
        p_stats,
        "gf",
    )

    # --------------------------------------------------------
    # ASSIST
    # --------------------------------------------------------

    assist = safe_sum(
        p_stats,
        "ass",
    )

    # --------------------------------------------------------
    # CONTINUITÀ
    # --------------------------------------------------------

    std, continuity_label = get_continuity(
        p_stats
    )

    # ========================================================
    # KPI PRINCIPALI
    # ========================================================

    k1, k2, k3, k4, k5, k6 = st.columns(6)

    with k1:

        st.metric(
            "Presenze",
            presenze,
        )

    with k2:

        st.metric(
            "Media voto",
            f"{media_voto:.2f}",
        )

    with k3:

        st.metric(
            "Fantamedia",
            f"{fantamedia:.2f}",
        )

    with k4:

        if std is not None:

            st.metric(
                "Continuità",
                f"{std:.2f}",
                help=(
                    "Deviazione standard del voto. "
                    "Più è bassa, più il rendimento "
                    "è continuo."
                ),
            )

            st.caption(
                continuity_label
            )

        else:

            st.metric(
                "Continuità",
                "N/D",
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
    # FORMA
    # ========================================================

    st.markdown(
        '<div class="section-title">'
        '📈 Forma recente'
        '</div>',
        unsafe_allow_html=True,
    )

    rolling_df = build_rolling_data(
        p_stats,
        window=5,
    )

    if rolling_df.empty:

        st.info(
            "Non ci sono dati sufficienti "
            "per costruire il grafico."
        )

    else:

        fig = go.Figure()

        # ----------------------------------------------------
        # MEDIA MOBILE VOTO
        # ----------------------------------------------------

        if "media_mobile_voto" in rolling_df.columns:

            fig.add_trace(
                go.Scatter(
                    x=rolling_df["periodo"],
                    y=rolling_df[
                        "media_mobile_voto"
                    ],
                    mode="lines",
                    name="Media voto",
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

        # ----------------------------------------------------
        # MEDIA MOBILE FANTAVOTO
        # ----------------------------------------------------

        if "media_mobile_fanta" in rolling_df.columns:

            fig.add_trace(
                go.Scatter(
                    x=rolling_df["periodo"],
                    y=rolling_df[
                        "media_mobile_fanta"
                    ],
                    mode="lines",
                    name="Fantamedia",
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
            title="Andamento della forma — media mobile 5 giornate",
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

        season_rows = []

        for season, group in p_stats.groupby(
            "stagione",
            sort=False,
        ):

            if "voto" in group.columns:

                season_presenze = int(
                    numeric_series(
                        group,
                        "voto",
                    ).count()
                )

            else:

                season_presenze = 0

            season_rows.append(
                {
                    "Stagione": season,
                    "Presenze": season_presenze,
                    "Media voto": round(
                        safe_mean(
                            group,
                            "voto",
                        ),
                        2,
                    ),
                    "Fantamedia": round(
                        safe_mean(
                            group,
                            "fanta_voto",
                        ),
                        2,
                    ),
                    "Gol": safe_sum(
                        group,
                        "gf",
                    ),
                    "Assist": safe_sum(
                        group,
                        "ass",
                    ),
                }
            )

        season_agg = pd.DataFrame(
            season_rows
        )

        if not season_agg.empty:

            season_agg["_sort"] = (
                season_agg["Stagione"]
                .apply(season_sort_key)
            )

            season_agg = (
                season_agg
                .sort_values(
                    "_sort",
                    ascending=False,
                )
                .drop(
                    columns="_sort"
                )
            )

            st.dataframe(
                season_agg,
                use_container_width=True,
                hide_index=True,
            )

    # ========================================================
    # BONUS / MALUS
    # ========================================================

    st.markdown(
        '<div class="section-title">'
        '⚽ Altri bonus e malus'
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
    # DATI COMPLETI
    # ========================================================

    with st.expander(
        "📄 Visualizza statistiche storiche complete"
    ):

        st.dataframe(
            p_stats,
            use_container_width=True,
            hide_index=True,
        )

        csv = (
            p_stats
            .to_csv(index=False)
            .encode("utf-8")
        )

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
        "❌ Errore nel caricamento dei dati da Supabase."
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
        "❌ La tabella player_stats_history "
        "non contiene dati."
    )

    st.stop()


if quot.empty:

    st.error(
        "❌ La tabella giocatori_quotazioni "
        "non contiene dati."
    )

    st.stop()


# ============================================================
# NORMALIZZAZIONE
# ============================================================

df = normalize_player_ids(
    df
)

quot = normalize_player_ids(
    quot
)


# ============================================================
# CONTROLLO COLONNE
# ============================================================

if "player_id" not in df.columns:

    st.error(
        "❌ player_stats_history non contiene "
        "la colonna player_id."
    )

    st.stop()


if "player_id" not in quot.columns:

    st.error(
        "❌ giocatori_quotazioni non contiene "
        "la colonna player_id."
    )

    st.stop()


# ============================================================
# RIMOZIONE ID NULL
# ============================================================

df = df[
    df["player_id"].notna()
].copy()

quot = quot[
    quot["player_id"].notna()
].copy()


# ============================================================
# ID COMUNI
# ============================================================

stats_ids = set(
    df["player_id"]
    .astype(int)
    .unique()
)

quote_ids = set(
    quot["player_id"]
    .astype(int)
    .unique()
)

common_ids = (
    stats_ids
    .intersection(quote_ids)
)


# ============================================================
# DIAGNOSTICA DATABASE
# ============================================================

with st.expander(
    "🔎 Diagnostica database",
    expanded=False,
):

    st.write(
        f"**Righe storico:** {len(df):,}"
    )

    st.write(
        f"**Righe quotazioni:** {len(quot):,}"
    )

    st.write(
        f"**Player ID distinti nello storico:** "
        f"{len(stats_ids):,}"
    )

    st.write(
        f"**Player ID distinti nelle quotazioni:** "
        f"{len(quote_ids):,}"
    )

    st.write(
        f"**Player ID presenti in entrambe:** "
        f"{len(common_ids):,}"
    )

    # --------------------------------------------------------
    # COLONNE
    # --------------------------------------------------------

    st.markdown(
        "#### Colonne database"
    )

    c1, c2 = st.columns(2)

    with c1:

        st.write(
            "**player_stats_history:**"
        )

        st.code(
            ", ".join(df.columns)
        )

    with c2:

        st.write(
            "**giocatori_quotazioni:**"
        )

        st.code(
            ", ".join(quot.columns)
        )

    # --------------------------------------------------------
    # TEST CUTRONE
    # --------------------------------------------------------

    st.markdown(
        "#### Test Cutrone — player_id 2155"
    )

    cutrone_id = 2155

    cutrone_stats = df[
        df["player_id"] == cutrone_id
    ].copy()

    cutrone_quote = quot[
        quot["player_id"] == cutrone_id
    ].copy()

    c1, c2 = st.columns(2)

    with c1:

        st.write(
            "### Storico"
        )

        if cutrone_stats.empty:

            st.error(
                "❌ Cutrone NON trovato nello storico."
            )

        else:

            st.success(
                f"✅ Trovato: "
                f"{len(cutrone_stats)} righe"
            )

            columns = [
                "player_id",
                "nome",
                "stagione",
                "giornata",
                "voto",
                "fanta_voto",
            ]

            columns = [
                c
                for c in columns
                if c in cutrone_stats.columns
            ]

            st.dataframe(
                cutrone_stats[columns].head(20),
                use_container_width=True,
                hide_index=True,
            )

    with c2:

        st.write(
            "### Quotazione"
        )

        if cutrone_quote.empty:

            st.error(
                "❌ Cutrone NON trovato nelle quotazioni."
            )

        else:

            st.success(
                f"✅ Trovato: "
                f"{len(cutrone_quote)} righe"
            )

            columns = [
                "player_id",
                "nome",
                "stagione",
                "quotazione_attuale",
                "fvm",
                "fantamilioni_suggeriti",
            ]

            columns = [
                c
                for c in columns
                if c in cutrone_quote.columns
            ]

            st.dataframe(
                cutrone_quote[columns].head(20),
                use_container_width=True,
                hide_index=True,
            )


# ============================================================
# ULTIMA STAGIONE QUOTAZIONI
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
# HEADER
# ============================================================

st.title(
    "⚽ FantaAI"
)

if latest_season:

    st.markdown(
        f"""
        ### Analisi dei giocatori della rosa attuale

        Quotazioni stagione **{latest_season}**
        """
    )

else:

    st.markdown(
        """
        ### Analisi dei giocatori della rosa attuale
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
        [
            "Tutti",
            "P",
            "D",
            "C",
            "A",
        ],
    )

with info_col:

    st.markdown(
        f"**Rosa attuale:** "
        f"{len(current_quot)} giocatori"
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


# ============================================================
# ORDINAMENTO
# ============================================================

if "nome" in quot_view.columns:

    quot_view = quot_view.sort_values(
        "nome",
        na_position="last",
    )


# ============================================================
# LAYOUT
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

        st.warning(
            "⚠️ Nessun giocatore trovato "
            "nella stagione corrente."
        )

        selected_id = None

    else:

        # ----------------------------------------------------
        # Una sola riga per player_id
        # ----------------------------------------------------

        options_df = (
            quot_view
            .drop_duplicates(
                subset="player_id"
            )
            .copy()
        )

        labels = []
        ids = []

        for _, row in options_df.iterrows():

            nome = row.get(
                "nome",
                "Giocatore",
            )

            squadra = row.get(
                "squadra",
                "-",
            )

            player_id = row[
                "player_id"
            ]

            labels.append(
                f"{nome} • {squadra}"
            )

            ids.append(
                int(player_id)
            )

        label_to_id = dict(
            zip(
                labels,
                ids,
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
```
