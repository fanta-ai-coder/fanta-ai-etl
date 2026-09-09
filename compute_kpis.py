"""
============================================================
COMPUTE KPIS - FANTA-AI ANALYTICS ENGINE
============================================================

Aggrega ed elabora offline tutti i dati analitici dei giocatori:
1. Listone quotazioni (giocatori_quotazioni)
2. Ranking algoritmico (player_ranking)
3. Storico voti e bonus/malus (player_stats_history)
4. Probabili formazioni, titolari e infortuni (titolari_infortuni.csv)
5. Rigoristi e battitori punizioni (rigoristi.csv, punizioni.csv)

Output:
Salva e aggiorna la tabella Supabase `player_kpi_summary`, fornendo
alla dashboard una singola tabella ultra-leggera con tutti i KPI
già pronti per una visualizzazione istantanea.

Uso:
    python compute_kpis.py
    python compute_kpis.py --stagione 2026-27
============================================================
"""

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import env_loader
import numpy as np
import pandas as pd
from supabase import create_client


def get_supabase_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        env_path = Path(r"C:\Users\andre\Documents\Python Scripts\fantacalcio\env.txt")
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line.startswith("set "):
                    line = line[4:]
                if "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip()
                    if k == "SUPABASE_URL":
                        url = v
                    elif k == "SUPABASE_KEY":
                        key = v

    if not url or not key:
        raise RuntimeError("Credenziali SUPABASE_URL e SUPABASE_KEY non trovate.")

    return create_client(url, key)


def fetch_all_paginated(client, table_name, select_cols="*", page_size=1000):
    """Scarica tutte le righe di una tabella paginando."""
    rows = []
    start = 0
    actual_limit = min(page_size, 1000)
    while True:
        res = (
            client.table(table_name)
            .select(select_cols)
            .range(start, start + actual_limit - 1)
            .execute()
        )
        data = res.data or []
        rows.extend(data)
        if len(data) < actual_limit:
            break
        start += actual_limit
        if start % 10000 == 0:
            print(f"         ...scaricate {start} righe...")
    return pd.DataFrame(rows)


def clean_num_series(series):
    return pd.to_numeric(series, errors="coerce")


def safe_mean(series):
    s = clean_num_series(series).dropna()
    return float(s.mean()) if not s.empty else None


def safe_sum(series):
    s = clean_num_series(series).dropna()
    return float(s.sum()) if not s.empty else 0.0


def safe_variance(series):
    s = clean_num_series(series).dropna()
    return float(s.var(ddof=1)) if len(s) > 1 else None


