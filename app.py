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

# [CSS omesso per brevità: rimane invariato rispetto al tuo codice originale]

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

rigoristi_df = load_rigoristi()
punizioni_df = load_punizioni()

# ==========================================
# 3. STATISTICAL UTILITIES
# ==========================================
# [tutte le funzioni sono quelle che hai già nel tuo codice originale:
# normalize_player_id_series, normalize_dataframe, numeric_series, safe_sum,
# safe_mean, safe_variance, format_number, remove_starred_vote_rows,
# calculate_fantavoto, calculate_bonus_malus, calculate_relative_metrics,
# varianza_gol_binaria, season_sort_key, build_rolling_data,
# get_latest_season, get_latest_quote_row]

# Le lascio uguali e non le riporto qui per brevità.

# ==========================================
# 4. REUSABLE UI COMPONENTS (UI/UX PRO MAX)
# ==========================================
# [role colors e funzioni di rendering UI: rimangono invariati]

# ==========================================
# 5. PLAYER DETAIL VIEW (modificata)
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

    nome_upper, squadra_upper = str(nome).upper().strip(), str(squadra).upper().strip()

    # Rigorista & Punizioni check
    rigor_info = rigoristi_df[(rigoristi_df["giocatore"] == nome_upper) & (rigoristi_df["squadra"] == squadra_upper)]
    puniz_info = punizioni_df[(punizioni_df["giocatore"] == nome_upper) & (punizioni_df["squadra"] == squadra_upper)]

    role_meta = ROLE_COLORS.get(ruolo, {"bg": "#374151", "text": "#E5E7EB", "border": "#4B5563", "label": ruolo})

    # Header Card
    badge_html = f"""
    <span style="background:{role_meta['bg']}; color:{role_meta['text']}; border:1px solid {role_meta['border']}; padding:4px 10px; border-radius:8px; font-weight:700; font-size:0.85rem; margin-right:8px;">
        {ruolo} — {role_meta['label']}
    </span>
    <span style="background:rgba(255,255,255,0.06); color:#CBD5E1; padding:4px 10px; border-radius:8px; font-weight:600; font-size:0.85rem; margin-right:8px;">
        🛡️ {html.escape(str(squadra))}
    </span>
    """
    if not rigor_info.empty:
        pos_r = int(rigor_info["posizione"].values[0])
        badge_html += f'<span style="background:rgba(239, 68, 68, 0.15); color:#FCA5A5; border:1px solid rgba(239, 68, 68, 0.3); padding:4px 10px; border-radius:8px; font-weight:600; font-size:0.85rem; margin-right:8px;">🎯 Rigorista #{pos_r}</span>'
    if not puniz_info.empty:
        pos_p = int(puniz_info["posizione"].values[0])
        badge_html += f'<span style="background:rgba(147, 51, 234, 0.15); color:#D8B4FE; border:1px solid rgba(147, 51, 234, 0.3); padding:4px 10px; border-radius:8px; font-weight:600; font-size:0.85rem;">⚡ Punizioni #{pos_p}</span>'

    header_col1, header_col2 = st.columns([2.5, 1.5])
    with header_col1:
        st.markdown(f'<h1 style="font-size: 2.2rem; font-weight: 800; color: #F8FAFC; margin: 0 0 8px 0;">{html.escape(str(nome))}</h1>', unsafe_allow_html=True)
        st.markdown(f'<div style="display:flex; flex-wrap:wrap; gap:6px; margin-bottom:12px;">{badge_html}</div>', unsafe_allow_html=True)

    with header_col2:
        quota_val = current_quote.get("quotazione_attuale", "-") if current_quote is not None else "-"
        fvm_val = current_quote.get("fvm", "-") if current_quote is not None else "-"
        render_quote_hero_card(quota_val, fvm_val)

    if p_stats.empty:
        st.info("ℹ️ Nessuna statistica storica disponibile per questo giocatore.")
        return

    if "stagione" in p_stats.columns:
        p_stats["stagione"] = p_stats["stagione"].astype(str).str.strip()
    if "giornata" in p_stats.columns:
        p_stats["giornata"] = pd.to_numeric(p_stats["giornata"], errors="coerce")

    p_stats = remove_starred_vote_rows(p_stats)
    if p_stats.empty:
        st.info("ℹ️ Nessuna prestazione valida registrata.")
        return

    # *** FILTRO PER ESCLUDERE LA STAGIONE 2026-27 DAL CALCOLO DELLE STATISTICHE ***
    p_stats_filtered = p_stats[p_stats["stagione"] != "2026-27"].copy()

    p_stats_filtered = calculate_bonus_malus(p_stats_filtered)
    is_goalkeeper = (ruolo == "P")

    # Bento Grid KPIs
    render_section_header("📊 Rendimento Complessivo", "Medie pesate e metriche chiave calcolate su tutte le stagioni (esclusa 2026-27)")
    
    rel = calculate_relative_metrics(p_stats_filtered, is_goalkeeper=is_goalkeeper)
    media_voto = safe_mean(p_stats_filtered, "voto")
    fantamedia = safe_mean(p_stats_filtered, "fanta_voto_calcolato")
    varianza_bin = varianza_gol_binaria(p_stats_filtered)
    varianza_v = safe_variance(p_stats_filtered, "voto")

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi_card("Fantamedia", f"{fantamedia:.2f}", "Bonus/Malus inclusi", highlight=True)
    with k2:
        render_kpi_card("Media Voto Pura", f"{media_voto:.2f}", "Stabilità redazionale")
    with k3:
        render_kpi_card("% Presenze", f"{rel['presenza_pct']:.1f}%", f"{rel['presenze_medie']:.1f} partite / anno")
    with k4:
        if is_goalkeeper:
            render_kpi_card("Goal Subiti / Anno", f"{rel['gs_stagione']:.1f}", f"{rel['rigori_parati']:.1f} rig. parati")
        else:
            render_kpi_card("Gol Medi / Anno", f"{rel['gol_stagione']:.1f}", f"{rel['assist_stagione']:.1f} assist medi")

    # Stability & Variance indicators
    render_section_header("🎯 Continuità & Analisi del Rischio")
    var_col1, var_col2, var_col3, var_col4 = st.columns(4)
    with var_col1:
        st.metric("Varianza Voto", format_number(varianza_v), help="Minore è il valore, più costante è il rendimento (valore < 0.5 = ottimo)")
    with var_col2:
        st.metric("Varianza Gol", format_number(varianza_bin), help="Frequenza con cui va a segno su più giornate diverse")
    with var_col3:
        st.metric("Ammonizioni / anno", f"{rel['ammonizioni']:.1f}", help="Media cartellini gialli a stagione")
    with var_col4:
        st.metric("Espulsioni / anno", f"{rel['espulsioni']:.1f}", help="Media cartellini rossi a stagione")

    # Form Trend Chart (Plotly with UI/UX Pro Max Theme)
    render_section_header("📈 Trend di Forma (Rolling 5 Giornate)", "Evoluzione della media mobile su voto puro vs fantavoto")
    rolling_df = build_rolling_data(p_stats_filtered, window=5)

    if not rolling_df.empty:
        fig = go.Figure()
        if "media_mobile_fanta" in rolling_df.columns:
            fig.add_trace(go.Scatter(
                x=rolling_df["periodo"],
                y=rolling_df["media_mobile_fanta"],
                mode="lines",
                name="Fantamedia (5G)",
                line=dict(color="#10B981", width=3, shape="spline"),
                fill="tozeroy",
                fillcolor="rgba(16, 185, 129, 0.08)",
                hovertemplate="<b>%{x}</b><br>Fantamedia: <b>%{y:.2f}</b><extra></extra>",
            ))
        if "media_mobile_voto" in rolling_df.columns:
            fig.add_trace(go.Scatter(
                x=rolling_df["periodo"],
                y=rolling_df["media_mobile_voto"],
                mode="lines",
                name="Media Voto (5G)",
                line=dict(color="#60A5FA", width=2, dash="dot", shape="spline"),
                hovertemplate="<b>%{x}</b><br>Media Voto: <b>%{y:.2f}</b><extra></extra>",
            ))

        # Sufficienza reference line
        fig.add_hline(y=6.0, line_dash="dash", line_color="rgba(255,255,255,0.2)", annotation_text="Sufficienza (6.0)", annotation_position="bottom right")

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(17, 24, 39, 0.6)",
            font=dict(family="Plus Jakarta Sans", color="#94A3B8"),
            hovermode="x unified",
            height=380,
            margin=dict(l=10, r=10, t=30, b=10),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                bgcolor="rgba(0,0,0,0)"
            ),
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)", showgrid=True),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)", showgrid=True, range=[4.5, 10]),
        )
        st.plotly_chart(fig, use_container_width=True)

    # Season Breakdown Table con stagione 2026-27 inclusa
    render_section_header("📅 Storico Dettagliato per Stagione")
    if "stagione" in p_stats.columns:
        rows = []
        for s, g in p_stats.groupby("stagione"):
            gfanta = calculate_fantavoto(g)
            rows.append({
                "Stagione": s,
                "Presenze": int(numeric_series(g, "voto").count()),
                "Media Voto": round(safe_mean(g, "voto"), 2),
                "Fantamedia": round(safe_mean(gfanta, "fanta_voto_calcolato"), 2),
                "Gol": int(safe_sum(g, "gf") + safe_sum(g, "rf")),
                "Assist": int(safe_sum(g, "ass")),
                "Amm": int(safe_sum(g, "amm")),
                "Esp": int(safe_sum(g, "esp")),
                "Malus/Bonus Medio": round(safe_mean(calculate_bonus_malus(g), "bonus_malus"), 2),
            })
        season_df = pd.DataFrame(rows)
        if not season_df.empty:
            season_df["_sort"] = season_df["Stagione"].apply(season_sort_key)
            season_df = season_df.sort_values("_sort", ascending=False).drop(columns="_sort")
            
            st.dataframe(
                season_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Fantamedia": st.column_config.NumberColumn(format="%.2f ⭐"),
                    "Media Voto": st.column_config.NumberColumn(format="%.2f"),
                    "Presenze": st.column_config.ProgressColumn(min_value=0, max_value=38, format="%d / 38"),
                }
            )

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
current_quot = quot[quot["stagione"].astype(str).str.strip() == str(latest_s).strip()] if latest_s else quot.copy()

