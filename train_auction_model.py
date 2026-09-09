"""Modello di Machine Learning per la stima dei fantamilioni d'asta (con range basato su RMSE).

1. Carica lo storico acquisti d'asta (`historical_auctions.csv`) con costi normalizzati (base 1000 FM).
2. Associa a ogni acquisto dell'anno T le statistiche della stagione precedente (T-1) da Supabase / cache.
3. Addestra un modello di regressione con feature di rendimento (Fantamedia, Media Voto, Gol, Assist, Presenze)
   ed elasticità per ruolo (P, D, C, A) con termini di interazione.
4. Calcola lo Scarto Quadratico Medio (RMSE) dei residui per determinare il range di confidenza dell'asta.
5. Genera le previsioni per tutti i giocatori della stagione 2026-27 (sia su budget 1000 FM che su budget 500 FM).
6. Salva `auction_predictions.csv` e aggiorna `player_kpi_summary`.
"""

import os
from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import numpy as np
import pandas as pd
import env_loader
from supabase import create_client


def get_supabase_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        return None
    try:
        return create_client(url, key)
    except Exception:
        return None


def fetch_votes_by_seasons(client, seasons):
    """Scarica lo storico voti per le stagioni specificate."""
    cache_file = Path(__file__).resolve().parent / "historical_votes_cache.parquet"
    if cache_file.exists():
        try:
            cached = pd.read_parquet(cache_file)
            cached_seasons = set(cached["stagione"].unique()) if "stagione" in cached.columns else set()
            if set(seasons).issubset(cached_seasons):
                print(f"📦 [Cache] Caricati {len(cached)} voti storici dal file locale.")
                return cached
        except Exception:
            pass

    if client is None:
        print("[AVVISO] Supabase non disponibile, impossibile scaricare voti storici.")
        return pd.DataFrame()

    all_rows = []
    print(f"☁️ Download voti per le stagioni {seasons} da Supabase...")
    for s in seasons:
        start = 0
        s_count = 0
        while True:
            res = (
                client.table("player_stats_history")
                .select("nome, ruolo, squadra, stagione, voto, gf, rf, ass, gs, rp, amm, esp")
                .eq("stagione", s)
                .range(start, start + 999)
                .execute()
            )
            data = res.data or []
            all_rows.extend(data)
            s_count += len(data)
            if len(data) < 1000:
                break
            start += 1000
        print(f"   -> Stagione {s}: {s_count} voti scaricati.")

    df_votes = pd.DataFrame(all_rows)
    if not df_votes.empty:
        try:
            df_votes.to_parquet(cache_file, index=False)
            print(f"💾 Salvata cache locale voti: {cache_file}")
        except Exception:
            pass
    return df_votes


def aggregate_season_stats(votes_df):
    """Aggrega le statistiche per giocatore e stagione."""
    if votes_df.empty:
        return pd.DataFrame()

    df = votes_df.copy()
    df["voto"] = pd.to_numeric(df["voto"], errors="coerce")
    valid = df[df["voto"].notna()].copy()

    for col in ["gf", "rf", "ass", "gs", "rp", "amm", "esp"]:
        valid[col] = pd.to_numeric(valid[col], errors="coerce").fillna(0)

    # Calcolo fantavoto redazionale standard
    valid["fv"] = (
        valid["voto"]
        + (valid["gf"] * 3)
        + valid["ass"]
        + (valid["rf"] * 3)
        - (valid["amm"] * 0.5)
        - (valid["esp"] * 1.0)
        - (valid["gs"] * 1.0)
        + (valid["rp"] * 3)
    )

    valid["nome_norm"] = valid["nome"].astype(str).str.upper().str.strip()
    valid["stagione"] = valid["stagione"].astype(str).str.strip()

    agg = valid.groupby(["nome_norm", "stagione"]).agg(
        presenze=("voto", "count"),
        media_voto=("voto", "mean"),
        fantamedia=("fv", "mean"),
        gol=("gf", "sum"),
        rigori_fatti=("rf", "sum"),
        assist=("ass", "sum"),
        ammonizioni=("amm", "sum"),
        espulsioni=("esp", "sum"),
        gol_subiti=("gs", "sum"),
        rigori_parati=("rp", "sum")
    ).reset_index()

    agg["gol_totali"] = agg["gol"] + agg["rigori_fatti"]
    return agg


