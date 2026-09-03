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

# ================================
# 3. STATISTICAL UTILITIES
# (funzioni identiche come nel file originale)
# ================================
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

def safe_sum(df, column):
    if column not in df.columns:
        return 0.0
    return float(numeric_series(df, column).fillna(0).sum())

def safe_mean(df, column):
    if column not in df.columns:
        return 0.0
    values = numeric_series(df, column).dropna()
    return float(values.mean()) if not values.empty else 0.0

def safe_variance(df, column):
    if column not in df.columns:
        return None
    values = numeric_series(df, column).dropna()
    if len(values) < 2:
        return None
    val = values.var(ddof=1)
    return None if pd.isna(val) else float(val)

def format_number(value, decimals=2):
    return "N/D" if value is None or pd.isna(value) else f"{value:.{decimals}f}"

def remove_starred_vote_rows(df):
    if df.empty or "voto" not in df.columns:
        return df.copy()
    raw_vote = df["voto"].astype(str).str.strip()
    starred = raw_vote.str.contains(r"\*", regex=True, na=False)
    return df.loc[~starred].copy() if starred.any() else df.copy()

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
    penalty_saved = pd.Series(0.0, index=result.index)
    gol_subiti = pd.Series(0.0, index=result.index)

    for c in ["pi", "porta_inviolata", "clean_sheet", "imbattuto"]:
        if c in result.columns:
            clean_sheet = numeric_series(result, c).fillna(0)
            break
    for c in ["rp", "rigori_parati", "rigore_parato"]:
        if c in result.columns:
            penalty_saved = numeric_series(result, c).fillna(0)
            break
    for c in ["gs", "gol_subiti"]:
        if c in result.columns:
            gol_subiti = numeric_series(result, c).fillna(0)
            break

    if "ruolo" in result.columns:
        is_p = result["ruolo"].astype(str).str.strip().str.upper().eq("P")
        clean_sheet = clean_sheet.where(is_p, 0)
        gol_subiti = gol_subiti.where(is_p, 0)

    result["fanta_voto_calcolato"] = (
        voto + (gf * 3) + ass + (rf * 3) - (au * 2) - esp - (amm * 0.5) + clean_sheet + (penalty_saved * 3) - gol_subiti
    )
    result.loc[numeric_series(result, "voto").isna(), "fanta_voto_calcolato"] = float("nan")
    return result

def calculate_bonus_malus(df):
    res = calculate_fantavoto(df)
    res["bonus_malus"] = res["fanta_voto_calcolato"] - numeric_series(res, "voto")
    return res

def calculate_relative_metrics(p_stats, is_goalkeeper=False):
    seasons = p_stats["stagione"].dropna().astype(str).str.strip().nunique() if "stagione" in p_stats.columns else 0
    if seasons <= 0:
        return {
            "stagioni": 0, "presenze_medie": 0.0, "presenza_pct": 0.0,
            "gol_stagione": 0.0, "assist_stagione": 0.0, "rigori_segnati": 0.0,
            "rigori_sbagliati": 0.0, "ammonizioni": 0.0, "espulsioni": 0.0,
            "gs_stagione": 0.0, "rigori_parati": 0.0,
        }
    presenze_totali = numeric_series(p_stats, "voto").count()
    presenze_medie = presenze_totali / seasons
    presenza_pct = min(100.0, (presenze_medie / 38) * 100)

    if is_goalkeeper:
        gs_tot = safe_sum(p_stats, "gs")
        rp_tot = safe_sum(p_stats, "rp")
        gf_tot, rf_tot = 0, 0
    else:
        gf_tot = safe_sum(p_stats, "gf") + safe_sum(p_stats, "rf")
        rf_tot = safe_sum(p_stats, "rf")
        gs_tot, rp_tot = 0, 0

    return {
        "stagioni": seasons,
        "presenze_medie": presenze_medie,
        "presenza_pct": presenza_pct,
        "assist_stagione": safe_sum(p_stats, "ass") / seasons,
        "rigori_sbagliati": safe_sum(p_stats, "rs") / seasons,
        "ammonizioni": safe_sum(p_stats, "amm") / seasons,
        "espulsioni": safe_sum(p_stats, "esp") / seasons,
        "gol_stagione": gf_tot / seasons,
        "rigori_segnati": rf_tot / seasons,
        "gs_stagione": gs_tot / seasons,
        "rigori_parati": rp_tot / seasons,
    }

