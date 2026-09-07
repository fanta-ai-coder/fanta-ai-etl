"""
Scraper per Rigoristi e Calci di Punizione da Fantacalcio.it
Genera i file:
  - rigoristi.csv
  - punizioni.csv
Compatibili con app.py (colonne: giocatore, squadra, posizione come int 1, 2, 3)
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

URL = "https://www.fantacalcio.it/rigoristi-serie-a"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "it-IT,it;q=0.9",
}


def scrape_rigoristi_e_punizioni(output_dir: Path | str = ".") -> tuple[pd.DataFrame, pd.DataFrame]:
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Scaricamento da {URL}...")
    resp = requests.get(URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    team_cards = soup.find_all("div", class_="team-card")

    if not team_cards:
        raise ValueError("Nessuna squadra trovata nella pagina. Verifica la struttura HTML.")

    rigoristi = []
    punizioni = []

    for card in team_cards:
        team_name_tag = card.find("span", class_="team-name")
        if not team_name_tag:
            continue
        team_name = team_name_tag.get_text(strip=True)

        for col in card.find_all("div", class_="col"):
            header = col.find("header")
            if not header:
                continue
            header_text = header.get_text(strip=True).lower()

            ol = col.find("ol")
            if not ol:
                continue

            for rank, li in enumerate(ol.find_all("li"), start=1):
                player_tag = li.find("a", class_="player-name")
                if not player_tag:
                    continue
                player_name = player_tag.get_text(strip=True)

                entry = {
                    "giocatore": player_name,
                    "squadra": team_name,
                    "posizione": rank,
                }

                if "rigor" in header_text:
                    rigoristi.append(entry)
                elif "piazzat" in header_text or "punizion" in header_text:
                    punizioni.append(entry)

    df_rigori = pd.DataFrame(rigoristi)
    df_punizioni = pd.DataFrame(punizioni)

    # Salvataggio CSV compatibili al 100% con app.py
    file_rigori = out_path / "rigoristi.csv"
    file_punizioni = out_path / "punizioni.csv"

    df_rigori.to_csv(file_rigori, index=False, encoding="utf-8-sig")
    df_punizioni.to_csv(file_punizioni, index=False, encoding="utf-8-sig")

    print(f"[OK] rigoristi.csv salvato ({len(df_rigori)} record)")
    print(f"[OK] punizioni.csv salvato ({len(df_punizioni)} record)")

    return df_rigori, df_punizioni


if __name__ == "__main__":
    scrape_rigoristi_e_punizioni()