def build_training_dataset(auctions_df, agg_stats):
    """Unisce gli acquisti storici alle statistiche T-1."""
    if auctions_df.empty or agg_stats.empty:
        return pd.DataFrame()

    auctions = auctions_df[auctions_df["costo"] > 0].copy()
    auctions["nome_norm"] = auctions["calciatore"].astype(str).str.upper().str.strip()
    auctions["prev_season"] = auctions["prev_season"].astype(str).str.strip()

    merged = pd.merge(
        auctions,
        agg_stats,
        left_on=["nome_norm", "prev_season"],
        right_on=["nome_norm", "stagione"],
        how="inner"
    )

    print(f"🔗 [Dataset ML] {len(merged)} acquisti storici abbinati con successo alle statistiche T-1.")
    return merged


def train_regression_model(train_df):
    """Addestra il modello di regressione per stimare costo_1000."""
    if len(train_df) < 30:
        raise ValueError("Dataset di addestramento insufficiente (< 30 campioni).")

    df = train_df.copy()

    # Creazione feature
    # Indicatori di Ruolo
    for r in ["A", "C", "D", "P"]:
        df[f"ruolo_{r}"] = (df["ruolo"].astype(str).str.upper().str.strip() == r).astype(float)

    # Feature continue
    df["fm"] = df["fantamedia"].fillna(6.0)
    df["mv"] = df["media_voto"].fillna(6.0)
    df["pg"] = df["presenze"].fillna(0.0)
    df["gol_rate"] = df["gol_totali"] / np.maximum(1.0, df["pg"])
    df["ass_rate"] = df["assist"] / np.maximum(1.0, df["pg"])

    # Termini di interazione Ruolo * Bonus (fondamentali: un gol per un A pesa molto più che per un D)
    df["fm_A"] = df["fm"] * df["ruolo_A"]
    df["fm_C"] = df["fm"] * df["ruolo_C"]
    df["fm_D"] = df["fm"] * df["ruolo_D"]
    df["gol_A"] = df["gol_totali"] * df["ruolo_A"]
    df["gol_C"] = df["gol_totali"] * df["ruolo_C"]
    df["ass_C"] = df["assist"] * df["ruolo_C"]
    df["ass_D"] = df["assist"] * df["ruolo_D"]

    feature_cols = [
        "ruolo_A", "ruolo_C", "ruolo_D", "ruolo_P",
        "fm", "mv", "pg", "gol_totali", "assist",
        "fm_A", "fm_C", "fm_D", "gol_A", "gol_C", "ass_C", "ass_D"
    ]

    X = df[feature_cols].values
    y = df["costo_normalizzato_1000"].values

    try:
        from sklearn.linear_model import Ridge
        model = Ridge(alpha=10.0, positive=False)
        model.fit(X, y)
        y_pred = model.predict(X)
        weights = model.coef_
        intercept = model.intercept_
    except Exception:
        # Fallback analitico OLS regolarizzato via numpy
        X_b = np.hstack([np.ones((X.shape[0], 1)), X])
        alpha = 10.0
        I = np.eye(X_b.shape[1])
        I[0, 0] = 0.0
        theta = np.linalg.solve(X_b.T @ X_b + alpha * I, X_b.T @ y)
        intercept = theta[0]
        weights = theta[1:]
        y_pred = X_b @ theta
        model = None

    # Calcolo metriche
    residuals = y - y_pred
    rmse = float(np.sqrt(np.mean(residuals ** 2)))
    mae = float(np.mean(np.abs(residuals)))
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = float(1.0 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0

    print("\n" + "=" * 55)
    print("📊 RISULTATI ADDESTRAMENTO MODELLO ML ASTA")
    print("=" * 55)
    print(f"   • Campioni analizzati : {len(df)} acquisti reali")
    print(f"   • R² Score             : {r2:.3f}")
    print(f"   • RMSE (Scarto Medio)  : ±{rmse:.1f} FM (su base 1000)")
    print(f"   • MAE (Errore Medio)   : ±{mae:.1f} FM (su base 1000)")
    print(f"   • Equivalente base 500 : RMSE ±{rmse / 2:.1f} FM | MAE ±{mae / 2:.1f} FM")
    print("=" * 55)

    return {
        "model": model,
        "intercept": float(intercept),
        "weights": weights,
        "feature_cols": feature_cols,
        "rmse_1000": round(rmse, 1),
        "rmse_500": round(rmse / 2.0, 1),
        "r2": round(r2, 3)
    }


def predict_for_all_players(model_dict, summary_df, stats_2025):
    """Applica il modello di stima a tutti i calciatori della rosa 2026-27."""
    print("\n🔮 [Predizione] Calcolo stima prezzo d'asta e range per tutti i giocatori...")

    feature_cols = model_dict["feature_cols"]
    intercept = model_dict["intercept"]
    weights = model_dict["weights"]
    rmse_1000 = model_dict["rmse_1000"]
    rmse_500 = model_dict["rmse_500"]

    results = []
    for _, row in summary_df.iterrows():
        pid = row.get("player_id")
        nome = str(row.get("nome", "Giocatore"))
        ruolo = str(row.get("ruolo", "C")).upper().strip()
        squadra = str(row.get("squadra", "-"))
        fvm = float(row.get("fvm", 10.0)) if pd.notna(row.get("fvm")) else 10.0
        q_att = float(row.get("quotazione_attuale", 10.0)) if pd.notna(row.get("quotazione_attuale")) else 10.0

        # Cerca statistiche del 2025-26 o usa i KPI precalcolati
        nome_norm = nome.upper().strip()
        p_stat = stats_2025[stats_2025["nome_norm"] == nome_norm] if not stats_2025.empty else pd.DataFrame()

        if not p_stat.empty:
            s_row = p_stat.iloc[0]
            fm = float(s_row.get("fantamedia", 6.0))
            mv = float(s_row.get("media_voto", 6.0))
            pg = float(s_row.get("presenze", 0.0))
            gol = float(s_row.get("gol_totali", 0.0))
            ass = float(s_row.get("assist", 0.0))
        else:
            # Fallback sui KPI generali aggregati
            fm = float(row.get("fantamedia", 6.0)) if pd.notna(row.get("fantamedia")) else 6.0
            mv = float(row.get("media_voto", 6.0)) if pd.notna(row.get("media_voto")) else 6.0
            pg = float(row.get("presenze_medie", 15.0)) if pd.notna(row.get("presenze_medie")) else 15.0
            gol = float(row.get("gol_stagione", 0.0)) if pd.notna(row.get("gol_stagione")) else 0.0
            ass = float(row.get("assist_stagione", 0.0)) if pd.notna(row.get("assist_stagione")) else 0.0

        # Costruzione vettore feature
        feat_vals = {
            "ruolo_A": 1.0 if ruolo == "A" else 0.0,
            "ruolo_C": 1.0 if ruolo == "C" else 0.0,
            "ruolo_D": 1.0 if ruolo == "D" else 0.0,
            "ruolo_P": 1.0 if ruolo == "P" else 0.0,
            "fm": fm,
            "mv": mv,
            "pg": pg,
            "gol_totali": gol,
            "assist": ass,
            "fm_A": fm if ruolo == "A" else 0.0,
            "fm_C": fm if ruolo == "C" else 0.0,
            "fm_D": fm if ruolo == "D" else 0.0,
            "gol_A": gol if ruolo == "A" else 0.0,
            "gol_C": gol if ruolo == "C" else 0.0,
            "ass_C": ass if ruolo == "C" else 0.0,
            "ass_D": ass if ruolo == "D" else 0.0,
        }

        x_vec = np.array([feat_vals[c] for c in feature_cols])
        pred_1000 = intercept + float(np.dot(weights, x_vec))

        # Se il giocatore è un rookie senza presenze passate, ancoriamo la stima al listino FVM
        if pg < 3:
            baseline_1000 = fvm * 2.0 if fvm < 200 else fvm
            pred_1000 = (pred_1000 * 0.3) + (baseline_1000 * 0.7)

        # Regole di salvaguardia minima/massima
        pred_1000 = max(1.0, pred_1000)
        pred_500 = max(1.0, round(pred_1000 / 2.0, 1))

        # Range basato sull'RMSE
        range_min_1000 = max(1.0, round(pred_1000 - rmse_1000, 1))
        range_max_1000 = round(pred_1000 + rmse_1000, 1)

        range_min_500 = max(1.0, round(pred_500 - rmse_500, 1))
        range_max_500 = round(pred_500 + rmse_500, 1)

        results.append({
            "player_id": pid,
            "nome": nome,
            "ruolo": ruolo,
            "squadra": squadra,
            "stima_prezzo_1000": round(pred_1000, 1),
            "range_min_1000": range_min_1000,
            "range_max_1000": range_max_1000,
            "stima_prezzo_500": pred_500,
            "range_min_500": range_min_500,
            "range_max_500": range_max_500,
            "rmse_modello_1000": rmse_1000,
            "r2_modello": model_dict["r2"]
        })

    pred_df = pd.DataFrame(results)
    return pred_df


def main():
    repo_dir = Path(__file__).resolve().parent
    auctions_csv = repo_dir / "historical_auctions.csv"

    if not auctions_csv.exists():
        print("Eseguo estrazione storico aste...")
        import load_historical_auctions
        load_historical_auctions.main()

    auctions_df = pd.read_csv(auctions_csv)

    sb = get_supabase_client()
    target_seasons = ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
    votes_df = fetch_votes_by_seasons(sb, target_seasons)

    agg_stats = aggregate_season_stats(votes_df)
    train_df = build_training_dataset(auctions_df, agg_stats)

    model_dict = train_regression_model(train_df)

    # Carica la tabella riassuntiva dei giocatori
    summary_csv = repo_dir / "player_kpi_summary.csv"
    if summary_csv.exists():
        summary_df = pd.read_csv(summary_csv)
    else:
        import compute_kpis
        summary_df = compute_kpis.main()

    stats_2025 = agg_stats[agg_stats["stagione"] == "2025-26"] if not agg_stats.empty else pd.DataFrame()
    predictions_df = predict_for_all_players(model_dict, summary_df, stats_2025)

    # Salva predictions CSV
    pred_csv = repo_dir / "auction_predictions.csv"
    predictions_df.to_csv(pred_csv, index=False, encoding="utf-8")
    print(f"💾 Salvate previsioni in: {pred_csv}")

    # Unisci le colonne ML a player_kpi_summary
    ml_cols = [
        "player_id", "stima_prezzo_1000", "range_min_1000", "range_max_1000",
        "stima_prezzo_500", "range_min_500", "range_max_500", "rmse_modello_1000", "r2_modello"
    ]
    merged_summary = pd.merge(
        summary_df.drop(columns=[c for c in ml_cols if c in summary_df.columns and c != "player_id"]),
        predictions_df[ml_cols],
        on="player_id",
        how="left"
    )
    merged_summary.to_csv(summary_csv, index=False, encoding="utf-8")
    print(f"✅ Aggiornato player_kpi_summary.csv con le colonne predittive ML!")

    # Carica su Supabase se disponibile
    if sb is not None:
        try:
            print("☁️ Upsert delle stime ML su Supabase (player_kpi_summary)...")
            records = merged_summary.replace({np.nan: None}).to_dict(orient="records")
            for i in range(0, len(records), 200):
                sb.table("player_kpi_summary").upsert(records[i:i + 200], on_conflict="player_id").execute()
            print("✅ Aggiornamento Supabase player_kpi_summary completato con successo!")
        except Exception as e:
            print(f"[AVVISO] Upsert su Supabase fallito o colonne non ancora aggiunte: {e}")

    # Mostra i primi 10 per stima
    top10 = predictions_df.sort_values("stima_prezzo_1000", ascending=False).head(10)
    print("\n👑 TOP 10 PREVISIONI PREZZO D'ASTA (Base 1000 FM):")
    for _, r in top10.iterrows():
        print(f"   [{r['ruolo']}] {r['nome']:18s} ({r['squadra']:10s}) : {r['stima_prezzo_1000']:.0f} FM (Range: {r['range_min_1000']:.0f} - {r['range_max_1000']:.0f} FM) | Base 500: {r['stima_prezzo_500']:.0f} FM")


if __name__ == "__main__":
    main()
