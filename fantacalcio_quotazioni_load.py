"""
============================================================
FANTACALCIO QUOTAZIONI LOADER
============================================================

Carica su Supabase la lista giocatori/quotazioni di una stagione
(file tipo "Quotazioni_Fantacalcio_Stagione_2026_27.xlsx"), in una
tabella SEPARATA da player_stats_history: qui c'è UN record per
ogni giocatore per stagione (anagrafica + quotazione), non uno per
ogni giornata.

Il file Excel ha più fogli; usiamo:
  - "Tutti"  -> tutti i giocatori attivi della stagione
  - "Ceduti" -> giocatori che hanno lasciato la Serie A durante la
               stagione (marcati con ceduto=True, non scartati:
               utili per storico squadre/trasferimenti)
I fogli per ruolo (Portieri/Difensori/Centrocampisti/Attaccanti)
sono sottoinsiemi di "Tutti": vengono ignorati per non duplicare i
giocatori.

------------------------------------------------------------
PRIMA DI ESEGUIRE QUESTO SCRIPT crea la tabella su Supabase, dal
SQL Editor del dashboard (Settings non serve, basta l'SQL Editor):

    create table if not exists giocatori_quotazioni (
        player_id integer not null,
        stagione text not null,
        nome text not null,
        ruolo text,
        ruolo_mantra text,
        squadra text,
        quotazione_attuale integer,
        quotazione_iniziale integer,
        diff_quotazione integer,
        quotazione_attuale_mantra integer,
        quotazione_iniziale_mantra integer,
        diff_quotazione_mantra integer,
        fvm integer,
        fvm_mantra integer,
        ceduto boolean not null default false,
        updated_at timestamptz not null default now(),
        primary key (player_id, stagione)
    );

------------------------------------------------------------
Uso:

    # Solo per controllare cosa verrebbe caricato:
    python fantacalcio_quotazioni_load.py --file Quotazioni_Fantacalcio_Stagione_2026_27.xlsx --stagione 2026-27 --dry-run

    # Caricamento vero (svuota prima le quotazioni di quella stagione):
    python fantacalcio_quotazioni_load.py --file Quotazioni_Fantacalcio_Stagione_2026_27.xlsx --stagione 2026-27

Richiede nella stessa cartella: fantacalcio_parser.py (riusa
clean_text/clean_number) e supabase_client.py.

Variabili d'ambiente richieste (le stesse degli altri script):
    SUPABASE_URL
    SUPABASE_KEY
============================================================
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import env_loader
import pandas as pd

from fantacalcio_parser import clean_number, clean_text

TABLE_NAME = "giocatori_quotazioni"

# Le prime 5 colonne attese sulla riga di intestazione del foglio,
# in minuscolo. Cerchiamo questa riga invece di assumere un numero
# fisso di righe di preambolo, così lo script resta valido anche se
# in futuro Fantacalcio.it cambia leggermente il file (es. aggiunge
# una riga in più prima della tabella).
EXPECTED_HEADER_PREFIX = ["id", "r", "rm", "nome", "squadra"]


# ============================================================
# PARSING
# ============================================================

def find_header_row(df: pd.DataFrame) -> int | None:
    for i, row in df.iterrows():
        cells = [clean_text(row.iloc[j]).lower() for j in range(min(5, len(row)))]
        if cells == EXPECTED_HEADER_PREFIX:
            return i
    return None


def parse_sheet(df: pd.DataFrame, stagione: str, ceduto: bool) -> list[dict]:
    header_row = find_header_row(df)

    if header_row is None:
        raise ValueError(
            "Riga di intestazione (Id/R/RM/Nome/Squadra) non trovata nel foglio."
        )

    records = []

    for i in range(header_row + 1, len(df)):
        row = df.iloc[i]

        player_id = clean_number(row.iloc[0], default=None)
        if player_id is None:
            continue  # riga vuota o di chiusura del foglio

        record = {
            "player_id": int(player_id),
            "stagione": stagione,
            "ruolo": clean_text(row.iloc[1]).upper(),
            "ruolo_mantra": clean_text(row.iloc[2]),
            "nome": clean_text(row.iloc[3]),
            "squadra": clean_text(row.iloc[4]).upper(),
            "quotazione_attuale": clean_number(row.iloc[5], default=None),
            "quotazione_iniziale": clean_number(row.iloc[6], default=None),
            "diff_quotazione": clean_number(row.iloc[7], default=None),
            "quotazione_attuale_mantra": clean_number(row.iloc[8], default=None),
            "quotazione_iniziale_mantra": clean_number(row.iloc[9], default=None),
            "diff_quotazione_mantra": clean_number(row.iloc[10], default=None),
            "fvm": clean_number(row.iloc[11], default=None),
            "fvm_mantra": clean_number(row.iloc[12], default=None),
            "ceduto": ceduto,
        }
        records.append(record)

    return records


def load_quotazioni(file_path: Path, stagione: str) -> list[dict]:
    xls = pd.ExcelFile(file_path)

    if "Tutti" not in xls.sheet_names:
        raise ValueError(
            f"Foglio 'Tutti' non trovato. Fogli presenti: {xls.sheet_names}"
        )

    df_tutti = pd.read_excel(xls, sheet_name="Tutti", header=None, dtype=object)
    records = parse_sheet(df_tutti, stagione, ceduto=False)

    if "Ceduti" in xls.sheet_names:
        df_ceduti = pd.read_excel(xls, sheet_name="Ceduti", header=None, dtype=object)
        ceduti_records = parse_sheet(df_ceduti, stagione, ceduto=True)

        # Se per qualche motivo un giocatore compare in entrambi i
        # fogli, diamo priorità allo stato "attivo" (Tutti).
        seen_ids = {r["player_id"] for r in records}
        records.extend(r for r in ceduti_records if r["player_id"] not in seen_ids)
    else:
        print("ℹ️  Foglio 'Ceduti' non presente in questo file, salto.")

    return records


# ============================================================
# SUPABASE
# ============================================================

def truncate_season(client, stagione: str) -> None:
    """
    Svuota solo le quotazioni della stagione indicata (non l'intera
    tabella): così si può ricaricare 2026-27 senza toccare eventuali
    quotazioni di stagioni precedenti già presenti.
    """
    print(f"🧹 Svuoto le quotazioni esistenti per la stagione {stagione}...")
    client.table(TABLE_NAME).delete().eq("stagione", stagione).execute()
    print("✅ Fatto.")


# ============================================================
# MAIN
# ============================================================

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Carica su Supabase l'anagrafica/quotazioni giocatori di una stagione."
    )
    parser.add_argument(
        "--file", required=True,
        help="Percorso del file Quotazioni_Fantacalcio_Stagione_*.xlsx",
    )
    parser.add_argument(
        "--stagione", required=True,
        help="Stagione a cui si riferisce il file, es. 2026-27",
    )
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parsa il file e mostra il riepilogo, senza toccare Supabase.",
    )
    parser.add_argument(
        "--skip-truncate", action="store_true",
        help="Non svuotare le quotazioni della stagione prima di caricare.",
    )
    args = parser.parse_args(argv)

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"❌ File non trovato: {file_path}")
        raise SystemExit(1)

    print()
    print("=" * 70)
    print("📄 PARSING QUOTAZIONI")
    print("=" * 70)
    print(f"File: {file_path}")
    print(f"Stagione: {args.stagione}")

    records = load_quotazioni(file_path, args.stagione)

    n_ceduti = sum(1 for r in records if r["ceduto"])
    n_attivi = len(records) - n_ceduti
    print(f"\n📦 Giocatori trovati: {len(records)} (attivi: {n_attivi}, ceduti: {n_ceduti})")

    if args.dry_run:
        print("\n🧪 Dry-run: nessun dato inviato a Supabase.")
        print("Esempio primi 3 record:")
        for r in records[:3]:
            print(f"   {r}")
        return

    print()
    print("=" * 70)
    print("💾 SUPABASE")
    print("=" * 70)

    from supabase_client import SupabaseClient
    supabase = SupabaseClient()

    if args.skip_truncate:
        print("⏭️  Pulizia saltata (--skip-truncate).")
    else:
        truncate_season(supabase.client, args.stagione)

    print(f"\n⬆️  Carico {len(records)} record su '{TABLE_NAME}'...")

    total = 0
    for start in range(0, len(records), args.batch_size):
        batch = records[start:start + args.batch_size]
        supabase.client.table(TABLE_NAME).upsert(
            batch, on_conflict="player_id,stagione"
        ).execute()
        total += len(batch)
        print(f"   ... {total}/{len(records)} record caricati")

    print()
    print("=" * 70)
    print("🎉 CARICAMENTO COMPLETATO")
    print("=" * 70)
    print(f"✅ Record caricati: {total}")


if __name__ == "__main__":
    main()
