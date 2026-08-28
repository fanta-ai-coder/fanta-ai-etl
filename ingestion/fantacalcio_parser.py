import re
from pathlib import Path

import pandas as pd


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


def clean_text(value):
    """
    Normalizza un valore proveniente dall'Excel.
    """
    if pd.isna(value):
        return ""

    return str(value).strip()


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
        return int(float(value.replace(",", ".")))
    except (ValueError, TypeError):
        return default


def clean_vote(value):
    """
    Converte il voto Fantacalcio.

    Esempi:
        6       -> 6.0
        5,5     -> 5.5
        6*      -> 6.0
        5,5*    -> 5.5
        vuoto   -> None
    """

    if pd.isna(value):
        return None

    value = str(value).strip()

    if not value:
        return None

    # Rimuove eventuali simboli come *
    value = value.replace("*", "").strip()

    # Normalizza decimali italiani
    value = value.replace(",", ".")

    # Cerca il numero
    match = re.search(r"-?\d+(?:\.\d+)?", value)

    if not match:
        return None

    try:
        return float(match.group(0))
    except ValueError:
        return None


def is_player_row(row):
    """
    Determina se una riga rappresenta un giocatore.
    """

    if len(row) < 4:
        return False

    code = clean_text(row.iloc[0])
    role = clean_text(row.iloc[1]).upper()

    if not code:
        return False

    if role not in PLAYER_ROLES:
        return False

    try:
        int(float(code))
        return True
    except ValueError:
        return False


def is_header_row(row):
    """
    Riconosce:

    Cod. | Ruolo | Nome | Voto | ...
    """

    if len(row) < 4:
        return False

    first = clean_text(row.iloc[0]).lower()
    second = clean_text(row.iloc[1]).lower()
    third = clean_text(row.iloc[2]).lower()
    fourth = clean_text(row.iloc[3]).lower()

    return (
        first in {"cod.", "cod", "codice"}
        and second == "ruolo"
        and third == "nome"
        and fourth == "voto"
    )


def is_probable_team_row(row):
    """
    Le righe squadra sono del tipo:

        ATALANTA
        BOLOGNA
        INTER
        ...

    senza Cod/Ruolo/Nome/Voto.
    """

    if len(row) == 0:
        return False

    first = clean_text(row.iloc[0])

    if not first:
        return False

    # Se la prima colonna è numerica, non è una squadra
    try:
        float(first)
        return False
    except ValueError:
        pass

    # Evita righe note del documento
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


def parse_excel(file_path, stagione, giornata):
    """
    Legge un Excel Fantacalcio e restituisce
    una lista di record pronti per Supabase.
    """

    file_path = Path(file_path)

    print(f"📄 Parsing: {file_path}")

    df = pd.read_excel(
        file_path,
        header=None,
        dtype=object,
    )

    records = []

    current_team = None

    for _, row in df.iterrows():

        # --------------------------------------------------------
        # HEADER
        # --------------------------------------------------------

        if is_header_row(row):
            continue

        # --------------------------------------------------------
        # GIOCATORE
        # --------------------------------------------------------

        if is_player_row(row):

            player_id = clean_number(row.iloc[0], default=None)

            ruolo = clean_text(row.iloc[1]).upper()

            nome = clean_text(row.iloc[2])

            voto = clean_vote(row.iloc[3])

            gf = clean_number(row.iloc[4])
            gs = clean_number(row.iloc[5])
            rp = clean_number(row.iloc[6])
            rs = clean_number(row.iloc[7])
            rf = clean_number(row.iloc[8])
            au = clean_number(row.iloc[9])
            amm = clean_number(row.iloc[10])
            esp = clean_number(row.iloc[11])
            ass = clean_number(row.iloc[12])
            gdv = clean_number(row.iloc[13])
            gdp = clean_number(row.iloc[14])

            if player_id is None:
                continue

            if not current_team:
                raise ValueError(
                    f"Giocatore trovato senza squadra: "
                    f"{nome} ({player_id})"
                )

            record = {
                "player_id": player_id,
                "nome": nome,
                "ruolo": ruolo,
                "squadra": current_team,
                "stagione": stagione,
                "giornata": giornata,
                "redazione": "Fantacalcio",

                "voto": voto,

                # Per ora il FantaVoto viene lasciato NULL.
                # Potremo calcolarlo con la formula ufficiale.
                "fanta_voto": None,

                "gf": gf,
                "gs": gs,
                "rp": rp,
                "rs": rs,
                "rf": rf,
                "au": au,
                "amm": amm,
                "esp": esp,
                "ass": ass,
                "gdv": gdv,
                "gdp": gdp,
            }

            records.append(record)

            continue

        # --------------------------------------------------------
        # SQUADRA
        # --------------------------------------------------------

        if is_probable_team_row(row):

            candidate = clean_text(row.iloc[0])

            # Evitiamo di interpretare righe descrittive
            # come squadre.
            if len(candidate) <= 30:
                current_team = candidate.upper()

    print(f"   👤 Giocatori trovati: {len(records)}")

    if not records:
        raise ValueError(
            f"Nessun giocatore trovato nel file {file_path}"
        )

    return records
