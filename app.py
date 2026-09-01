import os
import html
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from supabase import create_client

st.set_page_config(
    page_title="FantaAI Scelta Fantallenatore",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Tema scuro e stile personalizzato (semplificato)
st.markdown("""
<style>
body {
    background-color: #121212;
    color: #E0E0E0;
}
.stButton>button {
    background-color: #1F7A4D;
    color: white;
    font-weight: 600;
}
.stButton>button:hover {
    background-color: #14562e;
}
h1, h2, h3, h4, h5 {
    color: #FAFAFA;
}
.sidebar .sidebar-content {
    background-color: #1E1E1E;
    color: #E0E0E0;
}
</style>
""", unsafe_allow_html=True)

# --- Funzioni di utilità e caricamento dati (come nel tuo codice precedente) ---

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ SUPABASE_URL e/o SUPABASE_KEY non configurate.")
    st.stop()

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

def fetch_all_rows(table_name):
    rows = []
    page_size = 1000
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

def normalize_player_id_series(series):
    numeric = pd.to_numeric(series, errors="coerce")
    return numeric.round().astype("Int64")

def safe_mean(df, col):
    if col not in df.columns:
        return 0.0
    values = pd.to_numeric(df[col], errors="coerce").dropna()
    if len(values)==0:
        return 0.0
    return float(values.mean())

def remove_starred_vote_rows(df):
    if df.empty or "voto" not in df.columns:
        return df.copy()
    result = df.copy()
    starred = result["voto"].astype(str).str.contains(r"\*", regex=True, na=False)
    if starred.any():
        result = result.loc[~starred].copy()
    return result

def calculate_fantavoto(df):
    # Semplice versione per fantavoto
    result = df.copy()
    voto = pd.to_numeric(result["voto"], errors="coerce").fillna(0)
    gf = pd.to_numeric(result["gf"], errors="coerce").fillna(0)
    ass = pd.to_numeric(result["ass"], errors="coerce").fillna(0)
    fanta = voto + gf*3 + ass
    result["fanta_voto"] = fanta
    return result

def season_sort_key(value):
    try:
        return int(str(value).split("/")[0])
    except:
        return -1

def get_latest_season(df):
    seasons = df["stagione"].dropna().unique()
    seasons = [s for s in seasons if str(s).strip() != ""]
    return max(seasons, key=season_sort_key) if seasons else None

# Carica i dati
df_stats = load_stats()
df_quot = load_quotazioni()
rigoristi_df = load_rigoristi()
punizioni_df = load_punizioni()

# Normalizza dataframe
df_stats["player_id"] = normalize_player_id_series(df_stats["player_id"])
df_quot["player_id"] = normalize_player_id_series(df_quot["player_id"])

# Rimuovi voti "stellati"
df_stats = remove_starred_vote_rows(df_stats)

# Prendi stagione più recente
last_season = get_latest_season(df_quot)
quot_latest = df_quot
if last_season:
    quot_latest = df_quot[df_quot["stagione"] == last_season]

# Sidebar: filtri e ricerca
with st.sidebar:
    st.title("Filtri e Ricerca")
    role_filter = st.selectbox("Ruolo", ["Tutti", "P", "D", "C", "A"])
    search_name = st.text_input("Cerca giocatore")
    sort_by = st.selectbox("Ordina per", ["Fantamedia", "Quota", "Nome"])

# Filtra quotazioni
quot_view = quot_latest.copy()
if role_filter != "Tutti" and "ruolo" in quot_view.columns:
    quot_view = quot_view[quot_view["ruolo"].str.upper() == role_filter]
if search_name.strip() != "":
    quot_view = quot_view[quot_view["nome"].str.contains(search_name, case=False, na=False)]

# Ordina
if sort_by == "Fantamedia" and "fvm" in quot_view.columns:
    quot_view = quot_view.sort_values("fvm", ascending=False)
elif sort_by == "Quota" and "quotazione_attuale" in quot_view.columns:
    quot_view = quot_view.sort_values("quotazione_attuale", ascending=False)
else:
    quot_view = quot_view.sort_values("nome")

# List players on left, details on right
col_list, col_detail = st.columns([1, 3])

with col_list:
    st.header("Giocatori disponibili")
    selected_id = None
    
    for _, row in quot_view.iterrows():
        name = row.get("nome", "Sconosciuto")
        team = row.get("squadra", "-")
        role = row.get("ruolo", "-")
        quote = row.get("quotazione_attuale", 0)
        fvm = row.get("fvm", 0)
        
        # Simple button with label
        label = f"{name} ({team} - {role}) | Quota: {quote} | Fantamedia: {fvm}"
        if st.button(label, key=f"btn_{row['player_id']}"):
            selected_id = row["player_id"]

def display_player_metrics(p_stats):
    # Calcoli sintetici per KPI da mostrare
    media_voto = safe_mean(p_stats, "voto")
    fantamedia = safe_mean(calculate_fantavoto(p_stats), "fanta_voto")
    gol_media = safe_mean(p_stats, "gf") + safe_mean(p_stats, "rf")
    assist_media = safe_mean(p_stats, "ass")
    presenze = p_stats["voto"].count()
    presenze_pct = (presenze / 38) * 100

    # Display in riquadri
    st.markdown(f"### Statistiche principali")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Media voto", f"{media_voto:.2f}")
    col2.metric("Fantamedia", f"{fantamedia:.2f}")
    col3.metric("Gol medi / stagione", f"{gol_media:.2f}")
    col4.metric("Assist medi / stagione", f"{assist_media:.2f}")
    col5.metric("Presenza %", f"{presenze_pct:.0f}%")

def render_player_detail(selected_id):
    p_stats = df_stats[df_stats["player_id"] == selected_id]
    p_quote = quot_latest[quot_latest["player_id"] == selected_id]
    if p_quote.empty or p_stats.empty:
        st.warning("Dati insufficienti per questo giocatore.")
        return
    nome = p_quote.iloc[0]["nome"]
    squadra = p_quote.iloc[0]["squadra"]
    ruolo = p_quote.iloc[0]["ruolo"]

    nome_upper = str(nome).upper()
    squadra_upper = str(squadra).upper()

    # Info rigorista
    rigor = rigoristi_df[
        (rigoristi_df["giocatore"] == nome_upper) & 
        (rigoristi_df["squadra"] == squadra_upper)
    ]
    rig_desc = ""
    if not rigor.empty:
        pos = rigor.iloc[0]["posizione"]
        rig_desc = f"⚽ Rigorista (Ranking posizione: {pos})"

    # Info punizioni
    puni = punizioni_df[
        (punizioni_df["giocatore"] == nome_upper) & 
        (punizioni_df["squadra"] == squadra_upper)
    ]
    puni_desc = ""
    if not puni.empty:
        pos = puni.iloc[0]["posizione"]
        puni_desc = f"🎯 Tira punizioni (Ranking posizione: {pos})"

    st.markdown(f"## {nome}")
    st.markdown(f"**{squadra} • {ruolo}**")
    if rig_desc or puni_desc:
        st.markdown(f"### {rig_desc} {'•' if rig_desc and puni_desc else ''} {puni_desc}")

    display_player_metrics(p_stats)

    # Grafico semplice media mobile fantavoto
    p_stats = p_stats.copy()
    p_stats["data"] = pd.to_datetime(p_stats["data"], errors="coerce")
    p_stats = p_stats.sort_values("data")
    p_stats = calculate_fantavoto(p_stats)
    window = 5
    p_stats["fanta_media_mobile"] = p_stats["fanta_voto"].rolling(window, min_periods=1).mean()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=p_stats["data"],
        y=p_stats["fanta_media_mobile"],
        mode="lines+markers",
        name=f"Fantamedia mobile ({window} partite)"
    ))
    fig.update_layout(
        height=300, margin=dict(t=30, b=30),
        yaxis_title="Fantamedia",
        xaxis_title="Data",
        template="plotly_dark"
    )
    st.plotly_chart(fig, use_container_width=True)

if selected_id:
    with col_detail:
        render_player_detail(selected_id)
else:
    with col_detail:
        st.info("Seleziona un giocatore dalla lista.")

