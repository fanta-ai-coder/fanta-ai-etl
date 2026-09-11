"""
Script per popolare la tabella serie_a_calendar su Supabase con le 380 partite del calendario.
Utilizzo: python upload_calendar_to_supabase.py
(Assicurati di aver prima eseguito lo script supabase_calendar_setup.sql nel SQL Editor di Supabase)
"""

import os
import env_loader
from supabase import create_client
import serie_a_calendar

def main():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        print("Errore: SUPABASE_URL e/o SUPABASE_KEY non trovati nelle variabili d'ambiente.")
        return

    sb = create_client(url, key)
    matches, _ = serie_a_calendar.load_or_create_calendar()

    print(f"Caricamento di {len(matches)} partite in 'serie_a_calendar'...")
    try:
        # Carica a batch di 50 partite
        for i in range(0, len(matches), 50):
            batch = matches[i:i+50]
            sb.table("serie_a_calendar").upsert(batch).execute()
            print(f"Caricate partite {i+1} - {min(i+50, len(matches))}")
        print("Calendario caricato con successo su Supabase!")
    except Exception as e:
        print(f"Errore durante il caricamento su Supabase: {e}")
        print("Nota: assicurati di aver creato la tabella eseguendo prima supabase_calendar_setup.sql")

if __name__ == "__main__":
    main()
