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

# ... (qui va tutta la parte CSS presente nel tuo codice, per stile della pagina) ...

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

# Caricamenti dati
@st.cache_data(ttl=600)
def load_stats():
    return pd.DataFrame(fetch_all_rows("player_stats_history"))

@st.cache_data(ttl=600)
def load_quotazioni():
    return pd.DataFrame(fetch_all_rows("giocatori_quotazioni"))

@st.cache_data(ttl=600)
def load_ranking():
    try:
        ranking = pd.DataFrame(fetch_all_rows("player_ranking"))
        if ranking.empty:
            return ranking
        if "player_id" in ranking.columns:
            ranking["player_id"] = ranking["player_id"].astype(int)
        if "algorithm_version" in ranking.columns:
            ranking = ranking[
                ranking["algorithm_version"].astype(str).str.strip().str.lower() == "v3.0"
            ].copy()
        return ranking
    except Exception:
        return pd.DataFrame()

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

# ==========================================
# 3. STATISTICAL UTILITIES (estratti da tuo codice)
# ==========================================

def numeric_series(df, column):
    if column not in df.columns:
        return pd.Series(float("nan"), index=df.index, dtype="float64")
    return pd.to_numeric(df[column], errors="coerce")

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

def calculate_relative_metrics(p_stats, is_goalkeeper=False):
    # (copia la logica esistente...)
    seasons = p_stats["stagione"].dropna().astype(str).str.strip().nunique() if "stagione" in p_stats.columns else 0
    if seasons <= 0:
        return { "presenza_pct": 0.0, "presenze_medie": 0.0 }
    presenze_totali = numeric_series(p_stats, "voto").count()
    presenze_medie = presenze_totali / seasons
    presenza_pct = min(100.0, (presenze_medie / 38) * 100)
    return { "presenza_pct": presenza_pct, "presenze_medie": presenze_medie }

# ==========================================
# 4. UI COMPONENTS (estratti)
# ==========================================

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
    # Questo mostra la card con il ranking passandogli la riga ranking (puoi copiare il tuo html con stili)
    ranking_html = ""
    if ranking is not None:
        # Usa i dati ranking per formattare la card come vuoi (vedi messaggio precedente)
        # (Simplificato)
        ranking_html = f'<div style="padding-top:12px; border-top:1px solid #64748B;">Ranking: {ranking.get("indice_finale", "N/A"):.1f} / 100</div>'
    st.markdown(
        f'''
        <div style="background:#111827; border-radius:16px; padding:20px; border:1px solid rgba(16,185,129,0.4);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <span style="color:#94A3B8; font-size:0.85rem;">VALUTAZIONI ASTA</span>
                <span style="background:rgba(16,185,129,0.2); color:#34D399; font-size:0.75rem; font-weight:700; padding:2px 8px; border-radius:9999px; border:1px solid rgba(16,185,129,0.3);">⭐ GUIDA ASTA</span>
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
            {ranking_html}
        </div>
        ''',
        unsafe_allow_html=True,
    )

# ==========================================
# 5. PLAYER DETAIL VIEW
# ==========================================

def render_player_detail(player_id, stats, quotations, ranking=None):
    # (Qui il corpo della funzione)
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

    # Lookup dati aggiuntivi
    rigor_info = rigoristi_df[(rigoristi_df["giocatore"] == nome_upper) & (rigoristi_df["squadra"] == squadra_upper)]
    puniz_info = punizioni_df[(punizioni_df["giocatore"] == nome_upper) & (punizioni_df["squadra"] == squadra_upper)]
    titolare_info = titolari_df[(titolari_df["nome_giocatore"] == nome_upper) & (titolari_df["squadra"] == squadra_upper)]

    role_meta = ROLE_COLORS.get(ruolo, {"bg": "#374151", "text": "#E5E7EB", "border": "#4B5563", "label": ruolo})

    # Prepare badges...

    # Recupera riga ranking
    ranking_row = None
    if ranking is not None and not ranking.empty:
        rank_filtered = ranking[ranking["player_id"] == player_id]
        if not rank_filtered.empty:
            ranking_row = rank_filtered.iloc[0]

    # Visualizza header e badge (come nel tuo codice)...

    # Controlli su stats, rimozione starred, ecc...

    is_goalkeeper = (ruolo == "P")
    p_stats_hist = p_stats[p_stats["stagione"].astype(str).str.strip() != "2026-27"].copy() if "stagione" in p_stats.columns else p_stats.copy()
    if p_stats_hist.empty:
        p_stats_hist = p_stats.copy()

    rel = calculate_relative_metrics(p_stats_hist, is_goalkeeper=is_goalkeeper)
    media_voto = safe_mean(p_stats_hist, "voto")
    fantamedia = safe_mean(p_stats_hist, "fanta_voto_calcolato")
    varianza_bin = varianza_gol_binaria(p_stats_hist)
    varianza_v = safe_variance(p_stats_hist, "voto")

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi_card("Fantamedia", f"{fantamedia:.2f}", "Bonus/Malus inclusi", highlight=True)
    with k2:
        render_kpi_card("Media Voto Pura", f"{media_voto:.2f}", "Stabilità redazionale")
    with k3:
        render_kpi_card("% Presenze", f"{rel['presenza_pct']:.1f}%", f"{rel['presenze_medie']:.1f} partite / anno")
    with k4:
        if is_goalkeeper:
            render_kpi_card("Media GS / Stagione", f"{rel['gs_stagione']:.2f}", highlight=True)
        else:
            render_kpi_card("Gol Medi / Anno", f"{rel['gol_stagione']:.1f}", f"{rel['assist_stagione']:.1f} assist medi")

    st.markdown("<br>", unsafe_allow_html=True)
    if ranking_row is not None:
        render_kpi_card("Indice Affidabilità/Convenienza", f"{float(ranking_row.get('indice_finale', 0)):.3f}", highlight=True)

    #... Continua con seconda riga KPI, trend, storico ecc. come nel tuo codice ...

# ==========================================
# 6. MAIN UI
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
df = remove_starred_vote_rows(df)

latest_s = get_latest_season(quot)
current_quot = quot[quot["stagione"].astype(str).str.strip() == str(latest_s).strip()].copy() if latest_s else quot.copy()

ranking_current = ranking_df.copy()
if not ranking_current.empty and "stagione" in ranking_current.columns and latest_s:
    ranking_current = ranking_current[ranking_current["stagione"].astype(str).str.strip() == str(latest_s).strip()].copy()

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
        render_player_detail(selected_id, df, quot, ranking_current)
