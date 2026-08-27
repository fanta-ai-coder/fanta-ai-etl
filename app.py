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

ROLE_LABELS = {"P": "Portieri", "D": "Difensori", "C": "Centrocampisti", "A": "Attaccanti"}
ROLE_ORDER = {"P": 0, "D": 1, "C": 2, "A": 3}
MAX_SEASON_MINUTES = 3420  # 38 giornate x 90'

PLAYER_COLOR = "#2563eb"
PEER_COLOR = "#84cc16"


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        max-width: 1650px;
    }

    section[data-testid="stSidebar"] {
        min-width: 300px;
        max-width: 340px;
    }

    .main-title { font-size: 38px; font-weight: 800; margin-bottom: 0; }
    .subtitle { color: #6b7280; font-size: 15px; margin-top: -5px; margin-bottom: 16px; }

    .player-header {
        padding: 14px 0 18px 0;
        border-bottom: 1px solid #e5e7eb;
        margin-bottom: 16px;
    }
    .player-name { font-size: 28px; font-weight: 800; line-height: 1.1; }
    .player-meta { color: #6b7280; font-size: 14px; margin-top: 6px; }

    div[data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 12px;
    }
    div[data-testid="stMetricLabel"] { font-size: 12px; }
    div[data-testid="stMetricValue"] { font-size: 22px; font-weight: 700; }

    .section-title { font-size: 19px; font-weight: 750; margin-top: 18px; margin-bottom: 8px; }

    .verdict-box {
        border-radius: 14px;
        padding: 16px 20px;
        margin-bottom: 14px;
        border: 1px solid #e5e7eb;
    }
    .verdict-title { font-size: 20px; font-weight: 800; margin-bottom: 4px; }
    .verdict-sub { font-size: 13px; color: #374151; }

    .tier-S { background:#065f46; color:white; padding:2px 10px; border-radius:8px; font-weight:700; }
    .tier-A { background:#16a34a; color:white; padding:2px 10px; border-radius:8px; font-weight:700; }
    .tier-B { background:#ca8a04; color:white; padding:2px 10px; border-radius:8px; font-weight:700; }
    .tier-C { background:#ea580c; color:white; padding:2px 10px; border-radius:8px; font-weight:700; }
    .tier-D { background:#dc2626; color:white; padding:2px 10px; border-radius:8px; font-weight:700; }
    .tier-ND { background:#6b7280; color:white; padding:2px 10px; border-radius:8px; font-weight:700; }

    /* lista giocatori scrollabile */
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stButton"] > button {
        text-align: left;
        justify-content: flex-start;
        font-size: 13px;
        padding: 6px 10px;
    }

    .split-row { margin-bottom: 14px; }
    .split-label { font-size: 13px; font-weight: 700; text-align: center; margin-bottom: 4px; }
    .split-values { display: flex; justify-content: space-between; font-size: 12px; color: #6b7280; margin-top: 3px; }
    .split-bar-track { display: flex; height: 10px; border-radius: 6px; overflow: hidden; background: #f1f5f9; }
    .split-bar-player { background: #2563eb; }
    .split-bar-peer { background: #84cc16; }

    .gk-note {
        background: #fef9c3;
        border: 1px solid #fde68a;
        border-radius: 10px;
        padding: 12px 16px;
        font-size: 13px;
        color: #78350f;
        margin-bottom: 16px;
    }

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
def load_table(table_name):
    all_rows = []
    page_size = 1000
    start = 0

    while True:
        response = (
            supabase.table(table_name)
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


with st.spinner("Caricamento dati..."):
    try:
        df = load_table("player_stats")
    except Exception as e:
        st.error(f"Errore durante la lettura di player_stats: {e}")
        st.stop()

    try:
        quotazioni_raw = load_table("quotazioni")
    except Exception:
        quotazioni_raw = pd.DataFrame()

    try:
        mapping_raw = load_table("player_mapping")
    except Exception:
        mapping_raw = pd.DataFrame()

if df.empty:
    st.warning("La tabella `player_stats` non contiene dati.")
    st.stop()

quotazioni_available = not quotazioni_raw.empty and not mapping_raw.empty

if not quotazioni_available:
    st.info(
        "ℹ️ Tabelle `quotazioni`/`player_mapping` non trovate o vuote: la lista giocatori "
        "userà solo i dati Understat disponibili, senza quotazioni/FVM. "
        "Esegui l'ETL per popolarle e sbloccare la vista completa del listone."
    )


# ============================================================
# NORMALIZZAZIONE player_stats
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


def normalize_role_understat(position):
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

df["role"] = df["position"].apply(normalize_role_understat)


# ============================================================
# AGGREGAZIONE DUPLICATI (player_id + season)
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
# QUOTAZIONI + MAPPING -> RUOLO UFFICIALE PIU' AFFIDABILE
# ============================================================

if quotazioni_available:
    quotazioni = quotazioni_raw.copy()
    mapping = mapping_raw.copy()

    for col in ["id", "quotazione_attuale", "quotazione_iniziale", "fvm"]:
        if col in quotazioni.columns:
            quotazioni[col] = pd.to_numeric(quotazioni[col], errors="coerce")

    mapping["player_id"] = pd.to_numeric(mapping.get("player_id"), errors="coerce")
    mapping["id_excel"] = pd.to_numeric(mapping.get("id_excel"), errors="coerce")

    quotazioni_full = quotazioni.merge(
        mapping[["id_excel", "player_id"]],
        left_on="id",
        right_on="id_excel",
        how="left",
    )

    # Usa il ruolo del listone (piu' affidabile) ovunque disponibile
    role_map = (
        quotazioni_full.dropna(subset=["player_id"])
        .drop_duplicates(subset=["player_id"])
        .set_index("player_id")["ruolo"]
        .to_dict()
    )
    df["role"] = df["player_id"].map(role_map).fillna(df["role"])

else:
    # Fallback: costruiamo un "listone" surrogato a partire da Understat,
    # cosi' la lista a sinistra funziona comunque.
    fallback_latest = df[df["season_start"] == df["season_start"].max()].copy()
    quotazioni_full = pd.DataFrame({
        "id": fallback_latest["player_id"],
        "id_excel": fallback_latest["player_id"],
        "player_id": fallback_latest["player_id"],
        "nome": fallback_latest["player_name"],
        "ruolo": fallback_latest["role"],
        "squadra": fallback_latest["team"],
        "quotazione_attuale": np.nan,
        "fvm": np.nan,
    })


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


def compute_performance_scores(data):
    data = data.copy()
    data["performance_score"] = np.nan

    for (season, role), group in data.groupby(["season_start", "role"]):
        weights = ROLE_WEIGHTS.get(role)
        if not weights or len(group) < 3:
            continue

        score = pd.Series(0.0, index=group.index)
        for metric, weight in weights.items():
            pct = group[metric].rank(pct=True) * 100
            score = score + pct * weight

        data.loc[group.index, "performance_score"] = score.round(1)

    return data


df = compute_performance_scores(df)

df["availability_score"] = (
    (df["minutes_played"] / MAX_SEASON_MINUTES) * 100
).clip(upper=100)

df = df.sort_values(["player_id", "season_start"])

df["minutes_std3"] = (
    df.groupby("player_id")["minutes_played"].transform(lambda s: s.rolling(3, min_periods=2).std())
)
df["minutes_mean3"] = (
    df.groupby("player_id")["minutes_played"].transform(lambda s: s.rolling(3, min_periods=2).mean())
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

df["prev_performance_score"] = df.groupby("player_id")["performance_score"].shift(1)
df["trend_delta"] = (df["performance_score"] - df["prev_performance_score"]).round(1)


def assign_tier(group):
    valid = group.dropna(subset=["value_score"])
    if len(valid) < 5:
        return pd.Series("N/D", index=group.index)
    try:
        tiers = pd.qcut(
            valid["value_score"], q=[0, 0.10, 0.30, 0.60, 0.85, 1.0],
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


# ============================================================
# SHORTLIST (in memoria, per sessione)
# ============================================================

if "shortlist" not in st.session_state:
    st.session_state.shortlist = set()

if "selected_listone_id" not in st.session_state:
    first_row = quotazioni_full.sort_values("nome").iloc[0]
    st.session_state.selected_listone_id = first_row["id"]

with st.sidebar:
    st.markdown("## ⭐ Shortlist")
    if st.session_state.shortlist:
        st.caption(f"{len(st.session_state.shortlist)} giocatori salvati in questa sessione")
        if st.button("Svuota shortlist"):
            st.session_state.shortlist = set()
            st.rerun()
    else:
        st.caption("Aggiungi giocatori dalla scheda dettaglio o dal ranking.")


# ============================================================
# HEADER
# ============================================================

st.markdown('<div class="main-title">⚽ FantaAI</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Assistente per l\'asta del Fantacalcio · Serie A Analytics</div>',
    unsafe_allow_html=True,
)

tab_player, tab_ranking, tab_compare = st.tabs(
    ["🔍 Analisi Giocatore", "🏆 Ranking & Overview", "⚖️ Confronto"]
)


# ============================================================
# TAB — ANALISI GIOCATORE (lista a sinistra + dettaglio a destra)
# ============================================================

with tab_player:

    col_list, col_detail = st.columns([1, 2.6], gap="large")

    # --------------------------------------------------------
    # LISTA GIOCATORI (foglio "Tutti")
    # --------------------------------------------------------

    with col_list:

        st.markdown("#### Rosa Serie A")

        role_pick = st.radio(
            "Ruolo", ["P", "D", "C", "A"],
            format_func=lambda r: ROLE_LABELS[r],
            horizontal=True,
            key="role_pick_list",
        )

        search_list = st.text_input(
            "Cerca", placeholder="Cerca giocatore...", label_visibility="collapsed"
        )

        players_view = quotazioni_full[quotazioni_full["ruolo"] == role_pick].copy()

        if search_list:
            players_view = players_view[
                players_view["nome"].astype(str).str.lower().str.contains(search_list.lower(), na=False)
            ]

        players_view = players_view.sort_values("nome")

        st.caption(f"{len(players_view)} giocatori")

        with st.container(height=560):
            for _, row in players_view.iterrows():
                is_selected = row["id"] == st.session_state.selected_listone_id
                label = f"{'●' if is_selected else '○'} {row['nome']} · {row.get('squadra', '')}"
                if st.button(label, key=f"pbtn_{row['id']}", use_container_width=True):
                    st.session_state.selected_listone_id = row["id"]
                    st.rerun()

    # --------------------------------------------------------
    # DETTAGLIO GIOCATORE
    # --------------------------------------------------------

    def render_player_detail():

        listone_row = quotazioni_full[
            quotazioni_full["id"] == st.session_state.selected_listone_id
        ]

        if listone_row.empty:
            st.warning("Seleziona un giocatore dalla lista a sinistra.")
            return

        listone_row = listone_row.iloc[0]
        role = listone_row["ruolo"]
        selected_player_id = listone_row.get("player_id")
        has_stats = pd.notna(selected_player_id) and selected_player_id in df["player_id"].values

        display_name = listone_row["nome"]
        team_display = listone_row.get("squadra", "")
        quot = listone_row.get("quotazione_attuale", np.nan)
        fvm = listone_row.get("fvm", np.nan)

        player_history = None
        player_latest = None

        if has_stats:
            player_history = (
                df[df["player_id"] == selected_player_id].sort_values("season_start").copy()
            )
            player_latest = player_history.iloc[-1]
            display_name = player_latest["player_name"]
            team_display = player_latest["team"]

        st.markdown('<div class="player-header">', unsafe_allow_html=True)
        st.markdown(f'<div class="player-name">{display_name}</div>', unsafe_allow_html=True)

        meta_parts = [f"⚽ {team_display}", f"Ruolo: <b>{role}</b>"]
        if pd.notna(quot):
            meta_parts.append(f"Quotazione: <b>{int(quot)}</b>")
        if pd.notna(fvm):
            meta_parts.append(f"FVM: <b>{int(fvm)}</b>")
        st.markdown(
            f'<div class="player-meta">{" &nbsp;·&nbsp; ".join(meta_parts)}</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        if st.button("⭐ Aggiungi/rimuovi dalla shortlist"):
            if display_name in st.session_state.shortlist:
                st.session_state.shortlist.discard(display_name)
            else:
                st.session_state.shortlist.add(display_name)
            st.rerun()

        if not has_stats:
            st.info(
                "Nessuna statistica Understat disponibile per questo giocatore "
                "(nuovo arrivo in Serie A, infortunio prolungato o non ancora censito)."
            )
            return

        # ------------------------------------------------
        # VISTA PORTIERI — dati limitati, niente radar/value score
        # ------------------------------------------------

        if role == "P":

            st.markdown(
                '<div class="gk-note">⚠️ Understat non fornisce statistiche difensive '
                'per i portieri (parate, gol subiti, clean sheet). Qui sotto trovi solo '
                'disponibilità (presenze/minuti) e quotazione: usa questi dati insieme '
                'a fonti specifiche sui portieri prima di fare un\'offerta in asta.</div>',
                unsafe_allow_html=True,
            )

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Presenze", int(player_latest["matches_played"]))
            c2.metric("Minuti", f'{int(player_latest["minutes_played"]):,}'.replace(",", "."))
            c3.metric("Quotazione", int(quot) if pd.notna(quot) else "N/D")
            c4.metric("FVM", int(fvm) if pd.notna(fvm) else "N/D")

            st.markdown('<div class="section-title">📈 Presenze nel tempo</div>', unsafe_allow_html=True)

            history_display = player_history.copy()
            history_display["Stagione"] = history_display["season_start"].apply(format_season)

            fig_gk = go.Figure()
            fig_gk.add_trace(go.Bar(x=history_display["Stagione"], y=history_display["matches_played"], name="Presenze"))
            fig_gk.update_layout(height=340, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig_gk, use_container_width=True)

            return

        # ------------------------------------------------
        # VERDETTO
        # ------------------------------------------------

        player_latest_season = int(player_latest["season_start"])
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
            trend_text = f" &nbsp;·&nbsp; Trend: {arrow} {trend:+.1f} pt"

        value_text = f"{value_score:.1f}/100" if pd.notna(value_score) else "N/D"

        price_text = ""
        if pd.notna(quot) and pd.notna(value_score) and quot:
            vfm_ratio = value_score / quot
            price_text = f" &nbsp;·&nbsp; Val./Prezzo: {vfm_ratio:.2f}"

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

        # ----------------------------------------------------
        # KPI (ripuliti: niente coppie ridondanti tipo xA + xA/90)
        # ----------------------------------------------------

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Presenze", int(player_latest["matches_played"]))
        c2.metric("Minuti", f'{int(player_latest["minutes_played"]):,}'.replace(",", "."))
        c3.metric("⚽ Gol", int(player_latest["goals"]))
        c4.metric("🎯 Assist", int(player_latest["assists"]))
        c5.metric("xG", f'{player_latest["xg"]:.2f}')
        c6.metric("xA", f'{player_latest["xa"]:.2f}')

        # ----------------------------------------------------
        # STORICO
        # ----------------------------------------------------

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
            hovermode="x unified", height=340, margin=dict(l=20, r=20, t=50, b=20),
        )
        st.plotly_chart(fig_history, use_container_width=True)

        # ----------------------------------------------------
        # RADAR: GIOCATORE VS MEDIA DEI SIMILI
        # ----------------------------------------------------

        st.markdown('<div class="section-title">🎯 Confronto con giocatori simili</div>', unsafe_allow_html=True)
        st.caption(
            "Confronto solo con giocatori dello stesso ruolo e con minutaggio "
            "da titolare, per non mescolare Lautaro con le riserve."
        )

        starter_pct = st.slider(
            "Minuti minimi per essere considerato titolare (% della stagione)",
            min_value=20, max_value=90, value=50, step=5,
            key="starter_pct_slider",
        ) / 100

        min_minutes_threshold = starter_pct * MAX_SEASON_MINUTES

        peer_pool = df[
            (df["season_start"] == player_latest_season)
            & (df["role"] == role)
            & (df["player_id"] != selected_player_id)
            & (df["minutes_played"] >= min_minutes_threshold)
        ].copy()

        radar_metrics = {
            "goals_per_90": "Gol/90", "assists_per_90": "Assist/90",
            "xg_per_90": "xG/90", "xa_per_90": "xA/90",
            "shots_per_90": "Tiri/90", "key_passes_per_90": "Key Passes/90",
        }

        if len(peer_pool) >= 3:

            role_pool_all = df[
                (df["season_start"] == player_latest_season) & (df["role"] == role)
            ]

            peer_avg = {m: peer_pool[m].mean() for m in radar_metrics}
            player_vals = {m: float(player_latest[m]) for m in radar_metrics}
            scale_max = {
                m: max(role_pool_all[m].max(), player_vals[m], peer_avg[m], 0.01)
                for m in radar_metrics
            }

            categories = list(radar_metrics.values())

            player_radar = [player_vals[m] / scale_max[m] * 100 for m in radar_metrics]
            peer_radar = [peer_avg[m] / scale_max[m] * 100 for m in radar_metrics]

            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=player_radar + [player_radar[0]],
                theta=categories + [categories[0]],
                fill="toself", name=display_name,
                line=dict(color=PLAYER_COLOR), fillcolor="rgba(37,99,235,0.35)",
            ))
            fig_radar.add_trace(go.Scatterpolar(
                r=peer_radar + [peer_radar[0]],
                theta=categories + [categories[0]],
                fill="toself", name=f"Media {ROLE_LABELS[role].lower()} titolari",
                line=dict(color=PEER_COLOR), fillcolor="rgba(132,204,22,0.30)",
            ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                height=420, showlegend=True, margin=dict(l=30, r=30, t=30, b=30),
            )
            st.plotly_chart(fig_radar, use_container_width=True)

            st.caption(f"Media calcolata su {len(peer_pool)} {ROLE_LABELS[role].lower()} titolari nella stagione {format_season(player_latest_season)}.")

            # ------------------------------------------------
            # BARRE DI CONFRONTO (stile "share" come l'esempio)
            # ------------------------------------------------

            bars_html = ""
            for metric, label in radar_metrics.items():
                p_val = player_vals[metric]
                peer_val = peer_avg[metric]
                total = p_val + peer_val
                p_share = (p_val / total * 100) if total > 0 else 50
                peer_share = 100 - p_share

                bars_html += f"""
                <div class="split-row">
                    <div class="split-label">{label.upper()}</div>
                    <div class="split-bar-track">
                        <div class="split-bar-player" style="width:{p_share:.1f}%;"></div>
                        <div class="split-bar-peer" style="width:{peer_share:.1f}%;"></div>
                    </div>
                    <div class="split-values">
                        <span>{p_val:.2f}</span>
                        <span>{peer_val:.2f}</span>
                    </div>
                </div>
                """

            st.markdown(bars_html, unsafe_allow_html=True)

        else:
            st.info(
                "Non ci sono abbastanza giocatori titolari dello stesso ruolo per "
                "calcolare un confronto significativo. Prova ad abbassare la soglia minuti."
            )

        # ----------------------------------------------------
        # DETTAGLIO STAGIONALE (unica tabella, niente doppioni)
        # ----------------------------------------------------

        st.markdown('<div class="section-title">📋 Dettaglio stagionale</div>', unsafe_allow_html=True)

        detail = history_display[[
            "Stagione", "team", "matches_played", "minutes_played",
            "goals", "assists", "xg", "xa", "shots_total", "key_passes",
            "yellow_cards", "red_cards", "value_score", "tier",
        ]].rename(columns={
            "team": "Squadra", "matches_played": "Presenze", "minutes_played": "Minuti",
            "goals": "Gol", "assists": "Assist", "xg": "xG", "xa": "xA",
            "shots_total": "Tiri", "key_passes": "Key Passes",
            "yellow_cards": "Gialli", "red_cards": "Rossi",
            "value_score": "Value Score", "tier": "Tier",
        })
        detail["xG"] = detail["xG"].round(2)
        detail["xA"] = detail["xA"].round(2)

        st.dataframe(detail, use_container_width=True, hide_index=True)

    with col_detail:
        render_player_detail()


# ============================================================
# TAB — RANKING
# ============================================================

with tab_ranking:

    st.caption(f"Universo: tutti i giocatori del listone · statistiche stagione {format_season(latest_season)} dove disponibili")

    f1, f2, f3, f4 = st.columns([1.2, 1.5, 1.2, 1.5])

    with f1:
        roles_selected = st.multiselect("Ruolo", ["P", "D", "C", "A"], default=["P", "D", "C", "A"])
    with f2:
        teams_available = sorted(quotazioni_full["squadra"].dropna().unique().tolist())
        teams_selected = st.multiselect("Squadra", teams_available, default=[])
    with f3:
        min_minutes = st.slider("Minuti minimi", 0, 3420, 0, step=90)
    with f4:
        search_ranking = st.text_input("Cerca giocatore", placeholder="Es. Lautaro, Barella...")

    stats_latest = latest_players[[
        "player_id", "matches_played", "minutes_played", "goals", "assists", "xg", "xa",
        "performance_score", "reliability_score", "value_score", "tier", "trend_delta",
    ]]

    ranked = quotazioni_full.merge(stats_latest, on="player_id", how="left")
    ranked = ranked[ranked["ruolo"].isin(roles_selected)]
    ranked["minutes_played"] = ranked["minutes_played"].fillna(0)
    ranked = ranked[ranked["minutes_played"] >= min_minutes]

    if teams_selected:
        ranked = ranked[ranked["squadra"].isin(teams_selected)]

    if search_ranking:
        ranked = ranked[ranked["nome"].str.lower().str.contains(search_ranking.lower(), na=False)]

    ranked["value_for_money"] = (ranked["value_score"] / ranked["quotazione_attuale"]).replace([np.inf, -np.inf], np.nan)

    ranked = ranked.sort_values("value_score", ascending=False, na_position="last")

    display_cols = {
        "nome": "Giocatore", "squadra": "Squadra", "ruolo": "Ruolo", "tier": "Tier",
        "value_score": "Value Score", "reliability_score": "Affidabilità", "trend_delta": "Trend",
        "quotazione_attuale": "Quot.", "fvm": "FVM", "value_for_money": "Val./Prezzo",
        "matches_played": "Presenze", "minutes_played": "Minuti",
        "goals": "Gol", "assists": "Assist", "xg": "xG", "xa": "xA",
    }
    table = ranked[list(display_cols.keys())].rename(columns=display_cols)
    table.insert(0, "Shortlist", table["Giocatore"].isin(list(st.session_state.shortlist)))

    st.caption(f"{len(table)} giocatori corrispondenti ai filtri")

    edited = st.data_editor(
        table, use_container_width=True, hide_index=True, height=520,
        disabled=[c for c in table.columns if c != "Shortlist"],
        column_config={
            "Shortlist": st.column_config.CheckboxColumn(required=True),
            "Value Score": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
            "Affidabilità": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
            "Trend": st.column_config.NumberColumn(format="%+.1f"),
        },
        key="ranking_editor",
    )
    st.session_state.shortlist = set(edited.loc[edited["Shortlist"], "Giocatore"].tolist())

    st.markdown(
        "<span class='tier-S'>S</span> top assoluti &nbsp; "
        "<span class='tier-A'>A</span> ottimi &nbsp; "
        "<span class='tier-B'>B</span> buoni &nbsp; "
        "<span class='tier-C'>C</span> nella media &nbsp; "
        "<span class='tier-D'>D</span> da evitare",
        unsafe_allow_html=True,
    )
    st.caption(
        "Per i portieri (P) Understat non fornisce statistiche difensive: "
        "Value Score e Tier non sono calcolati, restano solo quotazione e FVM."
    )


# ============================================================
# TAB — CONFRONTO
# ============================================================

with tab_compare:

    st.caption("Confronta fino a 4 giocatori (stagione più recente disponibile).")

    default_selection = list(st.session_state.shortlist)[:4]

    compare_names = st.multiselect(
        "Giocatori da confrontare",
        quotazioni_full["nome"].sort_values().unique().tolist(),
        default=[n for n in default_selection if n in quotazioni_full["nome"].values],
        max_selections=4,
    )

    if len(compare_names) < 2:
        st.info("Seleziona almeno due giocatori (puoi partire dalla tua shortlist).")
    else:
        compare_ids = quotazioni_full[quotazioni_full["nome"].isin(compare_names)]["player_id"]
        compare_df = latest_players[latest_players["player_id"].isin(compare_ids)].copy()

        if compare_df.empty:
            st.warning("Nessuno dei giocatori selezionati ha statistiche Understat disponibili.")
        else:
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
                    fill="toself", name=row["player_name"],
                ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True)), height=480, showlegend=True,
                title="Confronto per 90 minuti",
            )
            st.plotly_chart(fig_radar, use_container_width=True)

            compare_cols = {
                "player_name": "Giocatore", "team": "Squadra", "role": "Ruolo",
                "tier": "Tier", "value_score": "Value Score", "reliability_score": "Affidabilità",
                "goals": "Gol", "assists": "Assist", "xg": "xG", "xa": "xA", "minutes_played": "Minuti",
            }
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
    f"{df['player_id'].nunique():,} giocatori con statistiche · "
    f"Ultima stagione disponibile: {format_season(latest_season)} · "
    "Value Score e Tier sono stime basate su dati Understat, non sostituiscono la valutazione personale."
)
