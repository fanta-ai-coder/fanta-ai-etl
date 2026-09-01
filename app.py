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
    initial_sidebar_state="expanded",
)

# Tema scuro e stili personalizzati
st.markdown("""
    <style>
    body, .main {
        background-color: #121212 !important;
        color: #E0E0E0 !important;
    }
    .stContainer > div {
        background-color: #1E1E1E !important;
        border-radius: 12px !important;
        padding: 16px !important;
        box-shadow: 0 0 10px rgba(255,255,255,0.1) !important;
    }
    h1, h2, h3, h4, h5, h6, .css-1v0mbdj, .css-hxt7ib {
        color: #FAFAFA !important;
    }
    a {
        color: #1F7A4D !important;
    }
    ::-webkit-scrollbar {
        width: 8px; height: 8px;
    }
    ::-webkit-scrollbar-thumb {
        background-color: #1F7A4D;
        border-radius: 10px;
    }
    #scroll-list {
        max-height: 640px; overflow-y: auto; padding-right: 8px;
    }
    .player-label {
        font-size: 18px;
        font-weight: 700;
        color: #1F7A4D;
        margin-bottom: 4px;
    }
    </style>
""", unsafe_allow_html=True)

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
        end = start + page_size - 1
        response = supabase.table(table_name).select("*").range(start, end).execute()
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
    url = "https://raw.githubusercontent.com/fanta-ai-coder/fanta-ai-etl/refs/heads/main/rigoristi.csv"
    df = pd.read_csv(url)
    df["giocatore"] = df["giocatore"].str.upper().str.strip()
    df["squadra"] = df["squadra"].str.upper().str.strip()
    return df

@st.cache_data(ttl=600)
def load_punizioni():
    url = "https://raw.githubusercontent.com/fanta-ai-coder/fanta-ai-etl/refs/heads/main/punizioni.csv"
    df = pd.read_csv(url)
    df["giocatore"] = df["giocatore"].str.upper().str.strip()
    df["squadra"] = df["squadra"].str.upper().str.strip()
    return df

rigoristi_df = load_rigoristi()
punizioni_df = load_punizioni()

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

# Rimuove righe con voto stellato
def remove_starred_vote_rows(df):
    if df.empty or "voto" not in df.columns:
        return df.copy()
    result = df.copy()
    raw_vote = result["voto"].astype(str).str.strip()
    starred = raw_vote.str.contains(r"\*", regex=True, na=False)
    if starred.any():
        result = result.loc[~starred].copy()
    return result

# Calcola fantavoto per riga (da storico)
def calculate_fantavoto(df):
    result = df.copy()
    if "voto" not in result.columns:
        result["fanta_voto_calcolato"] = float("nan")
        return result
    # Valori numerici con fallback zero
    voto = pd.to_numeric(result["voto"], errors="coerce").fillna(0)
    gf = pd.to_numeric(result.get("gf", 0), errors="coerce").fillna(0)
    ass = pd.to_numeric(result.get("ass", 0), errors="coerce").fillna(0)
    rf = pd.to_numeric(result.get("rf", 0), errors="coerce").fillna(0)
    au = pd.to_numeric(result.get("au", 0), errors="coerce").fillna(0)
    esp = pd.to_numeric(result.get("esp", 0), errors="coerce").fillna(0)
    amm = pd.to_numeric(result.get("amm", 0), errors="coerce").fillna(0)

    clean_sheet = pd.Series(0.0, index=result.index)
    for col in ["pi", "porta_inviolata", "clean_sheet", "imbattuto"]:
        if col in result.columns:
            clean_sheet = pd.to_numeric(result[col], errors="coerce").fillna(0)
            break

    penalty_saved = pd.Series(0.0, index=result.index)
    for col in ["rp", "rigori_parati", "rigore_parato"]:
        if col in result.columns:
            penalty_saved = pd.to_numeric(result[col], errors="coerce").fillna(0)
            break

    gol_subiti = pd.Series(0.0, index=result.index)
    for col in ["gs", "gol_subiti"]:
        if col in result.columns:
            gol_subiti = pd.to_numeric(result[col], errors="coerce").fillna(0)
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
    result.loc[pd.to_numeric(result["voto"], errors="coerce").isna(), "fanta_voto_calcolato"] = float("nan")
    return result

# Calcola la fantamedia per player_id e restituisce DataFrame con player_id e fantamedia
def aggregate_fantamedia(df_stats):
    df = remove_starred_vote_rows(df_stats)
    df = calculate_fantavoto(df)
    # Group by player_id e media quella fanta_voto_calcolato
    result = df.groupby("player_id")["fanta_voto_calcolato"].mean().reset_index()
    result.rename(columns={"fanta_voto_calcolato": "fantamedia_calcolata"}, inplace=True)
    return result

