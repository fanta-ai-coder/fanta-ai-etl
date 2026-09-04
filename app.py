import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from supabase import create_client


# === 1. PAGE CONFIG & CUSTOM CSS ===

st.set_page_config(
    page_title="FantaAI Analytics Pro",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

_CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
background-color: #0B0F19 !important;
color: #F8FAFC !important;
}
section.main, [data-testid="stMainBlockContainer"], [data-testid="stAppViewBlockContainer"] {
background-color: #0B0F19 !important;
}
/* ...omesso per brevità, resta lo stesso... */
</style>
"""
st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)


# === 2. SUPABASE & DATA FETCHING ===

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ SUPABASE_URL e/o SUPABASE_KEY non configurate.")
    st.stop()

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

@st.cache_data(ttl=900)
def fetch_table(table_name):
    rows = []
    start = 0
    page_size = 1000
    while True:
        response = supabase.table(table_name).select("*").range(start, start + page_size - 1).execute()
        page = response.data or []
        if not page:
            break
        rows.extend(page)
        if len(page) < page_size:
            break
        start += page_size
    return pd.DataFrame(rows)


# --- Load external csv data with caching ---

@st.cache_data(ttl=900)
def load_remote_csv(url, cols_to_upper=None):
    try:
        df = pd.read_csv(url)
        if cols_to_upper:
            for col in cols_to_upper:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.upper().str.strip()
        return df
    except Exception:
        return pd.DataFrame(columns=cols_to_upper or [])


# --- Load all data once ---

def load_all_data():
    stats_df = fetch_table("player_stats_history")
    quotations_df = fetch_table("giocatori_quotazioni")
    ranking_df = fetch_table("player_ranking")

    rigoristi_df = load_remote_csv(
        "https://raw.githubusercontent.com/fanta-ai-coder/fanta-ai-etl/refs/heads/main/rigoristi.csv",
        ["giocatore", "squadra"]
    )
    punizioni_df = load_remote_csv(
        "https://raw.githubusercontent.com/fanta-ai-coder/fanta-ai-etl/refs/heads/main/punizioni.csv",
        ["giocatore", "squadra"]
    )
    titolari_df = load_remote_csv(
        "https://raw.githubusercontent.com/fanta-ai-coder/fanta-ai-etl/refs/heads/main/titolari_infortuni",
        ["nome_giocatore", "squadra"]
    )

    return stats_df, quotations_df, ranking_df, rigoristi_df, punizioni_df, titolari_df


# === 3. UTILITY FUNCTIONS ===

def normalize_player_id(series):
    return pd.to_numeric(series, errors="coerce").round().astype("Int64")

def normalize_df(df):
    if df.empty:
        return df.copy()
    df = df.copy()
    if "player_id" in df.columns:
        df["player_id"] = normalize_player_id(df["player_id"])
    for col in ["nome", "squadra", "ruolo", "stagione"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().str.strip()
    return df

def numeric_series(df, col):
    if col not in df.columns:
        return pd.Series(float("nan"), index=df.index, dtype="float64")
    return pd.to_numeric(df[col], errors="coerce")

def safe_sum(df, col):
    return numeric_series(df, col).fillna(0).sum() if col in df.columns else 0.0

def safe_mean(df, col):
    if col not in df.columns:
        return 0.0
    vals = numeric_series(df, col).dropna()
    return float(vals.mean()) if not vals.empty else 0.0

def safe_variance(df, col):
    if col not in df.columns:
        return None
    vals = numeric_series(df, col).dropna()
    if len(vals) < 2:
        return None
    var = vals.var(ddof=1)
    return None if pd.isna(var) else float(var)

def remove_star_vote_rows(df):
    if df.empty or "voto" not in df.columns:
        return df.copy()
    stars = df["voto"].astype(str).str.contains(r"\*", regex=True, na=False)
    return df.loc[~stars].copy() if stars.any() else df.copy()

def calculate_fantavoto(df):
    if df.empty or "voto" not in df.columns:
        df["fanta_voto_calcolato"] = float("nan")
        return df
    df = df.copy()
    # Convert and fill with zeros all needed stats
    fields = ["voto", "gf", "ass", "rf", "au", "esp", "amm"]
    vals = {f: numeric_series(df, f).fillna(0) for f in fields}
    # Clean sheet, penalty saved, goals conceded logic with fallback columns
    clean_sheet_cols = ["pi", "porta_inviolata", "clean_sheet", "imbattuto"]
    for c in clean_sheet_cols:
        if c in df.columns:
            clean_sheet = numeric_series(df, c).fillna(0)
            break
    else:
        clean_sheet = pd.Series(0.0, index=df.index)

    penalty_saved_cols = ["rp", "rigori_parati", "rigore_parato"]
    for c in penalty_saved_cols:
        if c in df.columns:
            penalty_saved = numeric_series(df, c).fillna(0)
            break
    else:
        penalty_saved = pd.Series(0.0, index=df.index)

    gol_subiti_cols = ["gs", "gol_subiti"]
    for c in gol_subiti_cols:
        if c in df.columns:
            gol_subiti = numeric_series(df, c).fillna(0)
            break
    else:
        gol_subiti = pd.Series(0.0, index=df.index)

    # Apply only to goalkeepers clean sheet and gol subiti
    if "ruolo" in df.columns:
        is_gk = df["ruolo"].str.upper() == "P"
        clean_sheet = clean_sheet.where(is_gk, 0)
        gol_subiti = gol_subiti.where(is_gk, 0)

    df["fanta_voto_calcolato"] = (
        vals["voto"]
        + vals["gf"]*3
        + vals["ass"]
        + vals["rf"]*3
        - vals["au"]*2
        - vals["esp"]
        - vals["amm"]*0.5
        + clean_sheet
        + penalty_saved*3
        - gol_subiti
    )

    # NaN propagation for missing voto
    df.loc[vals["voto"].isna(), "fanta_voto_calcolato"] = float("nan")

    return df


# (Altre funzioni di utilità quali calculate_bonus_malus, calculate_relative_metrics ecc... si implementano nello stesso modo ottimizzato e leggibile.)

# === 4. UI COMPONENTS ===

ROLE_COLORS = {
    "P": {"bg": "rgba(245, 158, 11, 0.15)", "text": "#FBBF24", "border": "rgba(245, 158, 11, 0.4)", "label": "Portiere"},
    "D": {"bg": "rgba(59, 130, 246, 0.15)", "text": "#60A5FA", "border": "rgba(59, 130, 246, 0.4)", "label": "Difensore"},
    "C": {"bg": "rgba(16, 185, 129, 0.15)", "text": "#34D399", "border": "rgba(16, 185, 129, 0.4)", "label": "Centrocampista"},
    "A": {"bg": "rgba(239, 68, 68, 0.15)", "text": "#F87171", "border": "rgba(239, 68, 68, 0.4)", "label": "Attaccante"},
}

def render_section_header(title, subtitle=None):
    st.subheader(title)
    if subtitle:
        st.caption(subtitle)

def render_kpi_card(title, value, subtext="", highlight=False):
    with st.container(border=True):
        label = ("⭐ " + title) if highlight else title
        st.metric(label=label, value=value)
        if subtext:
            st.caption(subtext)

# Funzioni per rendering dettagli giocatore e grafici si riscrivono mantenendo stessa logica ma semplificando con variabili locali e meno coperture try-except generiche.

# === 5. MAIN ===

def main():
    try:
        stats_df, quotations_df, ranking_df, rigoristi_df, punizioni_df, titolari_df = load_all_data()
    except Exception as e:
        st.error(f"Errore nel caricamento dati: {e}")
        st.stop()

    if stats_df.empty or quotations_df.empty:
        st.warning("Nessun dato disponibile.")
        st.stop()

    # Normalizza dati per ricerca e filtro efficaci
    stats_df = normalize_df(stats_df)
    quotations_df = normalize_df(quotations_df)
    ranking_df = normalize_df(ranking_df)

    # Filtri UI
    selected_role = st.selectbox("Ruolo", ["Tutti", "P", "D", "C", "A"], label_visibility="collapsed")
    search_query = st.text_input("Cerca", placeholder="🔍 Cerca per nome giocatore o squadra...", label_visibility="collapsed").strip().upper()

    # Filtraggio efficiente
    df_view = quotations_df.copy()
    if selected_role != "Tutti":
        df_view = df_view[df_view["ruolo"] == selected_role]
    if search_query:
        mask = df_view["nome"].str.contains(search_query, na=False) | df_view["squadra"].str.contains(search_query, na=False)
        df_view = df_view[mask]

    # Sort by nome
    df_view = df_view.sort_values("nome")

    selected_id = None
    st.caption(f"GIOCATORI ({len(df_view)})")
    if df_view.empty:
        st.info("Nessun giocatore trovato con questi filtri.")
    else:
        options = df_view[["player_id", "nome", "squadra"]].drop_duplicates()
        labels = [f"{row.nome} [{row.squadra}]" for _, row in options.iterrows()]
        player_id_map = dict(zip(labels, options["player_id"]))

        default_idx = 0
        if "active_player_id" in st.session_state:
            for i, pid in enumerate(options["player_id"]):
                if pid == st.session_state["active_player_id"]:
                    default_idx = i
                    break
        selected_label = st.radio("Seleziona giocatore", labels, index=default_idx, label_visibility="collapsed")
        selected_id = player_id_map[selected_label]
        st.session_state["active_player_id"] = selected_id

    # Layout con colonne per lista e dettaglio
    col1, col2 = st.columns([1, 3])
    with col1:
        pass  # già fatto sopra la lista

    with col2:
        if selected_id is None:
            st.info("👈 Seleziona un giocatore."
                    )
        else:
            # Qui chiama la funzione di dettaglio del giocatore, passandogli i dataframe e id.
            # Esempio: render_player_detail(selected_id, stats_df, quotations_df, ranking_df,
            #    rigoristi_df, punizioni_df, titolari_df)
            # (Riscrivila usando i dataframe definiti e con logica ottimizzata come sopra.)
            pass


if __name__ == "__main__":
    main()
