import os
import html
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
    st.error("❌ SUPABASE_URL e/o SUPABASE_KEY non configurate.")
    st.stop()


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>
    /* --------------------------------------------------------
       TOKEN DI DESIGN
       Un solo accento cromatico deliberato (verde campo), scala
       di spaziatura e raggio bordi coerenti. Valori in rgba per
       restare leggibili sia su tema chiaro che scuro di Streamlit.
       -------------------------------------------------------- */
    :root {
        --fa-accent: #1F7A4D;
        --fa-accent-soft: rgba(31, 122, 77, .10);
        --fa-accent-border: rgba(31, 122, 77, .35);
        --fa-good: #1F7A4D;
        --fa-warn: #B8860B;
        --fa-bad: #C0392B;
        --fa-border: rgba(128, 128, 128, .18);
        --fa-border-strong: rgba(128, 128, 128, .28);
        --fa-surface: rgba(128, 128, 128, .05);
        --fa-muted: #7C8794;
        --fa-radius: 12px;
        --fa-space-sm: 10px;
        --fa-space-md: 16px;
        --fa-space-lg: 28px;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1600px;
    }

    /* --------------------------------------------------------
       TITOLI DI SEZIONE
       Barra di accento a sinistra per ancorare visivamente il
       titolo al blocco di contenuto che segue.
       -------------------------------------------------------- */
    .section-title {
        margin-top: var(--fa-space-lg);
        margin-bottom: var(--fa-space-md);
        padding-left: var(--fa-space-sm);
        border-left: 3px solid var(--fa-accent);
        font-size: 19px;
        font-weight: 650;
        letter-spacing: -0.01em;
        line-height: 1.3;
    }

    .player-subtitle {
        color: var(--fa-muted);
        font-size: 15px;
        margin-top: -10px;
        margin-bottom: var(--fa-space-md);
    }

    /* --------------------------------------------------------
       CARD DI QUOTAZIONE
       Gerarchia tra dato primario (quotazione) e secondario (FVM).
       -------------------------------------------------------- */
    .quote-card {
        border: 1px solid var(--fa-border-strong);
        border-top: 3px solid var(--fa-accent);
        border-radius: var(--fa-radius);
        padding: 16px 20px;
        margin-top: 4px;
        background: var(--fa-surface);
    }

    .quote-label {
        color: var(--fa-muted);
        font-size: 12px;
        text-transform: none;
        margin-bottom: 2px;
    }

    .quote-value {
        font-size: 32px;
        font-weight: 700;
        line-height: 1.1;
        color: var(--fa-accent);
    }

    .quote-divider {
        height: 1px;
        background: var(--fa-border);
        margin: 12px 0;
    }

    .quote-fvm {
        color: var(--fa-muted);
        font-size: 12px;
        margin-bottom: 2px;
    }

    .quote-value-secondary {
        font-size: 20px;
        font-weight: 600;
        line-height: 1.1;
    }

    /* --------------------------------------------------------
       PANNELLI KPI
       Raggruppano visivamente i gruppi di st.metric affini,
       usando il contenitore nativo st.container(border=True)
       di Streamlit (data-testid stVerticalBlockBorderWrapper).
       -------------------------------------------------------- */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: var(--fa-radius) !important;
        border-color: var(--fa-border-strong) !important;
        background: var(--fa-surface);
    }

    div[data-testid="stMetric"] {
        padding: 4px 2px;
    }

    div[data-testid="stMetricLabel"] {
        font-size: 13px;
        color: var(--fa-muted);
    }

    div[data-testid="stMetricValue"] {
        font-size: 26px;
        font-weight: 700;
    }

    /* Badge di continuità: rinforza con colore reale lo stesso
       giudizio 🟢/🟡/🔴 già calcolato dalla logica esistente
       (get_continuity), qui reso come elemento HTML sotto il
       nostro controllo diretto anziché una caption grigia piatta. */
    .fa-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 13px;
        font-weight: 600;
    }

    /* --------------------------------------------------------
       LISTA GIOCATORI
       Il contenitore scrollabile con altezza fissa è nativo
       (st.container(height=..., border=True)): riceve già lo
       stile pannello sopra tramite stVerticalBlockBorderWrapper.
       Qui aggiungiamo solo l'hover sulle singole opzioni.
       -------------------------------------------------------- */
    div[role="radiogroup"] label {
        padding: 5px 6px;
        border-radius: 8px;
    }

    div[role="radiogroup"] label:hover {
        background: var(--fa-accent-soft);
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
# CARICAMENTO SUPABASE PAGINATO
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
    return pd.DataFrame(fetch_all_rows("player_stats_history"))


@st.cache_data(ttl=600)
def load_quotazioni():
    return pd.DataFrame(fetch_all_rows("giocatori_quotazioni"))


# ============================================================
# NORMALIZZAZIONE
# ============================================================

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

    values = numeric_series(df, column).fillna(0)
    return float(values.sum())


def safe_mean(df, column):
    if column not in df.columns:
        return 0.0

    values = numeric_series(df, column).dropna()

    if values.empty:
        return 0.0

    return float(values.mean())


def safe_variance(df, column):
    if column not in df.columns:
        return None

    values = numeric_series(df, column).dropna()

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


# ============================================================
# BADGE VISIVO (solo presentazione, nessuna nuova logica)
# ============================================================

_CONTINUITY_BADGE_STYLE = {
    "🟢 Molto continuo": ("var(--fa-good)", "rgba(31,122,77,.12)"),
    "🟡 Abbastanza continuo": ("var(--fa-warn)", "rgba(184,134,11,.12)"),
    "🔴 Altalenante": ("var(--fa-bad)", "rgba(192,57,43,.12)"),
}


def render_continuity_badge(label):
    """
    Rende con colore reale il giudizio di continuità già calcolato
    da get_continuity(): stesso identico testo/etichetta, solo
    presentato come badge colorato invece di una caption grigia.
    """
    color, background = _CONTINUITY_BADGE_STYLE.get(
        label, ("var(--fa-muted)", "rgba(128,128,128,.10)")
    )
    st.markdown(
        f"""
        <span class="fa-badge" style="background:{background}; color:{color};">
            {html.escape(str(label))}
        </span>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# STAGIONE
# ============================================================

def season_sort_key(value):
    value = str(value).strip()

    try:
        return int(value.split("/")[0])
    except Exception:
        return -1


def get_latest_season(df):
    if df.empty or "stagione" not in df.columns:
        return None

    seasons = (
        df["stagione"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    seasons = seasons[seasons != ""]

    if seasons.empty:
        return None

    return max(seasons.unique(), key=season_sort_key)


# ============================================================
# QUOTAZIONE
# ============================================================

def get_latest_quote_row(player_quotes):
    if player_quotes.empty:
        return None

    result = player_quotes.copy()

    if "stagione" in result.columns:
        result["_season_sort"] = result["stagione"].apply(season_sort_key)
        result = result.sort_values("_season_sort")

    return result.iloc[-1]


# ============================================================
# PULIZIA RECORD CON VOTO *
# ============================================================

def remove_starred_vote_rows(df):
    """
    Il file Fantacalcio usa un asterisco nel voto per identificare
    una prestazione che non deve essere conteggiata come presenza.

    Se l'asterisco è ancora presente nel valore originale, la riga
    viene esclusa.

    Nota: se il parser ha già trasformato '6*' in 6.0 prima del
    caricamento su Supabase, l'informazione dell'asterisco è persa.
    In quel caso il parser deve essere corretto e i dati ricaricati.
    """
    if df.empty or "voto" not in df.columns:
        return df.copy()

    result = df.copy()

    raw_vote = result["voto"].astype(str).str.strip()

    starred = raw_vote.str.contains(r"\*", regex=True, na=False)

    if starred.any():
        result = result.loc[~starred].copy()

    return result


# ============================================================
# FANTAMEDIA
# ============================================================

def calculate_fantavoto(df):
    """
    Calcola il fantavoto secondo le regole classiche:

    +3  gol
    +1  assist
    +3  rigore segnato
    -2  autogol
    -1  espulsione
    -0.5 ammonizione
    +1  porta inviolata
    +3  rigore parato

    La porta inviolata viene applicata solo ai portieri.
    Il rigore parato viene applicato al portiere.

    Il valore viene calcolato a livello di singola prestazione,
    poi la fantamedia viene ottenuta dalla media dei fantavoti.
    """

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

    # Colonne possibili per porta inviolata / rigori parati.
    # Se non esistono, valgono zero.
    clean_sheet = pd.Series(0.0, index=result.index)
    penalty_saved = pd.Series(0.0, index=result.index)

    for column in ["pi", "porta_inviolata", "clean_sheet", "imbattuto"]:
        if column in result.columns:
            clean_sheet = numeric_series(result, column).fillna(0)
            break

    for column in ["rp", "rigori_parati", "rigore_parato"]:
        if column in result.columns:
            penalty_saved = numeric_series(result, column).fillna(0)
            break

    # Porta inviolata: solo P.
    if "ruolo" in result.columns:
        is_goalkeeper = (
            result["ruolo"]
            .astype(str)
            .str.strip()
            .str.upper()
            .eq("P")
        )
        clean_sheet = clean_sheet.where(is_goalkeeper, 0)

    result["fanta_voto_calcolato"] = (
        voto
        + gf * 3
        + ass
        + rf * 3
        - au * 2
        - esp
        - amm * 0.5
        + clean_sheet
        + penalty_saved * 3
    )

    # Il fantavoto deve esistere solo dove esiste un voto.
    result.loc[
        numeric_series(result, "voto").isna(),
        "fanta_voto_calcolato",
    ] = float("nan")

    return result


# ============================================================
# BONUS / MALUS TOTALI
# ============================================================

def calculate_bonus_malus(df):
    """
    Bonus/malus netto della singola prestazione:
        fantavoto - voto

    Questo permette di calcolare sia la media dei bonus/malus
    sia la loro varianza senza duplicare gol/assist nella dashboard.
    """

    result = calculate_fantavoto(df)

    result["bonus_malus"] = (
        result["fanta_voto_calcolato"]
        - numeric_series(result, "voto")
    )

    return result


# ============================================================
# CONTINUITÀ
# ============================================================

def get_continuity(player_stats):
    std = numeric_series(player_stats, "voto").dropna().std()

    if pd.isna(std):
        return None, "N/D"

    if std < 0.60:
        return float(std), "🟢 Molto continuo"

    if std < 0.90:
        return float(std), "🟡 Abbastanza continuo"

    return float(std), "🔴 Altalenante"


# ============================================================
# MEDIA MOBILE
# ============================================================

def build_rolling_data(player_stats, window=5):
    if player_stats.empty:
        return pd.DataFrame()

    required = ["stagione", "giornata"]

    if any(column not in player_stats.columns for column in required):
        return pd.DataFrame()

    result = player_stats.copy()

    result["giornata"] = pd.to_numeric(
        result["giornata"],
        errors="coerce",
    )

    result = result[result["giornata"].notna()].copy()

    if result.empty:
        return pd.DataFrame()

    result["giornata"] = result["giornata"].astype(int)

    result["stagione"] = (
        result["stagione"]
        .astype(str)
        .str.strip()
    )

    result["_season_sort"] = result["stagione"].apply(season_sort_key)

    result = result.sort_values(
        ["_season_sort", "giornata"]
    ).reset_index(drop=True)

    result = calculate_fantavoto(result)

    if "voto" in result.columns:
        result["voto"] = pd.to_numeric(
            result["voto"],
            errors="coerce",
        )

        result["media_mobile_voto"] = (
            result
            .groupby("stagione", sort=False)["voto"]
            .transform(
                lambda x: x.rolling(
                    window=window,
                    min_periods=1,
                ).mean()
            )
        )

    result["media_mobile_fanta"] = (
        result
        .groupby("stagione", sort=False)["fanta_voto_calcolato"]
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
# KPI RELATIVI
# ============================================================

def calculate_relative_metrics(p_stats):
    """
    Calcola indicatori confrontabili tra giocatori:

    - presenze medie per stagione
    - % di partite a voto rispetto alle 38 disponibili
    - gol medi per stagione
    - gol ogni 38 giornate
    - assist medi per stagione
    - assist ogni 38 giornate

    La percentuale di presenza è:
        presenze medie / 38 * 100
    """

    seasons = 0

    if "stagione" in p_stats.columns:
        seasons = (
            p_stats["stagione"]
            .dropna()
            .astype(str)
            .str.strip()
            .nunique()
        )

    if seasons <= 0:
        return {
            "stagioni": 0,
            "presenze_medie": 0.0,
            "presenza_pct": 0.0,
            "gol_stagione": 0.0,
            "gol_38": 0.0,
            "assist_stagione": 0.0,
            "assist_38": 0.0,
        }

    presenze_totali = (
        numeric_series(p_stats, "voto")
        .count()
    )

    gol_totali = safe_sum(p_stats, "gf")
    assist_totali = safe_sum(p_stats, "ass")

    presenze_medie = presenze_totali / seasons
    gol_stagione = gol_totali / seasons
    assist_stagione = assist_totali / seasons

    return {
        "stagioni": seasons,
        "presenze_medie": presenze_medie,
        "presenza_pct": (presenze_medie / 38) * 100,
        "gol_stagione": gol_stagione,
        "gol_38": (gol_stagione / 38) * 38,
        "assist_stagione": assist_stagione,
        "assist_38": (assist_stagione / 38) * 38,
    }


# ============================================================
# PROFILO GIOCATORE
# ============================================================

def render_player_detail(player_id, stats, quotations):

    try:
        player_id = int(float(player_id))
    except Exception:
        st.error(f"Player ID non valido: {player_id}")
        return

    # --------------------------------------------------------
    # QUOTAZIONE
    # --------------------------------------------------------

    p_quotes = quotations[
        quotations["player_id"] == player_id
    ].copy()

    current_quote = get_latest_quote_row(p_quotes)

    # --------------------------------------------------------
    # STORICO
    # --------------------------------------------------------

    p_stats = stats[
        stats["player_id"] == player_id
    ].copy()

    # --------------------------------------------------------
    # DIAGNOSTICA
    # --------------------------------------------------------

    with st.expander("🔎 Diagnostica giocatore", expanded=False):

        st.write(f"**Player ID:** `{player_id}`")
        st.write(f"**Righe quotazioni:** `{len(p_quotes)}`")
        st.write(f"**Righe storico:** `{len(p_stats)}`")

        if current_quote is not None:
            st.success("✅ Quotazione trovata.")
            st.json(
                {
                    "player_id": current_quote.get("player_id"),
                    "nome": current_quote.get("nome"),
                    "stagione": current_quote.get("stagione"),
                    "quotazione_attuale": current_quote.get(
                        "quotazione_attuale"
                    ),
                    "fvm": current_quote.get("fvm"),
                }
            )
        else:
            st.error(
                f"❌ Nessuna quotazione trovata per player_id {player_id}."
            )

        if not p_stats.empty:
            st.success("✅ Storico trovato.")
        else:
            st.error(
                f"❌ Nessuna statistica storica trovata per player_id {player_id}."
            )

    # --------------------------------------------------------
    # ANAGRAFICA
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

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    header_left, header_right = st.columns([2.6, 1])

    with header_left:
        st.header(str(nome))

        st.markdown(
            f"""
            <div class="player-subtitle">
                {html.escape(str(squadra))} • {html.escape(str(ruolo))}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # --------------------------------------------------------
    # CARD QUOTAZIONE
    # --------------------------------------------------------

    with header_right:
        if current_quote is not None:

            quota = current_quote.get("quotazione_attuale", "-")
            fvm = current_quote.get("fvm", "-")

            quota_num = pd.to_numeric(
                pd.Series([quota]),
                errors="coerce",
            ).iloc[0]

            fvm_num = pd.to_numeric(
                pd.Series([fvm]),
                errors="coerce",
            ).iloc[0]

            quota_text = (
                str(int(quota_num))
                if pd.notna(quota_num)
                else "-"
            )

            fvm_text = (
                str(int(fvm_num))
                if pd.notna(fvm_num)
                else "-"
            )

            st.markdown(
                f"""
                <div class="quote-card">
                    <div class="quote-label">Quotazione attuale</div>
                    <div class="quote-value">{html.escape(quota_text)}</div>

                    <div class="quote-divider"></div>

                    <div class="quote-fvm">Fantamilioni suggeriti</div>
                    <div class="quote-value-secondary">{html.escape(fvm_text)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # --------------------------------------------------------
    # CEDUTO
    # --------------------------------------------------------

    if current_quote is not None:
        ceduto = current_quote.get("ceduto", False)
        ceduto_string = str(ceduto).lower()

        if (
            ceduto is True
            or ceduto_string == "true"
            or ceduto_string == "1"
        ):
            st.warning("⚠️ Il giocatore risulta marcato come ceduto.")

    # --------------------------------------------------------
    # NESSUN STORICO
    # --------------------------------------------------------

    if p_stats.empty:
        st.info(
            "Non sono presenti statistiche storiche per questo giocatore."
        )
        return

    # --------------------------------------------------------
    # NORMALIZZAZIONE
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # ELIMINA EVENTUALI VOTI CON *
    # --------------------------------------------------------

    p_stats = remove_starred_vote_rows(p_stats)

    if p_stats.empty:
        st.info("Non ci sono prestazioni valide per questo giocatore.")
        return

    # --------------------------------------------------------
    # CALCOLA FANTAVOTO E BONUS/MALUS
    # --------------------------------------------------------

    p_stats = calculate_bonus_malus(p_stats)

    # ========================================================
    # RENDIMENTO STORICO
    # ========================================================

    st.markdown(
        '<div class="section-title">📊 Rendimento storico complessivo</div>',
        unsafe_allow_html=True,
    )

    relative = calculate_relative_metrics(p_stats)

    presenze = int(
        numeric_series(p_stats, "voto").count()
    )

    media_voto = safe_mean(p_stats, "voto")

    fantamedia = safe_mean(
        p_stats,
        "fanta_voto_calcolato",
    )

    std, continuity_label = get_continuity(p_stats)

    # Varianza voto
    varianza_voto = safe_variance(p_stats, "voto")

    # Varianza bonus/malus
    varianza_bonus_malus = safe_variance(
        p_stats,
        "bonus_malus",
    )

    with st.container(border=True):

        # ----------------------------------------------------
        # KPI PRINCIPALI
        # Continuità volutamente in alto
        # ----------------------------------------------------

        k1, k2, k3, k4 = st.columns(4)

        with k1:
            st.metric(
                "Continuità",
                format_number(std),
                help=(
                    "Deviazione standard del voto. "
                    "Più il valore è basso, più il rendimento "
                    "è continuo."
                ),
            )
            render_continuity_badge(continuity_label)

        with k2:
            st.metric(
                "Presenza media",
                f"{relative['presenza_pct']:.1f}%",
                help=(
                    "Presenze medie per stagione rapportate "
                    "alle 38 giornate disponibili."
                ),
            )

        with k3:
            st.metric(
                "Media voto",
                f"{media_voto:.2f}",
            )

        with k4:
            st.metric(
                "Fantamedia",
                f"{fantamedia:.2f}",
                help=(
                    "Calcolata da voto + bonus/malus "
                    "secondo le regole classiche."
                ),
            )

        # ----------------------------------------------------
        # KPI RELATIVI
        # ----------------------------------------------------

        r1, r2, r3, r4 = st.columns(4)

        with r1:
            st.metric(
                "Presenze medie / stagione",
                f"{relative['presenze_medie']:.1f}",
            )

        with r2:
            st.metric(
                "Gol medi / stagione",
                f"{relative['gol_stagione']:.2f}",
            )

        with r3:
            st.metric(
                "Assist medi / stagione",
                f"{relative['assist_stagione']:.2f}",
            )

        with r4:
            st.metric(
                "Stagioni analizzate",
                relative["stagioni"],
            )

    # --------------------------------------------------------
    # VARIANZA
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">📐 Variabilità del rendimento</div>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):

        v1, v2 = st.columns(2)

        with v1:
            st.metric(
                "Varianza voto",
                format_number(varianza_voto),
                help=(
                    "Varianza statistica dei voti. "
                    "Più è bassa, più i voti sono concentrati "
                    "intorno alla media."
                ),
            )

        with v2:
            st.metric(
                "Varianza bonus/malus",
                format_number(varianza_bonus_malus),
                help=(
                    "Varianza del bonus/malus netto per prestazione. "
                    "Il bonus/malus netto è Fantavoto - Voto."
                ),
            )

    # ========================================================
    # FORMA — MEDIA MOBILE 5 GIORNATE
    # ========================================================

    st.markdown(
        '<div class="section-title">📈 Andamento della forma</div>',
        unsafe_allow_html=True,
    )

    rolling_df = build_rolling_data(
        p_stats,
        window=5,
    )

    if rolling_df.empty:
        st.info(
            "Dati insufficienti per calcolare la media mobile."
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
                    line=dict(width=3),
                    hovertemplate=(
                        "%{x}<br>"
                        "Media voto: %{y:.2f}"
                        "<extra></extra>"
                    ),
                    connectgaps=False,
                )
            )

        if "media_mobile_fanta" in rolling_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=rolling_df["periodo"],
                    y=rolling_df["media_mobile_fanta"],
                    mode="lines",
                    name="Fantamedia — 5 giornate",
                    line=dict(width=3),
                    hovertemplate=(
                        "%{x}<br>"
                        "Fantamedia: %{y:.2f}"
                        "<extra></extra>"
                    ),
                    connectgaps=False,
                )
            )

        fig.update_layout(
            title="Media mobile a 5 giornate",
            xaxis_title="Stagione / Giornata",
            yaxis_title="Valutazione",
            hovermode="x unified",
            height=430,
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
            use_container_width=True,
        )

    # ========================================================
    # RENDIMENTO PER STAGIONE
    # ========================================================

    st.markdown(
        '<div class="section-title">📅 Rendimento per stagione</div>',
        unsafe_allow_html=True,
    )

    if "stagione" in p_stats.columns:

        season_rows = []

        for season, group in p_stats.groupby("stagione"):

            group_fanta = calculate_fantavoto(group)

            season_rows.append(
                {
                    "Stagione": season,
                    "Presenze": int(
                        numeric_series(group, "voto").count()
                    ),
                    "% Presenza": round(
                        numeric_series(group, "voto").count()
                        / 38
                        * 100,
                        1,
                    ),
                    "Media voto": round(
                        safe_mean(group, "voto"),
                        2,
                    ),
                    "Fantamedia": round(
                        safe_mean(
                            group_fanta,
                            "fanta_voto_calcolato",
                        ),
                        2,
                    ),
                    "Gol": int(safe_sum(group, "gf")),
                    "Assist": int(safe_sum(group, "ass")),
                    "Bonus/malus medio": round(
                        safe_mean(
                            calculate_bonus_malus(group),
                            "bonus_malus",
                        ),
                        2,
                    ),
                }
            )

        season_agg = pd.DataFrame(season_rows)

        if not season_agg.empty:
            season_agg["_sort"] = (
                season_agg["Stagione"]
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

    # ========================================================
    # BONUS / MALUS
    # ========================================================

    st.markdown(
        '<div class="section-title">⚽ Altri bonus e malus</div>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):

        b1, b2, b3, b4 = st.columns(4)

        with b1:
            st.metric(
                "Rigori segnati",
                int(safe_sum(p_stats, "rf")),
            )

        with b2:
            st.metric(
                "Rigori sbagliati",
                int(safe_sum(p_stats, "rs")),
            )

        with b3:
            st.metric(
                "Ammonizioni",
                int(safe_sum(p_stats, "amm")),
            )

        with b4:
            st.metric(
                "Espulsioni",
                int(safe_sum(p_stats, "esp")),
            )

    # ========================================================
    # DATI COMPLETI
    # ========================================================

    with st.expander("📄 Visualizza statistiche storiche complete"):

        display_stats = p_stats.copy()

        if "fanta_voto_calcolato" in display_stats.columns:
            display_stats["fanta_voto"] = display_stats[
                "fanta_voto_calcolato"
            ]

        st.dataframe(
            display_stats,
            use_container_width=True,
            hide_index=True,
        )

        csv = display_stats.to_csv(
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
    st.error("❌ Errore nel caricamento dei dati da Supabase.")
    st.code(str(e))
    st.stop()


# ============================================================
# CONTROLLO DATI
# ============================================================

if df.empty:
    st.error("❌ player_stats_history non contiene dati.")
    st.stop()

if quot.empty:
    st.error("❌ giocatori_quotazioni non contiene dati.")
    st.stop()


# ============================================================
# NORMALIZZAZIONE
# ============================================================

df = normalize_dataframe(df)
quot = normalize_dataframe(quot)


# ============================================================
# CONTROLLO PLAYER_ID
# ============================================================

if "player_id" not in df.columns:
    st.error(
        "❌ La tabella player_stats_history non contiene "
        "la colonna player_id."
    )
    st.stop()

if "player_id" not in quot.columns:
    st.error(
        "❌ La tabella giocatori_quotazioni non contiene "
        "la colonna player_id."
    )
    st.stop()


# ============================================================
# RIMUOVI ID NULL
# ============================================================

df = df[df["player_id"].notna()].copy()
quot = quot[quot["player_id"].notna()].copy()


# ============================================================
# RIMUOVI EVENTUALI RECORD CON VOTO *
# ============================================================

df = remove_starred_vote_rows(df)


# ============================================================
# ID COMUNI
# ============================================================

stats_ids = set(
    df["player_id"]
    .dropna()
    .astype(int)
    .unique()
)

quote_ids = set(
    quot["player_id"]
    .dropna()
    .astype(int)
    .unique()
)

common_ids = stats_ids.intersection(quote_ids)


# ============================================================
# DIAGNOSTICA DATABASE
# ============================================================

with st.expander("🔎 Diagnostica database", expanded=False):

    st.write(f"**Righe storico valide:** {len(df):,}")
    st.write(f"**Righe quotazioni:** {len(quot):,}")
    st.write(f"**Player ID distinti storico:** {len(stats_ids):,}")
    st.write(f"**Player ID distinti quotazioni:** {len(quote_ids):,}")
    st.write(f"**Player ID presenti in entrambe:** {len(common_ids):,}")

    cutrone_id = 2155

    cutrone_stats = df[df["player_id"] == cutrone_id]
    cutrone_quote = quot[quot["player_id"] == cutrone_id]

    st.markdown("#### Test player_id 2155")

    c1, c2 = st.columns(2)

    with c1:
        if cutrone_stats.empty:
            st.error("❌ Player 2155 NON trovato nello storico.")
        else:
            st.success(
                f"✅ Player 2155 trovato nello storico: "
                f"{len(cutrone_stats)} righe"
            )

            columns = [
                c for c in [
                    "player_id",
                    "nome",
                    "stagione",
                    "giornata",
                    "voto",
                ]
                if c in cutrone_stats.columns
            ]

            st.dataframe(
                cutrone_stats[columns].head(10),
                use_container_width=True,
                hide_index=True,
            )

    with c2:
        if cutrone_quote.empty:
            st.error("❌ Player 2155 NON trovato nelle quotazioni.")
        else:
            st.success(
                f"✅ Player 2155 trovato nelle quotazioni: "
                f"{len(cutrone_quote)} righe"
            )

            columns = [
                c for c in [
                    "player_id",
                    "nome",
                    "stagione",
                    "quotazione_attuale",
                    "fvm",
                ]
                if c in cutrone_quote.columns
            ]

            st.dataframe(
                cutrone_quote[columns].head(10),
                use_container_width=True,
                hide_index=True,
            )


# ============================================================
# ULTIMA STAGIONE QUOTAZIONI
# ============================================================

latest_season = get_latest_season(quot)

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

st.title("⚽ FantaAI")

if latest_season:
    st.markdown(
        f"""
        ### Analisi dei giocatori della rosa attuale

        Quotazioni stagione **{latest_season}**
        """
    )
else:
    st.markdown(
        "### Analisi dei giocatori della rosa attuale"
    )


# ============================================================
# FILTRO RUOLO
# ============================================================

role_col, info_col = st.columns([1, 3])

with role_col:
    selected_role = st.selectbox(
        "Filtra per ruolo",
        ["Tutti", "P", "D", "C", "A"],
    )

with info_col:
    st.markdown(
        f"**Rosa attuale:** {len(current_quot)} giocatori"
    )


# ============================================================
# FILTRO
# ============================================================

quot_view = current_quot.copy()

if (
    selected_role != "Tutti"
    and "ruolo" in quot_view.columns
):
    quot_view = quot_view[
        quot_view["ruolo"]
        .astype(str)
        .str.upper()
        .str.strip()
        == selected_role
    ]


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

    st.markdown("### 👥 Giocatori")

    st.caption(
        f"{len(quot_view)} giocatori disponibili"
    )

    if quot_view.empty:

        st.info("Nessun giocatore trovato.")
        selected_id = None

    else:

        options_df = (
            quot_view
            .drop_duplicates(subset="player_id")
            .copy()
        )

        labels = []
        ids = []

        for row in options_df.itertuples():

            nome_row = getattr(row, "nome", "Giocatore")
            squadra_row = getattr(row, "squadra", "-")
            player_id_row = getattr(row, "player_id")

            label = f"{nome_row} • {squadra_row}"

            # Evita collisioni nel radio se esistono nomi identici.
            if label in labels:
                label = f"{label} • ID {int(player_id_row)}"

            labels.append(label)
            ids.append(int(player_id_row))

        label_to_id = dict(zip(labels, ids))

        with st.container(height=640, border=True):
            selected_label = st.radio(
                "Seleziona giocatore",
                options=labels,
                label_visibility="collapsed",
            )

        selected_id = label_to_id[selected_label]


# ============================================================
# DETTAGLIO
# ============================================================

with col_detail:

    if selected_id is None:
        st.info("Seleziona un giocatore.")
    else:
        render_player_detail(
            selected_id,
            df,
            quot,
        )
