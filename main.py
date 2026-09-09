"""
============================================================
MAIN PIPELINE ETL SETTIMANALE - FANTA-AI
============================================================

Orchestratore unico per l'aggiornamento settimanale completo:
1. Scraping Rigoristi e Punizioni (da fantacalcio.it)
2. Scraping Probabili Formazioni, Titolari e Infortuni (da fantacalcio.it)
3. Sincronizzazione Voti & Quotazioni Excel su Supabase (se presenti nuovi file)
4. Calcolo Analitico Offline e Precomputazione KPI Giocatori
   -> Aggiorna la tabella Supabase `player_kpi_summary`
   -> Genera `player_kpi_summary.csv`
5. Git Commit & Push automatico (se specificato con --push o --full)

Uso:
    python main.py             # Esegue scraping + calcolo e aggiornamento KPI Supabase
    python main.py --push      # Esegue tutto + commit e push automatico su GitHub
    python main.py --dry-run   # Calcola i dati in locale senza scrivere su Supabase
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

import env_loader

from compute_kpis import compute_kpis_for_all
from scrape_rigoristi_punizioni import scrape_rigoristi_e_punizioni
from scrape_titolari_infortuni import scrape_titolari_infortuni


def run_command(cmd, cwd=None):
    """Esegue un comando shell catturando l'output in tempo reale."""
    res = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.stdout:
        print(res.stdout.strip())
    if res.stderr and res.returncode != 0:
        print(f"[ERRORE] {res.stderr.strip()}", file=sys.stderr)
    return res.returncode == 0


def git_commit_and_push(repo_dir: Path):
    """Aggiunge, committa e invia a GitHub tutti i file aggiornati."""
    print("\n" + "=" * 60)
    print("🚀 SINCRONIZZAZIONE GITHUB")
    print("=" * 60)

    git_cmd = "git"
    git_custom = r"C:\Users\andre\AppData\Local\Programs\Git\cmd\git.exe"
    if Path(git_custom).exists():
        git_cmd = f'"{git_custom}"'

    files_to_add = [
        "rigoristi.csv",
        "punizioni.csv",
        "titolari_infortuni",
        "titolari_infortuni.csv",
        "player_kpi_summary.csv",
    ]
    for f in files_to_add:
        if (repo_dir / f).exists():
            run_command(f"{git_cmd} add {f}", cwd=repo_dir)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    commit_msg = f'"Aggiornamento settimanale dati ed ETL FantaAI ({timestamp})"'

    print(f"[INFO] Creazione commit: {commit_msg}")
    committed = run_command(f"{git_cmd} commit -m {commit_msg}", cwd=repo_dir)

    if not committed:
        print("[INFO] Nessuna modifica da committare.")
    else:
        print("[INFO] Push verso GitHub (origin/main)...")
        pushed = run_command(f"{git_cmd} push origin main", cwd=repo_dir)
        if pushed:
            print("[OK] Push su GitHub completato con successo!")
        else:
            print("[ATTENZIONE] Il push su GitHub ha riscontrato un errore di rete o credenziali.")


def check_and_sync_excel(repo_dir: Path, stagione="2026-27"):
    """Controlla se ci sono file Excel recenti di quotazioni o voti da sincronizzare su Supabase."""
    quote_files = list(repo_dir.glob(f"Quotazioni_Fantacalcio_Stagione_{stagione.replace('-', '_')}*.xlsx"))
    if quote_files:
        quote_script = repo_dir / "fantacalcio_quotazioni_load.py"
        if quote_script.exists():
            print(f"\n[INFO] Rilevato file quotazioni: {quote_files[0].name}")
            print("       Verifica sincronizzazione listone...")
            run_command(f'python "{quote_script}" --file "{quote_files[0]}" --stagione {stagione}', cwd=repo_dir)


def main():
    parser = argparse.ArgumentParser(description="Pipeline ETL Settimanale FantaAI")
    parser.add_argument("--push", action="store_true", help="Esegue il commit e push su GitHub al termine")
    parser.add_argument("--dry-run", action="store_true", help="Esegue scraping e calcolo KPI senza inviare a Supabase")
    parser.add_argument("--stagione", default="2026-27", help="Stagione di riferimento (default: 2026-27)")
    parser.add_argument("--skip-scraping", action="store_true", help="Salta lo scraping di probabili formazioni e rigoristi")

    args = parser.parse_args()
    repo_dir = Path(__file__).resolve().parent

    print("=" * 60)
    print("⚽ AVVIO PIPELINE ETL SETTIMANALE FANTA-AI")
    print("=" * 60)
    print(f"Directory: {repo_dir}")
    print(f"Stagione:  {args.stagione}\n")

    # STEP 1 & 2: Scraping
    if not args.skip_scraping:
        print("[STEP 1/4] Scraping Rigoristi e Battitori Punizioni...")
        try:
            scrape_rigoristi_e_punizioni(output_dir=repo_dir)
            print("       [OK] Rigoristi e Punizioni aggiornati.")
        except Exception as e:
            print(f"[ERRORE] Scraping rigoristi fallito: {e}", file=sys.stderr)

        print("\n[STEP 2/4] Scraping Probabili Formazioni, Titolari e Infortuni...")
        try:
            scrape_titolari_infortuni(output_dir=repo_dir)
            print("       [OK] Probabili Formazioni e Infortuni aggiornati.")
        except Exception as e:
            print(f"[ERRORE] Scraping formazioni fallito: {e}", file=sys.stderr)
    else:
        print("[INFO] Scraping saltato (--skip-scraping).")

    # STEP 3: Controllo Voti / Quotazioni Excel (se presenti)
    print("\n[STEP 3/4] Controllo file Excel e Dati Base...")
    try:
        check_and_sync_excel(repo_dir, stagione=args.stagione)
    except Exception as e:
        print(f"[AVVISO] Controllo Excel: {e}")

    # STEP 4: Calcolo Analitico e Precomputazione KPI
    print("\n[STEP 4/4] Precalcolo KPI analitici ed invio a Supabase...")
    try:
        compute_kpis_for_all(repo_dir=repo_dir, stagione=args.stagione, dry_run=args.dry_run)
        print("       [OK] KPI Precalcolati pronti per la dashboard.")
    except Exception as e:
        print(f"[ERRORE] Calcolo KPI fallito: {e}", file=sys.stderr)
        sys.exit(1)

    # STEP 5: Push su GitHub
    if args.push:
        git_commit_and_push(repo_dir)

    print("\n" + "=" * 60)
    print("🎉 PIPELINE ETL COMPLETATA CON SUCCESSO!")
    print("=" * 60)


if __name__ == "__main__":
    main()
