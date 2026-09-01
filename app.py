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

# --- CSS tema retro game / pixel art ---
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

/* Background & fonts */
.main, .stApp {
  background-color: var(--color-background) !important;
  color: var(--color-foreground);
  font-family: 'VT323', monospace;
  font-size: 20px;
  background-image:
    repeating-linear-gradient(0deg, rgba(255,255,255,0.02) 0px, rgba(255,255,255,0.02) 1px, transparent 1px, transparent 3px);
}

/* Headers */
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

/* Links */
a {
  color: var(--color-secondary);
  text-decoration: underline;
  text-underline-offset: 3px;
}

/* Scrollbar chunky */
::-webkit-scrollbar { width: 14px; height: 14px; }
::-webkit-scrollbar-track { background: #1F1829; }
::-webkit-scrollbar-thumb {
  background-color: var(--color-accent);
  border-radius: 0px;
  border: 3px solid var(--color-background);
}

/* Cards/containers */
.stContainer > div {
  background-color: var(--color-card);
  border: 3px solid var(--color-border);
  border-radius: 0px;
  padding: 16px;
  box-shadow: var(--pixel-shadow);
}

/* Buttons, selects - arcade style */
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

/* Lista giocatori scrollabile, pixel style */
div[data-testid="stVerticalBlockBorderWrapper"] {
  border: 3px solid var(--color-border) !important;
  border-radius: 0px !important;
  background-color: var(--color-card);
  box-shadow: var(--pixel-shadow);
}
/* Radio list custom */
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
/* Hover effetto */
.stRadio [role="radiogroup"] label:hover {
  background-color: rgba(34, 197, 94, 0.15);
  border-color: var(--color-accent);
  transform: translate(-2px, -2px);
  box-shadow: 3px 3px 0 rgba(0,0,0,0.5);
}
/* Nome evidenziato */
.stRadio [role="radiogroup"] label p {
  font-family: 'VT323', monospace !important;
  font-size: 22px !important;
  font-weight: 700 !important;
  color: var(--color-accent) !important;
  letter-spacing: 0.5px;
  margin: 0;
}
/* Selezionato: bordo rosso pixel */
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

/* Metriche stile arcade */
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

/* Scroll lista fissa altezza */
#scroll-list {
  max-height: 640px;
  overflow-y: auto;
  padding-right: 8px;
}
</style>
""", unsafe_allow_html=True)

# --- Funzioni di utilità ---

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
    # come da tuo original script (calcolo fanta voto per riga)
    # ... mantieni la tua funzione completa qui ...
    # Puoi integrare direttamente qui la tua definizione completa
    # per brevità, qui abbrevio ma nel codice inserisci la funzione completa già data
    return df  # placeholder

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

# --- Caricamento dati e impostazioni Supabase ---

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ SUPABASE_URL e/o SUPABASE_KEY non configurate.")
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

# --- Caricamento dati e preparazione vista ---

try:
    df_stats = load_stats()
    df_quotes = load_quotazioni()
except Exception as e:
    st.error("❌ Errore caricamento dati Supabase.")
    st.stop()

df_stats = normalize_dataframe(df_stats)
df_quotes = normalize_dataframe(df_quotes)

if df_stats.empty or df_quotes.empty:
    st.error("❌ I dati sono vuoti.")
    st.stop()

if "player_id" not in df_stats.columns or "player_id" not in df_quotes.columns:
    st.error("❌ Mancano colonne player_id.")
    st.stop()

df_stats = df_stats[df_stats["player_id"].notna()]
df_quotes = df_quotes[df_quotes["player_id"].notna()]

df_stats = remove_starred_vote_rows(df_stats)

# Calcola fantamedia ed unisci con quotazioni
df_fantamedia = aggregate_fantamedia(df_stats)
df_quotes = df_quotes.merge(df_fantamedia, on="player_id", how="left")
df_quotes["fantamedia_calcolata"] = df_quotes["fantamedia_calcolata"].fillna(0)

# Sidebar filtri multipli
st.sidebar.header("Filtri giocatori")
roles_selected = st.sidebar.multiselect("Ruolo", options=["P", "D", "C", "A"], default=["P","D","C","A"])
squadre = sorted(df_quotes["squadra"].dropna().unique())
squadra_selected = st.sidebar.multiselect("Squadra", options=squadre)
min_fantamedia = st.sidebar.slider("Fantamedia minima", 0.0, 10.0, 5.0, 0.1)
search_name = st.sidebar.text_input("Cerca per nome")

view_quotes = df_quotes.copy()
if roles_selected:
    view_quotes = view_quotes[view_quotes["ruolo"].str.upper().isin(roles_selected)]
if squadra_selected:
    view_quotes = view_quotes[view_quotes["squadra"].isin(squadra_selected)]
view_quotes = view_quotes[view_quotes["fantamedia_calcolata"] >= min_fantamedia]
if search_name:
    view_quotes = view_quotes[view_quotes["nome"].str.contains(search_name, case=False, na=False)]

view_quotes = view_quotes.sort_values("nome", na_position="last")

st.title("⚽ FantaAI Analytics — Retro Pixel Style")

col_players, col_details = st.columns([1, 3.2], gap="small")

with col_players:
    st.markdown('<div id="scroll-list">', unsafe_allow_html=True)

    if view_quotes.empty:
        st.info("Nessun giocatore trovato con i filtri selezionati.")
        selected_id = None
    else:
        labels = []
        ids = []
        labels_set = set()
        for r in view_quotes.itertuples():
            nome = getattr(r, "nome", "Giocatore")
            squad = getattr(r, "squadra", "?")
            fmedia = getattr(r, "fantamedia_calcolata", 0)
            pid = getattr(r, "player_id")
            emoji = emoji_forma(fmedia)
            label = f"{nome} • {squad} {emoji} — FM: {fmedia:.2f}"
            if label in labels_set:
                label = f"{label} • ID {pid}"
            labels_set.add(label)
            labels.append(label)
            ids.append(pid)

        label_to_id = dict(zip(labels, ids))
        selected_label = st.radio("Seleziona giocatore", labels, label_visibility="collapsed")
        selected_id = label_to_id.get(selected_label, None)

    st.markdown('</div>', unsafe_allow_html=True)

with col_details:
    if selected_id is None:
        st.info("Seleziona un giocatore nella lista per vedere i dettagli.")
    else:
        # Inserisci qui la funzione render_player_detail completa, come da script precedente
        render_player_detail(selected_id, df_stats, df_quotes)
