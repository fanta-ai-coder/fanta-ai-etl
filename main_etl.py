"""
============================================================
MAIN ETL SETTIMANALE - FANTA-AI
============================================================

Orchestratore unico per l'aggiornamento settimanale dei dati:
1. Scraping Rigoristi e Punizioni (da fantacalcio.it/rigoristi-serie-a)
2. Scraping Probabili Formazioni, Titolari e Infortuni (da fantacalcio.it/probabili-formazioni-serie-a)
3. Salvataggio locale dei file formattati per app.py:
   - rigoristi.csv
   - punizioni.csv
   - titolari_infortuni
4. (Opzionale) Commit e Push automatico su GitHub:
   git add, commit e push
5. (Opzionale) Aggiornamento Voti / Quotazioni su Supabase

Uso:
    python main_etl.py            # Esegue lo scraping e aggiorna i file locali
    python main_etl.py --push     # Esegue lo scraping e fa automaticamente commit e push su GitHub
    python main_etl.py --full     # Scraping + Git Push + Sincronizzazione Supabase voti
============================================================
"""

import argparse
from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from scrape_rigoristi_punizioni import scrape_rigoristi_e_punizioni
from scrape_titolari_infortuni import scrape_titolari_infortuni


def run_command(cmd, cwd=None):
    """Esegue un comando shell catturando l'output in tempo reale."""
    res = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True)
    if res.stdout:
        print(res.stdout.strip())
    if res.stderr and res.returncode != 0:
        print(f"[ERRORE] {res.stderr.strip()}", file=sys.stderr)
    return res.returncode == 0


def git_commit_and_push(repo_dir: Path):
    """Aggiunge, committa e invia a GitHub i file aggiornati."""
    print("\n" + "=" * 60)
    print("🚀 SINCRONIZZAZIONE GITHUB")
    print("=" * 60)

    # Identifica il percorso di git se disponibile
    git_cmd = "git"
    git_custom = r"C:\Users\andre\AppData\Local\Programs\Git\cmd\git.exe"
    if Path(git_custom).exists():
        git_cmd = f'"{git_custom}"'

    # Verifica status
    print("[INFO] Controllo modifiche Git...")
    files_to_add = ["rigoristi.csv", "punizioni.csv", "titolari_infortuni", "titolari_infortuni.csv"]
    for f in files_to_add:
        if (repo_dir / f).exists():
            run_command(f"{git_cmd} add {f}", cwd=repo_dir)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    commit_msg = f'"Aggiornamento dati settimanali: rigoristi, punizioni e titolari ({timestamp})"'

    # Esegui il commit
    print(f"[INFO] Creazione commit: {commit_msg}")
    committed = run_command(f"{git_cmd} commit -m {commit_msg}", cwd=repo_dir)

    if not committed:
        print("[INFO] Nessuna modifica rilevata o commit già allineato.")
    else:
        print("[INFO] Push verso GitHub (origin/main)...")
        pushed = run_command(f"{git_cmd} push origin main", cwd=repo_dir)
        if pushed:
            print("[OK] Push su GitHub completato con successo!")
        else:
            print("[ATTENZIONE] Il push su GitHub ha richiesto autenticazione o ha fallito.")
            print("             Verifica le credenziali (token GitHub o chiave SSH).")


def run_supabase_sync(repo_dir: Path, stagione="2026-27"):
    """Sincronizza i dati su Supabase se le credenziali sono presenti."""
    print("\n" + "=" * 60)
    print("💾 SINCRONIZZAZIONE SUPABASE")
    print("=" * 60)

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        print("[AVVISO] Variabili SUPABASE_URL e SUPABASE_KEY non rilevate nell'ambiente.")
        print("         Configurale prima di sincronizzare con Supabase.")
        return

    bulk_script = repo_dir / "fantacalcio_bulk_load.py"
    if bulk_script.exists():
        print(f"[INFO] Aggiornamento voti per la stagione {stagione}...")
        run_command(f'python "{bulk_script}" --seasons {stagione} --skip-truncate', cwd=repo_dir)


def main():
    parser = argparse.ArgumentParser(description="Main ETL Settimanale Fantacalcio")
    parser.add_argument("--push", action="store_true", help="Esegue il commit e push su GitHub dopo lo scraping")
    parser.add_argument("--supabase", action="store_true", help="Esegue anche l'aggiornamento dei voti su Supabase")
    parser.add_argument("--full", action="store_true", help="Esegue lo scraping completo, git push e sincronizzazione Supabase")
    parser.add_argument("--stagione", default="2026-27", help="Stagione di riferimento (default: 2026-27)")

    args = parser.parse_args()
    repo_dir = Path(__file__).resolve().parent

    print("=" * 60)
    print("⚽ AVVIO ETL SETTIMANALE FANTA-AI")
    print("=" * 60)
    print(f"Directory di lavoro: {repo_dir}")

    # 1. Scraping Rigoristi e Punizioni
    print("\n[STEP 1/2] Scraping Rigoristi e Punizioni...")
    try:
        scrape_rigoristi_e_punizioni(output_dir=repo_dir)
    except Exception as e:
        print(f"[ERRORE] Scraping rigoristi fallito: {e}", file=sys.stderr)

    # 2. Scraping Probabili Formazioni e Infortuni
    print("\n[STEP 2/2] Scraping Probabili Formazioni, Titolari e Infortuni...")
    try:
        scrape_titolari_infortuni(output_dir=repo_dir)
    except Exception as e:
        print(f"[ERRORE] Scraping titolari/infortuni fallito: {e}", file=sys.stderr)

    # 3. Supabase (se richiesto)
    if args.supabase or args.full:
        run_supabase_sync(repo_dir, stagione=args.stagione)

    # 4. Git Push (se richiesto)
    if args.push or args.full:
        git_commit_and_push(repo_dir)

    print("\n" + "=" * 60)
    print("🎉 ETL SETTIMANALE COMPLETATO!")
    print("=" * 60)


if __name__ == "__main__":
    main()
