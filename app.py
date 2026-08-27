import os
import pandas as pd
import streamlit as st

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
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        max-width: 1650px;
    }

    section[data-testid="stSidebar"] {
        min-width: 300px;
        max-width: 340px;
    }

    .main-title {
        font-size: 38px;
        font-weight: 800;
        margin-bottom: 0;
    }

    .subtitle {
        color: #6b7280;
        font-size: 15px;
        margin-top: -5px;
        margin-bottom: 20px;
    }

    div[data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 12px;
    }

    div[data-testid="stMetricLabel"] {
        font-size: 12px;
    }

    div[data-testid="stMetricValue"] {
        font-size: 22px;
        font-weight: 700;
    }

    .section-title {
        font-size: 19px;
        font-weight: 750;
        margin-top: 18px;
        margin-bottom: 8px;
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
    st.error(
        "⚠️ Credenziali Supabase non trovate. "
        "Configura SUPABASE_URL e SUPABASE_KEY."
    )
    st.stop()


@st.cache_resource
def init_supabase():
    return create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
    )


try:
    supabase = init_supabase()

except Exception as e:
    st.error(f"Errore nella connessione a Supabase: {e}")
    st.stop()


# ============================================================
# CARICAMENTO TABELLA QUOTAZIONI
# ============================================================

@st.cache_data(ttl=600, show_spinner=False)
def load_table(table_name):

    all_rows = []

    page_size = 1000
    start = 0

    while True:

        response = (
            supabase
            .table(table_name)
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


with st.spinner("Caricamento quotazioni..."):

    try:
        quotazioni = load_table("quotazioni")

    except Exception as e:
        st.error(
            f"Errore durante la lettura della tabella `quotazioni`: {e}"
        )
        st.stop()


if quotazioni.empty:

    st.warning(
        "La tabella `quotazioni` non contiene dati."
    )

    st.stop()


# ============================================================
# NORMALIZZAZIONE MINIMA
# ============================================================

# NON vengono creati nuovi dati.
# Convertiamo solamente alcune colonne numeriche, se esistono,
# per permettere ordinamento e visualizzazione corretti.

numeric_columns = [
    "id",
    "quotazione_attuale",
    "quotazione_iniziale",
    "fvm",
]

for col in numeric_columns:

    if col in quotazioni.columns:

        quotazioni[col] = pd.to_numeric(
            quotazioni[col],
            errors="coerce"
        )


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">⚽ FantaAI</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">'
    'Lista quotazioni Fantacalcio · Dati dalla tabella quotazioni'
    '</div>',
    unsafe_allow_html=True,
)


# ============================================================
# INFORMAZIONI TABELLA
# ============================================================

c1, c2, c3 = st.columns(3)

c1.metric(
    "Giocatori",
    len(quotazioni)
)

if "ruolo" in quotazioni.columns:
    c2.metric(
        "Ruoli",
        quotazioni["ruolo"].nunique()
    )
else:
    c2.metric(
        "Colonne",
        len(quotazioni.columns)
    )

if "squadra" in quotazioni.columns:
    c3.metric(
        "Squadre",
        quotazioni["squadra"].nunique()
    )
else:
    c3.metric(
        "Record",
        len(quotazioni)
    )


# ============================================================
# FILTRI
# ============================================================

st.markdown(
    '<div class="section-title">🔎 Lista giocatori</div>',
    unsafe_allow_html=True,
)


f1, f2, f3, f4 = st.columns(
    [1.0, 1.5, 2.0, 1.5]
)


# ------------------------------------------------------------
# RUOLO
# ------------------------------------------------------------

with f1:

    if "ruolo" in quotazioni.columns:

        roles = (
            quotazioni["ruolo"]
            .dropna()
            .astype(str)
            .sort_values()
            .unique()
            .tolist()
        )

        roles_with_all = ["Tutti"] + roles

        role_selected = st.selectbox(
            "Ruolo",
            roles_with_all,
        )

    else:

        role_selected = "Tutti"


# ------------------------------------------------------------
# SQUADRA
# ------------------------------------------------------------

