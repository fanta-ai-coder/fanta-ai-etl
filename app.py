import os
import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client

st.set_page_config(page_title="Fantacalcio Analytics Dashboard", layout="wide")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


supabase = init_supabase()


@st.cache_data(ttl=600)
def load_stats():
    """Statistiche voto/fantavoto per giocatore e giornata."""
    res = supabase.table("player_stats_history").select("*").execute()
    return pd.DataFrame(res.data)


@st.cache_data(ttl=600)
def load_quotazioni():
    """Anagrafica/quotazioni giocatori per stagione (rosa quotata)."""
    res = supabase.table("giocatori_quotazioni").select("*").execute()
    return pd.DataFrame(res.data)


# ============================================================
# DETTAGLIO GIOCATORE (usato dal nuovo tab "Rosa & Quotazioni")
# ============================================================

def render_player_detail(player_id, df, quot, df_filtered, sidebar_seasons):
    p_all = df[df["player_id"] == player_id].sort_values(["stagione", "giornata"])
    p_quot_rows = quot[quot["player_id"] == player_id].sort_values("stagione")

    if p_quot_rows.empty and p_all.empty:
        st.warning("Nessun dato disponibile per questo giocatore.")
        return

    # ---- Header: anagrafica dall'ultima quotazione disponibile ----
    last_quot = p_quot_rows.iloc[-1] if not p_quot_rows.empty else None
    nome = last_quot["nome"] if last_quot is not None else p_all.iloc[-1]["nome"]

    st.markdown(f"### {nome}")

    if last_quot is not None:
        h1, h2, h3, h4 = st.columns(4)
        h1.metric("Ruolo", last_quot["ruolo"])
        h2.metric("Squadra", last_quot["squadra"])
        h3.metric("Quotazione", last_quot["quotazione_attuale"])
        h4.metric("FVM", last_quot["fvm"])
        if bool(last_quot.get("ceduto", False)):
            st.warning(
                f"⚠️ Segnato come CEDUTO nell'ultima stagione quotata "
                f"({last_quot['stagione']})."
            )

    if p_all.empty:
        st.info("Nessuna statistica storica (voti) trovata per questo giocatore.")
        return

    # Statistiche calcolate sul periodo selezionato nella sidebar
    # (stesso filtro Stagione/Ruolo usato dalle altre tab).
    p_view = p_all[p_all["stagione"].isin(sidebar_seasons)] if sidebar_seasons else p_all

    if p_view.empty:
        st.info("Nessuna partita di questo giocatore nel periodo selezionato in sidebar.")
        return

    # ---- KPI principali ----
    st.markdown("#### Riepilogo periodo selezionato (sidebar)")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Partite", int(p_view["voto"].count()))
    k2.metric("Media voto", round(p_view["voto"].mean(), 2))
    k3.metric("Gol", int(p_view["gf"].sum()))
    k4.metric("Assist", int(p_view["ass"].sum()))

    # ---- Bonus / Malus (conteggi grezzi, non punteggio fantacalcio:
    # le regole di punteggio variano da lega a lega) ----
    st.markdown("#### Bonus")
    b1, b2, b3 = st.columns(3)
    b1.metric("Gol fatti", int(p_view["gf"].sum()))
    b2.metric("Assist", int(p_view["ass"].sum()))
    b3.metric("Rigori segnati", int(p_view["rf"].sum()))

    st.markdown("#### Malus")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Ammonizioni", int(p_view["amm"].sum()))
    m2.metric("Espulsioni", int(p_view["esp"].sum()))
    m3.metric("Autogol", int(p_view["au"].sum()))
    m4.metric("Rigori sbagliati", int(p_view["rs"].sum()))
    m5.metric("Gol subiti", int(p_view["gs"].sum()))
    st.caption(
        "Nota: 'Gol subiti' ha senso solo per i portieri, mostrato a 0 per gli altri ruoli."
    )

    # ---- Presenze / assenze stimate ----
    st.markdown("#### Presenze")
    presenze_rows = []
    for season in sorted(p_view["stagione"].unique()):
        giornate_totali = df[df["stagione"] == season]["giornata"].nunique()
        giornate_giocate = p_view[p_view["stagione"] == season]["giornata"].nunique()
        presenze_rows.append({
            "Stagione": season,
            "Giornate nel dataset": giornate_totali,
            "Presenze": giornate_giocate,
            "Assenze (stimate)": giornate_totali - giornate_giocate,
        })
    st.dataframe(pd.DataFrame(presenze_rows), use_container_width=True, hide_index=True)
    st.caption(
        "⚠️ 'Assenze stimate' = giornate del dataset in cui il giocatore non ha un voto "
        "registrato. Non è un dato di infortunio: nei dati attuali non esiste un campo "
        "specifico che distingua infortunio, squalifica o esclusione tecnica."
    )

    # ---- Statistiche per anno: storico COMPLETO, non filtrato dalla sidebar ----
    st.markdown("#### Statistiche per anno (storico completo)")
    per_anno = (
        p_all.groupby("stagione")
        .agg(
            Partite=("voto", "count"),
            Media_Voto=("voto", "mean"),
            Dev_Std_Voto=("voto", "std"),
            Gol=("gf", "sum"),
            Assist=("ass", "sum"),
            Ammonizioni=("amm", "sum"),
            Espulsioni=("esp", "sum"),
        )
        .reset_index()
        .round(2)
    )
    st.dataframe(per_anno, use_container_width=True, hide_index=True)

    # ---- Trend voto/fantavoto (storico completo) ----
    st.markdown("#### Andamento voto/fantavoto")
    fig_trend = px.line(
        p_all, x="giornata", y=["voto", "fanta_voto"], color="stagione",
        markers=True, title=f"Andamento per {nome}",
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    # ---- Distribuzione gol (periodo selezionato) ----
    st.markdown("#### Distribuzione gol per partita (periodo selezionato)")
    if p_view["gf"].sum() == 0:
        st.info("Nessun gol segnato nel periodo selezionato.")
    else:
        dist = p_view["gf"].value_counts().sort_index().reset_index()
        dist.columns = ["Gol nella partita", "Numero partite"]
        fig_dist = px.bar(
            dist, x="Gol nella partita", y="Numero partite",
            title="Distribuzione gol a partita",
        )
        st.plotly_chart(fig_dist, use_container_width=True)

    # ---- Continuità di rendimento (deviazione standard del voto) ----
    st.markdown("#### Continuità di rendimento (voto)")
    player_std = p_view["voto"].std()

    if pd.isna(player_std):
        st.info("Non ci sono abbastanza partite nel periodo selezionato per calcolare la continuità.")
    else:
        peer_std = df_filtered.groupby("player_id")["voto"].std().dropna()

        col_a, col_b = st.columns(2)
        col_a.metric("Deviazione standard voto", round(player_std, 2))

        if len(peer_std) > 3:
            pct_std = (peer_std < player_std).mean() * 100
            if pct_std >= 66:
                label = "🔴 Altalenante (rendimento meno prevedibile della media)"
            elif pct_std <= 33:
                label = "🟢 Continuo (rendimento più stabile della media)"
            else:
                label = "🟡 Nella media"
            col_b.metric("Percentile variabilità", f"{pct_std:.0f}°")
            st.markdown(f"**Valutazione:** {label}")
            st.caption(
                "Calcolato confrontando la deviazione standard del voto di questo "
                "giocatore con quella di tutti i giocatori nel filtro Stagione/Ruolo "
                "attivo in sidebar. Percentile alto = variabilità più alta della "
                "maggior parte dei colleghi nello stesso filtro (voti altalenanti); "
                "percentile basso = rendimento più costante."
            )
        else:
            st.caption(
                "Non ci sono abbastanza giocatori nel filtro corrente per un confronto significativo."
            )

    # ---- Dati grezzi + export ----
    with st.expander("📄 Dati grezzi (storico completo)"):
        st.dataframe(p_all, use_container_width=True, hide_index=True)
        csv = p_all.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Scarica storico completo (CSV)",
            data=csv,
            file_name=f"{nome}_storico.csv",
            mime="text/csv",
        )


