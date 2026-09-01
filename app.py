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
    initial_sidebar_state="expanded",
)

# CSS tema scuro migliorato e stili lista giocatori
st.markdown("""
    <style>
    body, .main {
        background-color: #121212 !important;
        color: #E0E0E0 !important;
    }
    .stContainer > div {
        background-color: #1E1E1E !important;
        border-radius: 12px !important;
        padding: 16px !important;
        box-shadow: 0 0 10px rgba(255,255,255,0.1) !important;
    }
    h1, h2, h3, h4, h5, h6, .css-1v0mbdj, .css-hxt7ib {
        color: #FAFAFA !important;
    }
    a {
        color: #1F7A4D !important;
    }
    ::-webkit-scrollbar {
        width: 8px; height: 8px;
    }
    ::-webkit-scrollbar-thumb {
        background-color: #1F7A4D;
        border-radius: 10px;
    }
    #scroll-list {
        max-height: 640px; overflow-y: auto; padding-right: 8px;
    }
    .player-label {
        font-size: 18px;
        font-weight: 700;
        color: #1F7A4D;
        margin-bottom: 4px;
    }
    </style>
""", unsafe_allow_html=True)

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
    df = pd.read_csv(url)
    df["giocatore"] = df["giocatore"].str.upper().str.strip()
    df["squadra"] = df["squadra"].str.upper().str.strip()
    return df

@st.cache_data(ttl=600)
def load_punizioni():
    url = "https://raw.githubusercontent.com/fanta-ai-coder/fanta-ai-etl/refs/heads/main/punizioni.csv"
    df = pd.read_csv(url)
    df["giocatore"] = df["giocatore"].str.upper().str.strip()
    df["squadra"] = df["squadra"].str.upper().str.strip()
    return df

rigoristi_df = load_rigoristi()
punizioni_df = load_punizioni()

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
    values = numeric_series(df, column).fillna(0)
    return float(values.sum())

def safe_mean(df, column):
    if column not in df.columns:
        return 0.0
    values = numeric_series(df, column).dropna()
    if values.empty:
        return 0.0
    return float(values.mean())

def safe_variance(df, column):
    if column not in df.columns:
        return None
    values = numeric_series(df, column).dropna()
    if len(values) < 2:
        return None
    value = values.var(ddof=1)
    if pd.isna(value):
        return None
    return float(value)

def format_number(value, decimals=2):
    if value is None or pd.isna(value):
        return "N/D"
    return f"{value:.{decimals}f}"

def remove_starred_vote_rows(df):
    if df.empty or "voto" not in df.columns:
        return df.copy()
    result = df.copy()
    raw_vote = result["voto"].astype(str).str.strip()
    starred = raw_vote.str.contains(r"\*", regex=True, na=False)
    if starred.any():
        result = result.loc[~starred].copy()
    return result

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

    # clean_sheet, penalty_saved, gol_subiti calculation with fallback
    clean_sheet = pd.Series(0.0, index=result.index)
    penalty_saved = pd.Series(0.0, index=result.index)
    gol_subiti = pd.Series(0.0, index=result.index)
    for col in ["pi", "porta_inviolata", "clean_sheet", "imbattuto"]:
        if col in result.columns:
            clean_sheet = numeric_series(result, col).fillna(0)
            break
    for col in ["rp", "rigori_parati", "rigore_parato"]:
        if col in result.columns:
            penalty_saved = numeric_series(result, col).fillna(0)
            break
    for col in ["gs", "gol_subiti"]:
        if col in result.columns:
            gol_subiti = numeric_series(result, col).fillna(0)
            break

    is_goalkeeper = False
    if "ruolo" in result.columns:
        is_goalkeeper = result["ruolo"].astype(str).str.strip().str.upper() == "P"
        clean_sheet = clean_sheet.where(is_goalkeeper, 0)
        gol_subiti = gol_subiti.where(is_goalkeeper, 0)

    result["fanta_voto_calcolato"] = (
        voto
        + gf * 3
        + ass
        + rf * 3
        - au * 2
        - esp
        - amm * 0.5
        + clean_sheet
        + penalty_saved * 3
        - gol_subiti
    )
    result.loc[numeric_series(result, "voto").isna(), "fanta_voto_calcolato"] = float("nan")
    return result

def calculate_bonus_malus(df):
    result = calculate_fantavoto(df)
    result["bonus_malus"] = result["fanta_voto_calcolato"] - numeric_series(result, "voto")
    return result