def varianza_gol_binaria(p_stats):
    gol_g = p_stats.groupby("giornata").apply(
        lambda df: 1 if (safe_sum(df, "gf") + safe_sum(df, "rf")) > 0 else 0
    )
    return 0.0 if len(gol_g) <= 1 else float(gol_g.var(ddof=1))

def season_sort_key(value):
    try:
        return int(str(value).strip().split("/")[0])
    except Exception:
        return -1

def build_rolling_data(player_stats, window=5):
    if player_stats.empty or any(c not in player_stats.columns for c in ["stagione", "giornata"]):
        return pd.DataFrame()
    res = player_stats.copy()
    res["giornata"] = pd.to_numeric(res["giornata"], errors="coerce")
    res = res[res["giornata"].notna()].copy()
    if res.empty:
        return pd.DataFrame()
    res["giornata"] = res["giornata"].astype(int)
    res["stagione"] = res["stagione"].astype(str).str.strip()
    res["_season_sort"] = res["stagione"].apply(season_sort_key)
    res = res.sort_values(["_season_sort", "giornata"]).reset_index(drop=True)
    res = calculate_fantavoto(res)
    if "voto" in res.columns:
        res["voto"] = pd.to_numeric(res["voto"], errors="coerce")
        res["media_mobile_voto"] = res.groupby("stagione", sort=False)["voto"].transform(
            lambda x: x.rolling(window=window, min_periods=1).mean()
        )
    res["media_mobile_fanta"] = res.groupby("stagione", sort=False)["fanta_voto_calcolato"].transform(
        lambda x: x.rolling(window=window, min_periods=1).mean()
    )
    res["periodo"] = res["stagione"] + " G" + res["giornata"].astype(str)
    return res

def get_latest_season(df):
    if df.empty or "stagione" not in df.columns:
        return None
    seasons = df["stagione"].dropna().astype(str).str.strip()
    seasons = seasons[seasons != ""]
    return max(seasons.unique(), key=season_sort_key) if not seasons.empty else None

def get_latest_quote_row(player_quotes):
    if player_quotes.empty:
        return None
    res = player_quotes.copy()
    if "stagione" in res.columns:
        res["_season_sort"] = res["stagione"].apply(season_sort_key)
        res = res.sort_values("_season_sort")
    return res.iloc[-1]