with f2:

    if "squadra" in quotazioni.columns:

        teams = (
            quotazioni["squadra"]
            .dropna()
            .astype(str)
            .sort_values()
            .unique()
            .tolist()
        )

        team_selected = st.selectbox(
            "Squadra",
            ["Tutte"] + teams,
        )

    else:

        team_selected = "Tutte"


# ------------------------------------------------------------
# RICERCA
# ------------------------------------------------------------

with f3:

    if "nome" in quotazioni.columns:

        search = st.text_input(
            "Cerca giocatore",
            placeholder="Es. Lautaro, Barella...",
        )

    else:

        search = st.text_input(
            "Cerca",
            placeholder="Cerca...",
        )


# ------------------------------------------------------------
# ORDINAMENTO
# ------------------------------------------------------------

with f4:

    sort_options = []

    if "nome" in quotazioni.columns:
        sort_options.append("Nome")

    if "quotazione_attuale" in quotazioni.columns:
        sort_options.append("Quotazione attuale")

    if "quotazione_iniziale" in quotazioni.columns:
        sort_options.append("Quotazione iniziale")

    if "fvm" in quotazioni.columns:
        sort_options.append("FVM")

    if not sort_options:
        sort_options = ["ID"]

    sort_selected = st.selectbox(
        "Ordina per",
        sort_options,
    )


# ============================================================
# APPLICAZIONE FILTRI
# ============================================================

filtered = quotazioni.copy()


# Ruolo
if (
    role_selected != "Tutti"
    and "ruolo" in filtered.columns
):

    filtered = filtered[
        filtered["ruolo"].astype(str) == role_selected
    ]


# Squadra
if (
    team_selected != "Tutte"
    and "squadra" in filtered.columns
):

    filtered = filtered[
        filtered["squadra"].astype(str) == team_selected
    ]


# Ricerca nome
if search and "nome" in filtered.columns:

    filtered = filtered[
        filtered["nome"]
        .astype(str)
        .str.contains(
            search,
            case=False,
            na=False
        )
    ]


# ============================================================
# ORDINAMENTO
# ============================================================

sort_mapping = {
    "Nome": "nome",
    "Quotazione attuale": "quotazione_attuale",
    "Quotazione iniziale": "quotazione_iniziale",
    "FVM": "fvm",
    "ID": "id",
}

sort_column = sort_mapping.get(
    sort_selected
)

if sort_column in filtered.columns:

    if sort_column == "nome":

        filtered = filtered.sort_values(
            sort_column,
            ascending=True,
            na_position="last",
        )

    else:

        filtered = filtered.sort_values(
            sort_column,
            ascending=False,
            na_position="last",
        )


# ============================================================
# RISULTATI
# ============================================================

st.caption(
    f"{len(filtered)} giocatori visualizzati "
    f"su {len(quotazioni)} totali"
)


# ============================================================
# PREPARAZIONE VISUALIZZAZIONE
# ============================================================

display_df = filtered.copy()


# ------------------------------------------------------------
# Rinomina SOLO le colonne esistenti.
# Non vengono create nuove colonne.
# ------------------------------------------------------------

column_labels = {

    "id": "ID",

    "nome": "Giocatore",

    "ruolo": "Ruolo",

    "squadra": "Squadra",

    "quotazione_attuale": "Quotazione",

    "quotazione_iniziale": "Quotazione iniziale",

    "fvm": "FVM",
}


display_df = display_df.rename(
    columns={
        col: column_labels[col]
        for col in display_df.columns
        if col in column_labels
    }
)


# ============================================================
# CONFIGURAZIONE COLONNE
# ============================================================

column_config = {}


if "Quotazione" in display_df.columns:

    column_config["Quotazione"] = st.column_config.NumberColumn(
        "Quotazione",
        format="%d",
    )


if "Quotazione iniziale" in display_df.columns:

    column_config["Quotazione iniziale"] = st.column_config.NumberColumn(
        "Quotazione iniziale",
        format="%d",
    )


if "FVM" in display_df.columns:

    column_config["FVM"] = st.column_config.NumberColumn(
        "FVM",
        format="%d",
    )


# ============================================================
# TABELLA
# ============================================================

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    height=650,
    column_config=column_config,
)


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    f"FantaAI · {len(quotazioni):,} giocatori "
    "· Fonte: tabella Supabase `quotazioni`"
)