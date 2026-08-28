import os
import sys
import io
import requests
import pandas as pd
from supabase import create_client

# ============================================================
# CONFIGURAZIONE
# ============================================================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ SUPABASE_URL e SUPABASE_KEY devono essere impostati.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Definizione delle stagioni da coprire
STAGIONI = ["2023-24", "2024-25", "2025-26", "2026-27"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# ============================================================
# UTILITY
# ============================================================
def get_completed_days():
    """Recupera le giornate già scaricate con successo dal DB di log."""
    res = supabase.table("download_logs").select("stagione, giornata").eq("status", "COMPLETED").execute()
    completed = set()
    for row in res.data:
        completed.add((row["stagione"], row["giornata"]))
    return completed

def parse_excel_and_insert(content, stagione, giornata):
    """Esegue il parsing del file Excel in memory e salva su Supabase."""
    df_raw = pd.read_excel(io.BytesIO(content), sheet_name=0)
    
    headers = df_raw.iloc[4].values
    rows = []
    current_team = None
    
    for i in range(3, len(df_raw)):
        row_vals = df_raw.iloc[i].values
        # Riconoscimento intestazione squadra
        if pd.notna(row_vals[0]) and all(pd.isna(x) for x in row_vals[1:]):
            current_team = str(row_vals[0]).strip()
        elif row_vals[0] != 'Cod.' and pd.notna(row_vals[0]) and pd.notna(row_vals[1]):
            # Cast sicuro
            def safe_val(val, default=0):
                if pd.isna(val) or val == '*' or val is None:
                    return default
                try:
                    return float(val) if isinstance(default, float) else int(val)
                except (ValueError, TypeError):
                    return default

            voto_raw = str(row_vals[3]).replace('*', '') if pd.notna(row_vals[3]) else None
            voto = float(voto_raw) if voto_raw and voto_raw != '5.5*' and voto_raw != '6*' and voto_raw.replace('.', '').isdigit() else None
            
            # Pulisce stringhe di voto con asterisco (es. "6*")
            if voto is None and pd.notna(row_vals[3]):
                try:
                    voto = float(str(row_vals[3]).replace('*', ''))
                except:
                    voto = None

            row_dict = {
                "player_id": int(row_vals[0]),
                "ruolo": str(row_vals[1]).strip(),
                "nome": str(row_vals[2]).strip(),
                "squadra": current_team,
                "stagione": stagione,
                "giornata": giornata,
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
            
            # Calcolo automatico FantaVoto base
            fanta_voto = voto if voto is not None else 0.0
            if voto is not None:
                fanta_voto += (row_dict["gf"] * 3) + (row_dict["ass"] * 1) + (row_dict["rf"] * 3) + (row_dict["rp"] * 3)
                fanta_voto += (row_dict["gdv"] * 0) + (row_dict["gdp"] * 0)
                fanta_voto -= (row_dict["gs"] * 1) + (row_dict["rs"] * 3) + (row_dict["au"] * 2)
                fanta_voto -= (row_dict["amm"] * 0.5) + (row_dict["esp"] * 1)
            
            row_dict["fanta_voto"] = round(fanta_voto, 1) if voto is not None else None
            rows.append(row_dict)

    if rows:
        supabase.table("player_stats_history").upsert(
            rows, 
            on_conflict="player_id,stagione,giornata,redazione"
        ).execute()

    return len(rows)

# ============================================================
# MAIN INGESTION WORKFLOW
# ============================================================
def run():
    completed_logs = get_completed_days()
    print(f"📊 Trovate {len(completed_logs)} giornate già elaborate nel log.")

    for stagione in STAGIONI:
        for giornata in range(1, 39):
            if (stagione, giornata) in completed_logs:
                continue

            # Costruzione URL download Excel ufficiale
            excel_url = f"https://www.fantacalcio.it/servizi/voti/excel/{stagione}/{giornata}"
            print(f"📡 Downloading: {stagione} | Giornata {giornata}...", end=" ")

            res = requests.get(excel_url, headers=HEADERS)
            
            if res.status_code != 200 or len(res.content) < 5000:
                print(f"⚠️ Non disponibile o stagione futura. Interruzione per {stagione}.")
                break  # Se la giornata non è ancora stata giocata, passa alla stagione successiva

            # 1. Salva copia file Excel per repository GitHub
            folder_path = f"data/excel/{stagione}"
            os.makedirs(folder_path, exist_ok=True)
            file_path = os.path.join(folder_path, f"giornata_{giornata}.xlsx")
            
            with open(file_path, "wb") as f:
                f.write(res.content)

            # 2. Parsing e inserimento in Supabase
            inserted = parse_excel_and_insert(res.content, stagione, giornata)

            # 3. Aggiorna Log su Supabase
            supabase.table("download_logs").upsert({
                "stagione": stagione,
                "giornata": giornata,
                "status": "COMPLETED",
                "records_inserted": inserted
            }, on_conflict="stagione,giornata").execute()

            print(f"✅ OK ({inserted} voti caricati)")

if __name__ == "__main__":
    run()
