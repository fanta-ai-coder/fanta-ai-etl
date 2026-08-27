"""
INGESTION FULL (una tantum / manuale)
======================================
- Scarica N stagioni storiche da FBref (default: ultime 5)
- Legge il listone quotazioni classico (no Mantra)
- Costruisce il mapping nomi listone <-> FBref
- SVUOTA completamente le tabelle Supabase e le ricarica da zero

Esegui con:
    python etl_ingestion_full.py

Variabili d'ambiente:
    SUPABASE_URL, SUPABASE_KEY  (obbligatorie)
    N_SEASONS                   (opzionale, default 5)
"""

import os
import pandas as pd

from common_fbref import (
    load_quotazioni_classic,
    fetch_fbref_player_stats,
    build_player_mapping,
    get_supabase_client,
    wipe_table,
    upload_to_supabase,
)

# Ultima stagione "di partenza": FBref usa l'anno di inizio stagione,
# es. 2024 = stagione 2024/25. Modifica se serve.
CURRENT_SEASON_START_YEAR = 2025
N_SEASONS = int(os.getenv("N_SEASONS", "5"))

SEASONS = [
    str(CURRENT_SEASON_START_YEAR - i) for i in range(N_SEASONS)
][::-1]


def main():
    print("\n" + "#" * 70)
    print("# FANTA-AI · INGESTION FULL (FBref, storico)")
    print("#" * 70)
    print(f"Stagioni da scaricare: {SEASONS}")

    # --------------------------------------------------------
    # 1) LISTONE QUOTAZIONI (classico, no Mantra)
    # --------------------------------------------------------
    df_quotazioni = load_quotazioni_classic()

    # --------------------------------------------------------
    # 2) STATISTICHE FBREF PER OGNI STAGIONE
    # --------------------------------------------------------
    all_stats = []
    failed_seasons = []
    for season in SEASONS:
        try:
            df_season = fetch_fbref_player_stats(season)
            if df_season is not None and not df_season.empty:
                all_stats.append(df_season)
            else:
                failed_seasons.append(season)
        except Exception as e:
            print(f"ERRORE stagione {season}: {e}")
            failed_seasons.append(season)

    if not all_stats:
        raise RuntimeError("Nessuna stagione scaricata correttamente da FBref. Interrompo.")

    df_fbref_all = pd.concat(all_stats, ignore_index=True)
    print(f"\nTotale record FBref (tutte le stagioni): {len(df_fbref_all)}")

    # --------------------------------------------------------
    # 3) MAPPING NOMI (listone <-> FBref)
    # --------------------------------------------------------
    df_mapping = build_player_mapping(df_quotazioni, df_fbref_all)

    # --------------------------------------------------------
    # 4) SVUOTAMENTO TABELLE SUPABASE
    # --------------------------------------------------------
    supabase = get_supabase_client()
    wipe_table(supabase, "quotazioni", id_column="id")
    wipe_table(supabase, "fbref_player_stats", id_column="fbref_id")
    # id_excel è un intero: uso una colonna intera per il filtro di wipe
    supabase.table("player_mapping_fbref").delete().gte("id_excel", -2147483648).execute()

    # --------------------------------------------------------
    # 5) CARICAMENTO
    # --------------------------------------------------------
    upload_to_supabase(df_quotazioni, "quotazioni", on_conflict="id,stagione")
    upload_to_supabase(df_fbref_all, "fbref_player_stats", on_conflict="fbref_id,season")
    upload_to_supabase(df_mapping, "player_mapping_fbref", on_conflict="id_excel")

    # --------------------------------------------------------
    # RIEPILOGO
    # --------------------------------------------------------
    print("\n" + "=" * 70)
    print("RIEPILOGO INGESTION FULL")
    print("=" * 70)
    print(f"Stagioni scaricate con successo: {[s for s in SEASONS if s not in failed_seasons]}")
    print(f"Stagioni fallite: {failed_seasons}")
    print(f"Giocatori nel listone: {len(df_quotazioni)}")
    print(f"Record FBref totali: {len(df_fbref_all)}")
    print(f"Mapping creati: {len(df_mapping)}")

    if failed_seasons:
        raise RuntimeError(f"Ingestion completata parzialmente. Stagioni fallite: {failed_seasons}")

    print("\nINGESTION FULL COMPLETATA CON SUCCESSO!")


if __name__ == "__main__":
    main()
