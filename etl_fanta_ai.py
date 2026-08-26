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
    """Scarica le statistiche dei giocatori da Understat con soccerdata e le trasforma.
    Nota: Understat definisce la stagione '2024-2025' semplicemente con l'anno di partenza ('2024').
    """
    print(f"Scaricamento dati Understat per la stagione: {seasons}...")
    
    try:
        # Usiamo Understat al posto di FBref per bypassare i blocchi CAPTCHA di Cloudflare
        understat = sd.Understat(leagues="ITA-Serie A", seasons=seasons)
        df_player = understat.read_player_season_stats()
    except Exception as e:
        print(f"Errore durante il download dei dati da Understat: {e}")
        return None

    # Reset degli indici (league, season, team, player) per averli come colonne standard
    df_player = df_player.reset_index()

    # Creazione DataFrame pulito e strutturato per Supabase
    df_clean = pd.DataFrame()
    
    df_clean["player_name"] = df_player["player"].astype(str)
    df_clean["team"] = df_player["team"].astype(str)
    df_clean["season"] = df_player["season"].astype(str)
    
    # Minutaggio e presenze
    df_clean["matches_played"] = pd.to_numeric(df_player.get("matches", 0), errors="coerce").fillna(0).astype(int)
    df_clean["minutes_played"] = pd.to_numeric(df_player.get("time", 0), errors="coerce").fillna(0).astype(int)
    
    # Gol & Assist
    df_clean["goals"] = pd.to_numeric(df_player.get("goals", 0), errors="coerce").fillna(0).astype(int)
    df_clean["assists"] = pd.to_numeric(df_player.get("assists", 0), errors="coerce").fillna(0).astype(int)
    
    # Metriche Avanzate (Expected Goals & Expected Assists)
    df_clean["xg"] = pd.to_numeric(df_player.get("xg", 0.0), errors="coerce").fillna(0.0).round(2)
    df_clean["xa"] = pd.to_numeric(df_player.get("xa", 0.0), errors="coerce").fillna(0.0).round(2)

    # Calcolo KPI per 90 minuti
    mins = df_clean["minutes_played"]
    df_clean["goals_per_90"] = (df_clean["goals"] / (mins / 90)).where(mins > 0, 0.0).round(2)
    df_clean["xg_per_90"] = (df_clean["xg"] / (mins / 90)).where(mins > 0, 0.0).round(2)

    # Tiri
    df_clean["shots_total"] = pd.to_numeric(df_player.get("shots", 0), errors="coerce").fillna(0).astype(int)
    df_clean["shots_on_target"] = pd.to_numeric(df_player.get("key_passes", 0), errors="coerce").fillna(0).astype(int)

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
    # In Understat l'anno '2024' identifica la stagione 2024/2025
    df_processed = fetch_and_process_data(seasons=["2024"])
    upload_to_supabase(df_processed)
