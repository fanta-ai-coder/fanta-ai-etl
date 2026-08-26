import os
import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client

# Configurazione layout Streamlit
st.set_page_config(page_title="FantaAI Dashboard", page_icon="⚽", layout="wide")

st.title("⚽ FantaAI - Advanced Serie A Analytics")
st.markdown("Statistiche avanzate ed Expected Goals aggiornati in tempo reale.")

# 1. Connessione a Supabase (usa le variabili di ambiente / secrets)
SUPABASE_URL = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("⚠️ Credenziali Supabase non trovate nei Secrets!")
    st.stop()

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# 2. Caricamento Dati
@st.cache_data(ttl=600)
def load_data():
    res = supabase.table("player_stats").select("*").execute()
    return pd.DataFrame(res.data)

df = load_data()

if df.empty:
    st.warning("Nessun dato trovato nella tabella 'player_stats'.")
    st.stop()

# 3. Sidebar - Filtri Interattivi
st.sidebar.header("🔍 Filtri")

# Filtro Squadra
squadre = ["Tutte"] + sorted(df["team"].dropna().unique().tolist())
squadra_sel = st.sidebar.selectbox("Seleziona Squadra", squadre)

# Filtro Minuti Minimi
min_minutes = st.sidebar.slider("Minuti minimi giocati", 0, int(df["minutes_played"].max()), 180)

# Applicazione Filtri
df_filtered = df[df["minutes_played"] >= min_minutes]
if squadra_sel != "Tutte":
    df_filtered = df_filtered[df_filtered["team"] == squadra_sel]

# 4. KPI Top Level
col1, col2, col3, col4 = st.columns(4)
col1.metric("Giocatori Analizzati", len(df_filtered))
col2.metric("Gol Totali", int(df_filtered["goals"].sum()))
col3.metric("Assist Totali", int(df_filtered["assists"].sum()))
col4.metric("xG Totali Lega", round(df_filtered["xg"].sum(), 1))

st.markdown("---")

# 5. Grafici Avanzati (Plotly)
st.subheader("📊 Analisi Prestazioni vs Metriche Avanzate")

tab1, tab2 = st.tabs(["Efficienza Realizzativa (Gol vs xG)", "Creazione Gioco (Assist vs xA)"])

with tab1:
    fig_xg = px.scatter(
        df_filtered,
        x="xg",
        y="goals",
        size="minutes_played",
        color="team",
        hover_name="player_name",
        labels={"xg": "Expected Goals (xG)", "goals": "Gol Effettivi"},
        title="Gol vs Expected Goals (Dimensione = Minuti Giocati)"
    )
    # Linea di parità xG = Gol
    fig_xg.add_shape(type="line", x0=0, y0=0, x1=df_filtered["xg"].max(), y1=df_filtered["xg"].max(),
                     line=dict(color="Gray", dash="dash"))
    st.plotly_chart(fig_xg, use_container_width=True)

with tab2:
    fig_xa = px.scatter(
        df_filtered,
        x="xa",
        y="assists",
        size="minutes_played",
        color="team",
        hover_name="player_name",
        labels={"xa": "Expected Assists (xA)", "assists": "Assist Effettivi"},
        title="Assist vs Expected Assists (xA)"
    )
    st.plotly_chart(fig_xa, use_container_width=True)

st.markdown("---")

# 6. Tabella Dati Completa
st.subheader("📋 Tabella Statistiche Giocatori")

cols_to_show = ["player_name", "team", "matches_played", "minutes_played", "goals", "assists", "xg", "xa", "goals_per_90", "xg_per_90"]
st.dataframe(
    df_filtered[cols_to_show].sort_values(by="goals", ascending=False),
    use_container_width=True,
    hide_index=True
)