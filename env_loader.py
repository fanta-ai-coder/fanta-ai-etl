"""
============================================================
ENV LOADER HELPER - FANTA-AI
============================================================
Carica automaticamente le variabili d'ambiente da env.txt o .env
se non sono già configurate nel sistema operativo.
============================================================
"""

import os
from pathlib import Path


def load_env_variables():
    """Cerca e carica SUPABASE_URL e SUPABASE_KEY dai file locali."""
    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY"):
        return

    candidate_files = [
        Path(__file__).resolve().parent / "env.txt",
        Path(__file__).resolve().parent / ".env",
        Path(r"C:\Users\andre\Documents\Python Scripts\fantacalcio\env.txt"),
        Path.cwd() / "env.txt",
        Path.cwd() / ".env",
    ]

    for fpath in candidate_files:
        if fpath.exists():
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                for line in content.splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if line.startswith("set "):
                        line = line[4:].strip()
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip().strip('"').strip("'")
                        if k and v and k not in os.environ:
                            os.environ[k] = v
            except Exception:
                pass


# Esegui automaticamente al caricamento del modulo
load_env_variables()