# ==========================================
# 4. REUSABLE UI COMPONENTS
# ==========================================
ROLE_COLORS = {
    "P": {"bg": "rgba(245, 158, 11, 0.15)", "text": "#FBBF24", "border": "rgba(245, 158, 11, 0.4)", "label": "Portiere"},
    "D": {"bg": "rgba(59, 130, 246, 0.15)", "text": "#60A5FA", "border": "rgba(59, 130, 246, 0.4)", "label": "Difensore"},
    "C": {"bg": "rgba(16, 185, 129, 0.15)", "text": "#34D399", "border": "rgba(16, 185, 129, 0.4)", "label": "Centrocampista"},
    "A": {"bg": "rgba(239, 68, 68, 0.15)", "text": "#F87171", "border": "rgba(239, 68, 68, 0.4)", "label": "Attaccante"},
}

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
                <div style="font-weight:bold; font-size:1.1rem; margin-bottom:4px;">👑 RANKING ASTA V3</div>
                <div style="font-weight:bold; font-size:1.5rem; color:{color}; margin-bottom:6px;">{indice_finale:.1f}/100</div>
                <div style="font-size:0.9rem; color:#94A3B8; margin-bottom:12px;">
                    100 = migliore del listone
                </div>
                <div style="display:flex; justify-content:flex-start; gap:20px; font-family: monospace; font-weight:600; font-size:1rem;">
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
        player_id_int = int(float(player_id))
    except Exception:
        st.error(f"Player ID non valido: {player_id}")
        return

    p_quotes = quotations[quotations["player_id"] == player_id_int].copy()
    current_quote = get_latest_quote_row(p_quotes)
    p_stats = stats[stats["player_id"] == player_id_int].copy()

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

    rigor_info = rigoristi_df[(rigoristi_df["giocatore"] == nome_upper) & (rigoristi_df["squadra"] == squadra_upper)]
    puniz_info = punizioni_df[(punizioni_df["giocatore"] == nome_upper) & (punizioni_df["squadra"] == squadra_upper)]
    titolare_info = titolari_df[(titolari_df["nome_giocatore"] == nome_upper) & (titolari_df["squadra"] == squadra_upper)]

    role_meta = ROLE_COLORS.get(ruolo, {"bg": "#374151", "text": "#E5E7EB", "border": "#4B5563", "label": ruolo})

    # ── Badge riga 1: ruolo, squadra, rigorista, punizioni ──
    badge_html = f"""
    <span style="background:{role_meta['bg']}; color:{role_meta['text']}; border:1px solid {role_meta['border']};
                 padding:4px 10px; border-radius:8px; font-weight:700; font-size:0.85rem; margin-right:6px;">
        {ruolo} — {role_meta['label']}
    </span>
    <span style="background:rgba(255,255,255,0.06); color:#CBD5E1; padding:4px 10px; border-radius:8px;
                 font-weight:600; font-size:0.85rem; margin-right:6px;">
        🛡️ {html.escape(str(squadra))}
    </span>
    """
    if not rigor_info.empty:
        pos_r = int(rigor_info["posizione"].values[0])
        badge_html += f'<span style="background:rgba(239,68,68,0.15); color:#FCA5A5; border:1px solid rgba(239,68,68,0.3); padding:4px 10px; border-radius:8px; font-weight:600; font-size:0.85rem; margin-right:6px;">🎯 Rigorista #{pos_r}</span>'
    if not puniz_info.empty:
        pos_p = int(puniz_info["posizione"].values[0])
        badge_html += f'<span style="background:rgba(147,51,234,0.15); color:#D8B4FE; border:1px solid rgba(147,51,234,0.3); padding:4px 10px; border-radius:8px; font-weight:600; font-size:0.85rem; margin-right:6px;">⚡ Punizioni #{pos_p}</span>'

    # ── Badge riga 2: titolarità, squalifica, infortunio ──
    status_html = ""
    if not titolare_info.empty:
        row = titolare_info.iloc[0]
        tit = row.get("titolarita", "")
        squalificato = str(row.get("squalificato", "no")).lower()
        infortunato = str(row.get("infortunato", "no")).lower()
        desc = str(row.get("desc_infortunio", "")).strip()

        if squalificato == "si":
            status_html += '<span style="background:rgba(239,68,68,0.2); color:#F87171; border:1px solid rgba(239,68,68,0.4); padding:4px 10px; border-radius:8px; font-weight:700; font-size:0.82rem; margin-right:6px;">🟥 Squalificato</span>'
        elif infortunato == "si":
            tooltip = f' title="{html.escape(desc)}"' if desc else ""
            status_html += f'<span{tooltip} style="background:rgba(234,179,8,0.15); color:#FDE047; border:1px solid rgba(234,179,8,0.35); padding:4px 10px; border-radius:8px; font-weight:700; font-size:0.82rem; margin-right:6px; cursor:help;">🤕 Infortunato{" — " + html.escape(desc[:40]) + ("…" if len(desc) > 40 else "") if desc else ""}</span>'
        elif tit == "titolare":
            status_html += '<span style="background:rgba(16,185,129,0.15); color:#34D399; border:1px solid rgba(16,185,129,0.3); padding:4px 10px; border-radius:8px; font-weight:700; font-size:0.82rem; margin-right:6px;">✅ Titolare</span>'
        elif tit == "panchina":
            status_html += '<span style="background:rgba(100,116,139,0.2); color:#94A3B8; border:1px solid rgba(100,116,139,0.3); padding:4px 10px; border-radius:8px; font-weight:700; font-size:0.82rem; margin-right:6px;">🪑 Panchina</span>'

    header_col1, header_col2 = st.columns([2.5, 1.5])
    with header_col1:
        st.markdown(
            f'<h1 style="font-size:2.2rem; font-weight:800; color:#F8FAFC; margin:0 0 8px 0;">{html.escape(str(nome))}</h1>',
            unsafe_allow_html=True
        )
        st.markdown(
            f'<div style="display:flex; flex-wrap:wrap; gap:6px; margin-bottom:6px;">{badge_html}</div>',
            unsafe_allow_html=True
        )
        if status_html:
            st.markdown(
                f'<div style="display:flex; flex-wrap:wrap; gap:6px; margin-bottom:12px;">{status_html}</div>',
                unsafe_allow_html=True
            )
    with header_col2:
        quota_val = current_quote.get("quotazione_attuale", "-") if current_quote is not None else "-"
        fvm_val = current_quote.get("fvm", "-") if current_quote is not None else "-"
        ranking = ranking_data.get(player_id_int)
        render_quote_hero_card(quota_val, fvm_val, ranking)

    # ... resto della funzione invariato ...

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

