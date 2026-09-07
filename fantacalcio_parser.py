import re
from pathlib import Path

import pandas as pd


# ============================================================
# CONFIGURAZIONE
# ============================================================

PLAYER_ROLES = {"P", "D", "C", "A"}

EXPECTED_COLUMNS = [
    "Cod.",
    "Ruolo",
    "Nome",
    "Voto",
    "Gf",
    "Gs",
    "Rp",
    "Rs",
    "Rf",
    "Au",
    "Amm",
    "Esp",
    "Ass",
    "Gdv",
    "Gdp",
]


# ============================================================
# PULIZIA TESTO
# ============================================================

def clean_text(value):
    """
    Normalizza un valore proveniente dall'Excel.
    """

    if pd.isna(value):
        return ""

    return str(value).strip()


# ============================================================
# PULIZIA NUMERI
# ============================================================

def clean_number(value, default=0):
    """
    Converte numeri Excel/stringhe in int.

    Esempi:
        1       -> 1
        "1"     -> 1
        "1.0"   -> 1
        ""      -> default
        NaN     -> default
    """

    if pd.isna(value):
        return default

    value = str(value).strip()

    if not value:
        return default

    try:
        return int(
            float(
                value.replace(",", ".")
            )
        )

    except (ValueError, TypeError):
        return default


# ============================================================
# PULIZIA VOTO
# ============================================================

def clean_vote(value):
    """
    Converte il voto Fantacalcio.

    Regola fondamentale:

        6       -> 6.0
        5,5     -> 5.5
        6*      -> None
        5,5*    -> None
        vuoto   -> None

    Il simbolo '*' indica che il giocatore NON deve essere
    considerato a voto.

    Non dobbiamo quindi rimuovere semplicemente '*':
    dobbiamo usarlo come indicatore per restituire None.
    """

    if pd.isna(value):
        return None

    value = str(value).strip()

    if not value:
        return None

    # --------------------------------------------------------
    # IMPORTANTE
    #
    # Se il voto contiene '*', il giocatore NON è a voto.
    #
    # Esempi:
    #   "6*"   -> None
    #   "6,5*" -> None
    # --------------------------------------------------------

    if "*" in value:
        return None

    # --------------------------------------------------------
    # Normalizza decimali italiani
    # --------------------------------------------------------

    value = value.replace(",", ".")

    # --------------------------------------------------------
    # Cerca il numero
    # --------------------------------------------------------

    match = re.search(
        r"-?\d+(?:\.\d+)?",
        value
    )

    if not match:
        return None

    try:
        return float(
            match.group(0)
        )

    except ValueError:
        return None


# ============================================================
# RIGA GIOCATORE
# ============================================================

def is_player_row(row):
    """
    Determina se una riga rappresenta un giocatore.
    """

    if len(row) < 4:
        return False

    code = clean_text(
        row.iloc[0]
    )

    role = clean_text(
        row.iloc[1]
    ).upper()

    if not code:
        return False

    if role not in PLAYER_ROLES:
        return False

    try:
        int(
            float(code)
        )

        return True

    except ValueError:
        return False


# ============================================================
# RIGA HEADER
# ============================================================

def is_header_row(row):
    """
    Riconosce:

        Cod. | Ruolo | Nome | Voto | ...
    """

    if len(row) < 4:
        return False

    first = clean_text(
        row.iloc[0]
    ).lower()

    second = clean_text(
        row.iloc[1]
    ).lower()

    third = clean_text(
        row.iloc[2]
    ).lower()

    fourth = clean_text(
        row.iloc[3]
    ).lower()

    return (
        first in {
            "cod.",
            "cod",
            "codice",
        }
        and second == "ruolo"
        and third == "nome"
        and fourth == "voto"
    )


# ============================================================
# RIGA SQUADRA
# ============================================================

def is_probable_team_row(row):
    """
    Le righe squadra sono del tipo:

        ATALANTA
        BOLOGNA
        INTER

    senza Cod/Ruolo/Nome/Voto.
    """

    if len(row) == 0:
        return False

    first = clean_text(
        row.iloc[0]
    )

    if not first:
        return False

    # Se la prima colonna è numerica, non è una squadra
    try:
        float(first)

        return False

    except ValueError:
        pass

    ignored = {
        "cod.",
        "ruolo",
        "nome",
        "voto",
        "gf",
        "gs",
        "rp",
        "rs",
        "rf",
        "au",
        "amm",
        "esp",
        "ass",
        "gdv",
        "gdp",
    }

    if first.lower() in ignored:
        return False

    return True


# ============================================================
# TROVA IL FOGLIO FANTACALCIO
# ============================================================

def load_fantacalcio_sheet(file_path):
    """
    Carica ESCLUSIVAMENTE il foglio 'Fantacalcio'.

    Non vengono utilizzati i fogli:
        - Statistico
        - Italia
        - altri eventuali fogli

    Il nome viene cercato in modo case-insensitive.
    """

    file_path = Path(file_path)

    # --------------------------------------------------------
    # Legge i nomi dei fogli disponibili
    # --------------------------------------------------------

    try:

        excel_file = pd.ExcelFile(
            file_path
        )

    except Exception as exc:

        raise ValueError(
            f"Impossibile aprire il file Excel "
            f"{file_path}: {exc}"
        )

    sheets = excel_file.sheet_names

    # --------------------------------------------------------
    # Cerca "Fantacalcio" ignorando maiuscole/minuscole
    # --------------------------------------------------------

    fantacalcio_sheet = None

    for sheet in sheets:

        if (
            str(sheet)
            .strip()
            .lower()
            == "fantacalcio"
        ):

            fantacalcio_sheet = sheet
            break

    if fantacalcio_sheet is None:

        raise ValueError(
            f"Foglio 'Fantacalcio' non trovato "
            f"nel file {file_path}. "
            f"Fogli disponibili: {sheets}"
        )

    print(
        f"   📑 Foglio utilizzato: "
        f"'{fantacalcio_sheet}'"
    )

    # --------------------------------------------------------
    # Legge SOLO questo foglio
    # --------------------------------------------------------

    return pd.read_excel(
        file_path,
        sheet_name=fantacalcio_sheet,
        header=None,
        dtype=object,
    )


