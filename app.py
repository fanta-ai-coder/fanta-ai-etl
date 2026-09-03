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
    url = "https://raw.githubusercontent.com/fanta-ai-coder
