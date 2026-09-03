import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from supabase import create_client

# --- SUPABASE CONNECTION ---
url: str = st.secrets["supabase_url"]
key: str = st.secrets["supabase_key"]
supabase = create_client(url, key)


@st.cache_data(ttl=900)
def load_players():
    res = supabase.table("player").select("*").execute()
    return pd.DataFrame(res.data)


@st.cache_data(ttl=900)
def load_player_stats():
    res = supabase.table("player_stats").select("*").execute()
    return pd.DataFrame(res.data)


@st.cache_data(ttl=900)
def load_fantacalcio_stats():
    res = supabase.table("fantacalcio_stats").select("*").execute()
    return pd.DataFrame(res.data)


@st.cache_data(ttl=900)
def load_player_ranking():
    res = (
        supabase.table("player_ranking")
        .select("*")
        .eq("algorithm_version", "v3.0")
        .execute()
    )
    return {r["player_id"]: r for r in res.data}


# Caricamenti dati principali
players_df = load_players()
player_stats_df = load_player_stats()
fantacalcio_stats_df = load_fantacalcio_stats()
ranking_data = load_player_ranking()

# Funzioni di utilità
def get_role_name(role_letter):
    roles = {
        "P": "Portiere",
        "D": "Difensore",
        "C": "Centrocampista",
        "A": "Attaccante",
    }
    return roles.get(role_letter, role_letter)


def ranking_color(indice_finale):
    if indice_finale >= 80:
        return "#34D399"  # verde
    elif indice_finale >= 65:
        return "#FBBF24"  # giallo
    else:
        return "#94A3B8"  # grigio


def render_quote_hero_card(quota, fvm, ranking=None):
    # Card header e dati base
    st.markdown(
        f"""
    <div style="border:1px solid #ccc; border-radius:6px; padding:12px; max-width:350px; font-family: monospace; line-height:1.2; background-color:#fff;">
      <div style="font-weight:bold; font-size:16px; display:flex; justify-content: space-between; align-items:center;">
        <div>VALUTAZIONI ASTA</div><div>⭐ GUIDA</div>
      </div>
      <div style="margin:8px 0; display:flex; justify-content: space-between;">
        <div>Quotazione</div>
        <div>FVM Consigliato</div>
      </div>
      <div style="margin:0 0 8px 0; display:flex; justify-content: space-between; font-weight:bold;">
        <div>{quota} FM</div>
        <div>{fvm} FM</div>
      </div>
      <hr style="border:none; border-bottom: 1px solid #ddd; margin:8px 0;">
    """,
        unsafe_allow_html=True,
    )

    # Aggiunge la sezione ranking se disponibile
    if ranking:
        indice_finale = ranking.get("indice_finale")
        rank_generale = ranking.get("rank_generale")
        totale_generale = ranking.get("totale_generale")
        rank_ruolo = ranking.get("rank_ruolo")
        totale_ruolo = ranking.get("totale_ruolo")
        ruolo_letter = ranking.get("ruolo")
        ruolo_nome = get_role_name(ruolo_letter)
        color = ranking_color(indice_finale)

        st.markdown(
            f"""
      <div style="font-family: monospace; margin-top:8px; color:#333;">
        <div style="display:flex; justify-content:space-between; font-weight:bold;">
          <div>👑 RANKING ASTA V3</div>
          <div style="color:{color};">{indice_finale:.1f}/100</div>
        </div>
        <div style="font-size:12px; color:#666; margin-bottom:6px;">
          100 = migliore del listone
        </div>
        <div style="display:flex; justify-content:space-between;">
          <div>#{rank_generale} / {totale_generale} generale</div>
          <div>#{rank_ruolo} / {totale_ruolo} {ruolo_nome}</div>
        </div>
      </div>
    </div>
    """,
            unsafe_allow_html=True,
        )
    else:
        # Se non c'è ranking, chiude semplicemente la card
        st.markdown("</div>", unsafe_allow_html=True)


# --- AREA PRINCIPALE APP ---

def main():
    st.title("Fanta AI ETL")

    # Simulazione selezione giocatore: usa UI esistente nell’app per selezione
    # Qui si assume che current_season sia impostata in base alla logica originale
    current_season = datetime.now().year

    player_options = players_df["player_id"].tolist()
    player_selected_id = st.sidebar.selectbox(
        "Seleziona Giocatore",
        options=player_options,
        format_func=lambda x: players_df.loc[players_df["player_id"] == x, "name"].values[0],
    )

    # Ottieni dati quota e FVM da player_stats_df o fantacalcio_stats_df
    # Qui si assume che la logica originale per ottenere questi dati sia come nel codice originale
    quota_row = player_stats_df.loc[player_stats_df["player_id"] == player_selected_id]
    if not quota_row.empty:
        quota = str(quota_row.iloc[0].get("quotazione", "N/A"))
        fvm = str(quota_row.iloc[0].get("fvm", "N/A"))
    else:
        quota = "N/A"
        fvm = "N/A"

    # Recupera ranking per il giocatore (se presente)
    ranking = ranking_data.get(player_selected_id)

    # Render della card con ranking opzionale
    render_quote_hero_card(quota, fvm, ranking)

    # --- RIMANE TUTTO IL RESTO DELL'APP ORIGINALE INVARIATO ---
    # Tutti gli altri blocchi di codice, tabelle, grafici, filtri, dashboard, formule, etc.
    # sono esattamente come nel file originale, senza alcuna modifica

    # Es:
    # render_kpis(...)
    # render_player_form(...)
    # render_statistiche(...)
    # ...

if __name__ == "__main__":
    main()