# ============================================================
# APP
# ============================================================

st.title("⚽ Dashboard Analitica Voti & Fantavoti Serie A")

try:
    df = load_stats()
    quot = load_quotazioni()
except Exception as e:
    st.error(f"Errore nel caricamento dei dati da Supabase: {e}")
    st.stop()

if df.empty:
    st.warning("Nessun dato presente in player_stats_history. Esegui prima lo script di ingestion.")
    st.stop()

# Sidebar filtri globali (validi per tutte le tab)
st.sidebar.header("🎯 Filtri Globali")
all_seasons = sorted(df["stagione"].unique())
selected_season = st.sidebar.multiselect(
    "Stagione", options=all_seasons, default=all_seasons[-1:]
)
selected_role = st.sidebar.multiselect(
    "Ruolo", options=["P", "D", "C", "A"], default=["P", "D", "C", "A"]
)

df_filtered = df[
    (df["stagione"].isin(selected_season)) & (df["ruolo"].isin(selected_role))
]

tab0, tab1, tab2, tab3 = st.tabs([
    "📇 Rosa & Quotazioni",
    "👤 Profilo Singolo Giocatore",
    "⚔️ Confronto Giocatori",
    "🛡️ Analisi Squadre",
])

# ------------------------------------------------------------
# TAB 0: ROSA & QUOTAZIONI (nuovo)
# ------------------------------------------------------------
with tab0:
    st.subheader("Rosa quotata")

    if quot.empty:
        st.warning(
            "Nessun dato in giocatori_quotazioni. Esegui prima "
            "fantacalcio_quotazioni_load.py per la stagione desiderata."
        )
    else:
        col_list, col_detail = st.columns([1, 2])

        with col_list:
            quot_seasons = sorted(quot["stagione"].unique())
            quot_season_sel = st.multiselect(
                "Stagione quotazioni", options=quot_seasons,
                default=quot_seasons[-1:], key="quot_season",
            )
            quot_role_sel = st.multiselect(
                "Ruolo", options=["P", "D", "C", "A"],
                default=["P", "D", "C", "A"], key="quot_role",
            )
            show_ceduti = st.checkbox("Includi giocatori ceduti", value=False)

            quot_view = quot[
                quot["stagione"].isin(quot_season_sel)
                & quot["ruolo"].isin(quot_role_sel)
            ]
            if not show_ceduti:
                quot_view = quot_view[~quot_view["ceduto"]]

            quot_view = quot_view.sort_values("nome")
            st.caption(f"{len(quot_view)} giocatori")

            options_df = quot_view[["player_id", "nome", "squadra"]].drop_duplicates(
                subset="player_id"
            )

            if options_df.empty:
                st.info("Nessun giocatore con questi filtri.")
                selected_id = None
            else:
                labels = [
                    f"{row.nome} ({row.squadra})" for row in options_df.itertuples()
                ]
                label_to_id = dict(zip(labels, options_df["player_id"]))
                selected_label = st.radio(
                    "Seleziona giocatore", options=labels,
                    label_visibility="collapsed",
                )
                selected_id = label_to_id[selected_label]

        with col_detail:
            if selected_id is None:
                st.info("Seleziona un giocatore dalla lista a sinistra.")
            else:
                render_player_detail(
                    selected_id, df, quot, df_filtered, selected_season
                )

