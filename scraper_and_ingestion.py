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

# Mappatura Stagioni: Nome -> ID interno usato dal backend di Fantacalcio.it
STAGIONI_MAP = {
    "2023-24": 18,
    "2024-25": 19,
    "2025-26": 20,
    "2026-27": 21
}

# Assicuriamo la creazione preliminare della directory base per evitare errori Git
os.makedirs("data/excel", exist_ok=True)

# ============================================================
# UTILITY DATABASE & LOGGING
# ============================================================
def get_completed_days():
    """Recupera l'elenco delle giornate già scaricate dal log."""
    try:
        res = supabase.table("download_logs").select("stagione, giornata").eq("status", "COMPLETED").execute()
        completed = set()
        for row in res.data:
            completed.add((row["stagione"], int(row["giornata"])))
        return completed
    except Exception as e:
        print(f"⚠️ Impossibile leggere i log da Supabase: {e}")
        return set()

# ============================================================
# PARSING EXCEL & INGESTION
# ============================================================
def parse_excel_and_insert(content, stagione, giornata):
    """Legge il file Excel ed esegue l'upsert dei voti su Supabase."""
    df_raw = pd.read_excel(io.BytesIO(content), sheet_name=0)
    
    rows = []
    current_team = None
    
    for i in range(3, len(df_raw)):
        row_vals = df_raw.iloc[i].values
        
        if pd.notna(row_vals[0]) and all(pd.isna(x) for x in row_vals[1:]):
            current_team = str(row_vals[0]).strip()
        elif row_vals[0] != 'Cod.' and pd.notna(row_vals[0]) and pd.notna(row_vals[1]):
            
            def safe_val(val, default=0):
                if pd.isna(val) or val == '*' or val is None:
                    return default
                try:
                    return int(val)
                except (ValueError, TypeError):
                    return default

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
        supabase.table("player_stats_history").upsert(
            rows, 
            on_conflict="player_id,stagione,giornata,redazione"
        ).execute()

    return len(rows)

# ============================================================
# FLUSSO DI DOWNLOAD & WORKFLOW
# ============================================================
def run():
    completed_logs = get_completed_days()
    print(f"📊 Trovate {len(completed_logs)} giornate già elaborate nel registro log.")

    session = requests.Session()
    headers_base = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    for stagione, season_id in STAGIONI_MAP.items():
        print(f"\n--- Elaborazione Stagione {stagione} (ID: {season_id}) ---")
        for giornata in range(1, 39):
            if (stagione, giornata) in completed_logs:
                continue

            # Tentativo 1: Endpoint basato su ID numerico stagione
            excel_url = f"https://www.fantacalcio.it/servizi/voti/excel?st={season_id}&g={giornata}"
            print(f"📡 Downloading: {stagione} | Giornata {giornata}...", end=" ", flush=True)

            try:
                headers_download = headers_base.copy()
                headers_download["Referer"] = f"https://www.fantacalcio.it/voti-fantacalcio-serie-a/{stagione}/{giornata}"
                res = session.get(excel_url, headers=headers_download, timeout=20, allow_redirects=True)
            except Exception as e:
                print(f"⚠️ Errore di connessione: {e}")
                break

            # Verifichiamo se abbiamo ricevuto un file Excel (magic bytes ZIP/XLSX: PK\x03\x04)
            is_excel = res.status_code == 200 and res.content.startswith(b'PK\x03\x04')

            if not is_excel:
                # Tentativo 2 (Fallback): Endpoint con stringa stagione
                alt_url = f"https://www.fantacalcio.it/servizi/voti/excel/{stagione}/{giornata}"
                try:
                    res = session.get(alt_url, headers=headers_download, timeout=20, allow_redirects=True)
                    is_excel = res.status_code == 200 and res.content.startswith(b'PK\x03\x04')
                except Exception:
                    pass

            if not is_excel:
                print(f"⚠️ Non disponibile o giornata futura. Interruzione per {stagione}.")
                break

            # 1. Salva file locale
            folder_path = f"data/excel/{stagione}"
            os.makedirs(folder_path, exist_ok=True)
            file_path = os.path.join(folder_path, f"giornata_{giornata}.xlsx")
            
            with open(file_path, "wb") as f:
                f.write(res.content)

            # 2. Parsing e Ingestion Supabase
            try:
                inserted = parse_excel_and_insert(res.content, stagione, giornata)
            except Exception as e:
                print(f"❌ Errore parsing/DB: {e}")
                continue

            # 3. Log di completamento
            supabase.table("download_logs").upsert({
                "stagione": stagione,
                "giornata": giornata,
                "status": "COMPLETED",
                "records_inserted": inserted
            }, on_conflict="stagione,giornata").execute()

            print(f"✅ OK ({inserted} voti caricati)")

if __name__ == "__main__":
    run()
