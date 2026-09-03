import os
import html
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

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: #0B0F19;
        color: #F8FAFC;
        overflow-anchor: none !important;
        scroll-behavior: auto !important;
    }

    .stAppViewContainer, section.main, [data-testid="stMainBlockContainer"] {
        background-color: #0B0F19;
        overflow-anchor: none !important;
        scroll-behavior: auto !important;
    }

    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #0B0F19; }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 9999px; }
    ::-webkit-scrollbar-thumb:hover { background: #10B981; }

    [data-testid="stRadio"] div[role="radiogroup"] {
        display: flex !important;
        flex-direction: column !important;
        flex-wrap: nowrap !important;
        width: 100% !important;
        max-height: 620px !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
        background-color: #111827 !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        padding: 8px !important;
        gap: 5px !important;
        overscroll-behavior: contain !important;
        contain: content !important;
    }

    [data-testid="stRadio"] label > div:first-child,
    [data-testid="stRadio"] input[type="radio"] {
        display: none !important;
    }

    [data-testid="stRadio"] label {
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        width: 100% !important;
        background-color: #1E293B !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 8px !important;
        padding: 10px 14px !important;
        margin: 0 !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
    }

    [data-testid="stRadio"] label:hover {
        background-color: #334155 !important;
        border-color: rgba(16, 185, 129, 0.4) !important;
    }

    [data-testid="stRadio"] label p,
    [data-testid="stRadio"] label span,
    [data-testid="stRadio"] label div {
        color: #F1F5F9 !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        margin: 0 !important;
    }

    [data-testid="stRadio"] label:has(input:checked) {
        background-color: rgba(16, 185, 129, 0.2) !important;
        border: 1.5px solid #10B981 !important;
    }

    [data-testid="stRadio"] label:has(input:checked) p,
    [data-testid="stRadio"] label:has(input:checked) span {
        color: #34D399 !important;
        font-weight: 700 !important;
    }

    .stTextInput input, .stSelectbox [data-baseweb="select"] {
        background-color: #111827 !important;
        border: 1px solid #374151 !important;
        border-radius: 8px !important;
        color: #F9FAFB !important;
    }

    [data-testid="stMetric"] {
        background-color: #111827;
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        padding: 14px 18px;
    }
    [data-testid="stMetricLabel"] { color: #94A3B8 !important; font-weight: 500; font-size: 0.85rem; }
    [data-testid="stMetricValue"] { color: #F8FAFC !important; font-weight: 700; }

    [data-testid="stRadio"],
    [data-testid="stRadio"] *,
    [data-testid="stRadio"] label,
    [data-testid="stRadio"] input {
        scroll-margin: 0 !important;
        scroll-padding: 0 !important;
        scroll-margin-top: 0 !important;
        scroll-margin-bottom: 0 !important;
    }

    div[data-testid="stHorizontalBlock"] { align-items: flex-start !important; }
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child {
        position: sticky !important;
        top: 12px !important;
        align-self: flex-start !important;
        z-index: 10 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# 2. SUPABASE & DATA FETCHING
# ==========================================
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
    try:
        df = pd.read_csv(url)
        df["giocatore"] = df["giocatore"].astype(str).str.upper().str.strip()
        df["squadra"] = df["squadra"].astype(str).str.upper().str.strip()
        return df
    except Exception:
        return pd.DataFrame(columns=["giocatore", "squadra", "posizione"])

@st.cache_data(ttl=600)
def load_punizioni():
    url = "https://raw.githubusercontent.com/fanta-ai-coder/fanta-ai-etl/refs/heads/main/punizioni.csv"
    try:
        df = pd.read_csv(url)
        df["giocatore"] = df["giocatore"].astype(str).str.upper().str.strip()
        df["squadra"] = df["squadra"].astype(str).str.upper().str.strip()
        return df
    except Exception:
        return pd.DataFrame(columns=["giocatore", "squadra", "posizione"])

@st.cache_data(ttl=300)
def load_titolari_infortuni():
    url = "https://raw.githubusercontent.com/fanta-ai-coder/fanta-ai-etl/refs/heads/main/titolari_infortuni"
    try:
        df = pd.read_csv(url)
        df["nome_giocatore"] = df["nome_giocatore"].astype(str).str.upper().str.strip()
        df["squadra"] = df["squadra"].astype(str).str.upper().str.strip()
        df["titolarita"] = df["titolarita"].astype(str).str.lower().str.strip()
        df["squalificato"] = df["squalificato"].astype(str).str.lower().str.strip()
        df["infortunato"] = df["infortunato"].astype(str).str.lower().str.strip()
        df["desc_infortunio"] = df["desc_infortunio"].fillna("").astype(str).str.strip()
        return df
    except Exception:
        return pd.DataFrame(columns=["nome_giocatore", "squadra", "titolarita", "squalificato", "infortunato", "desc_infortunio"])

rigoristi_df = load_rigoristi()
punizioni_df = load_punizioni()
titolari_df = load_titolari_infortuni()

# --- RANKING: carica e cache ---
@st.cache_data(ttl=600)
def load_player_ranking():
    res = (
        supabase.table("player_ranking")
        .select("*")
        .eq("algorithm_version", "v3.0")
        .execute()
    )
    return {r["player_id"]: r for r in res.data}

ranking_data = load_player_ranking()

# ==========================================
# 3. STATISTICAL UTILITIES
# ==========================================

# (tutte le funzioni statistiche originali rimangono invariate e non riscritte per brevità)
# copy paste esatto da app_versione_finale.py originale...

# ==========================================
# 4. REUSABLE UI COMPONENTS
# ==========================================
ROLE_COLORS = {
    "P": {"bg": "rgba(245, 158, 11, 0.15)", "text": "#FBBF24", "border": "rgba(245, 158, 11, 0.4)", "label": "Portiere"},
    "D": {"bg": "rgba(59, 130, 246, 0.15)", "text": "#60A5FA", "border": "rgba(59, 130, 246, 0.4)", "label": "Difensore"},
    "C": {"bg": "rgba(16, 185, 129, 0.15)", "text": "#34D399", "border": "rgba(16, 185, 129, 0.4)", "label": "Centrocampista"},
    "A": {"bg": "rgba(239, 68, 68, 0.15)", "text": "#F87171", "border": "rgba(239, 68, 68, 0.4)", "label": "Attaccante"},
}

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

def render_section_header(title, subtitle=None):
    sub_html = f'<p style="color:#94A3B8; font-size:0.85rem; margin:0 0 16px 0;">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f"""
        <div style="margin-top: 24px; margin-bottom: 12px; border-left: 3px solid #10B981; padding-left: 12px;">
            <h3 style="color:#F8FAFC; font-size:1.15rem; font-weight:700; margin:0;">{title}</h3>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_kpi_card(title, value, subtext="", highlight=False):
    bg_color = "rgba(16, 185, 129, 0.08)" if highlight else "#111827"
    border_color = "rgba(16, 185, 129, 0.3)" if highlight else "rgba(255, 255, 255, 0.07)"
    val_color = "#10B981" if highlight else "#F8FAFC"
    st.markdown(
        f"""
        <div style="background:{bg_color}; border:1px solid {border_color}; border-radius:12px; padding:16px;
                    display:flex; flex-direction:column; justify-content:space-between; height:100%;">
            <span style="font-size:0.8rem; font-weight:600; color:#94A3B8; text-transform:uppercase; letter-spacing:0.05em;">{title}</span>
            <span style="font-size:1.75rem; font-weight:800; color:{val_color}; margin:6px 0;">{value}</span>
            <span style="font-size:0.75rem; color:#64748B;">{subtext}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_quote_hero_card(quota, fvm, ranking=None):
    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,#111827 0%,#1E293B 100%);
                    border:1px solid rgba(16,185,129,0.4);
                    border-radius:16px; padding:20px;
                    box-shadow:0 10px 25px -5px rgba(0,0,0,0.5),0 0 15px rgba(16,185,129,0.15);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <span style="color:#94A3B8; font-size:0.85rem; font-weight:600;">VALUTAZIONI ASTA</span>
                <span style="background:rgba(16,185,129,0.2); color:#34D399; font-size:0.75rem; font-weight:700;
                             padding:2px 8px; border-radius:9999px; border:1px solid rgba(16,185,129,0.3);">⭐ GUIDA ASTA</span>
            </div>
            <div style="display:flex; gap:20px; align-items:baseline;">
                <div>
                    <div style="color:#64748B; font-size:0.75rem; text-transform:uppercase;">Quotazione</div>
                    <div style="color:#F8FAFC; font-size:2rem; font-weight:800;">{quota} <span style="font-size:1rem; color:#64748B;">FM</span></div>
                </div>
                <div style="border-left:1px solid rgba(255,255,255,0.1); padding-left:20px;">
                    <div style="color:#64748B; font-size:0.75rem; text-transform:uppercase;">FVM Consigliato</div>
                    <div style="color:#10B981; font-size:2rem; font-weight:800;">{fvm} <span style="font-size:1rem; color:#10B981;">FM</span></div>
                </div>
            </div>
        """,
        unsafe_allow_html=True,
    )
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
            <div style="font-family: monospace; margin-top: 16px; color:#F8FAFC;">
                <div style="display:flex; justify-content:space-between; font-weight:bold; font-size:1rem;">
                    <div>👑 RANKING ASTA V3</div>
                    <div style="color:{color};">{indice_finale:.1f}/100</div>
                </div>
                <div style="font-size:0.75rem; color:#94A3B8; margin-bottom:10px;">
                    100 = migliore del listone
                </div>
                <div style="display:flex; justify-content:space-between; font-family: monospace; font-weight:600;">
                    <div>#{rank_generale} / {totale_generale} generale</div>
                    <div>#{rank_ruolo} / {totale_ruolo} {ruolo_nome}</div>
                </div>
            </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 5. PLAYER DETAIL VIEW
# ==========================================
def render_player_detail(player_id, stats, quotations):
    try:
        player_id = int(float(player_id))
    except Exception:
        st.error(f"Player ID non valido: {player_id}")
        return

    p_quotes = quotations[quotations["player_id"] == player_id].copy()
    current_quote = get_latest_quote_row(p_quotes)
    p_stats = stats[stats["player_id"] == player_id].copy()

    if current_quote is not None:
        nome = current_quote.get("nome", "Giocatore")
        ruolo = str(current_quote.get("ruolo", "-")).upper().strip()
        squadra = current_quote.get("squadra", "-")
    elif not p_stats.empty:
        nome = p_stats.iloc[-1].get("nome", "Giocatore")
        ruolo = str(p_stats.iloc[-1].get("ruolo", "-")).upper().strip()
        squadra = p_stats.iloc[-1].get("squadra", "-")
    else:
        nome, ruolo, squadra = "Giocatore", "-", "-"

    nome_upper = str(nome).upper().strip()
    squadra_upper = str(squadra).upper().strip()

    # Lookup dati aggiuntivi (rigoristi, punizioni, titolari) rimangono inalterate...

    header_col1, header_col2 = st.columns([2.5, 1.5])
    with header_col1:
        st.markdown(
            f'<h1 style="font-size:2.2rem; font-weight:800; color:#F8FAFC; margin:0 0 8px 0;">{html.escape(str(nome))}</h1>',
            unsafe_allow_html=True,
        )
        # ... codice badge rimanente senza modifiche ...
    with header_col2:
        quota_val = current_quote.get("quotazione_attuale", "-") if current_quote is not None else "-"
        fvm_val = current_quote.get("fvm", "-") if current_quote is not None else "-"
        ranking = ranking_data.get(player_id)
        render_quote_hero_card(quota_val, fvm_val, ranking)

    # Il resto della funzione render_player_detail rimane identico all’originale,
    # non modificato qui per brevità.

# ==========================================
# 6. APP CONTROLLER & MAIN UI
# ==========================================

try:
    df = load_stats()
    quot = load_quotazioni()
except Exception as e:
    st.error(f"❌ Errore nel caricamento dei dati: {e}")
    st.stop()

if df.empty or quot.empty:
    st.warning("⚠️ Tabelle statistiche o quotazioni vuote.")
    st.stop()

# Normalizzazione, filtro dati e filtraggio giocatori sono invariati...
df = normalize_dataframe(df)
quot = normalize_dataframe(quot)
df = remove_starred_vote_rows(df)

latest_s = get_latest_season(quot)
current_quot = quot[quot["stagione"].astype(str).str.strip() == str(latest_s).strip()].copy() if latest_s else quot.copy()

# UI header e filtri rimangono identici...

col_players, col_detail = st.columns([0.9, 3.1], gap="medium")

with col_players:
    # Lista giocatori e selezione identica all’originale
    st.markdown(f'<div style="font-size:0.85rem; font-weight:700; color:#94A3B8; margin-bottom:8px;">GIOCATORI ({len(current_quot)})</div>', unsafe_allow_html=True)

    if current_quot.empty:
        st.info("Nessun giocatore trovato con questi filtri.")
        selected_id = None
    else:
        options_df = current_quot.drop_duplicates(subset="player_id").copy()
        labels, ids = [], []
        for row in options_df.itertuples():
            n = getattr(row, "nome", "Giocatore")
            s = getattr(row, "squadra", "-")
            pid = getattr(row, "player_id")
            lbl = f"{n} [{s}]"
            if lbl in labels:
                lbl = f"{lbl} #{int(pid)}"
            labels.append(lbl)
            ids.append(int(pid))

        label_to_id = dict(zip(labels, ids))

        radio_key = "player_radio"
        prev_label = st.session_state.get(radio_key)
        if prev_label not in labels:
            default_idx = 0
            if "active_player_id" in st.session_state and st.session_state["active_player_id"] in ids:
                default_idx = ids.index(st.session_state["active_player_id"])
            st.session_state[radio_key] = labels[default_idx]

        selected_label = st.radio(
            "Seleziona giocatore",
            options=labels,
            key=radio_key,
            label_visibility="collapsed",
        )
        selected_id = label_to_id.get(selected_label)
        st.session_state["active_player_id"] = selected_id

with col_detail:
    if selected_id is None:
        st.info("👈 Seleziona un giocatore dalla lista a sinistra per visualizzare la scheda analitica.")
    else:
        render_player_detail(selected_id, df, quot)
