import os
import re
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from supabase import create_client


# ============================================================
# CONFIGURAZIONE
# ============================================================

st.set_page_config(
    page_title="FantaAI",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1550px;
    }

    section[data-testid="stSidebar"] {
        min-width: 320px;
        max-width: 380px;
    }

    .main-title {
        font-size: 40px;
        font-weight: 800;
        margin-bottom: 0;
    }

    .subtitle {
        color: #6b7280;
        font-size: 15px;
        margin-top: -5px;
        margin-bottom: 20px;
    }

    .player-header {
        padding: 18px 0 22px 0;
        border-bottom: 1px solid #e5e7eb;
        margin-bottom: 20px;
    }

    .player-name {
        font-size: 32px;
        font-weight: 800;
        line-height: 1.1;
    }

    .player-meta {
        color: #6b7280;
        font-size: 15px;
        margin-top: 6px;
    }

    div[data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 14px;
    }

    div[data-testid="stMetricLabel"] { font-size: 13px; }
    div[data-testid="stMetricValue"] { font-size: 25px; font-weight: 700; }

    .section-title {
        font-size: 21px;
        font-weight: 750;
        margin-top: 22px;
        margin-bottom: 10px;
    }

    .verdict-box {
        border-radius: 14px;
        padding: 18px 22px;
        margin-bottom: 18px;
        border: 1px solid #e5e7eb;
    }

    .verdict-title {
        font-size: 22px;
        font-weight: 800;
        margin-bottom: 4px;
    }

    .verdict-sub {
        font-size: 14px;
        color: #374151;
    }

    .tier-S { background:#065f46; color:white; padding:2px 10px; border-radius:8px; font-weight:700; }
    .tier-A { background:#16a34a; color:white; padding:2px 10px; border-radius:8px; font-weight:700; }
    .tier-B { background:#ca8a04; color:white; padding:2px 10px; border-radius:8px; font-weight:700; }
    .tier-C { background:#ea580c; color:white; padding:2px 10px; border-radius:8px; font-weight:700; }
    .tier-D { background:#dc2626; color:white; padding:2px 10px; border-radius:8px; font-weight:700; }
    .tier-ND { background:#6b7280; color:white; padding:2px 10px; border-radius:8px; font-weight:700; }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SUPABASE
# ============================================================

def get_secret(name):
    value = os.getenv(name)
    if value:
        return value
    try:
        return st.secrets.get(name)
    except Exception:
        return None


SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("⚠️ Credenziali Supabase non trovate. Configura SUPABASE_URL e SUPABASE_KEY.")
    st.stop()


@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


try:
    supabase = init_supabase()
except Exception as e:
    st.error(f"Errore nella connessione a Supabase: {e}")
    st.stop()


@st.cache_data(ttl=600, show_spinner=False)
def load_player_stats():
    all_rows = []
    page_size = 1000
    start = 0

    while True:
        response = (
            supabase.table("player_stats")
            .select("*")
            .range(start, start + page_size - 1)
            .execute()
        )
        rows = response.data or []
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < page_size:
            break
        start += page_size

    return pd.DataFrame(all_rows)


with st.spinner("Caricamento statistiche giocatori..."):
    try:
        df = load_player_stats()
    except Exception as e:
        st.error(f"Errore durante la lettura di player_stats: {e}")
        st.stop()

if df.empty:
    st.warning("La tabella `player_stats` non contiene dati.")
    st.stop()


# ============================================================
# NORMALIZZAZIONE
# ============================================================

numeric_columns = [
    "player_id", "matches_played", "minutes_played", "goals", "assists",
    "xg", "xa", "shots_total", "key_passes", "yellow_cards", "red_cards",
    "xg_chain", "xg_buildup", "goals_per_90", "assists_per_90", "xg_per_90",
    "xa_per_90", "shots_per_90", "key_passes_per_90", "np_goals", "np_xg",
]

for col in numeric_columns:
    if col not in df.columns:
        df[col] = 0
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)


def season_start(value):
    if pd.isna(value):
        return np.nan
    s = str(value).strip()
    match = re.match(r"^(\d{4})/(\d{2})$", s)
    if match:
        first = int(match.group(1))
        second = int(match.group(2))
        if 1900 <= first <= 2100 and second == (first + 1) % 100:
            return first
        if first >= 2100:
            return 2000 + int(str(first)[:2])
    digits = re.sub(r"\D", "", s)
    if len(digits) == 4:
        number = int(digits)
        if 1900 <= number <= 2100:
            return number
        return 2000 + int(digits[:2])
    return np.nan


def format_season(value):
    start = season_start(value)
    if pd.isna(start):
        return str(value)
    start = int(start)
    return f"{start}/{str(start + 1)[-2:]}"


df["season_start"] = df["season"].apply(season_start)
df["season_label"] = df["season"].apply(format_season)


def normalize_role(position):
    if pd.isna(position):
        return "N/D"
    position = str(position).upper()
    if "GK" in position:
        return "P"
    if "D" in position:
        return "D"
    if "M" in position:
        return "C"
    if "F" in position or "S" in position:
        return "A"
    return "N/D"


if "position" not in df.columns:
    df["position"] = ""

df["role"] = df["position"].apply(normalize_role)


# ============================================================
# AGGREGAZIONE DUPLICATI (player_id + season, es. trasferimenti)
# ============================================================

sum_columns = [
    "matches_played", "minutes_played", "goals", "assists", "xg", "xa",
    "shots_total", "key_passes", "yellow_cards", "red_cards",
    "xg_chain", "xg_buildup", "np_goals", "np_xg",
]

aggregation = {col: "sum" for col in sum_columns if col in df.columns}
for col in ["player_name", "team", "position", "role"]:
    if col in df.columns:
        aggregation[col] = "first"

df = (
    df.sort_values(["season_start", "player_name"], ascending=[True, True])
    .groupby(["player_id", "season_start"], as_index=False)
    .agg(aggregation)
)


# ============================================================
# METRICHE DERIVATE PER 90
# ============================================================

minutes = df["minutes_played"].replace(0, np.nan)

df["goals_per_90"] = (df["goals"] / (minutes / 90)).fillna(0)
df["assists_per_90"] = (df["assists"] / (minutes / 90)).fillna(0)
df["xg_per_90"] = (df["xg"] / (minutes / 90)).fillna(0)
df["xa_per_90"] = (df["xa"] / (minutes / 90)).fillna(0)
df["shots_per_90"] = (df["shots_total"] / (minutes / 90)).fillna(0)
df["key_passes_per_90"] = (df["key_passes"] / (minutes / 90)).fillna(0)

df["shot_conversion"] = (
    df["goals"] / df["shots_total"].replace(0, np.nan)
).fillna(0) * 100

df["goal_xg_diff"] = df["goals"] - df["xg"]


# ============================================================
# PUNTEGGIO PRESTAZIONE / AFFIDABILITA' / VALUE SCORE / TIER
# ============================================================

ROLE_WEIGHTS = {
    "D": {"goals_per_90": 0.25, "assists_per_90": 0.20, "xg_per_90": 0.20,
          "xa_per_90": 0.15, "key_passes_per_90": 0.10, "shots_per_90": 0.10},
    "C": {"assists_per_90": 0.25, "xa_per_90": 0.20, "key_passes_per_90": 0.15,
          "goals_per_90": 0.20, "xg_per_90": 0.15, "shots_per_90": 0.05},
    "A": {"goals_per_90": 0.30, "xg_per_90": 0.25, "assists_per_90": 0.15,
          "xa_per_90": 0.15, "shots_per_90": 0.10, "key_passes_per_90": 0.05},
}

MAX_SEASON_MINUTES = 3420  # 38 giornate x 90'


def compute_performance_scores(data):
    """Calcola il Punteggio Prestazione (0-100) come percentile pesato
    all'interno dello stesso ruolo e della stessa stagione."""

    data = data.copy()
    data["performance_score"] = np.nan

    for (season, role), group in data.groupby(["season_start", "role"]):

        weights = ROLE_WEIGHTS.get(role)

        if not weights or len(group) < 3:
            # Portieri o gruppi troppo piccoli: Understat non ha
            # statistiche difensive da portiere, quindi non calcoliamo
            # un punteggio affidabile.
            continue

        score = pd.Series(0.0, index=group.index)

        for metric, weight in weights.items():
            pct = group[metric].rank(pct=True) * 100
            score = score + pct * weight

        data.loc[group.index, "performance_score"] = score.round(1)

    return data


df = compute_performance_scores(df)

# Affidabilita': disponibilita' minuti stagione + costanza minuti tra stagioni
df["availability_score"] = (
    (df["minutes_played"] / MAX_SEASON_MINUTES) * 100
).clip(upper=100)

df = df.sort_values(["player_id", "season_start"])

df["minutes_std3"] = (
    df.groupby("player_id")["minutes_played"]
    .transform(lambda s: s.rolling(3, min_periods=2).std())
)
df["minutes_mean3"] = (
    df.groupby("player_id")["minutes_played"]
    .transform(lambda s: s.rolling(3, min_periods=2).mean())
)

cv = (df["minutes_std3"] / df["minutes_mean3"].replace(0, np.nan)).fillna(0)
df["consistency_score"] = (100 - (cv * 100).clip(upper=100)).clip(lower=0)
df.loc[df["minutes_mean3"].isna(), "consistency_score"] = df["availability_score"]

df["reliability_score"] = (
    df["availability_score"] * 0.7 + df["consistency_score"] * 0.3
).round(1)

df["value_score"] = (
    df["performance_score"] * 0.65 + df["reliability_score"] * 0.35
).round(1)

# Trend rispetto alla stagione precedente dello stesso giocatore
df["prev_performance_score"] = df.groupby("player_id")["performance_score"].shift(1)
df["trend_delta"] = (df["performance_score"] - df["prev_performance_score"]).round(1)


def assign_tier(group):
    valid = group.dropna(subset=["value_score"])
    if len(valid) < 5:
        return pd.Series("N/D", index=group.index)
    try:
        tiers = pd.qcut(
            valid["value_score"],
            q=[0, 0.10, 0.30, 0.60, 0.85, 1.0],
            labels=["D", "C", "B", "A", "S"],
        )
    except ValueError:
        return pd.Series("N/D", index=group.index)
    out = pd.Series("N/D", index=group.index)
    out.loc[valid.index] = tiers.astype(str)
    return out


df["tier"] = "N/D"
for (season, role), group in df.groupby(["season_start", "role"]):
    df.loc[group.index, "tier"] = assign_tier(group)


latest_season = int(df["season_start"].dropna().max())

latest_players = df[df["season_start"] == latest_season].copy()
if latest_players.empty:
    latest_players = df.copy()

role_order = {"P": 0, "D": 1, "C": 2, "A": 3, "N/D": 4}
latest_players["role_order"] = latest_players["role"].map(role_order).fillna(4)


# ============================================================
# LISTONE QUOTAZIONI (opzionale)
# ============================================================

def normalize_name(name):
    return re.sub(r"\s+", " ", str(name)).strip().lower()


quotazioni_map = {}

with st.sidebar:
    st.markdown("## 💰 Listone (opzionale)")
    uploaded = st.file_uploader(
        "Carica CSV con colonne 'Nome' e 'Quotazione'",
        type=["csv"],
        help="Serve per calcolare il rapporto qualità/prezzo reale rispetto al listone della tua lega.",
    )

    if uploaded is not None:
        try:
            listone = pd.read_csv(uploaded)
            listone.columns = [c.strip().lower() for c in listone.columns]

            name_col = next((c for c in listone.columns if "nome" in c), None)
            price_col = next((c for c in listone.columns if "quotazion" in c), None)

            if name_col and price_col:
                listone["_key"] = listone[name_col].apply(normalize_name)
                quotazioni_map = dict(
                    zip(listone["_key"], pd.to_numeric(listone[price_col], errors="coerce"))
                )
                st.success(f"Listone caricato: {len(quotazioni_map)} giocatori.")
            else:
                st.warning("Non trovo colonne 'Nome' e 'Quotazione' nel CSV.")
        except Exception as e:
            st.error(f"Errore nel leggere il listone: {e}")

latest_players["quotazione"] = latest_players["player_name"].apply(
    lambda n: quotazioni_map.get(normalize_name(n), np.nan)
)
latest_players["value_for_money"] = (
    latest_players["value_score"] / latest_players["quotazione"]
).replace([np.inf, -np.inf], np.nan)


# ============================================================
# SHORTLIST (in memoria, per sessione)
# ============================================================

if "shortlist" not in st.session_state:
    st.session_state.shortlist = set()


with st.sidebar:
    st.markdown("## ⭐ Shortlist")
    if st.session_state.shortlist:
        st.caption(f"{len(st.session_state.shortlist)} giocatori salvati in questa sessione")
        if st.button("Svuota shortlist"):
            st.session_state.shortlist = set()
            st.rerun()
    else:
        st.caption("Aggiungi giocatori dalla tabella Ranking o dalla scheda dettaglio.")


# ============================================================
# HEADER
# ============================================================

st.markdown('<div class="main-title">⚽ FantaAI</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Assistente per l\'asta del Fantacalcio · Serie A Analytics</div>',
    unsafe_allow_html=True,
)

tab_ranking, tab_player, tab_compare = st.tabs(
    ["🏆 Ranking & Overview", "🔍 Analisi Giocatore", "⚖️ Confronto"]
)


# ============================================================
# TAB 1 — RANKING
# ============================================================

with tab_ranking:

    st.caption(f"Stagione di riferimento: {format_season(latest_season)}")

    f1, f2, f3, f4 = st.columns([1.2, 1.5, 1.2, 1.5])

    with f1:
        roles_selected = st.multiselect(
            "Ruolo", ["P", "D", "C", "A"], default=["P", "D", "C", "A"]
        )
    with f2:
        teams_available = sorted(latest_players["team"].dropna().unique().tolist())
        teams_selected = st.multiselect("Squadra", teams_available, default=[])
    with f3:
        min_minutes = st.slider("Minuti minimi", 0, 3420, 450, step=90)
    with f4:
        search_ranking = st.text_input("Cerca giocatore", placeholder="Es. Lautaro, Barella...")

    ranked = latest_players.copy()
    ranked = ranked[ranked["role"].isin(roles_selected)]
    ranked = ranked[ranked["minutes_played"] >= min_minutes]

    if teams_selected:
        ranked = ranked[ranked["team"].isin(teams_selected)]

    if search_ranking:
        ranked = ranked[
            ranked["player_name"].str.lower().str.contains(search_ranking.lower(), na=False)
        ]

    ranked = ranked.sort_values("value_score", ascending=False, na_position="last")

    display_cols = {
        "player_name": "Giocatore",
        "team": "Squadra",
        "role": "Ruolo",
        "tier": "Tier",
        "value_score": "Value Score",
        "performance_score": "Prestazione",
        "reliability_score": "Affidabilità",
        "trend_delta": "Trend",
        "matches_played": "Presenze",
        "minutes_played": "Minuti",
        "goals": "Gol",
        "assists": "Assist",
        "xg": "xG",
        "xa": "xA",
    }

    if quotazioni_map:
        display_cols["quotazione"] = "Quot."
        display_cols["value_for_money"] = "Val./Prezzo"

    table = ranked[list(display_cols.keys())].rename(columns=display_cols)
    table.insert(0, "Shortlist", table["Giocatore"].isin(
        [n for n in st.session_state.shortlist]
    ))

    st.caption(f"{len(table)} giocatori corrispondenti ai filtri")

    edited = st.data_editor(
        table,
        use_container_width=True,
        hide_index=True,
        height=520,
        disabled=[c for c in table.columns if c != "Shortlist"],
        column_config={
            "Shortlist": st.column_config.CheckboxColumn(required=True),
            "Value Score": st.column_config.ProgressColumn(
                min_value=0, max_value=100, format="%.1f"
            ),
            "Prestazione": st.column_config.ProgressColumn(
                min_value=0, max_value=100, format="%.1f"
            ),
            "Affidabilità": st.column_config.ProgressColumn(
                min_value=0, max_value=100, format="%.1f"
            ),
            "Trend": st.column_config.NumberColumn(format="%+.1f"),
        },
        key="ranking_editor",
    )

    st.session_state.shortlist = set(
        edited.loc[edited["Shortlist"], "Giocatore"].tolist()
    )

    st.markdown(
        "<span class='tier-S'>S</span> top assoluti &nbsp; "
        "<span class='tier-A'>A</span> ottimi &nbsp; "
        "<span class='tier-B'>B</span> buoni &nbsp; "
        "<span class='tier-C'>C</span> nella media &nbsp; "
        "<span class='tier-D'>D</span> da evitare",
        unsafe_allow_html=True,
    )

    if not quotazioni_map:
        st.info(
            "Carica un listone (CSV con 'Nome' e 'Quotazione') dalla sidebar per vedere "
            "anche il rapporto qualità/prezzo reale rispetto ai valori d'asta."
        )

    st.caption(
        "Nota: per i portieri (P) Understat non fornisce statistiche difensive "
        "(parate, gol subiti), quindi Punteggio Prestazione e Tier non sono calcolati per loro."
    )


# ============================================================
# TAB 2 — ANALISI GIOCATORE
# ============================================================

with tab_player:

    player_options = []
    player_map = {}

    for _, row in latest_players.sort_values(["role_order", "player_name"]).iterrows():
        label = f"{row['player_name']} · {row['team']} · {row['role']}"
        player_options.append(label)
        player_map[label] = row["player_id"]

    if not player_options:
        st.warning("Nessun giocatore disponibile.")
        st.stop()

    if (
        "selected_player_id" not in st.session_state
        or st.session_state.selected_player_id not in player_map.values()
    ):
        st.session_state.selected_player_id = latest_players.iloc[0]["player_id"]

    current_index = 0
    for i, label in enumerate(player_options):
        if player_map[label] == st.session_state.selected_player_id:
            current_index = i
            break

    selected_label = st.selectbox(
        "Seleziona giocatore", player_options, index=current_index, key="player_selector"
    )
    selected_player_id = player_map[selected_label]
    st.session_state.selected_player_id = selected_player_id

    player_history = (
        df[df["player_id"] == selected_player_id].sort_values("season_start").copy()
    )

    if player_history.empty:
        st.error("Statistiche del giocatore non trovate.")
        st.stop()

    player_latest = player_history.iloc[-1]

    player_name = str(player_latest["player_name"])
    team = str(player_latest["team"])
    role = str(player_latest["role"])
    position = str(player_latest["position"])
    player_latest_season = int(player_latest["season_start"])

    st.markdown('<div class="player-header">', unsafe_allow_html=True)
    st.markdown(f'<div class="player-name">{player_name}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="player-meta">⚽ {team} &nbsp; · &nbsp; Ruolo: <b>{role}</b> '
        f'&nbsp; · &nbsp; {position} &nbsp; · &nbsp; '
        f'Stagione: <b>{format_season(player_latest_season)}</b></div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("⭐ Aggiungi/rimuovi dalla shortlist"):
        if player_name in st.session_state.shortlist:
            st.session_state.shortlist.discard(player_name)
        else:
            st.session_state.shortlist.add(player_name)
        st.rerun()

    # --------------------------------------------------------
    # VERDETTO
    # --------------------------------------------------------

    value_score = player_latest["value_score"]
    tier = player_latest["tier"]
    trend = player_latest["trend_delta"]

    tier_colors = {
        "S": ("#065f46", "#d1fae5", "TOP PICK — priorità assoluta"),
        "A": ("#16a34a", "#dcfce7", "OTTIMO ACQUISTO — spendici sopra"),
        "B": ("#ca8a04", "#fef9c3", "BUON PROFILO — valuta in base al prezzo"),
        "C": ("#ea580c", "#ffedd5", "NELLA MEDIA — comprare solo a prezzo basso"),
        "D": ("#dc2626", "#fee2e2", "DA EVITARE — rischio non giustificato"),
        "N/D": ("#6b7280", "#f3f4f6", "DATI INSUFFICIENTI per un verdetto affidabile"),
    }

    color, bg, verdict_text = tier_colors.get(tier, tier_colors["N/D"])

    trend_text = ""
    if pd.notna(trend):
        arrow = "↑" if trend > 1 else ("↓" if trend < -1 else "→")
        trend_text = f" &nbsp;·&nbsp; Trend rispetto alla stagione precedente: {arrow} {trend:+.1f} pt"

    value_text = f"{value_score:.1f}/100" if pd.notna(value_score) else "N/D"

    price_text = ""
    quot = player_latest.get("quotazione") if "quotazione" in player_latest else np.nan
    if pd.notna(quot):
        vfm = value_score / quot if pd.notna(value_score) and quot else np.nan
        price_text = f" &nbsp;·&nbsp; Quotazione: {quot:.0f} &nbsp;·&nbsp; Val./Prezzo: {vfm:.2f}"

    st.markdown(
        f"""
        <div class="verdict-box" style="background:{bg}; border-color:{color};">
            <div class="verdict-title" style="color:{color};">{verdict_text}</div>
            <div class="verdict-sub">
                Value Score: <b>{value_text}</b> &nbsp;·&nbsp; Tier: <b>{tier}</b>
                {trend_text}{price_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # KPI
    # --------------------------------------------------------

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("⚽ Gol", int(player_latest["goals"]))
    col2.metric("🎯 Assist", int(player_latest["assists"]))
    col3.metric("xG", f'{player_latest["xg"]:.2f}')
    col4.metric("xG / 90", f'{player_latest["xg_per_90"]:.2f}')
    col5.metric("⏱ Minuti", f'{int(player_latest["minutes_played"]):,}'.replace(",", "."))

    st.markdown("")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Presenze", int(player_latest["matches_played"]))
    col2.metric("Affidabilità", f'{player_latest["reliability_score"]:.0f}/100'
                if pd.notna(player_latest["reliability_score"]) else "N/D")
    col3.metric("xA", f'{player_latest["xa"]:.2f}')
    col4.metric("xA / 90", f'{player_latest["xa_per_90"]:.2f}')
    col5.metric("Tiri", int(player_latest["shots_total"]))

    # --------------------------------------------------------
    # STORICO
    # --------------------------------------------------------

    st.markdown('<div class="section-title">📈 Evoluzione storica</div>', unsafe_allow_html=True)

    history_display = player_history.copy()
    history_display["Stagione"] = history_display["season_start"].apply(format_season)

    fig_history = go.Figure()
    fig_history.add_trace(go.Scatter(
        x=history_display["Stagione"], y=history_display["goals"],
        mode="lines+markers", name="Gol", line=dict(width=3),
    ))
    fig_history.add_trace(go.Scatter(
        x=history_display["Stagione"], y=history_display["xg"],
        mode="lines+markers", name="xG", line=dict(width=3, dash="dash"),
    ))
    fig_history.update_layout(
        title="Gol vs Expected Goals", xaxis_title="Stagione", yaxis_title="Valore",
        hovermode="x unified", height=380, margin=dict(l=20, r=20, t=60, b=20),
    )
    st.plotly_chart(fig_history, use_container_width=True)

    col_left, col_right = st.columns(2)

    with col_left:
        fig_over = px.bar(
            history_display, x="Stagione", y="goal_xg_diff",
            title="Over / Underperformance · Gol − xG",
            labels={"goal_xg_diff": "Gol − xG", "Stagione": "Stagione"},
            text_auto=".2f",
        )
        fig_over.add_hline(y=0, line_dash="dash")
        fig_over.update_layout(height=360, margin=dict(l=20, r=20, t=60, b=20))
        st.plotly_chart(fig_over, use_container_width=True)

    with col_right:
        fig_value = px.line(
            history_display, x="Stagione", y="value_score", markers=True,
            title="Value Score nel tempo",
            labels={"value_score": "Value Score", "Stagione": "Stagione"},
        )
        fig_value.update_layout(height=360, margin=dict(l=20, r=20, t=60, b=20), yaxis_range=[0, 100])
        st.plotly_chart(fig_value, use_container_width=True)

    # --------------------------------------------------------
    # CONFRONTO CON IL RUOLO (percentili)
    # --------------------------------------------------------

    st.markdown('<div class="section-title">🎯 Confronto con i pari ruolo</div>', unsafe_allow_html=True)

    role_players = df[
        (df["season_start"] == player_latest_season) & (df["role"] == role)
    ].copy()

    if len(role_players) >= 5:
        metrics_for_percentile = {
            "goals_per_90": "Gol / 90", "xg_per_90": "xG / 90", "xa_per_90": "xA / 90",
            "shots_per_90": "Tiri / 90", "key_passes_per_90": "Key Passes / 90",
        }
        percentile_data = []
        for metric, label in metrics_for_percentile.items():
            values = pd.to_numeric(role_players[metric], errors="coerce").fillna(0)
            player_value = float(player_latest[metric])
            percentile = (values < player_value).mean() * 100
            percentile_data.append({"Metrica": label, "Valore": round(player_value, 2), "Percentile": round(percentile, 0)})

        percentile_df = pd.DataFrame(percentile_data)

        fig_percentile = px.bar(
            percentile_df, x="Percentile", y="Metrica", orientation="h", text="Percentile",
            range_x=[0, 100],
            title=f"Percentile rispetto ai {role} della Serie A · {format_season(player_latest_season)}",
        )
        fig_percentile.update_traces(texttemplate="%{text}°", textposition="inside")
        fig_percentile.update_layout(height=330, margin=dict(l=20, r=20, t=60, b=20))
        st.plotly_chart(fig_percentile, use_container_width=True)
    else:
        st.info("Non ci sono abbastanza giocatori dello stesso ruolo per un confronto significativo.")

    # --------------------------------------------------------
    # DETTAGLIO STAGIONALE
    # --------------------------------------------------------

    st.markdown('<div class="section-title">📋 Dettaglio stagionale</div>', unsafe_allow_html=True)

    detail = history_display[[
        "Stagione", "team", "role", "matches_played", "minutes_played",
        "goals", "assists", "xg", "xa", "shots_total", "key_passes",
        "yellow_cards", "red_cards", "value_score", "tier",
    ]].rename(columns={
        "team": "Squadra", "role": "Ruolo", "matches_played": "Presenze",
        "minutes_played": "Minuti", "goals": "Gol", "assists": "Assist",
        "xg": "xG", "xa": "xA", "shots_total": "Tiri", "key_passes": "Key Passes",
        "yellow_cards": "Gialli", "red_cards": "Rossi",
        "value_score": "Value Score", "tier": "Tier",
    })

    detail["xG"] = detail["xG"].round(2)
    detail["xA"] = detail["xA"].round(2)

    st.dataframe(detail, use_container_width=True, hide_index=True)


# ============================================================
# TAB 3 — CONFRONTO
# ============================================================

with tab_compare:

    st.caption("Confronta fino a 4 giocatori della stessa stagione più recente disponibile.")

    default_selection = list(st.session_state.shortlist)[:4]

    compare_names = st.multiselect(
        "Giocatori da confrontare",
        latest_players["player_name"].sort_values().unique().tolist(),
        default=default_selection,
        max_selections=4,
    )

    if len(compare_names) < 2:
        st.info("Seleziona almeno due giocatori (puoi partire dalla tua shortlist).")
    else:
        compare_df = latest_players[latest_players["player_name"].isin(compare_names)].copy()

        radar_metrics = {
            "goals_per_90": "Gol/90", "assists_per_90": "Assist/90",
            "xg_per_90": "xG/90", "xa_per_90": "xA/90",
            "shots_per_90": "Tiri/90", "key_passes_per_90": "Key Passes/90",
        }

        fig_radar = go.Figure()
        for _, row in compare_df.iterrows():
            values = [float(row[m]) for m in radar_metrics.keys()]
            fig_radar.add_trace(go.Scatterpolar(
                r=values + [values[0]],
                theta=list(radar_metrics.values()) + [list(radar_metrics.values())[0]],
                fill="toself",
                name=row["player_name"],
            ))

        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True)),
            height=500, showlegend=True,
            title="Confronto per 90 minuti",
        )
        st.plotly_chart(fig_radar, use_container_width=True)

        compare_cols = {
            "player_name": "Giocatore", "team": "Squadra", "role": "Ruolo",
            "tier": "Tier", "value_score": "Value Score",
            "performance_score": "Prestazione", "reliability_score": "Affidabilità",
            "goals": "Gol", "assists": "Assist", "xg": "xG", "xa": "xA",
            "minutes_played": "Minuti",
        }
        if quotazioni_map:
            compare_cols["quotazione"] = "Quot."
            compare_cols["value_for_money"] = "Val./Prezzo"

        st.dataframe(
            compare_df[list(compare_cols.keys())].rename(columns=compare_cols),
            use_container_width=True, hide_index=True,
        )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")
st.caption(
    f"FantaAI · Database: {len(df):,} record stagionali · "
    f"{df['player_id'].nunique():,} giocatori · "
    f"Ultima stagione disponibile: {format_season(latest_season)} · "
    "Value Score e Tier sono stime basate su dati Understat, non sostituiscono la valutazione personale."
)