# App Header
st.markdown("""
<div style="display: flex; align-items: center; justify-content: space-between; padding: 12px 0 20px 0; border-bottom: 1px solid rgba(255,255,255,0.08); margin-bottom: 20px;">
    <div style="display: flex; align-items: center; gap: 12px;">
        <span style="font-size: 2rem;">⚽</span>
        <div>
            <h2 style="margin: 0; font-size: 1.5rem; font-weight: 800; color: #F8FAFC;">FantaAI Analytics</h2>
            <p style="margin: 0; font-size: 0.8rem; color: #94A3B8;">Design Intelligence & Decision Support per l'Asta</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Search & Filter Bar
filter_col1, filter_col2 = st.columns([1, 2])
with filter_col1:
    selected_role = st.selectbox("Ruolo", ["Tutti", "P", "D", "C", "A"], label_visibility="collapsed")
with filter_col2:
    search_query = st.text_input("Cerca", placeholder="🔍 Cerca per nome giocatore o squadra...", label_visibility="collapsed")

# Filter View
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

# Main 2-Column Layout
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
            lbl = str(n)
            if lbl in labels:
                lbl = f"{lbl} ({s})"
            if lbl in labels:
                lbl = f"{lbl} #{int(pid)}"
            labels.append(lbl)
            ids.append(int(pid))
        
        label_to_id = dict(zip(labels, ids))

        # Recupera indice attivo per evitare salti
        current_idx = 0
        if "active_player_id" in st.session_state and st.session_state["active_player_id"] in ids:
            current_idx = ids.index(st.session_state["active_player_id"])

        selected_label = st.radio(
            "Seleziona giocatore",
            options=labels,
            index=current_idx,
            label_visibility="collapsed"
        )
        selected_id = label_to_id.get(selected_label)
        st.session_state["active_player_id"] = selected_id

with col_detail:
    if selected_id is None:
        st.info("👈 Seleziona un giocatore dalla lista a sinistra per visualizzare la scheda analitica.")
    else:
        render_player_detail(selected_id, df, quot)
