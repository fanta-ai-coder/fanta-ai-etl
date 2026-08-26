import os
import pandas as pd
import soccerdata as sd
from supabase import Client, create_client

# 1. Recupero delle chiavi d'accesso da GitHub Secrets
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Credenziali SUPABASE_URL o SUPABASE_KEY non trovate nei Secret di GitHub!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_and_process_data(seasons=["2024-2025"]):
    """Scarica le statistiche dei giocatori da FBref con soccerdata e le trasforma."""
    print(f"Scaricamento dati FBref per le stagioni: {seasons}...")
    
    # Inizializza lo scraper di soccerdata per la Serie A
    fbref = sd.FBref(leagues="ITA-Serie A", seasons=seasons)

    try:
        # Scarica le statistiche standard e di tiro
        df_standard = fbref.read_player_season_stats(stat_type="standard")
        df_shooting = fbref.read_player_season_stats(stat_type="shooting")
    except Exception as e:
        print(f"Errore durante il download dei dati da FBref: {e}")
        return None

    # Appiattisci le colonne MultiIndex (es. ('Performance', 'Gls') -> 'Gls')
    df_standard.columns = [
        col[1] if isinstance(col, tuple) and col[1] != "" else col[0] 
        for col in df_standard.columns
    ]
    df_shooting.columns = [
        col[1] if isinstance(col, tuple) and col[1] != "" else col[0] 
        for col in df_shooting.columns
    ]

    # Reset degli indici di riga (league, season, team, player) per averli come colonne normali
    df_standard = df_standard.reset_index()
    df_shooting = df_shooting.reset_index()

    # Creazione DataFrame pulito e strutturato per Supabase
    df_clean = pd.DataFrame()
    
    df_clean["player_name"] = df_standard["player"].astype(str)
    df_clean["team"] = df_standard["team"].astype(str)
    df_clean["season"] = df_standard["season"].astype(str)
    
    # Minutaggio e presenze
    df_clean["matches_played"] = pd.to_numeric(df_standard.get("MP", 0), errors="coerce").fillna(0).astype(int)
    df_clean["minutes_played"] = pd.to_numeric(df_standard.get("Min", 0), errors="coerce").fillna(0).astype(int)
    
    # Gol & Assist
    df_clean["goals"] = pd.to_numeric(df_standard.get("Gls", 0), errors="coerce").fillna(0).astype(int)
    df_clean["assists"] = pd.to_numeric(df_standard.get("Ast", 0), errors="coerce").fillna(0).astype(int)
    
    # Metriche Avanzate (Expected Goals & Expected Assisted Goals)
    df_clean["xg"] = pd.to_numeric(df_standard.get("xG", 0.0), errors="coerce").fillna(0.0).round(2)
    df_clean["xa"] = pd.to_numeric(df_standard.get("xAG", 0.0), errors="coerce").fillna(0.0).round(2)

    # Calcolo KPI per 90 minuti
    mins = df_clean["minutes_played"]
    df_clean["goals_per_90"] = (df_clean["goals"] / (mins / 90)).where(mins > 0, 0.0).round(2)
    df_clean["xg_per_90"] = (df_clean["xg"] / (mins / 90)).where(mins > 0, 0.0).round(2)

    # Tiri
    df_clean["shots_total"] = pd.to_numeric(df_shooting.get("Sh", 0), errors="coerce").fillna(0).astype(int)
    df_clean["shots_on_target"] = pd.to_numeric(df_shooting.get("SoT", 0), errors="coerce").fillna(0).astype(int)

    # Identificativo univoco (Chiave Primaria)
    df_clean["id"] = df_clean["player_name"] + "_" + df_clean["season"]

    return df_clean


def upload_to_supabase(df):
    """Invia i dati elaborati al database Supabase tramite Operazione di Upsert."""
    if df is None or df.empty:
        print("Nessun dato valido da caricare.")
        return

    print(f"Inizio caricamento di {len(df)} record su Supabase...")
    records = df.to_dict(orient="records")

    try:
        # Upsert: inserisce i dati nuovi ed aggiorna quelli esistenti senza duplicare
        response = supabase.table("player_stats").upsert(records).execute()
        print("Caricamento completato con successo su Supabase!")
    except Exception as e:
        print(f"Errore durante l'upsert su Supabase: {e}")


if __name__ == "__main__":
    # Esegue l'estrazione per la stagione corrente
    df_processed = fetch_and_process_data(seasons=["2024-2025"])
    upload_to_supabase(df_processed)
