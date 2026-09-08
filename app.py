import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from supabase import create_client

# ==========================================
# 1. PAGE CONFIG & DESIGN SYSTEM
# ==========================================

st.set_page_config(
    page_title="FantaAI Analytics Pro",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ... (tutto il CSS rimane uguale, ma aggiungo alcune regole in fondo per i chip e lo slider) ...
_CUSTOM_CSS = """
<style>
... (il tuo CSS esistente) ...

/* Nuove regole per i chip ruolo */
.st-key-role_chip button {
    background-color: #1E293B !important;
    border: 1px solid rgba(255,255,255,0.05) !important;
    border-radius: 8px !important;
    color: #F1F5F9 !important;
    padding: 6px 0 !important;
    font-weight: 600 !important;
    transition: all 0.15s ease !important;
    width: 100% !important;
}
.st-key-role_chip button:hover {
    background-color: #334155 !important;
    border-color: rgba(16, 185, 129, 0.4) !important;
}
.st-key-role_chip button[data-active="true"] {
    background-color: rgba(16, 185, 129, 0.2) !important;
    border: 1.5px solid #10B981 !important;
    color: #34D399 !important;
}
.st-key-role_chip button div {
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    gap: 2px !important;
}
.st-key-role_chip button div span:first-child {
    font-size: 14px !important;
    font-weight: 700 !important;
}
.st-key-role_chip button div span:last-child {
    font-size: 11px !important;
    color: #94A3B8 !important;
}

/* Stile per slider */
input[type="range"] {
    accent-color: #10B981;
}
</style>
"""
st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)

# ==========================================
# 2. SUPABASE & DATA FETCHING (invariato)
# ==========================================
# ... (tutte le funzioni di fetch e load rimangono identiche) ...

# ==========================================
# 3. STATISTICAL UTILITIES (invariato)
# ==========================================
# ... (tutte le funzioni di calcolo rimangono identiche) ...

# ==========================================
# 4. REUSABLE UI COMPONENTS (invariato)
# ==========================================
# ... (ROLE_COLORS, render_section_header, render_kpi_card, render_quote_hero_card rimangono) ...

# ==========================================
# 5. PLAYER DETAIL VIEW (invariato)
# ==========================================
# ... (la funzione render_player_detail rimane identica) ...

# ==========================================
# 6. APP CONTROLLER & MAIN UI (NUOVO LAYOUT)
# ==========================================

try:
    df = load_stats()
    quot = load_quotazioni()
    ranking_df = load_ranking()
except Exception as e:
    st.error(f"❌ Errore nel caricamento dei dati: {e}")
    st.stop()

if df.empty or quot.empty:
    st.warning("⚠️ Tabelle statistiche o quotazioni vuote.")
    st.stop()

df = normalize_dataframe(df)
quot = normalize_dataframe(quot)
ranking_df = normalize_dataframe(ranking_df)
df = remove_starred_vote_rows(df)

# Stagione corrente
latest_s = get_latest_season(quot)
current_quot = (
    quot[quot["stagione"].astype(str).str.strip() == str(latest_s).strip()].copy()
    if latest_s
    else quot.copy()
)

# Precalcolo summary (per filtri e lista)
summary_df = compute_player_summaries(
    df, current_quot, ranking_df, titolari_df
)

# ==========================================
# HEADER
# ==========================================
title_col1, title_col2 = st.columns([0.06, 0.94])
with title_col1:
    st.markdown("### ⚽")
with title_col2:
    st.title("FantaAI Analytics")
    st.caption("Design Intelligence & Decision Support per l'Asta")
st.divider()

# ==========================================
# LAYOUT PRINCIPALE: SINISTRA (FILTRI+LISTA) / DESTRA (DETTAGLIO)
# ==========================================
col_left, col_right = st.columns([1.1, 2.9], gap="medium")