# Emoji forma (per lista)
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

# Rendering dettagli giocatore (come nel tuo script, omesso qui per brevità, ma si integra uguale)

def render_player_detail(player_id, stats, quotations):
    # Inserisci qui la funzione dettagliata già fornita nel codice precedente...
    pass  # Per brevità, usa quella completa fornita in precedenza

# --- MAIN ---

try:
    df_stats = load_stats()
    df_quotes = load_quotazioni()
except Exception as e:
    st.error("❌ Errore nel caricamento dei dati da Supabase.")
    st.code(str(e))
    st.stop()

if df_stats.empty or df_quotes.empty:
    st.error("❌ Uno o più dataset sono vuoti.")
    st.stop()

df_stats = normalize_dataframe(df_stats)
df_quotes = normalize_dataframe(df_quotes)

if "player_id" not in df_stats.columns or "player_id" not in df_quotes.columns:
    st.error("❌ player_stats_history o giocatori_quotazioni non contengono player_id.")
    st.stop()

df_stats = df_stats[df_stats["player_id"].notna()]
df_quotes = df_quotes[df_quotes["player_id"].notna()]

# Calcolo fantamedia aggregata per giocatore dallo storico
df_fantamedia = aggregate_fantamedia(df_stats)

# Unisci fantamedia calcolata alle quotazioni (merge a sinistra su player_id)
df_quotes = df_quotes.merge(df_fantamedia, on="player_id", how="left")

# Riempi NaN fantamedia calcolata a 0 per ragioni di filtro
df_quotes["fantamedia_calcolata"] = df_quotes["fantamedia_calcolata"].fillna(0)

# Filtri sidebar
st.sidebar.header("Filtra giocatori")
roles_selected = st.sidebar.multiselect("Ruolo", options=["P", "D", "C", "A"], default=["P", "D", "C", "A"])
squadra_options = sorted(df_quotes["squadra"].dropna().unique())
squadra_selected = st.sidebar.multiselect("Squadra", options=squadra_options)
min_fantamedia = st.sidebar.slider("Fantamedia minima", 0.0, 10.0, 5.0, 0.1)
search_name = st.sidebar.text_input("Cerca nome")

quot_view = df_quotes.copy()
if roles_selected:
    quot_view = quot_view[quot_view["ruolo"].str.upper().isin(roles_selected)]
if squadra_selected:
    quot_view = quot_view[quot_view["squadra"].isin(squadra_selected)]
if min_fantamedia > 0:
    quot_view = quot_view[quot_view["fantamedia_calcolata"] >= min_fantamedia]
if search_name:
    quot_view = quot_view[quot_view["nome"].str.contains(search_name, case=False, na=False)]

quot_view = quot_view.sort_values("nome", na_position="last")

st.title("⚽ FantaAI")

col_players, col_detail = st.columns([1, 3.2], gap="small")

with col_players:
    st.markdown("<h3 style='color:#1F7A4D; margin-bottom:8px;'>👥 Giocatori disponibili</h3>", unsafe_allow_html=True)
    with st.container():
        st.markdown('<div id="scroll-list">', unsafe_allow_html=True)
        if quot_view.empty:
            st.info("Nessun giocatore trovato.")
            selected_id = None
        else:
            labels = []
            ids = []
            used_labels = set()
            for row in quot_view.itertuples():
                nome_row = getattr(row, "nome", "Giocatore")
                squadra_row = getattr(row, "squadra", "-")
                fantamedia_row = getattr(row, "fantamedia_calcolata", "?")
                player_id_row = getattr(row, "player_id")
                emoji = emoji_forma(fantamedia_row)
                label = f"{nome_row} • {squadra_row} {emoji} — FM: {fantamedia_row:.2f}"
                # Gestione duplicati label
                if label in used_labels:
                    label = f"{label} • ID {int(player_id_row)}"
                used_labels.add(label)
                labels.append(label)
                ids.append(int(player_id_row))
            label_to_id = dict(zip(labels, ids))
            selected_label = st.radio("Seleziona giocatore", options=labels, label_visibility="collapsed")
            selected_id = label_to_id[selected_label]
        st.markdown('</div>', unsafe_allow_html=True)

with col_detail:
    if selected_id is None:
        st.info("Seleziona un giocatore dalla lista per visualizzare i dettagli.")
    else:
        render_player_detail(selected_id, df_stats, df_quotes)
