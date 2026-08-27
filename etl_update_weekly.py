"""
UPDATE SETTIMANALE (cron)
==========================
- Rilegge il listone quotazioni corrente (classico, no Mantra) e
  aggiorna via upsert (i valori possono cambiare di settimana in
  settimana per via del listone aggiornato).
- Scarica solo la STAGIONE CORRENTE da FBref e aggiorna via upsert.
- Aggiorna il mapping SOLO per i giocatori del listone che risultano
  ancora senza un match affidabile (non ricalcola tutto da zero).

Esegui con:
    python etl_update_weekly.py
"""

import os
import pandas as pd

from common_fbref import (
    load_quotazioni_classic,
    fetch_fbref_player_stats,
    build_player_mapping,
    get_supabase_client,
    upload_to_supabase,
)

CURRENT_SEASON = os.getenv("CURRENT_SEASON", "2025")  # anno di inizio stagione per FBref


def main():
    print("\n" + "#" * 70)
    print("# FANTA-AI · UPDATE SETTIMANALE (FBref, stagione corrente)")
    print("#" * 70)

    # --------------------------------------------------------
    # 1) LISTONE QUOTAZIONI AGGIORNATO
    # --------------------------------------------------------
    df_quotazioni = load_quotazioni_classic()
    upload_to_supabase(df_quotazioni, "quotazioni", on_conflict="id,stagione")

    # --------------------------------------------------------
    # 2) STATISTICHE FBREF · SOLO STAGIONE CORRENTE
    # --------------------------------------------------------
    df_fbref_current = fetch_fbref_player_stats(CURRENT_SEASON)
    upload_to_supabase(df_fbref_current, "fbref_player_stats", on_conflict="fbref_id,season")

    # --------------------------------------------------------
    # 3) MAPPING: aggiorna solo le voci mancanti/da rivedere
    # --------------------------------------------------------
    supabase = get_supabase_client()
    existing = supabase.table("player_mapping_fbref").select("*").execute()
    df_existing_mapping = pd.DataFrame(existing.data) if existing.data else pd.DataFrame()

    if not df_existing_mapping.empty:
        gia_ok_ids = set(
            df_existing_mapping.loc[
                df_existing_mapping["match_method"] != "manual_review", "id_excel"
            ]
        )
        df_quotazioni_da_matchare = df_quotazioni[~df_quotazioni["id"].isin(gia_ok_ids)]
    else:
        df_quotazioni_da_matchare = df_quotazioni

    if not df_quotazioni_da_matchare.empty:
        print(f"Ricalcolo mapping per {len(df_quotazioni_da_matchare)} giocatori senza match affidabile...")
        df_new_mapping = build_player_mapping(df_quotazioni_da_matchare, df_fbref_current)
        upload_to_supabase(df_new_mapping, "player_mapping_fbref", on_conflict="id_excel")
    else:
        print("Nessun nuovo giocatore da mappare: mapping esistente già completo.")

    print("\nUPDATE SETTIMANALE COMPLETATO CON SUCCESSO!")


if __name__ == "__main__":
    main()