# ============================================================
# PARSER EXCEL
# ============================================================

def parse_excel(
    file_path,
    stagione,
    giornata,
):
    """
    Estrae i dati dal foglio Fantacalcio.

    Regole:

    1. Viene utilizzato esclusivamente il foglio
       "Fantacalcio".

    2. Le righe con un voto contenente '*'
       vengono registrate con voto=None.

    3. Le righe con voto=None NON saranno considerate
       "presenze a voto" dalla dashboard.

    4. Le statistiche numeriche Gf/Gs/Rp/Rs/Rf/Au/
       Amm/Esp/Ass/Gdv/Gdp vengono comunque conservate.
    """

    file_path = Path(
        file_path
    )

    print(
        f"📄 Parsing: {file_path}"
    )

    # ========================================================
    # CARICA SOLO FOGLIO FANTACALCIO
    # ========================================================

    df = load_fantacalcio_sheet(
        file_path
    )

    records = []

    current_team = None

    # Contatore diagnostico
    total_players = 0
    players_with_vote = 0
    players_without_vote = 0

    # ========================================================
    # SCANSIONE RIGHE
    # ========================================================

    for i, row in df.iterrows():

        # ----------------------------------------------------
        # HEADER
        # ----------------------------------------------------

        if is_header_row(row):

            # La riga precedente contiene la squadra
            if i > 0:

                previous_row = df.iloc[
                    i - 1
                ]

                candidate = clean_text(
                    previous_row.iloc[0]
                )

                if candidate:

                    current_team = (
                        candidate.upper()
                    )

            continue

        # ----------------------------------------------------
        # EVENTUALE RIGA SQUADRA
        # ----------------------------------------------------

        if is_probable_team_row(row):

            # Se la riga ha struttura da giocatore,
            # non deve essere interpretata come squadra.
            if not is_player_row(row):

                candidate = clean_text(
                    row.iloc[0]
                )

                if candidate:

                    current_team = (
                        candidate.upper()
                    )

                continue

        # ----------------------------------------------------
        # GIOCATORE
        # ----------------------------------------------------

        if is_player_row(row):

            player_id = clean_number(
                row.iloc[0],
                default=None,
            )

            ruolo = clean_text(
                row.iloc[1]
            ).upper()

            nome = clean_text(
                row.iloc[2]
            )

            # ------------------------------------------------
            # VOTO
            # ------------------------------------------------

            raw_vote = (
                row.iloc[3]
                if len(row) > 3
                else None
            )

            voto = clean_vote(
                raw_vote
            )

            if player_id is None:
                continue

            if not current_team:

                raise ValueError(
                    f"Squadra non determinata "
                    f"per {nome} "
                    f"(ID {player_id}) "
                    f"in {file_path}"
                )

            # ------------------------------------------------
            # FUNZIONE PER LE COLONNE NUMERICHE
            # ------------------------------------------------

            def col(
                index,
                default=0,
            ):
                """
                Legge row.iloc[index] solo se la colonna
                esiste.

                Formato tipico:
                    Cod.
                    Ruolo
                    Nome
                    Voto
                    Gf
                    Gs
                    Rp
                    Rs
                    Rf
                    Au
                    Amm
                    Esp
                    Ass
                    Gdv
                    Gdp
                """

                if index < len(row):

                    return clean_number(
                        row.iloc[index],
                        default=default,
                    )

                return default

            # ------------------------------------------------
            # RECORD
            # ------------------------------------------------

            record = {

                "player_id": player_id,

                "nome": nome,

                "ruolo": ruolo,

                "squadra": current_team,

                "stagione": stagione,

                "giornata": giornata,

                "redazione": "Fantacalcio",

                "voto": voto,

                "fanta_voto": None,

                "gf": col(4),

                "gs": col(5),

                "rp": col(6),

                "rs": col(7),

                "rf": col(8),

                "au": col(9),

                "amm": col(10),

                "esp": col(11),

                "ass": col(12),

                "gdv": col(13),

                "gdp": col(14),
            }

            records.append(
                record
            )

            # ------------------------------------------------
            # STATISTICHE DIAGNOSTICHE
            # ------------------------------------------------

            total_players += 1

            if voto is None:

                players_without_vote += 1

            else:

                players_with_vote += 1

    # ========================================================
    # LOG
    # ========================================================

    print(
        f"   👤 Giocatori trovati: "
        f"{total_players}"
    )

    print(
        f"   ✅ A voto: "
        f"{players_with_vote}"
    )

    print(
        f"   ⚪ Senza voto: "
        f"{players_without_vote}"
    )

    # ========================================================
    # CONTROLLO
    # ========================================================

    if not records:

        raise ValueError(
            "Nessun giocatore trovato "
            f"nel foglio 'Fantacalcio' "
            f"del file {file_path}"
        )

    return records
