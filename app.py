import os
import html
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from supabase import create_client
from streamlit_elements import elements, mui

st.set_page_config(
    page_title="FantaAI Analytics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# CSS per tema scuro e allineamento card KPI a destra
st.markdown(
    """
    <style>
    .main {
        background-color: #121212;
        color: #E0E0E0;
    }
    .css-18e3th9 {
        background-color: #121212;
        color: #E0E0E0;
    }
    .stContainer > div {
        background-color: #1E1E1E;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 0 10px rgba(255,255,255,0.1);
    }
    h1, h2, h3, h4, h5, h6, .css-1v0mbdj, .css-hxt7ib {
        color: #FAFAFA;
    }
    a {
        color: #1F7A4D;
    }
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-thumb {
        background-color: #1F7A4D;
        border-radius: 10px;
    }
    .stRadio label {
        font-size: 18px !important;
        font-weight: 700 !important;
        color: #1F7A4D !important;
    }
    #scroll-list {
        max-height: 640px;
        overflow-y: auto;
        padding-right: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

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

def remove_starred_vote_rows(df):
    if df.empty or "voto" not in df.columns:
        return df.copy()
    raw_vote = df["voto"].astype(str).str.strip()
    mask = ~raw_vote.str.contains(r"\*", regex=True, na=False)
    return df.loc[mask].copy()

# --- Caricamento CSV rigoristi e punitori da GitHub ---

@st.cache_data(ttl=3600)
def load_rigoristi_csv():
    url = "https://raw.githubusercontent.com/fanta-ai-coder/fanta-ai-etl/main/rigoristi.csv"
    df = pd.read_csv(url, sep=',', skip_blank_lines=True, on_bad_lines='skip')
    df['giocatore_lc'] = df['giocatore'].str.lower()
    return df

@st.cache_data(ttl=3600)
def load_punizioni_csv():
    url = "https://raw.githubusercontent.com/fanta-ai-coder/fanta-ai-etl/main/punizioni.csv"
    df = pd.read_csv(url, sep=',', skip_blank_lines=True, on_bad_lines='skip')
    df['giocatore_lc'] = df['giocatore'].str.lower()
    return df

# Placeholder per funzioni esterne eventualmente usate (aggiungi le tue)
def calculate_bonus_malus(df): return df
def get_latest_quote_row(df): return df.iloc[-1] if not df.empty else None
def calculate_relative_metrics(p_stats, is_goalkeeper=False):
    return {"presenza_pct": 75.3, "presenze_medie": 28.5, "gol_stagione": 0, "gs_stagione":0,
            "rigori_parati":0, "rigori_segnati":0, "rigori_sbagliati":0, "assist_stagione":0,
            "ammonizioni":0, "espulsioni":0, "stagioni":1}
def varianza_gol_binaria(df): return 0.1
def safe_mean(df, col): return 6.5
def numeric_series(df, col): return pd.Series([6.5])  # Dummy implementation
def render_quote_card_with_elements(quota, fvm):
    with elements("quote_card"):
        mui.Card(
            sx={
                "width": 230,
                "padding": 1,
                "borderTop": "5px solid #1F7A4D",
                "borderRadius": "12px",
                "boxShadow": "0 4px 12px rgba(31, 122, 77, 0.4)",
                "position": "relative",
                "marginLeft": "-16px",
            },
            children=[
                mui.Box(
                    sx={
                        "position": "absolute",
                        "top": 8,
                        "right": 8,
                        "backgroundColor": "#1F7A4D",
                        "color": "white",
                        "padding": "4px 10px",
                        "borderRadius": "20px",
                        "fontWeight": "700",
                        "fontSize": "0.75rem",
                        "boxShadow": "0 2px 6px rgba(0,0,0,0.3)"
                    },
                    children="⭐ FVM"
                ),
                mui.CardContent(
                    sx={"paddingTop": 3},
                    children=[
                        mui.Typography("Quotazione attuale", variant="subtitle2", sx={"color": "#7C8794"}),
                        mui.Typography(str(quota), variant="h4", sx={"color": "#1F7A4D", "fontWeight": "700"}),
                        mui.Divider(sx={"marginY": 1}),
                        mui.Typography("Fantamilioni suggeriti", variant="caption", sx={"color": "#7C8794"}),
                        mui.Typography(str(fvm), variant="h6", sx={"fontWeight": "600"}),
                    ],
                ),
            ],
        )

def render_section_title(text):
    st.markdown(f"""
    <div style="
        border-radius: 10px;
        padding: 12px 20px;
        background: rgba(31, 122, 77, 0.15);
        color: #1F7A4D;
        font-weight: 700;
        font-size: 19px;
        margin-top: 32px;
        margin-bottom: 24px;
        border-left: 5px solid #1F7A4D;
    ">{text}</div>
    """, unsafe_allow_html=True)

def render_kpi(title, value):
    st.markdown(f"""
        <div style="
            background-color: #1F7A4DBB;
            padding: 20px 16px;
            border-radius: 14px;
            color: #FAFAFA;
            font-weight: 700;
            box-shadow: 0 8px 20px rgba(31, 122, 77, 0.4);
            text-align: center;
            max-width: 220px;
            margin-left: auto;
            margin-bottom: 16px;
        ">
            <div style="font-size: 1.1rem;">{title}</div>
            <div style="font-size: 1.8rem;">{value}</div>
        </div>
    """, unsafe_allow_html=True)

def render_player_detail(player_id, stats, quotations, rigoristi_df, punitori_df):

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
        ruolo = current_quote.get("ruolo", "-")
        squadra = current_quote.get("squadra", "-")
    elif not p_stats.empty:
        nome = p_stats.iloc[-1].get("nome", "Giocatore")
        ruolo = p_stats.iloc[-1].get("ruolo", "-")
        squadra = p_stats.iloc[-1].get("squadra", "-")
    else:
        nome = "Giocatore"
        ruolo = "-"
        squadra = "-"

    giocatore_lc = nome.lower()

    # Cerca se è rigorista
    rig_row = rigoristi_df[rigoristi_df["giocatore_lc"] == giocatore_lc]
    if not rig_row.empty:
        rig_status = f"Rigorista: si pos: {int(rig_row.iloc[0]['posizione'])}"
    else:
        rig_status = "Rigorista: no"

    # Cerca se è tiratore punizioni (calci piazzati)
    pun_row = punitori_df[punitori_df["giocatore_lc"] == giocatore_lc]
    if not pun_row.empty:
        pun_status = f"Calci piazzati: si pos: {int(pun_row.iloc[0]['posizione'])}"
    else:
        pun_status = "Calci piazzati: no"

    header_left, header_right = st.columns([2.6, 1])

    with header_left:
        st.markdown(f'<h1 style="font-weight:bold; font-size:2.5rem; margin-bottom:0.1rem;">{html.escape(str(nome))}</h1>', unsafe_allow_html=True)
        st.markdown(f'<div style="color:#7C8794; font-size:15px; margin-top:-10px; margin-bottom:4px;">{html.escape(str(squadra))} • {html.escape(str(ruolo))}</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="color:#7C8794; font-size:13px; margin-bottom:8px;">{rig_status} | {pun_status}</div>', unsafe_allow_html=True)

    with header_right:
        if current_quote is not None:
            quota = current_quote.get("quotazione_attuale", "-")
            fvm = current_quote.get("fvm", "-")
            try:
                quota_val = int(float(quota))
            except:
                quota_val = "-"
            try:
                fvm_val = int(float(fvm))
            except:
                fvm_val = "-"
            render_quote_card_with_elements(quota_val, fvm_val)

    if p_stats.empty:
        st.info("Non sono presenti statistiche storiche per questo giocatore.")
        return

    if "stagione" in p_stats.columns:
        p_stats["stagione"] = p_stats["stagione"].astype(str).str.strip()
    if "giornata" in p_stats.columns:
        p_stats["giornata"] = pd.to_numeric(p_stats["giornata"], errors="coerce")

    p_stats = remove_starred_vote_rows(p_stats)
    if p_stats.empty:
        st.info("Non ci sono prestazioni valide per questo giocatore.")
        return

    p_stats = calculate_bonus_malus(p_stats)

    is_goalkeeper = ruolo.upper() == "P"

    render_section_title("📊 Rendimento storico complessivo")

    relative = calculate_relative_metrics(p_stats, is_goalkeeper=is_goalkeeper)

    presenze = int(numeric_series(p_stats, "voto").count())
    media_voto = safe_mean(p_stats, "voto")
    fantamedia = safe_mean(p_stats, "fanta_voto_calcolato")

    varianza_binaria = varianza_gol_binaria(p_stats)
    varianza_voto = safe_variance(p_stats, "voto")

    # Card KPI migliorate allineate a destra
    with st.container():
        cols = st.columns(3, gap="small")
        kpi_styles = """
            background-color: #1F7A4DBB;
            padding: 20px 16px;
            border-radius: 14px;
            color: #FAFAFA;
            font-weight: 700;
            box-shadow: 0 8px 20px rgba(31, 122, 77, 0.4);
            text-align: center;
            max-width: 220px;
            margin-left: auto;
            margin-bottom: 16px;
        """
        with cols[0]:
            st.markdown(f'<div style="{kpi_styles} font-size: 1.1rem;">Presenza media</div>'
                        f'<div style="{kpi_styles} font-size: 1.8rem;">{relative["presenza_pct"]:.1f}%</div>', unsafe_allow_html=True)
        with cols[1]:
            st.markdown(f'<div style="{kpi_styles} font-size: 1.1rem;">Media voto</div>'
                        f'<div style="{kpi_styles} font-size: 1.8rem;">{media_voto:.2f}</div>', unsafe_allow_html=True)
        with cols[2]:
            st.markdown(f'<div style="{kpi_styles} font-size: 1.1rem;">Fantamedia</div>'
                        f'<div style="{kpi_styles} font-size: 1.8rem;">{fantamedia:.2f}</div>', unsafe_allow_html=True)

    # Qui puoi continuare con il resto del codice (grafici, tabelle, etc.)

# Caricamento dati e setup
try:
    df = load_stats()
    quot = load_quotazioni()
    rigoristi_df = load_rigoristi_csv()
    punitori_df = load_punizioni_csv()
except Exception as e:
    st.error("❌ Errore nel caricamento dati.")
    st.code(str(e))
    st.stop()

df = normalize_dataframe(df)
quot = normalize_dataframe(quot)

df = df[df["player_id"].notna()].copy()
quot = quot[quot["player_id"].notna()].copy()

df = remove_starred_vote_rows(df)

latest_season = get_latest_season(quot)
if latest_season is not None:
    current_quot = quot[quot["stagione"].astype(str).str.strip() == str(latest_season).strip()].copy()
else:
    current_quot = quot.copy()

st.title("⚽ FantaAI")

role_col, _ = st.columns([1, 3])
with role_col:
    selected_role = st.selectbox("Filtra per ruolo", ["Tutti", "P", "D", "C", "A"])

quot_view = current_quot.copy()
if selected_role != "Tutti" and "ruolo" in quot_view.columns:
    quot_view = quot_view[quot_view["ruolo"].astype(str).str.upper().str.strip() == selected_role]

if "nome" in quot_view.columns:
    quot_view = quot_view.sort_values("nome", na_position="last")

col_players, col_detail = st.columns([1, 3.2], gap="small")

with col_players:
    st.markdown("<h3 style='color:#1F7A4D; margin-bottom:8px;'>👥 Giocatori disponibili</h3>", unsafe_allow_html=True)
    st.markdown('<div id="scroll-list">', unsafe_allow_html=True)
    if quot_view.empty:
        st.info("Nessun giocatore trovato.")
        selected_id = None
    else:
        options_df = quot_view.drop_duplicates(subset="player_id").copy()
        labels = []
        ids = []
        for row in options_df.itertuples():
            nome_row = getattr(row, "nome", "Giocatore")
            squadra_row = getattr(row, "squadra", "-")
            player_id_row = getattr(row, "player_id")
            label = f"{nome_row} • {squadra_row}"
            if label in labels:
                label = f"{label} • ID {int(player_id_row)}"
            labels.append(label)
            ids.append(int(player_id_row))

        label_to_id = dict(zip(labels, ids))

        selected_label = st.radio("Seleziona giocatore", options=labels, label_visibility="collapsed")
        selected_id = label_to_id[selected_label]
    st.markdown("</div>", unsafe_allow_html=True)

with col_detail:
    if selected_id is None:
        st.info("Seleziona un giocatore.")
    else:
        render_player_detail(selected_id, df, quot, rigoristi_df, punitori_df)
