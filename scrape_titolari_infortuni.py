"""
Scraper per Probabili Formazioni, Titolari, Panchinari, Infortunati e Squalificati da Fantacalcio.it
Genera il file:
  - titolari_infortuni (e titolari_infortuni.csv)
Compatibile con app.py:
  Colonne: nome_giocatore, squadra, titolarita, squalificato, infortunato, desc_infortunio
"""

import sys
from pathlib import Path
import pandas as pd
import requests
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

URL = "https://www.fantacalcio.it/probabili-formazioni-serie-a"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "it-IT,it;q=0.9",
}


def scrape_titolari_infortuni(output_dir: Path | str = ".") -> pd.DataFrame:
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Scaricamento probabili formazioni da {URL}...")
    resp = requests.get(URL, headers=HEADERS, timeout=25)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    matches = soup.find_all("li", class_="match-item")

    if not matches:
        raise ValueError("Nessuna partita trovata. Verifica la struttura HTML della pagina.")

    print(f"[INFO] Partite trovate: {len(matches)}")

    rows = []

    for match in matches:
        col_sm = match.find("div", class_="col-sm")
        if not col_sm:
            continue

        team_cards = col_sm.find_all("div", class_="team-card")
        if len(team_cards) < 2:
            continue

        home_card, away_card = team_cards[0], team_cards[1]
        home_team = home_card.find("h3", class_="team-name").get_text(strip=True)
        away_team = away_card.find("h3", class_="team-name").get_text(strip=True)

        # -------------------------------------------------------------
        # 1. Infortunati per le due squadre
        # -------------------------------------------------------------
        injuries = {home_team: {}, away_team: {}}
        inj_section = match.find("section", class_="injureds")
        if inj_section:
            contents = inj_section.find_all("div", class_="content")
            for idx, team in enumerate([home_team, away_team]):
                if idx < len(contents):
                    for li in contents[idx].find_all("li"):
                        p_name = li.find("a", class_="player-name")
                        desc = li.find("p", class_="description")
                        if p_name:
                            name_str = p_name.get_text(strip=True)
                            desc_str = desc.get_text(strip=True) if desc else ""
                            injuries[team][name_str] = desc_str

        # -------------------------------------------------------------
        # 2. Squalificati per le due squadre
        # -------------------------------------------------------------
        suspensions = {home_team: set(), away_team: set()}
        sus_section = match.find("section", class_="suspendeds")
        if sus_section:
            contents = sus_section.find_all("div", class_="content")
            for idx, team in enumerate([home_team, away_team]):
                if idx < len(contents):
                    for li in contents[idx].find_all("li"):
                        p_name = li.find("a", class_="player-name")
                        if p_name:
                            suspensions[team].add(p_name.get_text(strip=True))

        # -------------------------------------------------------------
        # 3. Titolari e Panchina
        # -------------------------------------------------------------
        for card, team in [(home_card, home_team), (away_card, away_team)]:
            # Titolari (starters)
            starters_ul = card.find("ul", class_="starters")
            if starters_ul:
                for li in starters_ul.find_all("li"):
                    p_tag = li.find("a", class_="player-name")
                    if not p_tag:
                        continue
                    p_name = p_tag.get_text(strip=True)
                    is_inj = "si" if p_name in injuries[team] else "no"
                    desc_inj = injuries[team].get(p_name, "")
                    is_sus = "si" if p_name in suspensions[team] else "no"
                    rows.append({
                        "nome_giocatore": p_name,
                        "squadra": team,
                        "titolarita": "titolare",
                        "squalificato": is_sus,
                        "infortunato": is_inj,
                        "desc_infortunio": desc_inj,
                    })

            # Panchinari (reserves)
            reserves_ul = card.find("ul", class_="reserves")
            if reserves_ul:
                for li in reserves_ul.find_all("li"):
                    p_tag = li.find("a", class_="player-name")
                    if not p_tag:
                        continue
                    p_name = p_tag.get_text(strip=True)
                    is_inj = "si" if p_name in injuries[team] else "no"
                    desc_inj = injuries[team].get(p_name, "")
                    is_sus = "si" if p_name in suspensions[team] else "no"
                    rows.append({
                        "nome_giocatore": p_name,
                        "squadra": team,
                        "titolarita": "panchina",
                        "squalificato": is_sus,
                        "infortunato": is_inj,
                        "desc_infortunio": desc_inj,
                    })

            # Infortunati non compresi nelle liste sopra (es. lungodegenti fuori lista)
            existing_names = {r["nome_giocatore"] for r in rows if r["squadra"] == team}
            for inj_name, desc_inj in injuries[team].items():
                if inj_name not in existing_names:
                    rows.append({
                        "nome_giocatore": inj_name,
                        "squadra": team,
                        "titolarita": "panchina",
                        "squalificato": "no",
                        "infortunato": "si",
                        "desc_infortunio": desc_inj,
                    })

    df = pd.DataFrame(rows)

    # Elimina eventuali duplicati accidentali mantenendo il primo
    df = df.drop_duplicates(subset=["nome_giocatore", "squadra"])

    # Salvataggio nel formato atteso da app.py:
    # 1. 'titolari_infortuni' (senza estensione, esattamente come letto da app.py su GitHub)
    file_raw = out_path / "titolari_infortuni"
    df.to_csv(file_raw, index=False, encoding="utf-8-sig")

    # 2. 'titolari_infortuni.csv' (versione con estensione)
    file_csv = out_path / "titolari_infortuni.csv"
    df.to_csv(file_csv, index=False, encoding="utf-8-sig")

    num_titolari = (df["titolarita"] == "titolare").sum()
    num_panchina = (df["titolarita"] == "panchina").sum()
    num_infortunati = (df["infortunato"] == "si").sum()
    num_squalificati = (df["squalificato"] == "si").sum()

    print(f"[OK] titolari_infortuni salvato ({len(df)} giocatori)")
    print(f"     - Titolari: {num_titolari}")
    print(f"     - Panchinari: {num_panchina}")
    print(f"     - Infortunati: {num_infortunati}")
    print(f"     - Squalificati: {num_squalificati}")

    return df


if __name__ == "__main__":
    scrape_titolari_infortuni()
