"""
============================================================
FANTACALCIO BULK LOAD - Caricamento massivo su Supabase
============================================================

Script "una tantum" per caricare su Supabase tutti gli Excel già
scaricati in locale con fantacalcio_downloader.py (cartelle
data/{stagione}/giornata_XX.xlsx).

A differenza di fantacalcio_ingestion.py (che scarica UNA giornata
alla volta via Selenium, in genere su GitHub Actions), questo script
NON scarica nulla: legge i file .xlsx già presenti sul disco, li
trasforma in un'unica tabella (un record per ogni combinazione
giocatore + stagione + giornata) e li carica su Supabase.

Prima di caricare, SVUOTA la tabella di destinazione
(player_stats_history di default), come richiesto: si riparte sempre
da una tabella pulita, evitando duplicati o dati vecchi incoerenti.

Uso tipico:

    python fantacalcio_bulk_load.py

    # Solo alcune stagioni:
    python fantacalcio_bulk_load.py --seasons 2023-24 2024-25

    # Solo per controllare cosa verrebbe caricato, senza toccare
    # Supabase:
    python fantacalcio_bulk_load.py --dry-run

    # Se la cartella "data" non è nella directory corrente:
    python fantacalcio_bulk_load.py --data-dir C:\\percorso\\data

    # Per aggiungere dati senza svuotare la tabella (upsert soltanto):
    python fantacalcio_bulk_load.py --skip-truncate

Variabili d'ambiente richieste (le stesse di fantacalcio_ingestion.py):

    SUPABASE_URL
    SUPABASE_KEY
============================================================
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from fantacalcio_parser import parse_excel


# ============================================================
# CONFIGURAZIONE
# ============================================================

SEASONS_DEFAULT = ["2023-24", "2024-25", "2025-26"]
TABLE_NAME = "player_stats_history"
BATCH_SIZE_DEFAULT = 500

GIORNATA_FILE_RE = re.compile(r"giornata_(\d+)\.xlsx$", re.IGNORECASE)


# ============================================================
# SCOPERTA FILE LOCALI
# ============================================================

def find_giornata_files(data_dir: Path, season: str):
    """
    Ritorna la lista (giornata, path) per una stagione, ordinata per
    numero di giornata, leggendo i file data/{stagione}/giornata_XX.xlsx.
    """

    season_dir = data_dir / season

    if not season_dir.exists():
        print(f"⚠️  Cartella non trovata, salto: {season_dir}")
        return []

    files = []

    for path in sorted(season_dir.glob("*.xlsx")):
        match = GIORNATA_FILE_RE.search(path.name)
        if not match:
            print(f"⚠️  Nome file inatteso, salto: {path}")
            continue
        files.append((int(match.group(1)), path))

    files.sort(key=lambda item: item[0])
    return files


# ============================================================
# SUPABASE: PULIZIA TABELLA
# ============================================================

def truncate_table(client, table_name: str) -> None:
    """
    Svuota completamente la tabella prima del caricamento.

    Il client supabase-py opera via PostgREST, che richiede sempre un
    filtro esplicito anche per un DELETE "totale": usiamo
    giornata >= 0, condizione sempre vera per dati reali (le giornate
    partono da 1), quindi equivalente a un TRUNCATE.
    """

    print(f"🧹 Svuoto la tabella '{table_name}'...")
    client.table(table_name).delete().gte("giornata", 0).execute()
    print(f"✅ Tabella '{table_name}' svuotata.")


# ============================================================
# MAIN
# ============================================================

def main(argv: list[str] | None = None) -> None:

    parser = argparse.ArgumentParser(
        description="Carica su Supabase tutti gli Excel Fantacalcio già scaricati in locale."
    )
    parser.add_argument(
        "--data-dir", default="data",
        help="Cartella che contiene le sottocartelle {stagione}/giornata_XX.xlsx (default: data).",
    )
    parser.add_argument(
        "--seasons", nargs="+", default=SEASONS_DEFAULT,
        help=f"Stagioni da caricare (default: {SEASONS_DEFAULT}).",
    )
    parser.add_argument(
        "--batch-size", type=int, default=BATCH_SIZE_DEFAULT,
        help=f"Righe per ogni chiamata di upsert a Supabase (default: {BATCH_SIZE_DEFAULT}).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parsa tutti i file e mostra il riepilogo, senza toccare Supabase.",
    )
    parser.add_argument(
        "--skip-truncate", action="store_true",
        help="Non svuotare la tabella prima di caricare: aggiunge/upserta soltanto.",
    )
    args = parser.parse_args(argv)

    data_dir = Path(args.data_dir)

    # ========================================================
    # 1. TROVA TUTTI I FILE
    # ========================================================

    print()
    print("=" * 70)
    print("📂 RICERCA FILE LOCALI")
    print("=" * 70)

    all_files = []
    for season in args.seasons:
        season_files = find_giornata_files(data_dir, season)
        print(f"   {season}: {len(season_files)} file trovati")
        for giornata, path in season_files:
            all_files.append((season, giornata, path))

    if not all_files:
        print()
        print("❌ Nessun file Excel trovato. Controlla --data-dir e --seasons.")
        sys.exit(1)

    print(f"\n📊 Totale file da processare: {len(all_files)}")

    # ========================================================
    # 2. PARSING (nessuna scrittura, solo lettura locale)
    # ========================================================

    print()
    print("=" * 70)
    print("📄 PARSING")
    print("=" * 70)

    all_records = []
    per_giornata_count = {}   # (stagione, giornata) -> numero record
    parse_errors = []          # (stagione, giornata, messaggio)

    for season, giornata, path in all_files:
        try:
            records = parse_excel(path, season, giornata)
            all_records.extend(records)
            per_giornata_count[(season, giornata)] = len(records)
        except Exception as exc:
            print(f"   ❌ {season} G{giornata}: {exc}")
            parse_errors.append((season, giornata, str(exc)))

    print()
    print(f"📦 Record totali estratti: {len(all_records)}")

    if parse_errors:
        print(f"⚠️  {len(parse_errors)} file hanno dato errore in parsing:")
        for season, giornata, msg in parse_errors:
            print(f"   - {season} G{giornata}: {msg}")

    if not all_records:
        print()
        print("❌ Nessun record valido estratto: interrompo senza toccare Supabase.")
        sys.exit(1)

    if args.dry_run:
        print()
        print("🧪 Dry-run: nessun dato inviato a Supabase.")
        print("   Riepilogo per stagione:")
        seasons_seen = sorted(set(s for s, _ in per_giornata_count))
        for season in seasons_seen:
            giornate = sorted(g for s, g in per_giornata_count if s == season)
            tot = sum(per_giornata_count[(season, g)] for g in giornate)
            print(
                f"   - {season}: {len(giornate)} giornate "
                f"(G{min(giornate)}-G{max(giornate)}), {tot} record"
            )
        return

    # ========================================================
    # 3. SUPABASE: PULIZIA + CARICAMENTO
    # ========================================================

    print()
    print("=" * 70)
    print("💾 SUPABASE")
    print("=" * 70)

    from supabase_client import SupabaseClient

    supabase = SupabaseClient()

    if args.skip_truncate:
        print("⏭️  Pulizia tabella saltata (--skip-truncate).")
    else:
        truncate_table(supabase.client, TABLE_NAME)

    print(f"\n⬆️  Carico {len(all_records)} record su '{TABLE_NAME}'...")

    total_inserted = 0
    for start in range(0, len(all_records), args.batch_size):
        batch = all_records[start:start + args.batch_size]
        inserted = supabase.insert_stats(batch)
        total_inserted += inserted
        print(f"   ... {total_inserted}/{len(all_records)} record caricati")

    # ========================================================
    # 4. AGGIORNA download_logs
    # ========================================================
    #
    # Fondamentale: senza questo passaggio, fantacalcio_ingestion.py
    # (in modalità "next", su GitHub Actions) non saprebbe che queste
    # giornate sono già state caricate, e proverebbe a riscaricarle
    # una ad una via Selenium inutilmente.

    print()
    print("📝 Aggiorno download_logs per le giornate caricate...")

    for (season, giornata), count in per_giornata_count.items():
        supabase.save_log(
            stagione=season,
            giornata=giornata,
            status="COMPLETED",
            records_inserted=count,
        )

    for season, giornata, msg in parse_errors:
        supabase.save_log(
            stagione=season,
            giornata=giornata,
            status="FAILED",
            records_inserted=0,
            error_message=msg,
        )

    print()
    print("=" * 70)
    print("🎉 CARICAMENTO COMPLETATO")
    print("=" * 70)
    print(f"✅ Record caricati: {total_inserted}")
    print(f"📝 Giornate registrate in download_logs: {len(per_giornata_count)}")
    if parse_errors:
        print(f"⚠️  Giornate con errore di parsing: {len(parse_errors)}")


if __name__ == "__main__":
    main()
