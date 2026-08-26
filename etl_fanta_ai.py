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


def fetch_and_process_data(seasons=["2024"]):
    """Scarica le statistiche dei giocatori da Understat con soccerdata e le trasforma."""
    print(f"Scaricamento dati Understat per la stagione: {seasons}...")
    
    try:
        understat = sd.Understat(leagues="ITA-Serie A", seasons=seasons)
        df_player = understat.read_player_season_stats()
    except Exception as e:
        print(f"Errore durante il download dei dati da Understat: {e}")
        return None

    # Reset degli indici per averli come colonne standard
    df_player = df_player.reset_index()

    # Creazione DataFrame pulito
    df_clean = pd.DataFrame()
    
    df_clean["player_name"] = df_player["player"].astype(str) if "player" in df_player.columns else ""
    df_clean["team"] = df_player["team"].astype(str) if "team" in df_player.columns else ""
    df_clean["season"] = df_player["season"].astype(str) if "season" in df_player.columns else ""
    
    # Minutaggio e presenze
    df_clean["matches_played"] = pd.to_numeric(df_player["matches"] if "matches" in df_player.columns else 0, errors="coerce").fillna(0).astype(int)
    df_clean["minutes_played"] = pd.to_numeric(df_player["time"] if "time" in df_player.columns else 0, errors="coerce").fillna(0).astype(int)
    
    # Gol & Assist
    df_clean["goals"] = pd.to_numeric(df_player["goals"] if "goals" in df_player.columns else 0, errors="coerce").fillna(0).astype(int)
    df_clean["assists"] = pd.to_numeric(df_player["assists"] if "assists" in df_player.columns else 0, errors="coerce").fillna(0).astype(int)
    
    # Metriche Avanzate (Expected Goals & Expected Assists)
    df_clean["xg"] = pd.to_numeric(df_player["xg"] if "xg" in df_player.columns else 0.0, errors="coerce").fillna(0.0).round(2)
    df_clean["xa"] = pd.to_numeric(df_player["xa"] if "xa" in df_player.columns else 0.0, errors="coerce").fillna(0.0).round(2)

    # Calcolo KPI per 90 minuti
    mins = df_clean["minutes_played"]
    df_clean["goals_per_90"] = (df_clean["goals"] / (mins / 90)).where(mins > 0, 0.0).round(2)
    df_clean["xg_per_90"] = (df_clean["xg"] / (mins / 90)).where(mins > 0, 0.0).round(2)

    # Tiri e Passaggi chiave
    df_clean["shots_total"] = pd.to_numeric(df_player["shots"] if "shots" in df_player.columns else 0, errors="coerce").fillna(0).astype(int)
    df_clean["shots_on_target"] = pd.to_numeric(df_player["key_passes"] if "key_passes" in df_player.columns else 0, errors="coerce").fillna(0).astype(int)

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
        response = supabase.table("player_stats").upsert(records).execute()
        print("Caricamento completato con successo su Supabase!")
    except Exception as e:
        print(f"Errore durante l'upsert su Supabase: {e}")


if __name__ == "__main__":
    df_processed = fetch_and_process_data(seasons=["2024"])
    upload_to_supabase(df_processed)