# ------------------------------------------------------------
# TAB 1: PROFILO GIOCATORE (esistente, invariato)
# ------------------------------------------------------------
with tab1:
    player_list = sorted(df_filtered["nome"].unique())
    selected_player = st.selectbox("Seleziona Calciatore", options=player_list)

    p_df = df_filtered[df_filtered["nome"] == selected_player].sort_values(by=["stagione", "giornata"])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Media Voto", round(p_df["voto"].mean(), 2))
    col2.metric("Media FantaVoto", round(p_df["fanta_voto"].mean(), 2))
    col3.metric("Gol Fatti Totali", int(p_df["gf"].sum()))
    col4.metric("Assist Totali", int(p_df["ass"].sum()))

    fig = px.line(p_df, x="giornata", y=["voto", "fanta_voto"], color="stagione",
                  title=f"Andamento Voti per {selected_player}", markers=True)
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------
# TAB 2: CONFRONTO GIOCATORI (esistente, invariato)
# ------------------------------------------------------------
with tab2:
    st.subheader("Confronta fino a 4 Giocatori")
    comp_players = st.multiselect("Scegli Giocatori da Confrontare", options=sorted(df_filtered["nome"].unique()), max_selections=4)

    if comp_players:
        c_df = df_filtered[df_filtered["nome"].isin(comp_players)]
        summary = c_df.groupby("nome").agg(
            Partite=('voto', 'count'),
            Media_Voto=('voto', 'mean'),
            Media_Fantavoto=('fanta_voto', 'mean'),
            Gol=('gf', 'sum'),
            Assist=('ass', 'sum'),
            Ammonizioni=('amm', 'sum')
        ).reset_index()

        st.dataframe(summary.style.highlight_max(axis=0, color='lightgreen'))

        fig_bar = px.bar(c_df, x="nome", y="fanta_voto", color="nome", barmode="group", title="Distribuzione FantaVoti")
        st.plotly_chart(fig_bar, use_container_width=True)

# ------------------------------------------------------------
# TAB 3: ANALISI SQUADRE (esistente, invariato)
# ------------------------------------------------------------
with tab3:
    st.subheader("Rendimento Medio per Squadra e Ruolo")
    team_summary = df_filtered.groupby(["squadra", "ruolo"]).agg(
        Media_Voto=('voto', 'mean'),
        Media_Fantavoto=('fanta_voto', 'mean')
    ).reset_index()

    fig_heat = px.density_heatmap(team_summary, x="squadra", y="ruolo", z="Media_Fantavoto",
                                  title="Heatmap Media FantaVoto per Squadra e Ruolo", color_continuous_scale="Viridis")
    st.plotly_chart(fig_heat, use_container_width=True)
