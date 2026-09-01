import os
import html
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from supabase import create_client
from streamlit_elements import elements, mui

st.set_page_config(
    page_title="FantaAI Analytics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Tema retro arcade / pixel art - CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&family=VT323&display=swap');
:root {
  --color-primary: #DC2626;
  --color-secondary: #2563EB;
  --color-accent: #22C55E;
  --color-background: #0F172A;
  --color-foreground: #FFFFFF;
  --color-card: #192134;
  --color-border: rgba(255, 255, 255, 0.14);
  --pixel-shadow: 4px 4px 0 rgba(0, 0, 0, 0.55);
}
.main, .stApp {
  background-color: var(--color-background) !important;
  color: var(--color-foreground);
  font-family: 'VT323', monospace;
  font-size: 20px;
  background-image:
    repeating-linear-gradient(0deg, rgba(255,255,255,0.02) 0px, rgba(255,255,255,0.02) 1px, transparent 1px, transparent 3px);
}
h1, h2, h3, h4, h5, h6 {
  font-family: 'Press Start 2P', monospace !important;
  color: var(--color-accent) !important;
  text-shadow: 3px 3px 0 rgba(0, 0, 0, 0.6);
  letter-spacing: 1px;
  line-height: 1.5;
}
h1 { font-size: 1.7rem !important; }
h2 { font-size: 1.2rem !important; }
h3 { font-size: 1rem !important; }
a {
  color: var(--color-secondary);
  text-decoration: underline;
  text-underline-offset: 3px;
}
::-webkit-scrollbar { width: 14px; height: 14px; }
::-webkit-scrollbar-track { background: #1F1829; }
::-webkit-scrollbar-thumb {
  background-color: var(--color-accent);
  border-radius: 0px;
  border: 3px solid var(--color-background);
}
.stContainer > div {
  background-color: var(--color-card);
  border: 3px solid var(--color-border);
  border-radius: 0px;
  padding: 16px;
  box-shadow: var(--pixel-shadow);
}
.stButton > button, .stSelectbox > div > div, .stDownloadButton > button {
  font-family: 'Press Start 2P', monospace !important;
  font-size: 0.65rem !important;
  background-color: var(--color-card) !important;
  color: var(--color-accent) !important;
  border: 3px solid var(--color-accent) !important;
  border-radius: 0px !important;
  box-shadow: var(--pixel-shadow);
}
.stButton > button:hover {
  background-color: var(--color-accent) !important;
  color: var(--color-background) !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
  border: 3px solid var(--color-border) !important;
  border-radius: 0px !important;
  background-color: var(--color-card);
  box-shadow: var(--pixel-shadow);
}
.stRadio [role="radiogroup"] {
  gap: 6px;
}
.stRadio [role="radiogroup"] label {
  display: block;
  width: 100%;
  margin-bottom: 6px;
  padding: 10px 12px;
  background-color: #1F1829;
  border: 3px solid var(--color-border);
  border-radius: 0px;
  cursor: pointer;
  transition: transform 80ms steps(2), background-color 80ms steps(2);
}
.stRadio [role="radiogroup"] label:hover {
  background-color: rgba(34, 197, 94, 0.15);
  border-color: var(--color-accent);
  transform: translate(-2px, -2px);
  box-shadow: 3px 3px 0 rgba(0,0,0,0.5);
}
.stRadio [role="radiogroup"] label p {
  font-family: 'VT323', monospace !important;
  font-size: 22px !important;
  font-weight: 700 !important;
  color: var(--color-accent) !important;
  letter-spacing: 0.5px;
  margin: 0;
}
.stRadio [role="radiogroup"] label[data-checked="true"],
.stRadio [role="radiogroup"] label:has(input:checked) {
  background-color: rgba(220, 38, 38, 0.18);
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--color-primary), var(--pixel-shadow);
}
.stRadio [role="radiogroup"] label:has(input:checked) p {
  color: white !important;
  text-shadow: 0 0 6px var(--color-primary);
}
div[data-testid="stMetric"] {
  background-color: var(--color-card);
  border: 3px solid var(--color-border);
  border-radius: 0px;
  padding: 12px;
  box-shadow: var(--pixel-shadow);
}
div[data-testid="stMetricLabel"] {
  font-family: 'Press Start 2P', monospace !important;
  font-size: 0.6rem !important;
  color: #94A3B8 !important;
}
div[data-testid="stMetricValue"] {
  font-family: 'VT323', monospace !important;
  font-size: 2rem !important;
  color: var(--color-accent) !important;
}
#scroll-list {
  max-height: 640px;
  overflow-y: auto;
  padding-right: 8px;
}
</style>
""", unsafe_allow_html=True)

# ------------- Funzioni utilità --------------

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

def safe_mean(df, column):
    if column not in df.columns:
        return 0.0
    values = numeric_series(df, column).dropna()
    if values.empty:
        return 0.0
    return float(values.mean())

def remove_starred_vote_rows(df):
    if df.empty or "voto" not in df.columns:
        return df.copy()
    result = df.copy()
    raw_vote = result["voto"].astype(str).str.strip()
    starred = raw_vote.str.contains(r"\*", regex=True, na=False)
    if starred.any():
        result = result.loc[~starred].copy()
    return result

def calculate_fantavoto(df):
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

    clean_sheet = pd.Series(0.0, index=result.index)
    for col in ["pi", "porta_inviolata", "clean_sheet", "imbattuto"]:
        if col in result.columns:
            clean_sheet = numeric_series(result, col).fillna(0)
            break

    penalty_saved = pd.Series(0.0, index=result.index)
    for col in ["rp", "rigori_parati", "rigore_parato"]:
        if col in result.columns:
            penalty_saved = numeric_series(result, col).fillna(0)
            break

    gol_subiti = pd.Series(0.0, index=result.index)
    for col in ["gs", "gol_subiti"]:
        if col in result.columns:
            gol_subiti = numeric_series(result, col).fillna(0)
            break

    is_goalkeeper = False
    if "ruolo" in result.columns:
        is_goalkeeper = result["ruolo"].astype(str).str.strip().str.upper() == "P"
        clean_sheet = clean_sheet.where(is_goalkeeper, 0)
        gol_subiti = gol_subiti.where(is_goalkeeper, 0)

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
        - gol_subiti
    )

    result.loc[numeric_series(result, "voto").isna(), "fanta_voto_calcolato"] = float("nan")
    return result

def aggregate_fantamedia(df_stats):
    df = remove_starred_vote_rows(df_stats)
    df = calculate_fantavoto(df)
    result = df.groupby("player_id")["fanta_voto_calcolato"].mean().reset_index()
    result.rename(columns={"fanta_voto_calcolato": "fantamedia_calcolata"}, inplace=True)
    return result

def emoji_forma(fanta_voto):
    try:
        val = float(fanta_voto)
        if val >= 7:
            return "🔥"
        elif val >= 5.5:
            return "🙂"
        else:
            return "⚠️"
    except Exception:
        return ""

# Funzioni di caricamento dati Supabase e CSV...

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ SUPABASE_URL o SUPABASE_KEY non configurate.")
    st.stop()

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)
supabase = init_supabase()

def fetch_all_rows(table_name, page_size=1000):
    rows = []
    start = 0
    while True:
        response = supabase.table(table_name).select("*").range(start, start + page_size - 1).execute()
        page = response.data or []
        if not page: break
        rows.extend(page)
        if len(page) < page_size: break
        start += page_size
    return rows

@st.cache_data(ttl=600)
def load_stats():
    return pd.DataFrame(fetch_all_rows("player_stats_history"))

@st.cache_data(ttl=600)
def load_quotazioni():
    return pd.DataFrame(fetch_all_rows("giocatori_quotazioni"))

@st.cache_data(ttl=600)
def load_rigoristi():
    df = pd.read_csv("https://raw.githubusercontent.com/fanta-ai-coder/fanta-ai-etl/refs/heads/main/rigoristi.csv")
    df["giocatore"] = df["giocatore"].str.upper().str.strip()
    df["squadra"] = df["squadra"].str.upper().str.strip()
    return df

@st.cache_data(ttl=600)
def load_punizioni():
    df = pd.read_csv("https://raw.githubusercontent.com/fanta-ai-coder/fanta-ai-etl/refs/heads/main/punizioni.csv")
    df["giocatore"] = df["giocatore"].str.upper().str.strip()
    df["squadra"] = df["squadra"].str.upper().str.strip()
    return df

rigoristi_df = load_rigoristi()
punizioni_df = load_punizioni()

# [Inserisci qui la definizione completa di render_player_detail]
# (Usa la funzione completa che hai, come da script precedente)

try:
    df_stats = load_stats()
    df_quotes = load_quotazioni()
except Exception as e:
    st.error("Errore caricamento dati Supabase")
    st.stop()

df_stats = normalize_dataframe(df_stats)
df_quotes = normalize_dataframe(df_quotes)

if df_stats.empty or df_quotes.empty:
    st.error("Dati Vuoti")
    st.stop()

if "player_id" not in df_stats.columns or "player_id" not in df_quotes.columns:
    st.error("Colonne player_id mancanti")
    st.stop()

df_stats = df_stats[df_stats["player_id"].notna()]
df_quotes = df_quotes[df_quotes["player_id"].notna()]

df_stats = remove_starred_vote_rows(df_stats)

# Calcolo fantamedia calcolata, merge con quotazioni
df_fantamedia = aggregate_fantamedia(df_stats)
df_quotes = df_quotes.merge(df_fantamedia, on="player_id", how="left")
df_quotes["fantamedia_calcolata"] = df_quotes["fantamedia_calcolata"].fillna(0)

# Sidebar filtri
st.sidebar.header("Filtra giocatori")
roles = st.sidebar.multiselect("Ruolo", ["P", "D", "C", "A"], default=["P", "D", "C", "A"])
squadre = sorted(df_quotes["squadra"].dropna().unique())
squadra_filtro = st.sidebar.multiselect("Squadra", squadre)
min_fantamedia = st.sidebar.slider("Fantamedia Minima", 0.0, 10.0, 5.0, 0.1)
search_nome = st.sidebar.text_input("Cerca Nome")

view_quotes = df_quotes.copy()
if roles:
    view_quotes = view_quotes[view_quotes["ruolo"].str.upper().isin(roles)]
if squadra_filtro:
    view_quotes = view_quotes[view_quotes["squadra"].isin(squadra_filtro)]
view_quotes = view_quotes[view_quotes["fantamedia_calcolata"] >= min_fantamedia]
if search_nome:
    view_quotes = view_quotes[view_quotes["nome"].str.contains(search_nome, case=False, na=False)]

view_quotes = view_quotes.sort_values("nome", na_position="last")

st.title("⚽ FantaAI Analytics - Retro Pixel Art Style")

col_players, col_detail = st.columns([1, 3.2], gap="small")

with col_players:
    st.markdown('<div id="scroll-list">', unsafe_allow_html=True)
    if view_quotes.empty:
        st.info("Nessun giocatore trovato con i filtri.")
        selected_id = None
    else:
        labels = []
        ids = []
        seen_labels = set()
        for r in view_quotes.itertuples():
            nome = getattr(r, "nome", "Giocatore")
            squadra = getattr(r, "squadra", "?")
            fantamedia = getattr(r, "fantamedia_calcolata", 0)
            pid = getattr(r, "player_id")
            emoji = emoji_forma(fantamedia)
            label = f"{nome} • {squadra} {emoji} — FM: {fantamedia:.2f}"
            if label in seen_labels:  
                label = f"{label} • ID {pid}"
            seen_labels.add(label)
            labels.append(label)
            ids.append(pid)
        label_to_id = dict(zip(labels, ids))
        selected_label = st.radio("Seleziona giocatore", labels, label_visibility="collapsed")
        selected_id = label_to_id.get(selected_label)
    st.markdown('</div>', unsafe_allow_html=True)

with col_detail:
    if selected_id is None:
        st.info("Seleziona un giocatore per vedere i dettagli.")
    else:
        render_player_detail(selected_id, df_stats, df_quotes)

