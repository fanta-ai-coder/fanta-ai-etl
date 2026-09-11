"""
Modulo di gestione del Calendario di Serie A e Simulatore Monte Carlo 38 Giornate.
Supporta il caricamento da tabella Supabase 'serie_a_calendar' con fallback su algoritmo generatore locale.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np

# Elenco ufficiale 20 squadre Serie A presenti nel database
SERIE_A_TEAMS = [
    "ATALANTA", "BOLOGNA", "CAGLIARI", "COMO", "FIORENTINA",
    "FROSINONE", "GENOA", "INTER", "JUVENTUS", "LAZIO",
    "LECCE", "MILAN", "MONZA", "NAPOLI", "PARMA",
    "ROMA", "SASSUOLO", "TORINO", "UDINESE", "VENEZIA"
]

# Rating Offensivo (pericolosità attacco: penalizza P e D avversari)
TEAM_OFFENSE_STRENGTH: Dict[str, float] = {
    "INTER": 1.40,
    "ATALANTA": 1.35,
    "MILAN": 1.25,
    "NAPOLI": 1.25,
    "JUVENTUS": 1.20,
    "ROMA": 1.15,
    "LAZIO": 1.15,
    "FIORENTINA": 1.10,
    "BOLOGNA": 1.10,
    "TORINO": 0.95,
    "COMO": 0.92,
    "GENOA": 0.90,
    "UDINESE": 0.90,
    "PARMA": 0.88,
    "MONZA": 0.85,
    "CAGLIARI": 0.85,
    "SASSUOLO": 0.85,
    "LECCE": 0.80,
    "VENEZIA": 0.80,
    "FROSINONE": 0.75,
}

# Vulnerabilità Difensiva (quanto è permeabile la difesa: favorisce C e A)
TEAM_DEFENSE_WEAKNESS: Dict[str, float] = {
    "JUVENTUS": 0.75,
    "INTER": 0.78,
    "NAPOLI": 0.82,
    "ATALANTA": 0.88,
    "MILAN": 0.88,
    "ROMA": 0.90,
    "BOLOGNA": 0.90,
    "LAZIO": 0.95,
    "TORINO": 0.95,
    "FIORENTINA": 0.95,
    "GENOA": 1.05,
    "UDINESE": 1.08,
    "MONZA": 1.10,
    "COMO": 1.12,
    "CAGLIARI": 1.15,
    "PARMA": 1.18,
    "LECCE": 1.20,
    "SASSUOLO": 1.22,
    "VENEZIA": 1.25,
    "FROSINONE": 1.30,
}

# SQL DDL per creare la tabella in Supabase se l'utente vuole caricarla nel cloud
SUPABASE_CALENDAR_SQL = """
-- Esegui questo script nel SQL Editor del tuo progetto Supabase
CREATE TABLE IF NOT EXISTS public.serie_a_calendar (
    id BIGSERIAL PRIMARY KEY,
    giornata INT NOT NULL,
    squadra_casa TEXT NOT NULL,
    squadra_trasferta TEXT NOT NULL,
    stagione TEXT DEFAULT '2026-27',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_calendar_giornata ON public.serie_a_calendar(giornata);
CREATE INDEX IF NOT EXISTS idx_calendar_casa ON public.serie_a_calendar(squadra_casa);
CREATE INDEX IF NOT EXISTS idx_calendar_trasferta ON public.serie_a_calendar(squadra_trasferta);
"""


def generate_round_robin_calendar(teams: Optional[List[str]] = None) -> List[Dict]:
    """
    Genera un calendario canonico all'italiana (Round-Robin) a 38 giornate per 20 squadre.
    19 giornate di andata + 19 di ritorno con campi invertiti.
    Restituisce una lista di 380 partite: [{'giornata': 1, 'squadra_casa': 'INTER', 'squadra_trasferta': 'COMO'}, ...]
    """
    teams = list(teams or SERIE_A_TEAMS)
    n = len(teams)
    if n % 2 != 0:
        teams.append("RIPOSO")
        n += 1

    matches = []
    rotating = teams[1:]
    
    # Andata (19 turni)
    for round_idx in range(n - 1):
        round_num = round_idx + 1
        cur_teams = [teams[0]] + rotating
        for i in range(n // 2):
            t1 = cur_teams[i]
            t2 = cur_teams[n - 1 - i]
            if (round_idx + i) % 2 == 0:
                home, away = t1, t2
            else:
                home, away = t2, t1
            matches.append({
                "giornata": round_num,
                "squadra_casa": home,
                "squadra_trasferta": away,
                "stagione": "2026-27"
            })
        rotating = [rotating[-1]] + rotating[:-1]

    # Ritorno (giornate 20-38): stesse sfide a campi invertiti
    andata_matches = list(matches)
    for m in andata_matches:
        matches.append({
            "giornata": m["giornata"] + 19,
            "squadra_casa": m["squadra_trasferta"],
            "squadra_trasferta": m["squadra_casa"],
            "stagione": "2026-27"
        })

    return matches


def get_schedule_by_team(calendar_matches: List[Dict]) -> Dict[str, Dict[int, Dict]]:
    """
    Riorganizza il calendario per ricerca istantanea O(1):
    {
        'INTER': {
            1: {'avversario': 'COMO', 'is_home': True},
            2: {'avversario': 'LAZIO', 'is_home': False},
            ...
        }
    }
    """
    schedule: Dict[str, Dict[int, Dict]] = {t: {} for t in SERIE_A_TEAMS}
    for m in calendar_matches:
        g = int(m["giornata"])
        h = m["squadra_casa"].upper().strip()
        a = m["squadra_trasferta"].upper().strip()
        
        if h in schedule:
            schedule[h][g] = {"avversario": a, "is_home": True}
        else:
            schedule[h] = {g: {"avversario": a, "is_home": True}}
            
        if a in schedule:
            schedule[a][g] = {"avversario": h, "is_home": False}
        else:
            schedule[a] = {g: {"avversario": h, "is_home": False}}
            
    return schedule


def load_or_create_calendar(supabase_client=None) -> Tuple[List[Dict], Dict[str, Dict[int, Dict]]]:
    """
    Carica il calendario da Supabase se disponibile, altrimenti da file locale
    data/serie_a_calendar.json, oppure lo genera istantaneamente.
    """
    matches = []
    
    # 1. Tentativo Supabase
    if supabase_client is not None:
        try:
            res = supabase_client.table("serie_a_calendar").select("*").order("giornata", desc=False).execute()
            if res.data and len(res.data) >= 380:
                matches = res.data
        except Exception:
            pass

    # 2. Tentativo File Locale
    if not matches:
        local_path = Path(__file__).parent / "data" / "serie_a_calendar.json"
        if local_path.exists():
            try:
                with open(local_path, "r", encoding="utf-8") as f:
                    matches = json.load(f)
            except Exception:
                pass

    # 3. Fallback Generatore Algoritmico & Salvataggio locale
    if not matches or len(matches) < 380:
        matches = generate_round_robin_calendar()
        try:
            local_path = Path(__file__).parent / "data" / "serie_a_calendar.json"
            local_path.parent.mkdir(parents=True, exist_ok=True)
            with open(local_path, "w", encoding="utf-8") as f:
                json.dump(matches, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    schedule_by_team = get_schedule_by_team(matches)
    return matches, schedule_by_team


def run_monte_carlo_simulation(
    roster: List[Dict],
    schedule_by_team: Dict[str, Dict[int, Dict]],
    forced_module: str = "Auto",
    n_simulations: int = 1000
) -> Optional[Dict]:
    """
    Simula 1.000 volte il campionato 38 Giornate con vettorizzazione NumPy.
    Per ogni turno seleziona i migliori 11 titolari disponibili e applica
    i moltiplicatori di difficoltà partita (FDR e fattore campo).
    """
    if not roster:
        return None

    modules = {
        "3-4-3": {"P": 1, "D": 3, "C": 4, "A": 3},
        "4-3-3": {"P": 1, "D": 4, "C": 3, "A": 3},
        "3-5-2": {"P": 1, "D": 3, "C": 5, "A": 2},
        "4-4-2": {"P": 1, "D": 4, "C": 4, "A": 2},
        "4-5-1": {"P": 1, "D": 4, "C": 5, "A": 1},
        "5-3-2": {"P": 1, "D": 5, "C": 3, "A": 2},
        "5-4-1": {"P": 1, "D": 5, "C": 4, "A": 1},
    }

    target_modules = [forced_module] if forced_module in modules else list(modules.keys())

    # Pre-calcolo dati base giocatori
    player_pool = []
    for p in roster:
        r = str(p.get("ruolo", "C")).upper().strip()
        if r not in ["P", "D", "C", "A"]:
            r = "C"
        base_fm = float(p.get("fantamedia") or p.get("media_voto") or 6.0)
        sq = str(p.get("squadra", "")).upper().strip()
        player_pool.append({
            "nome": p.get("nome", ""),
            "ruolo": r,
            "squadra": sq,
            "base_fm": base_fm
        })

    daily_matrix = np.zeros((38, n_simulations))
    daily_expected = np.zeros(38)

    # 38 Giornate di simulazione
    for g in range(1, 39):
        # Valutazione di ciascun giocatore per la giornata g
        evaluated_players = []
        for p in player_pool:
            sq = p["squadra"]
            r = p["ruolo"]
            base = p["base_fm"]
            match_info = schedule_by_team.get(sq, {}).get(g, {"avversario": "GENOA", "is_home": True})
            opp = match_info.get("avversario", "GENOA")
            is_home = match_info.get("is_home", True)
            
            # Fattore campo: +0.20 FM in casa, -0.20 FM in trasferta
            home_delta = 0.20 if is_home else -0.20

            if r == "P":
                # Portiere: influenzato dai gol subiti attesi
                off_p = TEAM_OFFENSE_STRENGTH.get(opp, 1.0)
                # off_p da 0.75 a 1.40: delta tra +0.40 e -0.65
                opp_delta = (1.0 - off_p) * 1.5
                mu = max(3.5, base + opp_delta + home_delta)
                sig = 1.20
            elif r == "D":
                # Difensore: influenzato dall'attacco avversario e leggermente dalla difesa avversaria
                off_p = TEAM_OFFENSE_STRENGTH.get(opp, 1.0)
                def_w = TEAM_DEFENSE_WEAKNESS.get(opp, 1.0)
                opp_delta = (1.0 - off_p) * 0.5 + (def_w - 1.0) * 0.3
                mu = max(4.5, base + opp_delta + home_delta * 0.7)
                sig = 1.05
            elif r == "C":
                # Centrocampista: premiato da difese fragili
                def_w = TEAM_DEFENSE_WEAKNESS.get(opp, 1.0)
                opp_delta = (def_w - 1.0) * 1.0
                mu = max(4.5, base + opp_delta + home_delta)
                sig = 1.35
            else:
                # Attaccante: forte impatto della difesa avversaria e alta varianza
                def_w = TEAM_DEFENSE_WEAKNESS.get(opp, 1.0)
                opp_delta = (def_w - 1.0) * 1.8
                mu = max(4.5, base + opp_delta + home_delta * 1.2)
                sig = 2.10

            evaluated_players.append({"ruolo": r, "mu": mu, "sig": sig})

        # Selezione dei migliori 11 per questa giornata
        best_sum_mu = -1e9
        best_starters = []

        for mod_name in target_modules:
            req = modules[mod_name]
            cur_starters = []
            cur_mu = 0.0

            for ro, count in req.items():
                avail = sorted([x for x in evaluated_players if x["ruolo"] == ro], key=lambda x: x["mu"], reverse=True)
                picked = avail[:count]
                cur_starters.extend(picked)
                cur_mu += sum(x["mu"] for x in picked)
                # Slot mancanti compensati con riserva base (voto 5.5, dev. std 0.8)
                missing = count - len(picked)
                for _ in range(missing):
                    cur_starters.append({"ruolo": ro, "mu": 5.5, "sig": 0.8})
                    cur_mu += 5.5

            if cur_mu > best_sum_mu:
                best_sum_mu = cur_mu
                best_starters = cur_starters

        matchday_mu = sum(s["mu"] for s in best_starters)
        matchday_sig = float(np.sqrt(sum(s["sig"]**2 for s in best_starters)))

        daily_expected[g - 1] = matchday_mu
        # Campionamento Monte Carlo vettorizzato per la giornata g
        daily_matrix[g - 1, :] = np.clip(
            np.random.normal(loc=matchday_mu, scale=matchday_sig, size=n_simulations),
            50.0, 115.0
        )

    # Calcolo curve cumulative (38, n_simulations)
    cum_matrix = np.cumsum(daily_matrix, axis=0)

    p10 = np.percentile(cum_matrix, 10, axis=1)
    p50 = np.percentile(cum_matrix, 50, axis=1)
    p90 = np.percentile(cum_matrix, 90, axis=1)

    best_g = int(np.argmax(daily_expected)) + 1
    worst_g = int(np.argmin(daily_expected)) + 1

    # Probabilità di superare quota podio lega (2660 punti = media 70.0 FM a partita)
    podium_threshold = 2660.0
    podium_prob = float(np.mean(cum_matrix[-1, :] >= podium_threshold) * 100.0)

    return {
        "p10": [round(float(v), 1) for v in p10],
        "p50": [round(float(v), 1) for v in p50],
        "p90": [round(float(v), 1) for v in p90],
        "daily_expected": [round(float(v), 1) for v in daily_expected],
        "final_p10": round(float(p10[-1]), 1),
        "final_p50": round(float(p50[-1]), 1),
        "final_p90": round(float(p90[-1]), 1),
        "avg_per_matchday": round(float(p50[-1] / 38.0), 2),
        "podium_prob": round(podium_prob, 1),
        "best_giornata": {"giornata": best_g, "score": round(float(daily_expected[best_g - 1]), 1)},
        "worst_giornata": {"giornata": worst_g, "score": round(float(daily_expected[worst_g - 1]), 1)},
    }