def calculate_relative_metrics(p_stats, is_goalkeeper=False):
    seasons = 0
    if "stagione" in p_stats.columns:
        seasons = p_stats["stagione"].dropna().astype(str).str.strip().nunique()
    if seasons <= 0:
        zero_metrics = {
            "stagioni": 0,
            "presenze_medie": 0.0,
            "presenza_pct": 0.0,
            "gol_stagione": 0.0,
            "assist_stagione": 0.0,
            "rigori_segnati": 0.0,
            "rigori_sbagliati": 0.0,
            "ammonizioni": 0.0,
            "espulsioni": 0.0,
            "gs_stagione": 0.0,
            "rigori_parati": 0.0,
        }
        return zero_metrics
    presenze_totali = numeric_series(p_stats, "voto").count()
    presenze_medie = presenze_totali / seasons
    presenza_pct = (presenze_medie / 38) * 100
    if is_goalkeeper:
        gs_totali = safe_sum(p_stats, "gs")
        rigori_parati_tot = safe_sum(p_stats, "rp")
        rigori_sbagliati_tot = safe_sum(p_stats, "rs")
    else:
        gf_totali = safe_sum(p_stats, "gf")
        rf_totali = safe_sum(p_stats, "rf")
        gf_totali += rf_totali
        rigori_parati_tot = 0
        rigori_sbagliati_tot = safe_sum(p_stats, "rs")
    assist_totali = safe_sum(p_stats, "ass")
    ammonizioni_tot = safe_sum(p_stats, "amm")
    espulsioni_tot = safe_sum(p_stats, "esp")
    result = {
        "stagioni": seasons,
        "presenze_medie": presenze_medie,
        "presenza_pct": presenza_pct,
        "assist_stagione": assist_totali / seasons,
        "rigori_sbagliati": rigori_sbagliati_tot / seasons,
        "ammonizioni": ammonizioni_tot / seasons,
        "espulsioni": espulsioni_tot / seasons,
    }
    if is_goalkeeper:
        result.update({
            "gs_stagione": gs_totali / seasons,
            "rigori_parati": rigori_parati_tot / seasons,
            "gol_stagione": 0.0,
            "rigori_segnati": 0.0,
        })
    else:
        result.update({
            "gol_stagione": gf_totali / seasons,
            "rigori_segnati": rf_totali / seasons,
            "rigori_parati": 0.0,
            "gs_stagione": 0.0,
        })
    return result

def varianza_gol_binaria(p_stats):
    gol_giornata = p_stats.groupby("giornata").apply(
        lambda df: 1 if (safe_sum(df, "gf") + safe_sum(df, "rf")) > 0 else 0
    )
    if len(gol_giornata) <= 1:
        return 0.0
    return gol_giornata.var(ddof=1)

def build_rolling_data(player_stats, window=5):
    if player_stats.empty:
        return pd.DataFrame()
    required = ["stagione", "giornata"]
    if any(column not in player_stats.columns for column in required):
        return pd.DataFrame()
    result = player_stats.copy()
    result["giornata"] = pd.to_numeric(result["giornata"], errors="coerce")
    result = result[result["giornata"].notna()].copy()
    if result.empty:
        return pd.DataFrame()
    result["giornata"] = result["giornata"].astype(int)
    result["stagione"] = result["stagione"].astype(str).str.strip()
    result["_season_sort"] = result["stagione"].apply(lambda v: int(str(v).split("/")[0]) if str(v).split("/")[0].isdigit() else -1)
    result = result.sort_values(["_season_sort", "giornata"]).reset_index(drop=True)
    result = calculate_fantavoto(result)
    if "voto" in result.columns:
        result["voto"] = pd.to_numeric(result["voto"], errors="coerce")
        result["media_mobile_voto"] = result.groupby("stagione", sort=False)["voto"].transform(
            lambda x: x.rolling(window=window, min_periods=1).mean()
        )
    result["media_mobile_fanta"] = result.groupby("stagione", sort=False)["fanta_voto_calcolato"].transform(
        lambda x: x.rolling(window=window, min_periods=1).mean()
    )
    result["periodo"] = result["stagione"] + " • G" + result["giornata"].astype(str)
    return result

def get_latest_season(df):
    if df.empty or "stagione" not in df.columns:
        return None
    seasons = df["stagione"].dropna().astype(str).str.strip()
    seasons = seasons[seasons != ""]
    if seasons.empty:
        return None
    return max(seasons.unique(), key=lambda v: int(v.split("/")[0]) if v.split("/")[0].isdigit() else -1)