df = normalize_dataframe(df)
quot = normalize_dataframe(quot)
df = remove_starred_vote_rows(df)

latest_s = get_latest_season(quot)
current_quot = quot[quot["stagione"].astype(str).str.strip() == str(latest_s).strip()].copy() if latest_s else quot.copy()

st.markdown("""
<div style="display:flex; align-items:center; justify-content:space-between; padding:12px 0 20px 0;
            border-bottom:1px solid rgba(255,255,255,0.08); margin-bottom:20px;">
    <div style="display:flex; align-items:center; gap:12px;">
        <span style="font-size:2rem;">⚽</span>
        <div>
            <h2 style="margin:0; font-size:1.5rem; font-weight:800; color:#F8FAFC;">FantaAI Analytics</h2>
            <p style="margin:0; font-size:0.8rem; color:#94A3B8;">Design Intelligence & Decision Support per l'Asta</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

filter_col1, filter_col2 = st.columns([1, 2])
with filter_col1:
    selected_role = st.selectbox("Ruolo", ["Tutti", "P", "D", "C", "A"], label_visibility="collapsed")
with filter_col2:
    search_query = st.text_input("Cerca", placeholder="🔍 Cerca per nome giocatore o squadra...", label_visibility="collapsed")

quot_view = current_quot.copy()
if selected_role != "Tutti" and "ruolo" in quot_view.columns:
    quot_view = quot_view[quot_view["ruolo"].astype(str).str.upper().str.strip() == selected_role]
if search_query and "nome" in quot_view.columns:
    q = search_query.upper().strip()
    match_nome = quot_view["nome"].astype(str).str.upper().str.contains(q, na=False)
    match_squadra = quot_view["squadra"].astype(str).str.upper().str.contains(q, na=False) if "squadra" in quot_view.columns else False
    quot_view = quot_view[match_nome | match_squadra]
if "nome" in quot_view.columns:
    quot_view = quot_view.sort_values("nome", na_position="last")

col_players, col_detail = st.columns([0.9, 3.1], gap="medium")

with col_players:
    st.markdown(f'<div style="font-size:0.85rem; font-weight:700; color:#94A3B8; margin-bottom:8px;">GIOCATORI ({len(quot_view)})</div>', unsafe_allow_html=True)

    if quot_view.empty:
        st.info("Nessun giocatore trovato con questi filtri.")
        selected_id = None
    else:
        options_df = quot_view.drop_duplicates(subset="player_id").copy()
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
