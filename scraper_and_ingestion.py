import os
import sys
import io
import requests
import pandas as pd
from supabase import create_client

# ============================================================
# CONFIGURAZIONE AMBIENTE & SUPABASE
# ============================================================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ SUPABASE_URL e SUPABASE_KEY devono essere impostati nelle variabili d'ambiente.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Stagioni da analizzare
STAGIONI = ["2023-24", "2024-25", "2025-26", "2026-27"]

# ============================================================
# UTILITY DATABASE & LOGGING
# ============================================================
def get_completed_days():
    """Recupera l'elenco delle giornate già scaricate ed elaborate con successo dal database."""
    try:
        res = supabase.table("download_logs").select("stagione, giornata").eq("status", "COMPLETED").execute()
        completed = set()
        for row in res.data:
            completed.add((row["stagione"], int(row["giornata"])))
        return completed
    except Exception as e:
        print(f"⚠️ Impossibile leggere i log da Supabase (prima esecuzione?): {e}")
        return set()

# ============================================================
# PARSING EXCEL & INGESTION
# ============================================================
def parse_excel_and_insert(content, stagione, giornata):
    """Legge il file Excel in memoria, ne estrae le statistiche e le carica su Supabase."""
    df_raw = pd.read_excel(io.BytesIO(content), sheet_name=0)
    
    headers = df_raw.iloc[4].values
    rows = []
    current_team = None
    
    for i in range(3, len(df_raw)):
        row_vals = df_raw.iloc[i].values
        
        # Identificazione del nome della squadra (riga con solo la prima colonna valorizzata)
        if pd.notna(row_vals[0]) and all(pd.isna(x) for x in row_vals[1:]):
            current_team = str(row_vals[0]).strip()
        elif row_vals[0] != 'Cod.' and pd.notna(row_vals[0]) and pd.notna(row_vals[1]):
            
            # Helper per la conversione sicura dei numeri e la pulizia dei malus/bonus
            def safe_val(val, default=0):
                if pd.isna(val) or val == '*' or val is None:
                    return default
                try:
                    return int(val)
                except (ValueError, TypeError):
                    return default

            # Estrazione e pulizia del Voto (es. "6*", "5.5*", "6" -> 6.0, 5.5)
            voto_raw = str(row_vals[3]).replace('*', '').strip() if pd.notna(row_vals[3]) else None
            try:
                voto = float(voto_raw) if voto_raw and voto_raw != '-' else None
            except ValueError:
                voto = None

            row_dict = {
                "player_id": int(row_vals[0]),
                "ruolo": str(row_vals[1]).strip(),
                "nome": str(row_vals[2]).strip(),
                "squadra": current_team,
                "stagione": stagione,
                "giornata": int(giornata),
                "redazione": "Fantacalcio",
                "voto": voto,
                "gf": safe_val(row_vals[4]),
                "gs": safe_val(row_vals[5]),
                "rp": safe_val(row_vals[6]),
                "rs": safe_val(row_vals[7]),
                "rf": safe_val(row_vals[8]),
                "au": safe_val(row_vals[9]),
                "amm": safe_val(row_vals[10]),
                "esp": safe_val(row_vals[11]),
                "ass": safe_val(row_vals[12]),
                "gdv": safe_val(row_vals[13]),
                "gdp": safe_val(row_vals[14])
            }
            
            # Calcolo automatico del FantaVoto base
            if voto is not None:
                fanta_voto = voto
                fanta_voto += (row_dict["gf"] * 3) + (row_dict["ass"] * 1) + (row_dict["rf"] * 3) + (row_dict["rp"] * 3)
                fanta_voto -= (row_dict["gs"] * 1) + (row_dict["rs"] * 3) + (row_dict["au"] * 2)
                fanta_voto -= (row_dict["amm"] * 0.5) + (row_dict["esp"] * 1)
                row_dict["fanta_voto"] = round(fanta_voto, 1)
            else:
                row_dict["fanta_voto"] = None

            rows.append(row_dict)

    if rows:
        # Inserimento in batch/upsert su Supabase
        supabase.table("player_stats_history").upsert(
            rows, 
            on_conflict="player_id,stagione,giornata,redazione"
        ).execute()

    return len(rows)

# ============================================================
# FLUSSO PRINCIPALE DI DOWNLOAD & WORKFLOW
# ============================================================
def run():
    completed_logs = get_completed_days()
    print(f"📊 Trovate {len(completed_logs)} giornate già elaborate nel registro log.")

    # Configurazione della sessione HTTP per simulare la navigazione reale da browser
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,*/*;q=0.8",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.fantacalcio.it/voti-fantacalcio-serie-a"
    })

    for stagione in STAGIONI:
        print(f"\n--- Elaborazione Stagione {stagione} ---")
        for giornata in range(1, 39):
            if (stagione, giornata) in completed_logs:
                continue

            excel_url = f"https://www.fantacalcio.it/servizi/voti/excel/{stagione}/{giornata}"
            print(f"📡 Downloading: {stagione} | Giornata {giornata}...", end=" ", flush=True)

            try:
                res = session.get(excel_url, timeout=20, allow_redirects=True)
            except Exception as e:
                print(f"⚠️ Errore di connessione: {e}")
                break

            # Verifichiamo che la risposta sia un file Excel ZIP/XLSX reale (magic bytes: PK\x03\x04)
            is_excel = res.status_code == 200 and res.content.startswith(b'PK\x03\x04')

            if not is_excel:
                print(f"⚠️ Non disponibile o giornata non ancora giocata. Interruzione per la stagione {stagione}.")
                break  # Passa alla stagione successiva se la giornata non è stata ancora disputata

            # 1. Salva la copia locale del file Excel per il commit su GitHub
            folder_path = f"data/excel/{stagione}"
            os.makedirs(folder_path, exist_ok=True)
            file_path = os.path.join(folder_path, f"giornata_{giornata}.xlsx")
            
            with open(file_path, "wb") as f:
                f.write(res.content)

            # 2. Parsing ed inserimento in Supabase
            try:
                inserted = parse_excel_and_insert(res.content, stagione, giornata)
            except Exception as e:
                print(f"❌ Errore durante il parsing o il salvataggio su DB: {e}")
                continue

            # 3. Registrazione della giornata completata nel log di Supabase
            supabase.table("download_logs").upsert({
                "stagione": stagione,
                "giornata": giornata,
                "status": "COMPLETED",
                "records_inserted": inserted
            }, on_conflict="stagione,giornata").execute()

            print(f"✅ OK ({inserted} voti caricati)")

if __name__ == "__main__":
    run()
