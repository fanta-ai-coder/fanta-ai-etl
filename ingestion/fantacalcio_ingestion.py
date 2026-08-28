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

    wait = WebDriverWait(
        driver,
        WAIT_SECONDS,
    )

    # ========================================================
    # APERTURA LOGIN
    # ========================================================

    driver.get(LOGIN_URL)

    wait.until(
        EC.presence_of_element_located(
            (
                By.ID,
                "loginForm",
            )
        )
    )

    time.sleep(2)

    # ========================================================
    # USERNAME
    # ========================================================

    username_input = wait.until(
        EC.presence_of_element_located(
            (
                By.CSS_SELECTOR,
                "#loginForm input[name='username']",
            )
        )
    )

    # Impostiamo il valore direttamente nel DOM.
    # Non usiamo send_keys() perché in GitHub Actions
    # il campo viene trovato ma Chrome lo considera
    # non interagibile.

    driver.execute_script(
        """
        const element = arguments[0];
        const value = arguments[1];

        const setter = Object.getOwnPropertyDescriptor(
            HTMLInputElement.prototype,
            'value'
        ).set;

        setter.call(element, value);

        element.dispatchEvent(
            new Event('input', {
                bubbles: true
            })
        );

        element.dispatchEvent(
            new Event('change', {
                bubbles: true
            })
        );

        element.dispatchEvent(
            new Event('blur', {
                bubbles: true
            })
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
        EC.presence_of_element_located(
            (
                By.CSS_SELECTOR,
                "#loginForm input[name='password']",
            )
        )
    )

    driver.execute_script(
        """
        const element = arguments[0];
        const value = arguments[1];

        const setter = Object.getOwnPropertyDescriptor(
            HTMLInputElement.prototype,
            'value'
        ).set;

        setter.call(element, value);

        element.dispatchEvent(
            new Event('input', {
                bubbles: true
            })
        );

        element.dispatchEvent(
            new Event('change', {
                bubbles: true
            })
        );

        element.dispatchEvent(
            new Event('blur', {
                bubbles: true
            })
        );
        """,
        password_input,
        password,
    )

    print("   ✓ Password inserita")

    # ========================================================
    # VERIFICA VALORI
    # ========================================================

    username_value = driver.execute_script(
        "return arguments[0].value;",
        username_input,
    )

    password_value = driver.execute_script(
        "return arguments[0].value;",
        password_input,
    )

    if not username_value:
        raise RuntimeError(
            "Username non valorizzato nel campo login"
        )

    if not password_value:
        raise RuntimeError(
            "Password non valorizzata nel campo login"
        )

    print("   ✓ Campi login valorizzati")

    # ========================================================
    # LOGIN BUTTON
    # ========================================================

    login_button = wait.until(
        EC.presence_of_element_located(
            (
                By.CSS_SELECTOR,
                "#loginForm button[type='submit']",
            )
        )
    )

    # Click JavaScript.
    # Evitiamo anche qui problemi di interazione
    # del browser headless.

    driver.execute_script(
        """
        arguments[0].click();
        """,
        login_button,
    )

    print("   ✓ Pulsante Login premuto")

    # ========================================================
    # ATTESA LOGIN
    # ========================================================

    time.sleep(5)

    print(
        f"   URL dopo login: "
        f"{driver.current_url}"
    )

    # ========================================================
    # VERIFICA AUTENTICAZIONE
    # ========================================================

    # Il login di Fantacalcio può essere effettuato
    # tramite AJAX e quindi l'URL /login può rimanere
    # invariato.
    #
    # Per questo NON controlliamo l'URL.
    #
    # Andiamo direttamente su una pagina protetta.

    test_url = (
        f"{VOTES_URL}/2026-27/1"
    )

    print()
    print(
        f"   🔎 Verifica autenticazione..."
    )

    driver.get(test_url)

    # Aspettiamo il caricamento del documento
    wait.until(
        lambda d: d.execute_script(
            "return document.readyState"
        ) == "complete"
    )

    time.sleep(3)

    print(
        f"   URL verifica: "
        f"{driver.current_url}"
    )

    # ========================================================
    # CERCA DOWNLOAD EXCEL
    # ========================================================

    try:

        download_control = WebDriverWait(
            driver,
            20,
        ).until(
            EC.presence_of_element_located(
                (
                    By.ID,
                    "download-control",
                )
            )
        )

        href = (
            download_control
            .get_attribute("href")
        )

        if not href:

            raise RuntimeError(
                "Pulsante Excel trovato ma "
                "senza href"
            )

        print(
            "   ✓ Utente autenticato"
        )

        print(
            f"   ✓ Excel disponibile: "
            f"{href}"
        )

        print(
            "✅ Login Fantacalcio effettuato"
        )

        return True

    except TimeoutException:

        # ----------------------------------------------------
        # DEBUG
        # ----------------------------------------------------

        print(
            "   ❌ Pulsante Excel non trovato"
        )

        try:

            screenshot_path = (
                DOWNLOAD_TEMP
                / "login_error.png"
            )

            html_path = (
                DOWNLOAD_TEMP
                / "login_error.html"
            )

            driver.save_screenshot(
                str(screenshot_path)
            )

            with open(
                html_path,
                "w",
                encoding="utf-8",
            ) as file:

                file.write(
                    driver.page_source
                )

            print(
                f"   📸 Screenshot: "
                f"{screenshot_path}"
            )

            print(
                f"   📄 HTML: "
                f"{html_path}"
            )

        except Exception as debug_error:

            print(
                f"   ⚠️ Debug non disponibile: "
                f"{debug_error}"
            )

        raise RuntimeError(
            "Login Fantacalcio non verificato: "
            "il pulsante Excel non è disponibile."
        )




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

    # ========================================================
    # OTTIENI URL EXCEL
    # ========================================================

    excel_url = get_excel_url(
        driver,
        stagione,
        giornata,
    )

    print(
        "⬇️ Download Excel tramite Selenium..."
    )

    # ========================================================
    # DIRECTORY DESTINAZIONE
    # ========================================================

    season_dir = (
        DOWNLOAD_ROOT / stagione
    )

    season_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = (
        season_dir
        / f"giornata_{giornata:02d}.xlsx"
    )

    # Se esiste già lo eliminiamo
    if destination.exists():

        destination.unlink()

    # ========================================================
    # FILE PRESENTI PRIMA DEL DOWNLOAD
    # ========================================================

    before = set(
        DOWNLOAD_TEMP.iterdir()
    )

    # ========================================================
    # TROVA PULSANTE DOWNLOAD
    # ========================================================

    download_control = WebDriverWait(
        driver,
        WAIT_SECONDS,
    ).until(
        EC.presence_of_element_located(
            (
                By.ID,
                "download-control",
            )
        )
    )

    # ========================================================
    # URL
    # ========================================================

    print(
        f"📎 Excel URL: {excel_url}"
    )

    # ========================================================
    # CLICK DOWNLOAD
    # ========================================================

    driver.execute_script(
        """
        arguments[0].click();
        """,
        download_control,
    )

    print(
        "   ✓ Download avviato"
    )

    # ========================================================
    # ATTENDI FILE
    # ========================================================

    downloaded_file = None

    deadline = (
        time.time()
        + WAIT_SECONDS
    )

    while time.time() < deadline:

        time.sleep(1)

        current_files = set(
            DOWNLOAD_TEMP.iterdir()
        )

        new_files = (
            current_files - before
        )

        # -----------------------------------------------
        # Cerca XLSX
        # -----------------------------------------------

        xlsx_files = [
            file
            for file in new_files
            if (
                file.is_file()
                and file.suffix.lower()
                == ".xlsx"
            )
        ]

        if xlsx_files:

            downloaded_file = max(
                xlsx_files,
                key=lambda file: file.stat().st_mtime,
            )

            break

        # -----------------------------------------------
        # Download ancora in corso
        # -----------------------------------------------

        crdownload_files = [
            file
            for file in new_files
            if (
                file.is_file()
                and file.suffix.lower()
                == ".crdownload"
            )
        ]

        if crdownload_files:

            print(
                "   ⏳ Download in corso..."
            )

    # ========================================================
    # CONTROLLO
    # ========================================================

    if downloaded_file is None:

        raise RuntimeError(
            "Download Excel non completato "
            f"entro {WAIT_SECONDS} secondi"
        )

    # ========================================================
    # ATTENDI CHE IL FILE SIA STABILE
    # ========================================================

    previous_size = -1

    stable_count = 0

    deadline = (
        time.time()
        + 20
    )

    while time.time() < deadline:

        current_size = (
            downloaded_file.stat().st_size
        )

        if current_size == previous_size:

            stable_count += 1

        else:

            stable_count = 0

        previous_size = current_size

        if stable_count >= 2:
            break

        time.sleep(1)

    # ========================================================
    # VALIDAZIONE
    # ========================================================

    file_size = (
        downloaded_file.stat().st_size
    )

    print(
        f"   ✓ File scaricato: "
        f"{downloaded_file.name}"
    )

    print(
        f"   ✓ Dimensione: "
        f"{file_size:,} bytes"
    )

    if file_size < 1000:

        raise RuntimeError(
            "File Excel troppo piccolo: "
            f"{file_size} bytes"
        )

    # ========================================================
    # VERIFICA XLSX
    # ========================================================

    with open(
        downloaded_file,
        "rb",
    ) as file:

        signature = file.read(2)

    if signature != b"PK":

        raise RuntimeError(
            "Il file scaricato non sembra "
            "essere un XLSX valido"
        )

    # ========================================================
    # SPOSTA FILE
    # ========================================================

    shutil.move(
        str(downloaded_file),
        str(destination),
    )

    print(
        f"✅ Excel salvato: "
        f"{destination}"
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