# -------- COLONNA SINISTRA: FILTRI E LISTA --------
with col_left:
    st.caption("**ROSTER & FILTRI SCOUTING**")

    # 1. Ricerca
    search_query = st.text_input(
        "Cerca giocatore o squadra",
        placeholder="🔍 Filtra per cognome o ruolo...",
        key="search_left",
        label_visibility="collapsed"
    )

    # 2. Filtro ruolo (chip)
    st.markdown("**FILTRO RUOLO TATTICO**")
    cols = st.columns(5)
    roles = ["Tutti", "P", "D", "C", "A"]
    total_counts = {}
    total_counts["Tutti"] = len(summary_df)
    for r in ["P","D","C","A"]:
        total_counts[r] = len(summary_df[summary_df["ruolo"].astype(str).str.upper().str.strip() == r])
    
    if "selected_role_chip" not in st.session_state:
        st.session_state.selected_role_chip = "Tutti"
    
    for i, r in enumerate(roles):
        with cols[i]:
            is_active = (st.session_state.selected_role_chip == r)
            if st.button(
                f"{r}\n{total_counts.get(r,0)}",
                key=f"role_{r}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
                help=f"Mostra solo {r}" if r!="Tutti" else "Mostra tutti"
            ):
                st.session_state.selected_role_chip = r
                st.rerun()

    # 3. Filtro Squadra e Ordinamento
    squadre_raw = (
        current_quot["squadra"].dropna().astype(str).str.strip().unique()
        if "squadra" in current_quot.columns
        else []
    )
    squadre_list = ["Tutte"] + sorted(list(squadre_raw))
    
    col_team, col_sort = st.columns(2)
    with col_team:
        selected_team = st.selectbox(
            "Club Serie A",
            squadre_list,
            index=0,
            key="team_select"
        )
    with col_sort:
        sort_options = [
            "👑 Indice Ranking (Decrescente)",
            "⭐ Fantamedia (Decrescente)",
            "🔤 Nome (A-Z)",
            "💰 Quotazione (Decrescente)",
        ]
        selected_sort = st.selectbox(
            "Ordinamento",
            sort_options,
            index=0,
            key="sort_select"
        )

    # 4. Filtri avanzati
    only_titolari = st.checkbox(
        "✅ Solo Titolari (Formazione Tipo)",
        value=False,
        key="only_titolari_left"
    )
    
    min_partite = st.slider(
        "Partite minime giocate",
        min_value=0,
        max_value=38,
        value=0,
        step=1,
        key="min_partite_left",
        help="Filtra i giocatori che hanno disputato almeno questo numero di partite nello storico"
    )

    # 5. APPLICAZIONE FILTRI E ORDINAMENTO
    filtered = summary_df.copy()
    
    # Ruolo (dal chip)
    selected_role = st.session_state.selected_role_chip
    if selected_role != "Tutti" and "ruolo" in filtered.columns:
        filtered = filtered[filtered["ruolo"].astype(str).str.upper().str.strip() == selected_role]
    
    # Squadra
    if selected_team != "Tutte" and "squadra" in filtered.columns:
        filtered = filtered[filtered["squadra"].astype(str).str.upper().str.strip() == selected_team.upper().strip()]
    
    # Ricerca
    if search_query.strip():
        q = search_query.upper().strip()
        match_nome = filtered["nome"].astype(str).str.upper().str.contains(q, na=False) if "nome" in filtered.columns else False
        match_squadra = filtered["squadra"].astype(str).str.upper().str.contains(q, na=False) if "squadra" in filtered.columns else False
        filtered = filtered[match_nome | match_squadra]
    
    # Titolari
    if only_titolari and "is_titolare" in filtered.columns:
        filtered = filtered[filtered["is_titolare"] == True]
    
    # Partite minime
    if min_partite > 0 and "presenze_totali" in filtered.columns:
        filtered = filtered[filtered["presenze_totali"] >= min_partite]
    
    # Ordinamento
    if selected_sort == "👑 Indice Ranking (Decrescente)":
        filtered = filtered.sort_values(
            by=["indice_finale", "quotazione_attuale", "nome"],
            ascending=[False, False, True],
            na_position="last"
        )
    elif selected_sort == "⭐ Fantamedia (Decrescente)":
        filtered = filtered.sort_values(
            by=["fantamedia", "presenze_totali", "nome"],
            ascending=[False, False, True],
            na_position="last"
        )
    elif selected_sort == "🔤 Nome (A-Z)":
        filtered = filtered.sort_values(by=["nome"], ascending=[True], na_position="last")
    elif selected_sort == "💰 Quotazione (Decrescente)":
        filtered = filtered.sort_values(
            by=["quotazione_attuale", "fvm", "nome"],
            ascending=[False, False, True],
            na_position="last"
        )

    # 6. LISTA GIOCATORI (con radio arricchito)
    st.caption(f"**GIOCATORI ({len(filtered)})**")
    
    if filtered.empty:
        st.info("Nessun giocatore trovato con questi filtri.")
        selected_id = None
    else:
        options_df = filtered.drop_duplicates(subset="player_id").copy()
        labels = []
        ids = []
        
        for row in options_df.itertuples():
            n = getattr(row, "nome", "Giocatore")
            s = getattr(row, "squadra", "-")
            pid = getattr(row, "player_id")
            ruolo = getattr(row, "ruolo", "")
            
            # Costruisco la label
            if selected_sort == "👑 Indice Ranking (Decrescente)":
                ind = getattr(row, "indice_finale", None)
                rk = getattr(row, "rank_ruolo", None)
                if pd.notna(ind):
                    rk_txt = f" (#{int(float(rk))} {ruolo})" if pd.notna(rk) else ""
                    lbl = f"{n} [{s}] • Ind: {float(ind):.1f}{rk_txt}"
                else:
                    lbl = f"{n} [{s}] • Ind: N/D"
            elif selected_sort == "⭐ Fantamedia (Decrescente)":
                fm = getattr(row, "fantamedia", None)
                pz = getattr(row, "presenze_totali", 0)
                if pd.notna(fm):
                    lbl = f"{n} [{s}] • FM: {float(fm):.2f} ({int(float(pz))}P)"
                else:
                    lbl = f"{n} [{s}] • FM: N/D"
            elif selected_sort == "💰 Quotazione (Decrescente)":
                q_val = getattr(row, "quotazione_attuale", "-")
                f_val = getattr(row, "fvm", "-")
                lbl = f"{n} [{s}] • Q: {q_val} | FVM: {f_val}"
            else:
                lbl = f"{n} [{s}]"
            
            # Aggiunta tag (rigorista, punizioni, titolare, infortunato)
            nome_upper = str(n).upper().strip()
            squadra_upper = str(s).upper().strip()
            is_rig = not rigoristi_df[(rigoristi_df["giocatore"] == nome_upper) & (rigoristi_df["squadra"] == squadra_upper)].empty
            is_pun = not punizioni_df[(punizioni_df["giocatore"] == nome_upper) & (punizioni_df["squadra"] == squadra_upper)].empty
            if is_rig:
                lbl += " 🎯"
            if is_pun:
                lbl += " ⚡"
            tit_info = titolari_df[(titolari_df["nome_giocatore"] == nome_upper) & (titolari_df["squadra"] == squadra_upper)]
            if not tit_info.empty:
                row_t = tit_info.iloc[0]
                if str(row_t.get("titolarita", "")).lower() == "titolare":
                    lbl += " ✅"
                if str(row_t.get("infortunato", "no")).lower() == "si":
                    lbl += " 🤕"
            
            if lbl in labels:
                lbl = f"{lbl} #{int(pid)}"
            labels.append(lbl)
            ids.append(int(pid))
        
        label_to_id = dict(zip(labels, ids))
        radio_key = "player_radio"
        if radio_key not in st.session_state or st.session_state[radio_key] not in labels:
            default_idx = 0
            if "active_player_id" in st.session_state and st.session_state["active_player_id"] in ids:
                default_idx = ids.index(st.session_state["active_player_id"])
            st.session_state[radio_key] = labels[default_idx]
        
        selected_label = st.radio(
            "Seleziona giocatore",
            options=labels,
            key=radio_key,
            label_visibility="collapsed"
        )
        selected_id = label_to_id.get(selected_label)
        st.session_state["active_player_id"] = selected_id

# -------- COLONNA DESTRA: DETTAGLIO GIOCATORE --------
with col_right:
    if selected_id is None:
        st.info("👈 Seleziona un giocatore dalla lista a sinistra per visualizzare la scheda analitica.")
    else:
        render_player_detail(selected_id, df, quot, ranking_df)
