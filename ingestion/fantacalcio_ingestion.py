```python
import os
import shutil
import time
from pathlib import Path

import requests

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from fantacalcio_parser import parse_excel
from supabase_client import SupabaseClient


# ============================================================
# CONFIGURAZIONE
# ============================================================

SEASONS = [
    "2023-24",
    "2024-25",
    "2025-26",
    "2026-27",
]

BASE_URL = "https://www.fantacalcio.it"

LOGIN_URL = f"{BASE_URL}/login"

VOTES_URL = (
    f"{BASE_URL}/voti-fantacalcio-serie-a"
)

DOWNLOAD_ROOT = (
    Path(__file__).resolve().parent.parent / "data"
)

DOWNLOAD_TEMP = (
    Path(__file__).resolve().parent / "tmp_download"
)

WAIT_SECONDS = 40


# ============================================================
# SELENIUM
# ============================================================

def create_driver():

    DOWNLOAD_TEMP.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Pulizia directory temporanea
    # --------------------------------------------------------

    for file in DOWNLOAD_TEMP.iterdir():

        try:

            if file.is_file():
                file.unlink()

            elif file.is_dir():
                shutil.rmtree(file)

        except Exception:
            pass

    # --------------------------------------------------------
    # Chrome
    # --------------------------------------------------------

    options = Options()

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    # --------------------------------------------------------
    # Download
    # --------------------------------------------------------

    options.add_experimental_option(
        "prefs",
        {
            "download.default_directory": str(
                DOWNLOAD_TEMP.resolve()
            ),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        },
    )

    driver = webdriver.Chrome(
        options=options
    )

    return driver


# ============================================================
# LOGIN
# ============================================================

def login(driver):

    username = os.environ.get(
        "FANTACALCIO_USERNAME"
    )

    password = os.environ.get(
        "FANTACALCIO_PASSWORD"
    )

    if not username:
        raise RuntimeError(
            "FANTACALCIO_USERNAME non configurato"
        )

    if not password:
        raise RuntimeError(
            "FANTACALCIO_PASSWORD non configurato"
        )

    print()
    print("=" * 60)
    print("🔐 LOGIN FANTACALCIO")
    print("=" * 60)

    # --------------------------------------------------------
    # Apertura pagina login
    # --------------------------------------------------------

    driver.get(LOGIN_URL)

    wait = WebDriverWait(
        driver,
        WAIT_SECONDS,
    )

    # Aspetta il form
    wait.until(
        EC.presence_of_element_located(
            (
                By.ID,
                "loginForm",
            )
        )
    )

    # ========================================================
    # USERNAME
    # ========================================================

    username_input = wait.until(
        EC.visibility_of_element_located(
            (
                By.CSS_SELECTOR,
                "#loginForm input[name='username']",
            )
        )
    )

    # Scroll
    driver.execute_script(
        """
        arguments[0].scrollIntoView({
            block: 'center',
            inline: 'center'
        });
        """,
        username_input,
    )

    # Aspetta che sia interagibile
    wait.until(
        lambda d: (
            username_input.is_displayed()
            and username_input.is_enabled()
        )
    )

    # Click via JavaScript
    driver.execute_script(
        "arguments[0].click();",
        username_input,
    )

    # Impostazione valore tramite JavaScript
    driver.execute_script(
        """
        arguments[0].value = arguments[1];

        arguments[0].dispatchEvent(
            new Event('input', { bubbles: true })
        );

        arguments[0].dispatchEvent(
            new Event('change', { bubbles: true })
        );
        """,
        username_input,
        username,
    )

    print("   ✓ Username inserito")

    # ========================================================
    # PASSWORD
    # ========================================================

    password_input = wait.until(
        EC.visibility_of_element_located(
            (
                By.CSS_SELECTOR,
                "#loginForm input[name='password']",
            )
        )
    )

    driver.execute_script(
        """
        arguments[0].scrollIntoView({
            block: 'center',
            inline: 'center'
        });
        """,
        password_input,
    )

    wait.until(
        lambda d: (
            password_input.is_displayed()
            and password_input.is_enabled()
        )
    )

    driver.execute_script(
        "arguments[0].click();",
        password_input,
    )

    driver.execute_script(
        """
        arguments[0].value = arguments[1];

        arguments[0].dispatchEvent(
            new Event('input', { bubbles: true })
        );

        arguments[0].dispatchEvent(
            new Event('change', { bubbles: true })
        );
        """,
        password_input,
        password,
    )

    print("   ✓ Password inserita")

    # ========================================================
    # LOGIN BUTTON
    # ========================================================

    login_button = wait.until(
        EC.element_to_be_clickable(
            (
                By.CSS_SELECTOR,
                "#loginForm button[type='submit']",
            )
        )
    )

    driver.execute_script(
        """
        arguments[0].scrollIntoView({
            block: 'center',
            inline: 'center'
        });
        """,
        login_button,
    )

    driver.execute_script(
        "arguments[0].click();",
        login_button,
    )

    print("   ✓ Pulsante Login premuto")

    # --------------------------------------------------------
    # Attesa risposta
    # --------------------------------------------------------

    time.sleep(3)

    current_url = driver.current_url

    print(
        f"   URL dopo login: {current_url}"
    )

    # ========================================================
    # VERIFICA LOGIN
    # ========================================================

    # Se il form è ancora presente e visibile,
    # il login probabilmente non è andato a buon fine.

    try:

        login_form = driver.find_element(
            By.ID,
            "loginForm",
        )

        if login_form.is_displayed():

            page_source = (
                driver.page_source.lower()
            )

            if (
                "password errata" in page_source
                or "credenziali non valide" in page_source
                or "username o password" in page_source
            ):

                raise RuntimeError(
                    "Login Fantacalcio fallito: "
                    "username o password non validi"
                )

            raise RuntimeError(
                "Login Fantacalcio fallito: "
                "il form di login è ancora presente"
            )

    except RuntimeError:
        raise

    except Exception:
        # Form non trovato = comportamento atteso
        pass

    print("✅ Login effettuato")


# ============================================================
# OTTIENI URL EXCEL
# ============================================================

def get_excel_url(
    driver,
    stagione,
    giornata,
):

    url = (
        f"{VOTES_URL}/"
        f"{stagione}/"
        f"{giornata}"
    )

    print()
    print("=" * 60)
    print(
        f"📥 {stagione} - Giornata {giornata}"
    )
    print("=" * 60)

    print(
        f"🌐 {url}"
    )

    driver.get(url)

    wait = WebDriverWait(
        driver,
        WAIT_SECONDS,
    )

    # --------------------------------------------------------
    # Pulsante download
    # --------------------------------------------------------

    download_control = wait.until(
        EC.presence_of_element_located(
            (
                By.ID,
                "download-control",
            )
        )
    )

    excel_url = (
        download_control
        .get_attribute("href")
    )

    if not excel_url:

        raise RuntimeError(
            "Il pulsante download-control "
            "non contiene href"
        )

    # URL relativo
    if excel_url.startswith("/"):

        excel_url = (
            BASE_URL + excel_url
        )

    print(
        f"📎 Excel URL: {excel_url}"
    )

    return excel_url


# ============================================================
# DOWNLOAD EXCEL CON SESSIONE SELENIUM
# ============================================================

def download_excel(
    driver,
    stagione,
    giornata,
):

    excel_url = get_excel_url(
        driver,
        stagione,
        giornata,
    )

    print(
        "⬇️ Download Excel..."
    )

    # --------------------------------------------------------
    # Cookie Selenium
    # --------------------------------------------------------

    selenium_cookies = (
        driver.get_cookies()
    )

    # --------------------------------------------------------
    # Requests session
    # --------------------------------------------------------

    session = requests.Session()

    for cookie in selenium_cookies:

        session.cookies.set(
            cookie["name"],
            cookie["value"],
            domain=".fantacalcio.it",
        )

    # --------------------------------------------------------
    # Headers
    # --------------------------------------------------------

    user_agent = driver.execute_script(
        "return navigator.userAgent;"
    )

    headers = {
        "User-Agent": user_agent,
        "Referer": driver.current_url,
        "Accept": (
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet,"
            "application/vnd.ms-excel,"
            "*/*"
        ),
    }

    # --------------------------------------------------------
    # Request
    # --------------------------------------------------------

    response = session.get(
        excel_url,
        headers=headers,
        timeout=60,
    )

    print(
        f"HTTP Excel: "
        f"{response.status_code}"
    )

    if response.status_code != 200:

        raise RuntimeError(
            "Download Excel fallito: "
            f"HTTP {response.status_code}"
        )

    content_type = (
        response.headers
        .get("Content-Type", "")
        .lower()
    )

    # --------------------------------------------------------
    # Controllo risposta
    # --------------------------------------------------------

    if len(response.content) < 1000:

        raise RuntimeError(
            "Risposta Excel troppo piccola: "
            f"{len(response.content)} bytes"
        )

    # Controllo XLSX
    if not response.content.startswith(
        b"PK"
    ):

        raise RuntimeError(
            "La risposta non sembra essere "
            "un file XLSX valido"
        )

    # --------------------------------------------------------
    # Directory stagione
    # --------------------------------------------------------

    season_dir = (
        DOWNLOAD_ROOT / stagione
    )

    season_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Nome file
    # --------------------------------------------------------

    destination = (
        season_dir
        / f"giornata_{giornata:02d}.xlsx"
    )

    # --------------------------------------------------------
    # Salvataggio
    # --------------------------------------------------------

    with open(
        destination,
        "wb",
    ) as file:

        file.write(
            response.content
        )

    print(
        f"✅ Excel salvato: "
        f"{destination}"
    )

    print(
        f"   Dimensione: "
        f"{len(response.content):,} bytes"
    )

    print(
        f"   Content-Type: "
        f"{content_type}"
    )

    return destination


# ============================================================
# PROCESS GIORNATA
# ============================================================

def process_day(
    driver,
    supabase,
    stagione,
    giornata,
):

    try:

        # ----------------------------------------------------
        # DOWNLOAD
        # ----------------------------------------------------

        excel_path = download_excel(
            driver,
            stagione,
            giornata,
        )

        # ----------------------------------------------------
        # PARSE
        # ----------------------------------------------------

        records = parse_excel(
            excel_path,
            stagione,
            giornata,
        )

        # ----------------------------------------------------
        # SUPABASE
        # ----------------------------------------------------

        inserted = (
            supabase.insert_stats(
                records
            )
        )

        # ----------------------------------------------------
        # LOG
        # ----------------------------------------------------

        supabase.save_log(
            stagione=stagione,
            giornata=giornata,
            status="COMPLETED",
            records_inserted=inserted,
        )

        print()
        print(
            f"✅ COMPLETED "
            f"{stagione} G{giornata}"
        )

        print(
            f"   Record: {inserted}"
        )

        return True

    except Exception as exc:

        print()
        print(
            f"❌ FAILED "
            f"{stagione} G{giornata}"
        )

        print(
            f"   Errore: {exc}"
        )

        # ----------------------------------------------------
        # Salva il fallimento nel log
        # ----------------------------------------------------

        try:

            supabase.save_log(
                stagione=stagione,
                giornata=giornata,
                status="FAILED",
                records_inserted=0,
                error_message=str(exc),
            )

        except Exception as log_error:

            print(
                "⚠️ Impossibile salvare "
                f"il log: {log_error}"
            )

        return False


# ============================================================
# MAIN
# ============================================================

def main():

    mode = os.environ.get(
        "INGESTION_MODE",
        "next",
    ).lower()

    if mode not in {
        "next",
        "all",
    }:

        raise ValueError(
            "INGESTION_MODE deve essere "
            "'next' oppure 'all'"
        )

    print()
    print("=" * 60)
    print(
        "⚽ FANTACALCIO HISTORICAL INGESTION"
    )
    print("=" * 60)

    print(
        f"Modalità: {mode}"
    )

    print("=" * 60)

    supabase = SupabaseClient()

    driver = create_driver()

    try:

        # ====================================================
        # LOGIN
        # ====================================================

        login(driver)

        # ====================================================
        # MODALITÀ NEXT
        # ====================================================

        if mode == "next":

            stagione, giornata = (
                supabase.get_next_missing(
                    SEASONS
                )
            )

            if not stagione:

                print(
                    "🎉 Tutte le giornate "
                    "sono già state scaricate."
                )

                return

            print()
            print(
                f"🎯 Prossima giornata: "
                f"{stagione} G{giornata}"
            )

            success = process_day(
                driver,
                supabase,
                stagione,
                giornata,
            )

            if not success:

                raise RuntimeError(
                    "Ingestion fallita"
                )

        # ====================================================
        # MODALITÀ ALL
        # ====================================================

        else:

            for stagione in SEASONS:

                for giornata in range(
                    1,
                    39,
                ):

                    if supabase.is_completed(
                        stagione,
                        giornata,
                    ):

                        print(
                            f"⏭️ SKIP "
                            f"{stagione} "
                            f"G{giornata}"
                        )

                        continue

                    process_day(
                        driver,
                        supabase,
                        stagione,
                        giornata,
                    )

    finally:

        print()
        print(
            "🌐 Chiusura browser..."
        )

        driver.quit()

        print(
            "🏁 Ingestion terminata."
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
```
