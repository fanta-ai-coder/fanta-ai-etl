import os
import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client

st.set_page_config(page_title="Fantacalcio Analytics Dashboard", layout="wide")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

@st.cache_data(ttl=600)
def load_data():
    res = supabase.table("player_stats_history").select("*").execute()
    df = pd.DataFrame(res.data)
    return df

st.title("⚽ Dashboard Analitica Voti & Fantavoti Serie A")

try:
    df = load_data()
except Exception as e:
    st.error(f"Errore nel caricamento dei dati da Supabase: {e}")
    st.stop()

if df.empty:
    st.warning("Nessun dato presente nel database. Esegui prima lo script di ingestion.")
    st.stop()

# Sidebar filtri globali
st.sidebar.header("🎯 Filtri Globali")
selected_season = st.sidebar.multiselect("Stagione", options=sorted(df["stagione"].unique()), default=sorted(df["stagione"].unique())[-1:])
selected_role = st.sidebar.multiselect("Ruolo", options=["P", "D", "C", "A"], default=["P", "D", "C", "A"])

df_filtered = df[(df["stagione"].isin(selected_season)) & (df["ruolo"].isin(selected_role))]

tab1, tab2, tab3 = st.tabs(["👤 Profilo Singolo Giocatore", "⚔️ Confronto Giocatori", "🛡️ Analisi Squadre"])

# ------------------------------------------------------------
# TAB 1: PROFILO GIOCATORE
# ------------------------------------------------------------
with tab1:
    player_list = sorted(df_filtered["nome"].unique())
    selected_player = st.selectbox("Seleziona Calciatore", options=player_list)
    
    p_df = df_filtered[df_filtered["nome"] == selected_player].sort_values(by=["stagione", "giornata"])
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Media Voto", round(p_df["voto"].mean(), 2))
    col2.metric("Media FantaVoto", round(p_df["fanta_voto"].mean(), 2))
    col3.metric("Gol Fatti Totali", int(p_df["gf"].sum()))
    col4.metric("Assist Totali", int(p_df["ass"].sum()))
    
    fig = px.line(p_df, x="giornata", y=["voto", "fanta_voto"], color="stagione", 
                  title=f"Andamento Voti per {selected_player}", markers=True)
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------
# TAB 2: CONFRONTO GIOCATORI
# ------------------------------------------------------------
with tab2:
    st.subheader("Confronta fino a 4 Giocatori")
    comp_players = st.multiselect("Scegli Giocatori da Confrontare", options=player_list, max_selections=4)
    
    if comp_players:
        c_df = df_filtered[df_filtered["nome"].isin(comp_players)]
        summary = c_df.groupby("nome").agg(
            Partite=('voto', 'count'),
            Media_Voto=('voto', 'mean'),
            Media_Fantavoto=('fanta_voto', 'mean'),
            Gol=('gf', 'sum'),
            Assist=('ass', 'sum'),
            Ammonizioni=('amm', 'sum')
        ).reset_index()
        
        st.dataframe(summary.style.highlight_max(axis=0, color='lightgreen'))
        
        fig_bar = px.bar(c_df, x="nome", y="fanta_voto", color="nome", barmode="group", title="Distribuzione FantaVoti")
        st.plotly_chart(fig_bar, use_container_width=True)

# ------------------------------------------------------------
# TAB 3: ANALISI SQUADRE
# ------------------------------------------------------------
with tab3:
    st.subheader("Rendimento Medio per Squadra e Ruolo")
    team_summary = df_filtered.groupby(["squadra", "ruolo"]).agg(
        Media_Voto=('voto', 'mean'),
        Media_Fantavoto=('fanta_voto', 'mean')
    ).reset_index()
    
    fig_heat = px.density_heatmap(team_summary, x="squadra", y="ruolo", z="Media_Fantavoto", 
                                  title="Heatmap Media FantaVoto per Squadra e Ruolo", color_continuous_scale="Viridis")
    st.plotly_chart(fig_heat, use_container_width=True)
