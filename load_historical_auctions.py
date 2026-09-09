"""ETL: Estrazione e normalizzazione dello storico acquisti d'asta dalle rose.

Legge i file Excel delle rose iniziali (2021-2024) da:
C:\\Users\\andre\\Documents\\Data_Science\\PowerBI\\source\\ROSE\\iniziali
Normalizza i costi d'acquisto rispetto al budget della lega (es. 250 FM o 1000 FM),
salva `historical_auctions.csv` e carica i dati su Supabase nella tabella `historical_auction_purchases`.
"""

import os
from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import pandas as pd
import env_loader
from supabase import create_client



def parse_leghe_excel(path, anno, season_str, budget, prev_season):
    """Parsa un file Excel esportato da Leghe Fantacalcio."""
    df = pd.read_excel(path, header=None)
    records = []
    ruolo_locs = []

    # Cerca tutte le intestazioni 'Ruolo'
    for r in range(len(df)):
        for c in range(len(df.columns)):
            if str(df.iloc[r, c]).strip().lower() == "ruolo":
                ruolo_locs.append((r, c))

    for r, c in ruolo_locs:
        team_name = str(df.iloc[r - 1, c]).strip() if r > 0 else "FantaSquadra"
        curr_r = r + 1
        while curr_r < len(df):
            ruolo = str(df.iloc[curr_r, c]).strip()
            calciatore = str(df.iloc[curr_r, c + 1]).strip()

            if ruolo.lower() in ["nan", "none", "", "ruolo"] or calciatore.lower() in ["nan", "none", ""]:
                break
            if ruolo.upper() not in ["P", "D", "C", "A"]:
                break

            squadra = str(df.iloc[curr_r, c + 2]).strip()
            try:
                costo = float(df.iloc[curr_r, c + 3])
            except Exception:
                costo = 0.0

            # Normalizzazione del costo
            costo_pct = (costo / budget) * 100.0 if budget > 0 else 0.0
            costo_1000 = costo_pct * 10.0  # Normalizzato su budget standard 1000 FM

            records.append({
                "calciatore": calciatore,
                "ruolo": ruolo.upper(),
                "squadra": squadra,
                "fantasquadra": team_name,
                "costo": round(costo, 2),
                "budget_lega": float(budget),
                "costo_pct": round(costo_pct, 4),
                "costo_normalizzato_1000": round(costo_1000, 2),
                "anno_asta": int(anno),
                "stagione_asta": season_str,
                "prev_season": prev_season
            })
            curr_r += 1

    return pd.DataFrame(records)


def extract_all_auctions(base_dir=None):
    if base_dir is None:
        base_dir = Path(r"C:\Users\andre\Documents\Data_Science\PowerBI\source\ROSE\iniziali")

    file_configs = [
        (base_dir / "Rose_fantaasta_2021.xlsx", 2021, "2021-22", 250, "2020-21"),
        (base_dir / "Rose_scappoinmexico_2022.xlsx", 2022, "2022-23", 1000, "2021-22"),
        (base_dir / "Rose_billy-ballo-touree_2023.xlsx", 2023, "2023-24", 1000, "2022-23"),
        (base_dir / "Rose_complimentibaraldiperlavittoria_2024.xlsx", 2024, "2024-25", 1000, "2023-24"),
    ]

    all_dfs = []
    print("📂 [1/3] Estrazione acquisti d'asta dai file Excel...")
    for p, anno, season_str, budget, prev_s in file_configs:
        if p.exists():
            df_p = parse_leghe_excel(p, anno, season_str, budget, prev_s)
            cnt_pos = int((df_p["costo"] > 0).sum())
            print(f"   -> {p.name}: {len(df_p)} acquisti totali ({cnt_pos} con prezzo > 0, budget {budget} FM)")
            all_dfs.append(df_p)
        else:
            print(f"   [AVVISO] File non trovato: {p}")

    if not all_dfs:
        raise FileNotFoundError("Nessun file d'asta trovato.")

    combined = pd.concat(all_dfs, ignore_index=True)
    print(f"\n✅ Totale acquisti estratti: {len(combined)} (di cui {(combined['costo'] > 0).sum()} con prezzo > 0)")
    return combined


def save_and_upload(df):
    repo_dir = Path(__file__).resolve().parent
    csv_out = repo_dir / "historical_auctions.csv"
    df.to_csv(csv_out, index=False, encoding="utf-8")
    print(f"💾 [2/3] Salvato file locale: {csv_out}")

    print("☁️ [3/3] Sincronizzazione con Supabase (tabella historical_auction_purchases)...")
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        print("   [INFO] Credenziali Supabase non configurate. I dati sono salvati in locale.")
        return

    try:
        sb = create_client(url, key)
        records = df.to_dict(orient="records")

        # Inserimento a lotti di 150 record
        batch_size = 150
        inserted = 0
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            res = sb.table("historical_auction_purchases").upsert(batch).execute()
            inserted += len(batch)

        print(f"   ✅ {inserted} acquisti d'asta caricati con successo su Supabase!")
    except Exception as e:
        print(f"   [INFO] Tabella 'historical_auction_purchases' non ancora presente su Supabase: {e}")
        print("   -> Puoi crearla eseguendo lo script 'schema_historical_auctions.sql' su Supabase SQL Editor.")
        print("   -> Il dataset locale 'historical_auctions.csv' è comunque pronto per l'addestramento ML.")


def main():
    df = extract_all_auctions()
    save_and_upload(df)


if __name__ == "__main__":
    main()