def compute_kpis_for_all(repo_dir: Path, stagione="2026-27", dry_run=False):
    print("=" * 60)
    print("🧠 CALCOLO E PRECOMPUTAZIONE KPI GIOCATORI")
    print("=" * 60)

    client = get_supabase_client()

    # 1. Caricamento Listone Quotazioni
    print(f"[1/5] Lettura giocatori_quotazioni per la stagione {stagione}...")
    quot_df = pd.DataFrame(
        client.table("giocatori_quotazioni")
        .select("*")
        .eq("stagione", stagione)
        .execute()
        .data or []
    )

    if quot_df.empty:
        print(f"[ATTENZIONE] Nessun giocatore trovato per la stagione {stagione}. Carico tutte le quotazioni...")
        quot_df = pd.DataFrame(client.table("giocatori_quotazioni").select("*").execute().data or [])

    if quot_df.empty:
        raise RuntimeError("Tabella giocatori_quotazioni vuota o inaccessibile.")

    print(f"      -> {len(quot_df)} giocatori nel listone.")

    # 2. Caricamento Ranking Algoritmico
    print("[2/5] Lettura player_ranking...")
    try:
        rank_df = pd.DataFrame(client.table("player_ranking").select("*").execute().data or [])
        print(f"      -> {len(rank_df)} record di ranking trovati.")
    except Exception as e:
        print(f"      -> [AVVISO] Impossibile caricare player_ranking: {e}")
        rank_df = pd.DataFrame()

    # 3. Caricamento File Scraped (Titolari, Rigoristi, Punizioni)
    print("[3/5] Lettura dati formazioni, rigoristi e punizioni...")
    titolari_path = repo_dir / "titolari_infortuni.csv"
    if not titolari_path.exists():
        titolari_path = repo_dir / "titolari_infortuni"
    
    titolari_df = pd.read_csv(titolari_path) if titolari_path.exists() else pd.DataFrame()
    rigoristi_path = repo_dir / "rigoristi.csv"
    rigoristi_df = pd.read_csv(rigoristi_path) if rigoristi_path.exists() else pd.DataFrame()
    punizioni_path = repo_dir / "punizioni.csv"
    punizioni_df = pd.read_csv(punizioni_path) if punizioni_path.exists() else pd.DataFrame()

    print(f"      -> Formazioni: {len(titolari_df)} righe | Rigoristi: {len(rigoristi_df)} | Punizioni: {len(punizioni_df)}")

    # 4. Caricamento ed elaborazione Storico Voti
    print("[4/5] Lettura ed aggregazione storico voti (player_stats_history)...")
    cols_to_fetch = "player_id,stagione,giornata,ruolo,voto,gf,gs,rp,rs,rf,au,amm,esp,ass"
    stats_df = fetch_all_paginated(client, "player_stats_history", select_cols=cols_to_fetch, page_size=2000)
    print(f"      -> {len(stats_df)} voti storici scaricati. Elaborazione metriche...")

    # Calcolo fanta_voto e pulizia voti
    if not stats_df.empty:
        stats_df["player_id"] = pd.to_numeric(stats_df["player_id"], errors="coerce")
        stats_df = stats_df[stats_df["player_id"].notna()].copy()
        stats_df["player_id"] = stats_df["player_id"].astype(int)

        # Rimuovi voti asteriscati (es. "6*", s.v.)
        raw_vote = stats_df["voto"].astype(str).str.strip()
        starred = raw_vote.str.contains(r"\*", regex=True, na=False)
        stats_clean = stats_df.loc[~starred].copy()

        voto = clean_num_series(stats_clean["voto"])
        stats_clean["voto_num"] = voto
        gf = clean_num_series(stats_clean["gf"]).fillna(0)
        rf = clean_num_series(stats_clean["rf"]).fillna(0)
        ass = clean_num_series(stats_clean["ass"]).fillna(0)
        au = clean_num_series(stats_clean["au"]).fillna(0)
        esp = clean_num_series(stats_clean["esp"]).fillna(0)
        amm = clean_num_series(stats_clean["amm"]).fillna(0)
        gs = clean_num_series(stats_clean["gs"]).fillna(0)
        rp = clean_num_series(stats_clean["rp"]).fillna(0)

        is_p = stats_clean["ruolo"].astype(str).str.strip().str.upper().eq("P")
        gs = gs.where(is_p, 0)

        fv = voto + (gf * 3) + ass + (rf * 3) - (au * 2) - esp - (amm * 0.5) + (rp * 3) - gs
        stats_clean["fanta_voto_calcolato"] = fv
        stats_clean.loc[voto.isna(), "fanta_voto_calcolato"] = np.nan

        # Aggregazioni per giocatore
        print("      -> Calcolo aggregati avanzati per giocatore...")
        valid_votes = stats_clean[stats_clean["voto_num"].notna()].copy()
        
        # Statistiche per player_id
        grouped = valid_votes.groupby("player_id")
        
        agg_dict = {}
        for pid, group in grouped:
            seasons_cnt = group["stagione"].dropna().astype(str).str.strip().nunique()
            if seasons_cnt == 0:
                seasons_cnt = 1
            
            p_ruolo = group["ruolo"].iloc[-1] if not group.empty else ""
            is_gk = str(p_ruolo).upper().strip() == "P"

            presenze_tot = int(group["voto_num"].count())
            presenze_med = presenze_tot / seasons_cnt
            pres_pct = min(100.0, (presenze_med / 38.0) * 100.0)

            mv = safe_mean(group["voto_num"])
            fm = safe_mean(group["fanta_voto_calcolato"])
            var_voto = safe_variance(group["voto_num"])

            # Varianza gol binaria
            if "giornata" in group.columns and len(group) > 1:
                gf_rf = clean_num_series(group["gf"]).fillna(0) + clean_num_series(group["rf"]).fillna(0)
                day_goals = gf_rf.groupby(group["giornata"]).sum()
                binary_goals = (day_goals > 0).astype(int)
                var_gol = float(binary_goals.var(ddof=1)) if len(binary_goals) > 1 else 0.0
            else:
                var_gol = 0.0

            if is_gk:
                gs_stag = safe_sum(group["gs"]) / seasons_cnt
                rp_stag = safe_sum(group["rp"]) / seasons_cnt
                gol_stag = 0.0
            else:
                gs_stag = 0.0
                rp_stag = 0.0
                gol_stag = (safe_sum(group["gf"]) + safe_sum(group["rf"])) / seasons_cnt

            ass_stag = safe_sum(group["ass"]) / seasons_cnt
            amm_stag = safe_sum(group["amm"]) / seasons_cnt
            esp_stag = safe_sum(group["esp"]) / seasons_cnt

            agg_dict[pid] = {
                "presenze_totali": presenze_tot,
                "fantamedia": round(fm, 2) if fm is not None else None,
                "media_voto": round(mv, 2) if mv is not None else None,
                "presenze_medie": round(presenze_med, 1),
                "presenza_pct": round(pres_pct, 1),
                "gol_stagione": round(gol_stag, 1),
                "assist_stagione": round(ass_stag, 1),
                "gs_stagione": round(gs_stag, 1),
                "rigori_parati": round(rp_stag, 1),
                "varianza_voto": round(var_voto, 3) if var_voto is not None else None,
                "varianza_gol": round(var_gol, 3) if var_gol is not None else None,
                "ammonizioni": round(amm_stag, 1),
                "espulsioni": round(esp_stag, 1),
            }
    else:
        agg_dict = {}

    # 5. Normalizzazione e Creazione Record Finali
    print("[5/5] Fusione dati ed elaborazione player_kpi_summary...")

    # Indicizzazione Ranking
    rank_dict = {}
    if not rank_df.empty and "player_id" in rank_df.columns:
        rank_df["player_id"] = pd.to_numeric(rank_df["player_id"], errors="coerce")
        for _, r in rank_df.dropna(subset=["player_id"]).iterrows():
            pid = int(r["player_id"])
            rank_dict[pid] = {
                "indice_finale": round(float(r["indice_finale"]), 2) if pd.notna(r.get("indice_finale")) else None,
                "rank_ruolo": int(r["rank_ruolo"]) if pd.notna(r.get("rank_ruolo")) else None,
                "totale_ruolo": int(r["totale_ruolo"]) if pd.notna(r.get("totale_ruolo")) else None,
                "rank_generale": int(r["rank_generale"]) if pd.notna(r.get("rank_generale")) else None,
                "totale_generale": int(r["totale_generale"]) if pd.notna(r.get("totale_generale")) else None,
                "performance_score": round(float(r["performance_score"]), 2) if pd.notna(r.get("performance_score")) else None,
                "reliability_score": round(float(r["reliability_score"]), 2) if pd.notna(r.get("reliability_score")) else None,
                "forma_attuale_score": round(float(r["forma_attuale_score"]), 2) if pd.notna(r.get("forma_attuale_score")) else None,
                "titolarita_score": round(float(r["titolarita_score"]), 2) if pd.notna(r.get("titolarita_score")) else None,
                "presenze_pesate": round(float(r["presenze_pesate"]), 2) if pd.notna(r.get("presenze_pesate")) else None,
            }

    # Indicizzazione Titolari & Infortuni
    titolari_dict = {}
    if not titolari_df.empty:
        titolari_df["nome_norm"] = titolari_df["nome_giocatore"].astype(str).str.upper().str.strip()
        titolari_df["squadra_norm"] = titolari_df["squadra"].astype(str).str.upper().str.strip()
        for _, tr in titolari_df.iterrows():
            k = (tr["nome_norm"], tr["squadra_norm"])
            tit = str(tr.get("titolarita", "")).strip().lower()
            is_tit = "titolare" in tit
            inf = str(tr.get("infortunato", "")).strip().lower() in ["sì", "si", "true", "1", "yes"]
            squal = str(tr.get("squalificato", "")).strip().lower() in ["sì", "si", "true", "1", "yes"]
            desc_inf = str(tr.get("desc_infortunio", "")).strip()
            if desc_inf.lower() == "nan":
                desc_inf = ""
            titolari_dict[k] = {
                "titolarita": tit,
                "is_titolare": is_tit,
                "infortunato": inf,
                "desc_infortunio": desc_inf,
                "squalificato": squal,
            }

    # Indicizzazione Rigoristi
    rigoristi_dict = {}
    if not rigoristi_df.empty:
        rigoristi_df["giocatore_norm"] = rigoristi_df["giocatore"].astype(str).str.upper().str.strip()
        rigoristi_df["squadra_norm"] = rigoristi_df["squadra"].astype(str).str.upper().str.strip()
        for _, rr in rigoristi_df.iterrows():
            k = (rr["giocatore_norm"], rr["squadra_norm"])
            pos = pd.to_numeric(rr.get("posizione"), errors="coerce")
            rigoristi_dict[k] = int(pos) if pd.notna(pos) else 1

    # Indicizzazione Punizioni
    punizioni_dict = {}
    if not punizioni_df.empty:
        punizioni_df["giocatore_norm"] = punizioni_df["giocatore"].astype(str).str.upper().str.strip()
        punizioni_df["squadra_norm"] = punizioni_df["squadra"].astype(str).str.upper().str.strip()
        for _, pr in punizioni_df.iterrows():
            k = (pr["giocatore_norm"], pr["squadra_norm"])
            pos = pd.to_numeric(pr.get("posizione"), errors="coerce")
            punizioni_dict[k] = int(pos) if pd.notna(pos) else 1

    # Costruzione record unificati
    records_to_upsert = []
    now_ts = datetime.now(timezone.utc).isoformat()

    for _, q in quot_df.iterrows():
        pid = int(q["player_id"])
        nome = str(q.get("nome", "")).strip()
        squadra = str(q.get("squadra", "")).strip()
        nome_norm = nome.upper()
        squadra_norm = squadra.upper()
        key_pair = (nome_norm, squadra_norm)

        r_info = rank_dict.get(pid, {})
        s_info = agg_dict.get(pid, {
            "presenze_totali": 0, "fantamedia": None, "media_voto": None,
            "presenze_medie": 0.0, "presenza_pct": 0.0, "gol_stagione": 0.0,
            "assist_stagione": 0.0, "gs_stagione": 0.0, "rigori_parati": 0.0,
            "varianza_voto": None, "varianza_gol": None, "ammonizioni": 0.0, "espulsioni": 0.0
        })
        t_info = titolari_dict.get(key_pair, {
            "titolarita": "", "is_titolare": False, "infortunato": False,
            "desc_infortunio": "", "squalificato": False
        })
        rig_pos = rigoristi_dict.get(key_pair, None)
        pun_pos = punizioni_dict.get(key_pair, None)

        record = {
            "player_id": pid,
            "stagione": str(q.get("stagione", stagione)).strip(),
            "nome": nome,
            "ruolo": str(q.get("ruolo", "-")).upper().strip(),
            "ruolo_mantra": str(q.get("ruolo_mantra", "")).strip() if pd.notna(q.get("ruolo_mantra")) else None,
            "squadra": squadra,
            "quotazione_attuale": int(q.get("quotazione_attuale", 0)) if pd.notna(q.get("quotazione_attuale")) else 0,
            "quotazione_iniziale": int(q.get("quotazione_iniziale", 0)) if pd.notna(q.get("quotazione_iniziale")) else 0,
            "diff_quotazione": int(q.get("diff_quotazione", 0)) if pd.notna(q.get("diff_quotazione")) else 0,
            "fvm": int(q.get("fvm", 0)) if pd.notna(q.get("fvm")) else 0,
            "ceduto": bool(q.get("ceduto", False)),

            # Indici Algoritmici
            "indice_finale": r_info.get("indice_finale"),
            "rank_ruolo": r_info.get("rank_ruolo"),
            "totale_ruolo": r_info.get("totale_ruolo"),
            "rank_generale": r_info.get("rank_generale"),
            "totale_generale": r_info.get("totale_generale"),
            "performance_score": r_info.get("performance_score"),
            "reliability_score": r_info.get("reliability_score"),
            "forma_attuale_score": r_info.get("forma_attuale_score"),
            "titolarita_score": r_info.get("titolarita_score"),
            "presenze_pesate": r_info.get("presenze_pesate"),

            # Statistiche Aggregate Storiche
            "fantamedia": s_info.get("fantamedia"),
            "media_voto": s_info.get("media_voto"),
            "presenze_totali": s_info.get("presenze_totali", 0),
            "presenza_pct": s_info.get("presenza_pct", 0.0),
            "presenze_medie": s_info.get("presenze_medie", 0.0),
            "gol_stagione": s_info.get("gol_stagione", 0.0),
            "assist_stagione": s_info.get("assist_stagione", 0.0),
            "gs_stagione": s_info.get("gs_stagione", 0.0),
            "rigori_parati": s_info.get("rigori_parati", 0.0),
            "varianza_voto": s_info.get("varianza_voto"),
            "varianza_gol": s_info.get("varianza_gol"),
            "ammonizioni": s_info.get("ammonizioni", 0.0),
            "espulsioni": s_info.get("espulsioni", 0.0),

            # Status Formazioni & Battitori
            "titolarita": t_info.get("titolarita"),
            "is_titolare": t_info.get("is_titolare", False),
            "infortunato": t_info.get("infortunato", False),
            "desc_infortunio": t_info.get("desc_infortunio"),
            "squalificato": t_info.get("squalificato", False),
            "rigorista_pos": rig_pos,
            "punizioni_pos": pun_pos,

            "updated_at": now_ts,
        }
        records_to_upsert.append(record)

    print(f"\n💾 Upsert di {len(records_to_upsert)} record in `player_kpi_summary` su Supabase...")

    # Salva copia CSV/JSON locale di sicurezza
    summary_df = pd.DataFrame(records_to_upsert)
    csv_out = repo_dir / "player_kpi_summary.csv"
    summary_df.to_csv(csv_out, index=False)
    print(f"   Salvata copia locale: {csv_out} ({len(summary_df)} righe)")

    if dry_run:
        print("\n[DRY RUN] Calcolo completato con successo. Nessun dato inviato a Supabase.")
        return summary_df

    # Upsert in chunk da 100
    chunk_size = 100
    inserted_count = 0
    for i in range(0, len(records_to_upsert), chunk_size):
        chunk = records_to_upsert[i : i + chunk_size]
        try:
            client.table("player_kpi_summary").upsert(
                chunk,
                on_conflict="player_id,stagione"
            ).execute()
            inserted_count += len(chunk)
            print(f"   Salvato chunk {i // chunk_size + 1}/{(len(records_to_upsert) - 1) // chunk_size + 1} ({len(chunk)} record)")
        except Exception as e:
            print(f"\n[ERRORE] Upsert in player_kpi_summary fallito: {e}")
            print("Verifica che la tabella 'player_kpi_summary' sia stata creata su Supabase tramite schema_player_kpi_summary.sql")
            raise

    print(f"\n✅ COMPLETATO! {inserted_count} giocatori precalcolati e salvati in `player_kpi_summary`.")
    return summary_df


def main():
    parser = argparse.ArgumentParser(description="Calcolo e Precomputazione KPI Giocatori")
    parser.add_argument("--stagione", default="2026-27", help="Stagione di riferimento (default: 2026-27)")
    parser.add_argument("--dry-run", action="store_true", help="Calcola solo i KPI e salva CSV locale senza scrivere su Supabase")
    args = parser.parse_args()

    repo_dir = Path(__file__).resolve().parent
    compute_kpis_for_all(repo_dir=repo_dir, stagione=args.stagione, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
