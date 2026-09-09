"""
============================================================
FANTACALCIO DOWNLOADER - Ingestion voti storici
============================================================

Scarica gli Excel dei voti Fantacalcio.it per le stagioni e
giornate indicate, gestendo:

  - login (username/password da env var o input interattivo)
  - popup cookie (CMP)
  - popup pubblicitario dopo il click su "Scarica"
  - log locale di avanzamento (per riprendere da dove interrotto)
  - salvataggio ordinato: data/{stagione}/giornata_XX.xlsx

Uso tipico in locale (test visibile, popup chiuso a mano):

    python fantacalcio_downloader.py --interactive

Uso in CI / GitHub Actions (headless, popup chiuso in automatico):

    FANTACALCIO_USERNAME=... FANTACALCIO_PASSWORD=... \
    python fantacalcio_downloader.py --headless

Variabili d'ambiente:

    FANTACALCIO_USERNAME
    FANTACALCIO_PASSWORD

In GitHub Actions vanno configurate come Secrets del repository
e passate come env allo step che esegue lo script. NON vanno mai
scritte in chiaro nel codice o nel workflow YAML.
============================================================
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import env_loader
from datetime import datetime, timezone
from getpass import getpass
from pathlib import Path
from urllib.parse import urlsplit

from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    TimeoutException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# ============================================================
# CONFIGURAZIONE
# ============================================================

BASE_URL = "https://www.fantacalcio.it"
LOGIN_URL = f"{BASE_URL}/login"

SEASONS = ["2021-22", "2022-23", "2026-27"]
GIORNATE_RANGE = range(1, 39)  # 1..38 incluso

WAIT_SECONDS = 30
POPUP_WAIT_SECONDS = 15
POLL_INTERVAL = 1.0

ROOT_DIR = Path.cwd()
DATA_DIR = ROOT_DIR / "data"
STAGING_DIR = ROOT_DIR / "_staging_downloads"
LOG_FILE = DATA_DIR / "download_log.json"
SCREENSHOT_DIR = ROOT_DIR / "logs" / "screenshots"


# ============================================================
# LOG DI AVANZAMENTO (sostituibile in futuro da Supabase)
# ============================================================

def load_log() -> dict:
    if not LOG_FILE.exists():
        return {}
    try:
        return json.loads(LOG_FILE.read_text(encoding="utf-8"))
    except Exception:
        print("⚠️  Log corrotto o illeggibile, riparto da un log vuoto.")
        return {}


def save_log(log: dict) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOG_FILE.write_text(
        json.dumps(log, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def entry_key(season: str, giornata: int) -> str:
    return f"{season}:{giornata}"


def is_completed(log: dict, season: str, giornata: int) -> bool:
    entry = log.get(entry_key(season, giornata))
    return bool(entry) and entry.get("status") == "completed"


def mark_status(log: dict, season: str, giornata: int, status: str, **extra) -> None:
    log[entry_key(season, giornata)] = {
        "season": season,
        "giornata": giornata,
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **extra,
    }
    save_log(log)


# ============================================================
# CREDENZIALI
# ============================================================

def is_interactive_environment() -> bool:
    """
    True se possiamo ragionevolmente chiedere input all'utente:
    terminale vero, oppure notebook Jupyter/IPython (dove
    sys.stdin.isatty() è quasi sempre False anche se l'utente
    può rispondere a un input()).
    """
    if sys.stdin.isatty():
        return True

    try:
        from IPython import get_ipython
        return get_ipython() is not None
    except Exception:
        return False


def get_credentials(cli_username: str | None, cli_password: str | None):
    username = cli_username or os.environ.get("FANTACALCIO_USERNAME")
    password = cli_password or os.environ.get("FANTACALCIO_PASSWORD")

    if username and password:
        return username, password

    # Non chiediamo input interattivo se non c'è un terminale/notebook
    # attaccato (es. GitHub Actions): meglio fallire con un errore chiaro.
    if not is_interactive_environment():
        raise RuntimeError(
            "Credenziali mancanti. In ambienti non interattivi (CI) "
            "imposta FANTACALCIO_USERNAME e FANTACALCIO_PASSWORD come "
            "variabili d'ambiente / GitHub Secrets."
        )

    print()
    print("=" * 70)
    print("🔐 CREDENZIALI FANTACALCIO")
    print("=" * 70)

    if not username:
        username = input("👤 Username Fantacalcio: ").strip()
    if not password:
        password = getpass("🔑 Password Fantacalcio: ")

    if not username or not password:
        raise RuntimeError("Username o password non inseriti.")

    return username, password


# ============================================================
# CHROME
# ============================================================

def prepare_directories():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    clear_staging_dir()


def clear_staging_dir():
    for file in STAGING_DIR.iterdir():
        try:
            if file.is_file():
                file.unlink()
        except Exception:
            pass


def create_driver(headless: bool) -> webdriver.Chrome:
    prepare_directories()

    options = Options()
    options.page_load_strategy = "eager"

    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
    else:
        options.add_argument("--start-maximized")

    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")

    options.add_experimental_option(
        "prefs",
        {
            "download.default_directory": str(STAGING_DIR.resolve()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "profile.default_content_setting_values.notifications": 2,
        },
    )

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(WAIT_SECONDS)

    # Necessario per garantire il download anche in headless.
    try:
        driver.execute_cdp_cmd(
            "Page.setDownloadBehavior",
            {"behavior": "allow", "downloadPath": str(STAGING_DIR.resolve())},
        )
    except Exception:
        pass

    return driver


def safe_click(driver, element):
    try:
        element.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", element)


def scroll_to(driver, element):
    driver.execute_script(
        "arguments[0].scrollIntoView({block: 'center'});", element
    )
    time.sleep(0.3)


# ============================================================
# COOKIE POPUP
# ============================================================

def handle_cookie_popup(driver):
    time.sleep(2)

    selectors = [
        "#onetrust-accept-btn-handler",
        "button[id*='accept']",
        "button[class*='accept']",
        "button[id*='consent']",
        "button[class*='consent']",
        "//button[contains(translate(., "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), "
        "'accetta')]",
        "//button[contains(translate(., "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), "
        "'accept')]",
    ]

    for selector in selectors:
        try:
            elements = (
                driver.find_elements(By.XPATH, selector)
                if selector.startswith("//")
                else driver.find_elements(By.CSS_SELECTOR, selector)
            )
            for element in elements:
                if element.is_displayed():
                    scroll_to(driver, element)
                    safe_click(driver, element)
                    time.sleep(1)
                    return True
        except Exception:
            continue

    return False


# ============================================================
# LOGIN
# ============================================================

def login(driver, username, password):
    print()
    print("=" * 70)
    print("🔐 LOGIN FANTACALCIO")
    print("=" * 70)

    driver.get(LOGIN_URL)
    wait = WebDriverWait(driver, WAIT_SECONDS)

    wait.until(EC.presence_of_element_located((By.ID, "loginForm")))
    handle_cookie_popup(driver)

    username_input = wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "#loginForm input[name='username']")
        )
    )
    scroll_to(driver, username_input)
    safe_click(driver, username_input)
    username_input.clear()
    username_input.send_keys(username)

    password_input = wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "#loginForm input[name='password']")
        )
    )
    scroll_to(driver, password_input)
    safe_click(driver, password_input)
    password_input.clear()
    password_input.send_keys(password)

    login_button = wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "#loginForm button[type='submit']")
        )
    )
    scroll_to(driver, login_button)
    safe_click(driver, login_button)

    try:
        WebDriverWait(driver, WAIT_SECONDS).until(
            lambda d: "/login" not in d.current_url.lower()
        )
    except TimeoutException:
        pass

    time.sleep(1)
    current_url = driver.current_url.lower()

    if "/login" in current_url:
        page_source = driver.page_source.lower()
        error_words = [
            "password errata",
            "credenziali non valide",
            "username o password",
            "login fallito",
        ]
        if any(word in page_source for word in error_words):
            raise RuntimeError("Login fallito: credenziali non valide.")

        try:
            form = driver.find_element(By.ID, "loginForm")
            if form.is_displayed():
                raise RuntimeError(
                    "Login non riuscito: il form di login è ancora visibile."
                )
        except RuntimeError:
            raise
        except Exception:
            pass

    print("✅ Login completato")


# ============================================================
# CHIUSURA POPUP PUBBLICITARIO
# ============================================================

# Selettori precisi, osservati direttamente nell'HTML dell'annuncio
# "Vignette" di Google Ad Manager:
#
#   <div class="close-button-outer" id="dismiss-button"
#        aria-label="Chiudi annuncio" role="button" tabindex="0">
#     <div class="close-button" id="dismiss-button-element">
#       <div class="continue-prompt-text">Chiudi</div>
#     </div>
#   </div>
#
# Proviamo prima questi (molto più affidabili), e solo come fallback
# la ricerca generica per testo "Chiudi"/"Close" con posizione
# fixed/absolute (utile se in futuro cambia il formato dell'annuncio).
_CLOSE_SELECTORS_CSS = [
    "#dismiss-button",
    "#dismiss-button-element",
    "[aria-label='Chiudi annuncio']",
    "[aria-label='Close ad']",
]

_CLOSE_TEXTS_JS = ["chiudi", "close"]

_FIND_OVERLAY_CLOSE_JS = """
const targets = arguments[0];
const nodes = document.querySelectorAll('body *');
for (const el of nodes) {
    const text = (el.innerText || el.textContent || '').trim().toLowerCase();
    if (!targets.includes(text)) continue;

    const rect = el.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) continue;

    const style = window.getComputedStyle(el);
    if (style.position === 'fixed' || style.position === 'absolute') {
        return el;
    }
}
return null;
"""


def _find_overlay_close_element_here(driver):
    """
    Cerca l'elemento di chiusura SOLO nel contesto (frame) in cui il
    driver è attualmente posizionato: prima i selettori precisi
    conosciuti, poi il fallback testuale generico.
    """
    for selector in _CLOSE_SELECTORS_CSS:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
        except Exception:
            continue
        for element in elements:
            try:
                if element.is_displayed():
                    return element
            except Exception:
                continue

    try:
        return driver.execute_script(_FIND_OVERLAY_CLOSE_JS, _CLOSE_TEXTS_JS)
    except Exception:
        return None


def _search_close_element_all_frames(driver):
    """
    Cerca l'elemento di chiusura nel documento principale e, se non
    trovato, dentro ogni <iframe> di primo livello.

    Necessario perché la maggior parte degli interstitial pubblicitari
    (Google Ads/Vignette) vengono renderizzati dentro un <iframe>: una
    ricerca DOM lanciata dal documento principale non può vedere al
    suo interno (un iframe è un document separato, a prescindere da
    cross-origin). Selenium invece PUÒ raggiungere il contenuto di un
    iframe, anche cross-origin, tramite driver.switch_to.frame().

    Se trovato, il driver resta "switchato" nel frame contenente
    l'elemento: il chiamante deve poi richiamare
    driver.switch_to.default_content() dopo averlo usato.
    """

    driver.switch_to.default_content()

    element = _find_overlay_close_element_here(driver)
    if element is not None:
        return element

    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
    except Exception:
        iframes = []

    for iframe in iframes:
        try:
            driver.switch_to.frame(iframe)
        except Exception:
            driver.switch_to.default_content()
            continue

        element = _find_overlay_close_element_here(driver)
        if element is not None:
            return element  # driver resta switchato in questo frame

        driver.switch_to.default_content()

    return None


def _overlay_close_element_present(driver) -> bool:
    """Versione booleana, sicura da usare dentro una WebDriverWait."""
    element = _search_close_element_all_frames(driver)
    driver.switch_to.default_content()
    return element is not None


def _try_click_close_text(driver) -> bool:
    element = _search_close_element_all_frames(driver)
    if element is None:
        driver.switch_to.default_content()
        return False

    try:
        tag = element.tag_name
        text = element.text
    except Exception:
        tag, text = "?", "?"

    try:
        print(f"🖱️  Chiudo overlay pubblicitario (elemento <{tag}> testo='{text}').")
        scroll_to(driver, element)
        safe_click(driver, element)
        time.sleep(1)
        return True
    except Exception as exc:
        print(f"⚠️  Click sull'elemento di chiusura fallito: {exc}")
        return False
    finally:
        # Fondamentale: senza questo, le ricerche successive (es.
        # #download-control) continuerebbero a cercare dentro
        # l'iframe invece che nella pagina principale.
        driver.switch_to.default_content()


def close_ad_popup_auto(driver, main_handle, first_wait_seconds: int = 2) -> bool:
    """
    Tentativo di chiusura automatica del popup pubblicitario che compare
    dopo il click su #download-control.

    Strategie, in ordine:

      1. Il popup è una nuova finestra/tab -> la chiudiamo e torniamo
         alla finestra principale.
      2. Link/etichetta con testo esatto "Chiudi" / "Close" (l'interstitial
         "Pulse" osservato mostra proprio questo, in alto a destra fuori
         dal box dell'annuncio) -> lo aspettiamo con WebDriverWait, dato
         che il primo caricamento dell'annuncio può essere lento.
      3. Overlay/modal generico -> selettori CSS/XPath comuni.

    Ritorna True se una strategia ha avuto effetto (o se non c'era
    nessun popup da chiudere), False se non siamo riusciti a chiudere
    nulla.
    """

    time.sleep(first_wait_seconds)

    # --- Strategia 1: nuova finestra/tab -------------------------------
    handles = driver.window_handles
    if len(handles) > 1:
        for handle in handles:
            if handle != main_handle:
                try:
                    driver.switch_to.window(handle)
                    driver.close()
                except Exception:
                    pass
        driver.switch_to.window(main_handle)
        return True

    # --- Strategia 2: testo esatto "Chiudi" / "Close" -------------------
    # Aspettiamo che compaia (fino a POPUP_WAIT_SECONDS), perché il primo
    # annuncio della sessione può metterci qualche secondo in più a
    # renderizzarsi rispetto ai successivi.
    try:
        WebDriverWait(driver, POPUP_WAIT_SECONDS).until(_overlay_close_element_present)
    except TimeoutException:
        pass

    if _try_click_close_text(driver):
        return True

    # --- Strategia 3: overlay/modal generico ----------------------------
    close_selectors = [
        "button.close",
        "[class*='popup'] [class*='close']",
        "[class*='modal'] [class*='close']",
        "[class*='overlay'] [class*='close']",
        ".fancybox-close",
        ".fancybox-close-small",
        "button[aria-label='Close']",
        "button[aria-label='Chiudi']",
        "[id*='close']",
        "//button[contains(@class,'close')]",
        "//*[@aria-label='Close']",
        "//*[@aria-label='Chiudi']",
    ]

    for selector in close_selectors:
        try:
            elements = (
                driver.find_elements(By.XPATH, selector)
                if selector.startswith("//")
                else driver.find_elements(By.CSS_SELECTOR, selector)
            )
            for element in elements:
                if element.is_displayed():
                    scroll_to(driver, element)
                    safe_click(driver, element)
                    time.sleep(1)
                    return True
        except Exception:
            continue

    return False


def handle_popup(driver, main_handle, interactive: bool):
    if interactive:
        print()
        print("👉 Chiudi manualmente il popup pubblicitario nel browser.")
        print("👉 NON cliccare 'Scarica' dentro il popup.")
        input("Premi INVIO dopo aver chiuso il popup...")
        return

    closed = False
    for attempt in range(3):
        # Il primo tentativo dopo il click iniziale aspetta di più,
        # perché il primo interstitial della sessione può caricarsi
        # più lentamente dei successivi.
        first_wait = 3 if attempt == 0 else 1
        if close_ad_popup_auto(driver, main_handle, first_wait_seconds=first_wait):
            closed = True
            break
        time.sleep(1)

    if not closed:
        print(
            "⚠️  Nessun popup rilevato/chiuso automaticamente "
            "(potrebbe non essere comparso, o serve un selettore "
            "più specifico)."
        )


# ============================================================
# PAGINA VOTI + DOWNLOAD
# ============================================================

def find_download_control(driver, wait):
    return wait.until(
        EC.presence_of_element_located((By.ID, "download-control"))
    )


def wait_for_new_xlsx(before_files: set, timeout: int) -> Path | None:
    deadline = time.time() + timeout
    downloaded_file = None

    while time.time() < deadline:
        current_files = set(STAGING_DIR.iterdir())
        new_files = [
            f for f in (current_files - before_files)
            if f.suffix.lower() == ".xlsx"
        ]

        if new_files:
            candidate = max(new_files, key=lambda f: f.stat().st_mtime)
            size_1 = candidate.stat().st_size
            time.sleep(1)
            try:
                size_2 = candidate.stat().st_size
            except FileNotFoundError:
                size_2 = -1

            if size_1 == size_2 and size_1 > 0:
                downloaded_file = candidate
                break

        time.sleep(POLL_INTERVAL)

    return downloaded_file


def handle_navigation_popup(driver, interactive: bool, wait_seconds: int = 6):
    """
    Alcuni formati pubblicitari di Google (il "Vignette", riconoscibile
    dal suffisso '#google_vignette' che compare nell'URL) si attivano
    subito dopo la navigazione a una nuova pagina, non dopo il click su
    #download-control. Compaiono a intermittenza (frequency capping di
    Google), quindi vanno controllati ad ogni giornata, anche se magari
    non si erano mai visti prima.
    """

    time.sleep(1)

    def popup_present(d) -> bool:
        if "google_vignette" in d.current_url.lower():
            return True
        return _overlay_close_element_present(d)

    try:
        WebDriverWait(driver, wait_seconds).until(popup_present)
    except TimeoutException:
        return  # nessun interstitial di navigazione, si prosegue normalmente

    print("ℹ️  Rilevato interstitial pubblicitario dopo la navigazione (Vignette).")

    if interactive:
        print("👉 Chiudi manualmente il popup pubblicitario nel browser.")
        input("Premi INVIO dopo aver chiuso il popup...")
        return

    expected_path = urlsplit(driver.current_url).path

    for attempt in range(3):
        if _try_click_close_text(driver):
            print("✓ Interstitial di navigazione chiuso automaticamente.")
            break
        time.sleep(1)
    else:
        print(
            "⚠️  Non sono riuscito a chiudere l'interstitial di navigazione "
            "in automatico: proseguo comunque, la giornata potrebbe fallire."
        )
        return

    # Rete di sicurezza: se il click ha (per errore) portato la pagina
    # altrove invece di limitarsi a chiudere l'overlay, torniamo alla
    # pagina della giornata che stavamo per scaricare.
    time.sleep(1)
    if urlsplit(driver.current_url).path != expected_path:
        print(
            "⚠️  La pagina è cambiata dopo la chiusura del popup, "
            "ricarico la pagina corretta."
        )
        driver.get(f"{BASE_URL}{expected_path}")


def download_giornata(driver, wait, season: str, giornata: int, interactive: bool) -> str:
    """
    Ritorna uno stato tra: 'completed', 'not_available', 'failed'.
    """

    url = f"{BASE_URL}/voti-fantacalcio-serie-a/{season}/{giornata}"
    print(f"\n🌐 {url}")

    driver.get(url)

    # Il popup pubblicitario "Vignette" può comparire subito dopo il
    # caricamento della pagina, prima ancora di cercare il pulsante
    # di download.
    handle_navigation_popup(driver, interactive)

    try:
        download_control = find_download_control(driver, wait)
    except TimeoutException:
        print("ℹ️  #download-control non trovato: giornata non disponibile.")
        return "not_available"

    href = download_control.get_attribute("href") or ""
    if "/api/v1/Excel/votes/" not in href:
        print(f"⚠️  href inatteso: {href}")
        return "failed"

    clear_staging_dir()
    before_files = set(STAGING_DIR.iterdir())

    main_handle = driver.current_window_handle

    scroll_to(driver, download_control)
    safe_click(driver, download_control)
    print("✓ Click su #download-control eseguito")

    handle_popup(driver, main_handle, interactive)

    downloaded_file = wait_for_new_xlsx(before_files, WAIT_SECONDS)

    if not downloaded_file:
        screenshot = SCREENSHOT_DIR / f"{season}_giornata_{giornata:02d}_error.png"
        try:
            driver.save_screenshot(str(screenshot))
            print(f"📸 Screenshot salvato: {screenshot}")
        except Exception:
            pass
        return "failed"

    season_dir = DATA_DIR / season
    season_dir.mkdir(parents=True, exist_ok=True)
    final_path = season_dir / f"giornata_{giornata:02d}.xlsx"
    downloaded_file.replace(final_path)

    size_kb = final_path.stat().st_size / 1024
    print(f"✅ Salvato: {final_path} ({size_kb:.1f} KB)")

    return "completed"


def discover_comp_id(driver, wait, season: str, interactive: bool) -> str | None:
    """
    Visita UNA SOLA VOLTA la pagina voti (giornata 1) di una stagione
    per leggere l'ID numerico interno usato nell'endpoint Excel
    (es. .../api/v1/Excel/votes/{comp_id}/{giornata}). Da qui in poi
    si può scaricare ogni giornata chiamando direttamente l'endpoint,
    senza ricaricare la pagina voti per ognuna: molto più veloce, e
    l'interstitial pubblicitario (iniettato dallo script della pagina
    HTML) non compare mai su una risposta diretta di un endpoint
    binario, quindi non serve nemmeno gestirlo in questa modalità.
    """

    url = f"{BASE_URL}/voti-fantacalcio-serie-a/{season}/1"
    print(f"\n🌐 {url} (solo per scoprire l'ID stagione)")

    driver.get(url)
    handle_navigation_popup(driver, interactive)

    try:
        download_control = find_download_control(driver, wait)
    except TimeoutException:
        return None

    href = download_control.get_attribute("href") or ""
    match = re.search(r"/api/v1/Excel/votes/(\d+)/", href)
    if not match:
        return None

    return match.group(1)


def download_giornata_via_api(driver, season: str, comp_id: str, giornata: int) -> str:
    """
    Scarica direttamente dall'endpoint Excel (senza passare dalla
    pagina voti). Ritorna uno stato tra: 'completed', 'not_available',
    'failed'. Se la giornata non è ancora disponibile, l'endpoint non
    restituisce un file scaricabile: semplicemente non compare nulla
    nella cartella di staging entro il timeout.
    """

    excel_url = f"{BASE_URL}/api/v1/Excel/votes/{comp_id}/{giornata}"
    print(f"\n🌐 {excel_url}")

    clear_staging_dir()
    before_files = set(STAGING_DIR.iterdir())

    driver.get(excel_url)

    downloaded_file = wait_for_new_xlsx(before_files, WAIT_SECONDS)

    if not downloaded_file:
        print("ℹ️  Nessun file scaricato (probabile giornata non disponibile).")
        return "not_available"

    # Validazione minima: dimensione ragionevole + firma ZIP "PK"
    # (un vero .xlsx è un archivio ZIP), per evitare di salvare come
    # "completato" un file corrotto o una pagina di errore rinominata.
    file_size = downloaded_file.stat().st_size
    if file_size < 1000:
        print(f"⚠️  File troppo piccolo ({file_size} bytes), probabile errore.")
        return "failed"

    with open(downloaded_file, "rb") as f:
        signature = f.read(2)
    if signature != b"PK":
        print("⚠️  Il file scaricato non sembra un XLSX valido (firma non PK).")
        return "failed"

    season_dir = DATA_DIR / season
    season_dir.mkdir(parents=True, exist_ok=True)
    final_path = season_dir / f"giornata_{giornata:02d}.xlsx"
    downloaded_file.replace(final_path)

    size_kb = final_path.stat().st_size / 1024
    print(f"✅ Salvato: {final_path} ({size_kb:.1f} KB)")

    return "completed"


# ============================================================
# MAIN
# ============================================================

def parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Download batch dei voti Fantacalcio.it"
    )
    parser.add_argument("--username", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument(
        "--headless", action="store_true",
        help="Esegue Chrome in modalità headless (consigliato in CI).",
    )
    parser.add_argument(
        "--interactive", action="store_true",
        help="Chiude i popup manualmente, con pause su input(). "
             "Usalo per il primo test locale.",
    )
    parser.add_argument(
        "--seasons", nargs="+", default=SEASONS,
        help=f"Stagioni da scaricare (default: {SEASONS}).",
    )
    parser.add_argument(
        "--via-api", action="store_true",
        help="Scarica ogni giornata chiamando direttamente l'endpoint "
             "Excel (scoprendo l'ID stagione una sola volta), invece "
             "di ricaricare la pagina voti per ognuna. Più veloce ed "
             "evita l'interstitial pubblicitario, che compare solo "
             "sulla pagina HTML.",
    )
    parser.add_argument(
        "--from-giornata", type=int, default=1,
    )
    parser.add_argument(
        "--to-giornata", type=int, default=38,
    )

    # parse_known_args ignora eventuali argomenti extra che Jupyter
    # inietta in sys.argv (es. "-f /path/kernel.json"), che altrimenti
    # farebbero fallire argparse con "unrecognized arguments".
    args, _unknown = parser.parse_known_args(argv)
    return args


def main(argv: list[str] | None = None):
    """
    argv=None -> legge da sys.argv (uso da riga di comando).
    In Jupyter puoi anche chiamare direttamente, ad es.:

        main([
            "--interactive",
            "--seasons", "2023-24",
            "--from-giornata", "1",
            "--to-giornata", "1",
        ])
    """
    args = parse_args(argv)

    username, password = get_credentials(args.username, args.password)
    log = load_log()

    driver = None

    try:
        print()
        print("🌐 Avvio Chrome...")
        driver = create_driver(headless=args.headless)
        wait = WebDriverWait(driver, WAIT_SECONDS)

        login(driver, username, password)

        for season in args.seasons:
            print()
            print("=" * 70)
            print(f"📅 STAGIONE {season}")
            print("=" * 70)

            comp_id = None
            if args.via_api:
                comp_id = discover_comp_id(driver, wait, season, args.interactive)
                if comp_id is None:
                    print(
                        f"⚠️  Impossibile determinare l'ID della stagione "
                        f"{season}: salto l'intera stagione."
                    )
                    continue
                print(f"🔑 ID stagione {season}: {comp_id}")

            for giornata in range(args.from_giornata, args.to_giornata + 1):

                if is_completed(log, season, giornata):
                    print(f"⏭️  {season} giornata {giornata}: già completata, salto.")
                    continue

                try:
                    if args.via_api:
                        status = download_giornata_via_api(
                            driver, season, comp_id, giornata
                        )
                    else:
                        status = download_giornata(
                            driver, wait, season, giornata, args.interactive
                        )
                except Exception as exc:
                    print(f"❌ Errore su {season} giornata {giornata}: {exc}")
                    status = "failed"

                mark_status(log, season, giornata, status)

                if status == "not_available":
                    print(
                        f"⏹️  Stagione {season}: mi fermo qui "
                        f"(giornata {giornata} non ancora pubblicata)."
                    )
                    break

                # Piccola pausa tra una giornata e l'altra per non
                # sovraccaricare il sito.
                time.sleep(2)

        print()
        print("=" * 70)
        print("🎉 CICLO COMPLETATO")
        print("=" * 70)

        completed = sum(
            1 for v in log.values() if v.get("status") == "completed"
        )
        failed = sum(1 for v in log.values() if v.get("status") == "failed")
        print(f"✅ Completate: {completed}   ❌ Fallite: {failed}")
        print(f"📄 Log: {LOG_FILE}")

    finally:
        if driver:
            print()
            print("🌐 Chiusura Chrome...")
            driver.quit()


if __name__ == "__main__":
    main()