def get_latest_quote_row(player_quotes):
    if player_quotes.empty:
        return None
    result = player_quotes.copy()
    if "stagione" in result.columns:
        result["_season_sort"] = result["stagione"].apply(lambda v: int(str(v).split("/")[0]) if str(v).split("/")[0].isdigit() else -1)
        result = result.sort_values("_season_sort")
    return result.iloc[-1]

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

def render_kpi(title, value):
    st.markdown(f"""
        <div style="
            background-color: #1F7A4D22;
            padding: 16px;
            border-radius: 12px;
            margin-bottom: 10px;
            max-width: 220px;
            box-shadow: 0 2px 6px rgba(31, 122, 77, 0.25);
        ">
            <div style="font-weight:700; font-size:1.1rem; color:#1F7A4D; margin-bottom:6px;">{title}</div>
            <div style="font-size:1.7rem; font-weight:600;">{value}</div>
        </div>
    """, unsafe_allow_html=True)

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

def tooltip_icon(text):
    return f'<span style="color:#1F7A4D; cursor: help;" title="{text}">ℹ️</span>'

def emoji_forma(fanta_voto):
    try:
        val = float(fanta_voto)
        if val >= 7:
            return "🔥"
        elif val >= 5.5:
            return "🙂"
        else:
            return "⚠️"
    except Exception:
        return ""

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

    nome_upper = str(nome).upper().strip()
    squadra_upper = str(squadra).upper().strip()

    rigor_info = rigoristi_df[
        (rigoristi_df["giocatore"] == nome_upper) & (rigoristi_df["squadra"] == squadra_upper)
    ]
    tiratore_rigori = False
    pos_rigori = None
    if not rigor_info.empty:
        tiratore_rigori = True
        pos_rigori = int(rigor_info["posizione"].values[0])

    punizioni_info = punizioni_df[
        (punizioni_df["giocatore"] == nome_upper) & (punizioni_df["squadra"] == squadra_upper)
    ]
    tiratore_punizioni = False
    pos_punizioni = None
    if not punizioni_info.empty:
        tiratore_punizioni = True
        pos_punizioni = int(punizioni_info["posizione"].values[0])

    badges = []
    if tiratore_rigori:
        badges.append(f'Rigorista {tooltip_icon("Giocatore incaricato dei rigori, posizione nel ranking squadra")} (#{pos_rigori})')
    if tiratore_punizioni:
        badges.append(f'Tira punizioni {tooltip_icon("Giocatore incaricato delle punizioni, posizione nel ranking squadra")} (#{pos_punizioni})')
    badge_html = " • ".join(badges) if badges else "-"

    left_col, right_col = st.columns([2.6, 1])
    with left_col:
        st.markdown(f'<h1 style="font-weight:bold; font-size:2.5rem; margin-bottom:0.1rem;">{html.escape(nome)}</h1>', unsafe_allow_html=True)
        st.markdown(f'<div style="color:#7C8794; font-size:15px; margin-top:-10px; margin-bottom:8px;">{html.escape(squadra)} • {html.escape(ruolo)}</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="color:#74b274; font-size:14px; font-weight:600; margin-top:-6px; margin-bottom:16px;">{badge_html}</div>', unsafe_allow_html=True)

    with right_col:
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

    with st.container():
        c1, c2, c3 = st.columns(3)
        c1.metric("Presenza media", f"{relative['presenza_pct']:.1f}%")
        c2.metric("Media voto", f"{media_voto:.2f}")
        c3.metric("Fantamedia", f"{fantamedia:.2f}")

    with st.container():
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Presenze medie / stagione", f"{relative['presenze_medie']:.1f}")
        if is_goalkeeper:
            r2.metric("Goal subiti / stagione", f"{relative['gs_stagione']:.2f}")
        else:
            r2.metric("Gol medi / stagione", f"{relative['gol_stagione']:.2f}")
        if is_goalkeeper:
            r3.metric("Rigori parati / stagione", f"{relative['rigori_parati']:.2f}")
        else:
            r3.metric("Assist medi / stagione", f"{relative['assist_stagione']:.2f}")
        r4.metric("Stagioni analizzate", relative["stagioni"])

    var_col1, var_col2 = st.columns(2)
    var_col1.metric(
        "Varianza media voto",
        format_number(varianza_voto),
        help="Quanto i voti si discostano dalla media, misura la continuità delle prestazioni."
    )
    var_col2.metric(
        "Varianza gol (binaria)",
        format_number(varianza_binaria),
        help="Varianza binaria gol: misura la continuità nel segnare (gol in quante giornate i gol sono stati fatti)."
    )

    descrizione_voto = ""
    if varianza_voto is not None:
        if varianza_voto < 0.5:
            descrizione_voto = "Il voto è stabile intorno alla media."
        elif varianza_voto < 1:
            descrizione_voto = "Il voto mostra una variabilità moderata."
        else:
            descrizione_voto = "Il voto è molto variabile."

    descrizione_gol = ""
    if varianza_binaria is not None:
        if varianza_binaria < 0.1:
            descrizione_gol = "Il giocatore segna in modo molto regolare."
        elif varianza_binaria < 0.3:
            descrizione_gol = "La frequenza di gol è moderatamente variabile."
        else:
            descrizione_gol = "Il giocatore ha una frequenza di gol altalenante."

    st.markdown(f"**Media voto:** {media_voto:.2f} — {descrizione_voto}")
    st.markdown(f"**Descrizione varianza gol:** {descrizione_gol}")

    render_section_title("⚽ Altri bonus e malus (media/ stagione)")
    with st.container():
        b1, b2, b3, b4 = st.columns(4)
        b1.metric("Rigori segnati", f"{relative['rigori_segnati']:.2f}")
        b2.metric("Rigori sbagliati", f"{relative['rigori_sbagliati']:.2f}")
        b3.metric("Ammonizioni", f"{relative['ammonizioni']:.2f}")
        b4.metric("Espulsioni", f"{relative['espulsioni']:.2f}")

    render_section_title("📈 Andamento della forma")
    rolling_df = build_rolling_data(p_stats, window=5)
    if rolling_df.empty:
        st.info("Dati insufficienti per calcolare la media mobile.")
    else:
        fig = go.Figure()
        if "media_mobile_voto" in rolling_df.columns:
            fig.add_trace(go.Scatter(
                x=rolling_df["periodo"],
                y=rolling_df["media_mobile_voto"],
                mode="lines",
                name="Media voto — 5 giornate",
                line=dict(width=3),
                hovertemplate="%{x}<br>Media voto: %{y:.2f}<extra></extra>",
                connectgaps=False,
            ))
        if "media_mobile_fanta" in rolling_df.columns:
            fig.add_trace(go.Scatter(
                x=rolling_df["periodo"],
                y=rolling_df["media_mobile_fanta"],
                mode="lines",
                name="Fantamedia — 5 giornate",
                line=dict(width=3),
                hovertemplate="%{x}<br>Fantamedia: %{y:.2f}<extra></extra>",
                connectgaps=False,
            ))

        # Annotazioni semplici picchi e cali
        max_idx = rolling_df['media_mobile_fanta'].idxmax()
        min_idx = rolling_df['media_mobile_fanta'].idxmin()
        max_point = rolling_df.loc[max_idx]
        min_point = rolling_df.loc[min_idx]
        fig.add_annotation(x=max_point['periodo'], y=max_point['media_mobile_fanta'], text="Picco 👍", showarrow=True, arrowhead=2, ax=0, ay=-40)
        fig.add_annotation(x=min_point['periodo'], y=min_point['media_mobile_fanta'], text="Calò 👎", showarrow=True, arrowhead=2, ax=0, ay=40)

        fig.update_layout(
            title="Media mobile a 5 giornate",
            xaxis_title="Stagione / Giornata",
            yaxis_title="Valutazione",
            hovermode="x unified",
            height=430,
            margin=dict(l=20, r=20, t=60, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True)

    render_section_title("📅 Rendimento per stagione")
    if "stagione" in p_stats.columns:
        season_rows = []
        for season, group in p_stats.groupby("stagione"):
            group_fanta = calculate_fantavoto(group)
            gol_stag = safe_sum(group, "gf") + safe_sum(group, "rf")
            assist_stag = safe_sum(group, "ass")
            rigori_sg = safe_sum(group, "rf")
            rigori_sb = safe_sum(group, "rs")
            amm = safe_sum(group, "amm")
            esp = safe_sum(group, "esp")
            gs = safe_sum(group, "gs") if is_goalkeeper else 0
            rig_parati = safe_sum(group, "rp") if is_goalkeeper else 0

            season_rows.append({
                "Stagione": season,
                "Presenze": int(numeric_series(group, "voto").count()),
                "% Presenza": round(numeric_series(group, "voto").count() / 38 * 100, 1),
                "Media voto": round(safe_mean(group, "voto"), 2),
                "Fantamedia": round(safe_mean(group_fanta, "fanta_voto_calcolato"), 2),
                "Gol Totali": int(gol_stag),
                "Assist": int(assist_stag),
                "Rigori segnati": int(rigori_sg),
                "Rigori sbagliati": int(rigori_sb),
                "Ammonizioni": int(amm),
                "Espulsioni": int(esp),
                "Goal subiti": int(gs),
                "Rigori parati": int(rig_parati),
                "Bonus/malus medio": round(safe_mean(calculate_bonus_malus(group), "bonus_malus"), 2),
            })
        season_agg = pd.DataFrame(season_rows)
        if not season_agg.empty:
            season_agg["_sort"] = season_agg["Stagione"].apply(lambda v: int(str(v).split("/")[0]) if str(v).split("/")[0].isdigit() else -1)
            season_agg = season_agg.sort_values("_sort").drop(columns="_sort")
            st.dataframe(season_agg, use_container_width=True, hide_index=True)

# Caricamento dati e UI

try:
    df = load_stats()
    quot = load_quotazioni()
except Exception as e:
    st.error("❌ Errore nel caricamento dei dati da Supabase.")
    st.code(str(e))
    st.stop()

if df.empty:
    st.error("❌ player_stats_history non contiene dati.")
    st.stop()
if quot.empty:
    st.error("❌ giocatori_quotazioni non contiene dati.")
    st.stop()

df = normalize_dataframe(df)
quot = normalize_dataframe(quot)

if "player_id" not in df.columns or "player_id" not in quot.columns:
    st.error("❌ player_stats_history o giocatori_quotazioni non contengono player_id.")
    st.stop()

df = df[df["player_id"].notna()]
quot = quot[quot["player_id"].notna()]

df = remove_starred_vote_rows(df)

latest_season = get_latest_season(quot)
if latest_season is not None:
    current_quot = quot[quot["stagione"].astype(str).str.strip() == str(latest_season).strip()]
else:
    current_quot = quot.copy()

# Sidebar filtri multipli
st.sidebar.header("Filtra giocatori")
roles_selected = st.sidebar.multiselect("Ruolo", options=["P", "D", "C", "A"], default=["P", "D", "C", "A"])
squadra_options = sorted(current_quot["squadra"].dropna().unique())
squadra_selected = st.sidebar.multiselect("Squadra", options=squadra_options)
min_fantamedia = st.sidebar.slider("Fantamedia minima", 0.0, 10.0, 5.0, 0.1)
search_name = st.sidebar.text_input("Cerca nome")

quot_view = current_quot.copy()
if roles_selected:
    quot_view = quot_view[quot_view["ruolo"].str.upper().isin(roles_selected)]
if squadra_selected:
    quot_view = quot_view[quot_view["squadra"].isin(squadra_selected)]
if min_fantamedia > 0:
    quot_view = quot_view[pd.to_numeric(quot_view["fantamedia"], errors='coerce').fillna(0) >= min_fantamedia]
if search_name:
    quot_view = quot_view[quot_view["nome"].str.contains(search_name, case=False, na=False)]

quot_view = quot_view.sort_values("nome", na_position="last")

st.title("⚽ FantaAI")

col_players, col_detail = st.columns([1, 3.2], gap="small")

with col_players:
    st.markdown("<h3 style='color:#1F7A4D; margin-bottom:8px;'>👥 Giocatori disponibili</h3>", unsafe_allow_html=True)
    with st.container():
        st.markdown('<div id="scroll-list">', unsafe_allow_html=True)
        if quot_view.empty:
            st.info("Nessun giocatore trovato.")
            selected_id = None
        else:
            labels = []
            ids = []
            used_labels = set()
            for row in quot_view.itertuples():
                nome_row = getattr(row, "nome", "Giocatore")
                squadra_row = getattr(row, "squadra", "-")
                fantamedia_row = getattr(row, "fantamedia", "?")
                player_id_row = getattr(row, "player_id")
                emoji = emoji_forma(fantamedia_row)
                label = f"{nome_row} • {squadra_row} {emoji} — FM: {fantamedia_row}"
                # Gestione duplicati label
                if label in used_labels:
                    label = f"{label} • ID {int(player_id_row)}"
                used_labels.add(label)
                labels.append(label)
                ids.append(int(player_id_row))
            label_to_id = dict(zip(labels, ids))
            selected_label = st.radio("Seleziona giocatore", options=labels, label_visibility="collapsed")
            selected_id = label_to_id[selected_label]
        st.markdown('</div>', unsafe_allow_html=True)

with col_detail:
    if selected_id is None:
        st.info("Seleziona un giocatore dalla lista per visualizzare i dettagli.")
    else:
        render_player_detail(selected_id, df, quot)
