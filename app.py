import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from supabase import create_client

# ==========================================
# 1. PAGE CONFIG & DESIGN SYSTEM (M3 DARK)
# ==========================================

st.set_page_config(
    page_title="FantaAI Analytics Pro — Dashboard",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

_CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

/* GLOBAL RESET */
html, body, [class*="css"], .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    background-color: #0B0F19 !important;
    color: #F8FAFC !important;
}

section.main, [data-testid="stMainBlockContainer"], [data-testid="stAppViewBlockContainer"] {
    background-color: #0B0F19 !important;
    padding-top: 1.5rem !important;
    padding-bottom: 2rem !important;
}

/* SCROLLBAR CUSTOM */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #334155; border-radius: 9999px; }
::-webkit-scrollbar-thumb:hover { background: #10B981; }

/* INPUT & SELECT */
.stTextInput input, .stSelectbox [data-baseweb="select"] {
    background-color: #111827 !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 8px !important;
    color: #F9FAFB !important;
    font-size: 0.85rem !important;
}

/* FILTRO RUOLI COLORATO (ORIZZONTALE) */
#role-filter-anchor + div[data-testid="stRadio"] label:nth-child(1) p { color: #FFFFFF !important; font-weight: 700 !important; }
#role-filter-anchor + div[data-testid="stRadio"] label:nth-child(2) p { color: #F59E0B !important; font-weight: 700 !important; }
#role-filter-anchor + div[data-testid="stRadio"] label:nth-child(3) p { color: #3B82F6 !important; font-weight: 700 !important; }
#role-filter-anchor + div[data-testid="stRadio"] label:nth-child(4) p { color: #10B981 !important; font-weight: 700 !important; }
#role-filter-anchor + div[data-testid="stRadio"] label:nth-child(5) p { color: #EF4444 !important; font-weight: 700 !important; }

/* CARDS & PANELS */
.glass-panel { background: #111827; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 20px; }
.top-header { background: #111827; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding: 12px 20px; border-radius: 12px; margin-bottom: 16px; }

/* ROSTER ITEM CARD CONTAINER */
.player-card {
    background: #111827;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 12px 14px;
    margin-bottom: 8px;
    transition: all 0.2s ease-in-out;
}
.player-card:hover {
    background: #161F33;
    border-color: rgba(16, 185, 129, 0.4);
}
.player-card.active {
    background: #182238;
    border: 1.5px solid #10B981;
    box-shadow: 0 0 12px rgba(16, 185, 129, 0.2);
}
</style>
"""

st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)


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
        response = (
            supabase.table(table_name)
            .select("*")
            .range(start, end)
            .execute()
        )
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
def load_ranking():
    try:
        return pd.DataFrame(fetch_all_rows("player_ranking"))
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
        return pd.DataFrame(
            columns=["nome_giocatore", "squadra", "titolarita", "squalificato", "infortunato", "desc_infortunio"]
        )


rigoristi_df = load_rigoristi()
punizioni_df = load_punizioni()
titolari_df = load_titolari_infortuni()


# ==========================================
# 3. STATISTICAL UTILITIES
# ==========================================

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


def remove_starred_vote_rows(df):
    if df.empty or "voto" not in df.columns:
        return df.copy()
    raw_vote = df["voto"].astype(str).str.strip()
    starred = raw_vote.str.contains(r"\*", regex=True, na=False)
    return df.loc[~starred].copy() if starred.any() else df.copy()


def season_sort_key(value):
    try:
        return int(str(value).strip().split("/")[0])
    except Exception:
        return -1


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


def get_player_ranking(ranking_df, player_id, stagione=None):
    if ranking_df.empty or "player_id" not in ranking_df.columns:
        return None
    ranking = ranking_df.copy()
    ranking["player_id"] = normalize_player_id_series(ranking["player_id"])
    try:
        pid = int(float(player_id))
    except Exception:
        return None

    ranking = ranking[ranking["player_id"] == pid].copy()
    if ranking.empty:
        return None

    if stagione is not None and "stagione" in ranking.columns:
        current = ranking[ranking["stagione"].astype(str).str.strip() == str(stagione).strip()].copy()
        if not current.empty:
            ranking = current

    if len(ranking) > 1:
        if "calculated_at" in ranking.columns:
            ranking["calculated_at"] = pd.to_datetime(ranking["calculated_at"], errors="coerce")
            ranking = ranking.sort_values("calculated_at")
        elif "stagione" in ranking.columns:
            ranking["_season_sort"] = ranking["stagione"].apply(season_sort_key)
            ranking = ranking.sort_values("_season_sort")

    return ranking.iloc[-1]


@st.cache_data(ttl=600)
def compute_player_summaries(stats_df, quot_df, ranking_df, titolari_df):
    if quot_df.empty:
        return quot_df.copy()

    base = quot_df.copy()
    base["player_id"] = normalize_player_id_series(base["player_id"])

    if not ranking_df.empty and "player_id" in ranking_df.columns:
        rdf = ranking_df.copy()
        rdf["player_id"] = normalize_player_id_series(rdf["player_id"])
        rank_cols = [
            "player_id", "indice_finale", "rank_ruolo", "totale_ruolo",
            "rank_generale", "totale_generale", "titolarita_score",
            "presenze_pesate", "forma_attuale_score", "performance_score"
        ]
        avail_rank_cols = [c for c in rank_cols if c in rdf.columns]
        rdf_unique = rdf.drop_duplicates(subset=["player_id"])[avail_rank_cols]
        base = pd.merge(base, rdf_unique, on="player_id", how="left")
    else:
        for c in ["indice_finale", "rank_ruolo", "totale_ruolo", "rank_generale", "totale_generale", "titolarita_score", "presenze_pesate"]:
            base[c] = None

    if not titolari_df.empty:
        tdf = titolari_df.copy()
        tdf["nome_norm"] = tdf["nome_giocatore"].astype(str).str.upper().str.strip()
        tdf["squadra_norm"] = tdf["squadra"].astype(str).str.upper().str.strip()

        base["nome_norm"] = base["nome"].astype(str).str.upper().str.strip()
        base["squadra_norm"] = base["squadra"].astype(str).str.upper().str.strip()

        tdf_unique = tdf.drop_duplicates(subset=["nome_norm", "squadra_norm"])
        base = pd.merge(
            base,
            tdf_unique[["nome_norm", "squadra_norm", "titolarita", "squalificato", "infortunato"]],
            on=["nome_norm", "squadra_norm"],
            how="left"
        )
        base["is_titolare"] = base["titolarita"].astype(str).str.lower().str.strip() == "titolare"
    else:
        base["is_titolare"] = False

    if not stats_df.empty and "player_id" in stats_df.columns:
        sdf = stats_df.copy()
        sdf["player_id"] = normalize_player_id_series(sdf["player_id"])

        voto = pd.to_numeric(sdf["voto"], errors="coerce")
        gf = pd.to_numeric(sdf.get("gf", 0), errors="coerce").fillna(0)
        rf = pd.to_numeric(sdf.get("rf", 0), errors="coerce").fillna(0)
        ass = pd.to_numeric(sdf.get("ass", 0), errors="coerce").fillna(0)
        au = pd.to_numeric(sdf.get("au", 0), errors="coerce").fillna(0)
        esp = pd.to_numeric(sdf.get("esp", 0), errors="coerce").fillna(0)
        amm = pd.to_numeric(sdf.get("amm", 0), errors="coerce").fillna(0)
        gs = pd.to_numeric(sdf.get("gs", 0), errors="coerce").fillna(0)
        rp = pd.to_numeric(sdf.get("rp", 0), errors="coerce").fillna(0)

        clean_sheet = pd.Series(0.0, index=sdf.index)
        for c in ["pi", "porta_inviolata", "clean_sheet", "imbattuto"]:
            if c in sdf.columns:
                clean_sheet = pd.to_numeric(sdf[c], errors="coerce").fillna(0)
                break

        fv = voto + (gf * 3) + ass + (rf * 3) - (au * 2) - esp - (amm * 0.5) + clean_sheet + (rp * 3) - gs
        sdf["_fanta_calc"] = fv
        sdf["_voto_num"] = voto

        valid = sdf[voto.notna()]
        agg = valid.groupby("player_id").agg(
            presenze_totali=("_voto_num", "count"),
            fantamedia=("_fanta_calc", "mean"),
            media_voto=("_voto_num", "mean")
        ).reset_index()

        base = pd.merge(base, agg, on="player_id", how="left")
    else:
        base["presenze_totali"] = 0
        base["fantamedia"] = None
        base["media_voto"] = None

    base["presenze_totali"] = base["presenze_totali"].fillna(0).astype(int)
    return base


# ==========================================
# 4. APP TOP BARS & HEADERS
# ==========================================

st.markdown("""
<div class="top-header" style="display: flex; align-items: center; justify-content: space-between;">
    <div style="display: flex; align-items: center; gap: 12px;">
        <div style="background: #10B981; color: #0B0F19; border-radius: 8px; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; font-weight: 800;">
            ⚡
        </div>
        <div>
            <div style="font-weight: 800; font-size: 1.1rem; color: #F8FAFC; letter-spacing: -0.02em;">
                FantaAI <span style="color: #34D399;">Analytics Pro</span>
            </div>
            <div style="font-size: 0.72rem; color: #94A3B8;">SERIE A 2024/25 — ASTA LIVE READY</div>
        </div>
    </div>
    <div style="display: flex; align-items: center; gap: 16px;">
        <div style="background: rgba(255,255,255,0.05); padding: 6px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08); text-align: right;">
            <div style="font-size: 0.65rem; color: #64748B;">BUDGET FANTAMEDIA</div>
            <div style="font-size: 0.85rem; font-weight: 700; color: #F8FAFC;">342 / 500 FM</div>
        </div>
        <div style="background: rgba(16, 185, 129, 0.1); padding: 6px 12px; border-radius: 8px; border: 1px solid rgba(16, 185, 129, 0.2); color: #34D399; font-size: 0.75rem; font-weight: 600;">
            ● Supabase Live
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ==========================================
# 5. DATA LOADING & FILTER PREPARATION
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

latest_s = get_latest_season(quot)
current_quot = quot[quot["stagione"].astype(str).str.strip() == str(latest_s).strip()].copy() if latest_s else quot.copy()

summary_df = compute_player_summaries(df, current_quot, ranking_df, titolari_df)


# ==========================================
# 6. MAIN MASTER-DETAIL LAYOUT
# ==========================================

col_roster, col_dossier = st.columns([0.35, 0.65], gap="medium")

# ------------------------------------------
# COLONNA SINISTRA: ROSTER & FILTRI
# ------------------------------------------
with col_roster:
    st.markdown("""
    <div style="margin-bottom: 12px;">
        <div style="font-size: 0.95rem; font-weight: 800; color: #F8FAFC;">🔍 FILTRI SCOUTING</div>
        <div style="font-size: 0.72rem; color: #64748B;">Trova e ordina i calciatori nel listone</div>
    </div>
    """, unsafe_allow_html=True)

    search_query = st.text_input("Ricerca", placeholder="Cerca giocatore o squadra...", label_visibility="collapsed")

    st.markdown('<div id="role-filter-anchor"></div>', unsafe_allow_html=True)
    
    selected_role = st.radio(
        "Seleziona Ruolo",
        ["Tutti", "P", "D", "C", "A"],
        horizontal=True,
        key="role_filter_btn"
    )

    squadre_raw = current_quot["squadra"].dropna().astype(str).str.strip().unique() if "squadra" in current_quot.columns else []
    squadre_list = ["Tutte"] + sorted(list(squadre_raw))

    c1, c2 = st.columns(2)
    with c1: selected_team = st.selectbox("Squadra", squadre_list, index=0)
    with c2: selected_sort = st.selectbox("Ordina per", ["👑 Indice Ranking", "⭐ Fantamedia", "🔤 Nome (A-Z)", "💰 Quotazione"], index=0)

    f1, f2 = st.columns([1.1, 1.9])
    with f1: only_titolari = st.checkbox("Solo Titolari", value=False)
    with f2: min_partite = st.slider("Partite minime", 0, 38, 0, step=1)

    st.markdown("<hr style='border-color: rgba(255,255,255,0.06); margin: 12px 0;'>", unsafe_allow_html=True)

    quot_view = summary_df.copy()

    if selected_role != "Tutti" and "ruolo" in quot_view.columns:
        quot_view = quot_view[quot_view["ruolo"].astype(str).str.upper().str.strip() == selected_role]
    if selected_team != "Tutte" and "squadra" in quot_view.columns:
        quot_view = quot_view[quot_view["squadra"].astype(str).str.upper().str.strip() == selected_team.upper().strip()]
    if search_query.strip():
        q = search_query.upper().strip()
        match_nome = quot_view["nome"].astype(str).str.upper().str.contains(q, na=False) if "nome" in quot_view.columns else False
        match_squadra = quot_view["squadra"].astype(str).str.upper().str.contains(q, na=False) if "squadra" in quot_view.columns else False
        quot_view = quot_view[match_nome | match_squadra]
    if only_titolari and "is_titolare" in quot_view.columns:
        quot_view = quot_view[quot_view["is_titolare"] == True]
    if min_partite > 0 and "presenze_totali" in quot_view.columns:
        quot_view = quot_view[quot_view["presenze_totali"] >= min_partite]

    if selected_sort == "👑 Indice Ranking":
        quot_view = quot_view.sort_values(by=["indice_finale", "quotazione_attuale", "nome"], ascending=[False, False, True], na_position="last")
    elif selected_sort == "⭐ Fantamedia":
        quot_view = quot_view.sort_values(by=["fantamedia", "presenze_totali", "nome"], ascending=[False, False, True], na_position="last")
    elif selected_sort == "🔤 Nome (A-Z)":
        quot_view = quot_view.sort_values(by=["nome"], ascending=[True], na_position="last")
    elif selected_sort == "💰 Quotazione":
        quot_view = quot_view.sort_values(by=["quotazione_attuale", "fvm", "nome"], ascending=[False, False, True], na_position="last")

    st.markdown(f"<div style='font-size: 0.75rem; color: #94A3B8; font-weight: 700; margin-bottom: 8px;'>ROSTER SELEZIONATO ({len(quot_view)})</div>", unsafe_allow_html=True)

    if quot_view.empty:
        st.info("Nessun giocatore trovato con questi filtri.")
        selected_id = None
    else:
        options_df = quot_view.drop_duplicates(subset="player_id").copy()

        role_colors = {"P": "#F59E0B", "D": "#3B82F6", "C": "#10B981", "A": "#EF4444"}
        role_names = {"P": "PORTIERI", "D": "DIFENSORI", "C": "CENTROCAMPO", "A": "ATTACCANTI"}

        if "active_player_id" not in st.session_state:
            st.session_state["active_player_id"] = int(options_df.iloc[0]["player_id"])

        with st.container(height=650):
            for row in options_df.itertuples():
                pid = int(getattr(row, "player_id"))
                n = getattr(row, "nome", "Giocatore")
                s = getattr(row, "squadra", "-")
                r = str(getattr(row, "ruolo", "")).upper().strip()
                ind = getattr(row, "indice_finale", None)
                fm = getattr(row, "fantamedia", None)
                pg = getattr(row, "presenze_totali", 0)
                q_att = getattr(row, "quotazione_attuale", 0)
                fvm = getattr(row, "fvm", 0)
                rk_r = getattr(row, "rank_ruolo", None)

                bg_role = role_colors.get(r, "#64748B")
                r_full_name = role_names.get(r, "GIOCATORI")
                ind_str = f"{float(ind):.1f}" if pd.notna(ind) else "N/D"
                fm_str = f"{float(fm):.2f}" if pd.notna(fm) else "N/D"
                rk_str = f"#{int(rk_r)} {r_full_name}" if pd.notna(rk_r) else ""

                n_norm, s_norm = str(n).upper().strip(), str(s).upper().strip()
                is_rig = not rigoristi_df[(rigoristi_df["giocatore"] == n_norm) & (rigoristi_df["squadra"] == s_norm)].empty
                is_pun = not punizioni_df[(punizioni_df["giocatore"] == n_norm) & (punizioni_df["squadra"] == s_norm)].empty

                badges_html = ""
                if is_rig:
                    badges_html += '<span style="background: rgba(239, 68, 68, 0.2); color: #FCA5A5; padding: 2px 6px; border-radius: 4px; font-size: 0.65rem; font-weight: 700;">🎯 Rigorista</span> '
                if is_pun:
                    badges_html += '<span style="background: rgba(245, 158, 11, 0.2); color: #FCD34D; padding: 2px 6px; border-radius: 4px; font-size: 0.65rem; font-weight: 700;">⚡ Punizioni</span> '

                is_active = (st.session_state["active_player_id"] == pid)
                active_class = "active" if is_active else ""

                card_html = f"""
                <div class="player-card {active_class}">
                    <div style="display: flex; align-items: center; justify-content: space-between; width: 100%;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <div style="background: {bg_role}; color: #FFFFFF; font-weight: 800; border-radius: 6px; width: 26px; height: 26px; display: flex; align-items: center; justify-content: center; font-size: 0.75rem;">
                                {r}
                            </div>
                            <div>
                                <div style="font-weight: 800; font-size: 0.95rem; color: #FFFFFF; line-height: 1.1;">{n}</div>
                                <div style="font-size: 0.7rem; color: #94A3B8; margin-top: 2px;">{s}</div>
                            </div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-weight: 800; font-size: 1.1rem; color: #34D399;">{ind_str}</div>
                            <div style="font-size: 0.62rem; color: #64748B; font-weight: 700; text-transform: uppercase;">{rk_str}</div>
                        </div>
                    </div>
                    <div style="display: flex; align-items: center; justify-content: space-between; font-size: 0.75rem; color: #CBD5E1; background: rgba(255,255,255,0.03); padding: 4px 8px; border-radius: 6px; margin-top: 6px;">
                        <div>FM: <b style="color: #34D399;">{fm_str}</b></div>
                        <div>PG: <b>{pg}</b></div>
                        <div>Q: <b>{q_att}</b></div>
                        <div>FVM: <b style="color: #F59E0B;">{fvm} FM</b></div>
                    </div>
                    {f'<div style="display: flex; gap: 4px; margin-top: 6px;">{badges_html}</div>' if badges_html else ''}
                </div>
                """

                st.markdown(card_html, unsafe_allow_html=True)
                if st.button(f"Seleziona {n}", key=f"btn_{pid}", use_container_width=True):
                    st.session_state["active_player_id"] = pid
                    st.rerun()

        selected_id = st.session_state.get("active_player_id")


# ------------------------------------------
# COLONNA DESTRA: DOSSIER ANALITICO
# ------------------------------------------
with col_dossier:
    if selected_id is None:
        st.info("👈 Seleziona un giocatore dalla lista a sinistra per aprire la scheda analitica.")
    else:
        player_id = int(float(selected_id))
        p_quotes = quot[quot["player_id"] == player_id].copy()
        current_quote = get_latest_quote_row(p_quotes)
        p_stats = df[df["player_id"] == player_id].copy()

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
        ranking_row = get_player_ranking(ranking_df, player_id)
        titolare_info = titolari_df[(titolari_df["nome_giocatore"] == nome_upper) & (titolari_df["squadra"] == squadra_upper)]

        titolarita_val, infortunato_val, desc_infortunio = "", "", ""
        if not titolare_info.empty:
            t_row = titolare_info.iloc[0]
            titolarita_val = str(t_row.get("titolarita", "")).lower().strip()
            infortunato_val = str(t_row.get("infortunato", "")).lower().strip()
            desc_infortunio = str(t_row.get("desc_infortunio", "")).strip()

        tags_html = ""
        if "titolare" in titolarita_val:
            tags_html += '<span style="background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3); padding: 4px 10px; border-radius: 9999px; font-size: 0.72rem; font-weight: 700; text-transform: uppercase;">🟢 Titolare</span> '
        elif "panchina" in titolarita_val or "riserva" in titolarita_val:
            tags_html += '<span style="background: rgba(245, 158, 11, 0.15); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.3); padding: 4px 10px; border-radius: 9999px; font-size: 0.72rem; font-weight: 700; text-transform: uppercase;">🟠 Panchina</span> '
        
        if infortunato_val in ["sì", "si", "true", "1", "yes"]:
            tags_html += '<span style="background: rgba(239, 68, 68, 0.15); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.3); padding: 4px 10px; border-radius: 9999px; font-size: 0.72rem; font-weight: 700; text-transform: uppercase;">🚑 Infortunato</span> '

        desc_html = ""
        if desc_infortunio and desc_infortunio.lower() != "nan":
            desc_html = f'<div style="font-size: 0.8rem; color: #FCA5A5; margin-top: 8px; font-weight: 600; background: rgba(239, 68, 68, 0.1); padding: 6px 12px; border-radius: 6px; display: inline-block;">⚠️ {desc_infortunio}</div>'

        rk_ruolo = int(ranking_row.get("rank_ruolo")) if ranking_row is not None and pd.notna(ranking_row.get("rank_ruolo")) else 1
        tot_ruolo = int(ranking_row.get("totale_ruolo")) if ranking_row is not None and pd.notna(ranking_row.get("totale_ruolo")) else 68
        quota_val = current_quote.get("quotazione_attuale", 38) if current_quote is not None else 38
        fvm_val = current_quote.get("fvm", 320) if current_quote is not None else 320

        header_html = f"""
        <div class="glass-panel">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                        <span style="background: #10B981; color: #0B0F19; font-weight: 800; font-size: 0.8rem; padding: 2px 8px; border-radius: 6px;">{ruolo}</span>
                        <span style="color: #94A3B8; font-size: 0.9rem; font-weight: 600;">{squadra}</span>
                    </div>
                    <h1 style="margin: 0; font-size: 2.2rem; font-weight: 800; color: #F8FAFC; letter-spacing: -0.03em;">{nome}</h1>
                    <div style="margin-top: 10px;">{tags_html}</div>
                    {desc_html}
                </div>
                <div style="text-align: right; background: rgba(255,255,255,0.03); padding: 12px 18px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.06);">
                    <div style="font-size: 0.7rem; color: #94A3B8; font-weight: 700; text-transform: uppercase;">RANKING RUOLO</div>
                    <div style="font-size: 1.8rem; font-weight: 800; color: #34D399; line-height: 1.2;">#{rk_ruolo} <span style="font-size: 0.9rem; color: #64748B;">/ {tot_ruolo}</span></div>
                    <div style="font-size: 0.75rem; color: #CBD5E1; margin-top: 4px;">Quotazione: <b>{quota_val}</b> | FVM: <b style="color: #F59E0B;">{fvm_val} FM</b></div>
                </div>
            </div>
        </div>
        """
        st.markdown(header_html, unsafe_allow_html=True)
