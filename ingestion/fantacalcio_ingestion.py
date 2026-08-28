import os
import shutil
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
)
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

BASE_URL = (
    "https://www.fantacalcio.it/"
    "voti-fantacalcio-serie-a"
)

LOGIN_URL = "https://www.fantacalcio.it/login"

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

    # Pulizia download precedenti
    for file in DOWNLOAD_TEMP.iterdir():

        try:

            if file.is_file():
                file.unlink()

            elif file.is_dir():
                shutil.rmtree(file)

        except Exception:
            pass

    options = Options()

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

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
            "FANTACALCIO_PASSWORD non configurata"
        )

    print()
    print("=" * 60)
    print("🔐 LOGIN FANTACALCIO")
    print("=" * 60)

    driver.get(LOGIN_URL)

    wait = WebDriverWait(
        driver,
        WAIT_SECONDS,
    )

    # Username
    username_input = wait.until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                "//input[contains("
                "@placeholder, 'Username'"
                ")]"
            )
        )
    )

    username_input.clear()
    username_input.send_keys(username)

    # Password
    password_input = wait.until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                "//input[@type='password' "
                "or contains("
                "@placeholder, 'Password'"
                ")]"
            )
        )
    )

    password_input.clear()
    password_input.send_keys(password)

    # Login
    login_button = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//button["
                "contains("
                "translate(normalize-space(.), "
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
                "'abcdefghijklmnopqrstuvwxyz'"
                "),"
                "'login'"
                ")]"
                " | "
                "//input["
                "@type='submit' and "
                "contains("
                "translate(@value, "
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
                "'abcdefghijklmnopqrstuvwxyz'"
                "),"
                "'login'"
                ")]"
            )
        )
    )

    login_button.click()

    time.sleep(3)

    # Controlliamo che non siamo ancora sulla pagina login
    current_url = driver.current_url

    if "/login" in current_url.lower():

        # Controllo eventuale messaggio di errore
        page_text = driver.page_source.lower()

        if (
            "password errata" in page_text
            or "credenziali" in page_text
            or "username o password" in page_text
        ):
            raise RuntimeError(
                "Login Fantacalcio fallito: "
                "credenziali non valide"
            )

        raise RuntimeError(
            "Login Fantacalcio non riuscito"
        )

    print("✅ Login effettuato")


# ============================================================
# DOWNLOAD EXCEL
# ============================================================

def wait_for_download(timeout=WAIT_SECONDS):

    start = time.time()

    while time.time() - start < timeout:

        files = list(
            DOWNLOAD_TEMP.glob("*")
        )

        # Ignora file temporanei Chrome
        excel_files = [
            f
            for f in files
            if f.is_file()
            and f.suffix.lower() in {
                ".xlsx",
                ".xls",
            }
        ]

        if excel_files:

            # Prendiamo il più recente
            return max(
                excel_files,
                key=lambda x: x.stat().st_mtime,
            )

        time.sleep(1)

    raise TimeoutException(
        "Timeout: Excel non scaricato"
    )


def download_excel(
    driver,
    stagione,
    giornata,
):

    url = (
        f"{BASE_URL}/"
        f"{stagione}/"
        f"{giornata}"
    )

    print()
    print("=" * 60)
    print(
        f"📥 {stagione} - Giornata {giornata}"
    )
    print("=" * 60)

    print(f"🌐 {url}")

    driver.get(url)

    wait = WebDriverWait(
        driver,
        WAIT_SECONDS,
    )

    # Aspettiamo che la pagina sia caricata
    wait.until(
        EC.presence_of_element_located(
            (By.TAG_NAME, "body")
        )
    )

    # --------------------------------------------------------
    # CERCA IL PULSANTE SCARICA
    # --------------------------------------------------------

    selectors = [
        (
            By.XPATH,
            "//*[self::button or self::a]"
            "[contains("
            "translate(normalize-space(.), "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
            "'abcdefghijklmnopqrstuvwxyz'"
            "),"
            "'scarica'"
            ")]",
        ),
        (
            By.XPATH,
            "//*[contains("
            "translate(normalize-space(.), "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
            "'abcdefghijklmnopqrstuvwxyz'"
            "),"
            "'scarica'"
            ")]",
        ),
    ]

    download_button = None

    for by, selector in selectors:

        try:

            download_button = wait.until(
                EC.element_to_be_clickable(
                    (by, selector)
                )
            )

            if download_button:
                break

        except TimeoutException:
            continue

    if download_button is None:
        raise RuntimeError(
            "Pulsante 'Scarica' non trovato"
        )

    print("⬇️ Pulsante Scarica trovato")

    # Pulizia eventuali file precedenti
    for file in DOWNLOAD_TEMP.glob("*"):

        try:

            if file.is_file():
                file.unlink()

        except Exception:
            pass

    download_button.click()

    print("⏳ Attendo download Excel...")

    excel_file = wait_for_download()

    print(
        f"✅ Excel scaricato: "
        f"{excel_file.name}"
    )

    # --------------------------------------------------------
    # DESTINAZIONE GITHUB
    # --------------------------------------------------------

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

    shutil.copy2(
        excel_file,
        destination,
    )

    print(
        f"📁 Salvato: {destination}"
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

        inserted = supabase.insert_stats(
            records
        )

        # ----------------------------------------------------
        # LOG COMPLETED
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

        supabase.save_log(
            stagione=stagione,
            giornata=giornata,
            status="FAILED",
            records_inserted=0,
            error_message=str(exc),
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

    if mode not in {"next", "all"}:
        raise ValueError(
            "INGESTION_MODE deve essere "
            "'next' oppure 'all'"
        )

    print()
    print("=" * 60)
    print("⚽ FANTACALCIO HISTORICAL INGESTION")
    print("=" * 60)
    print(f"Modalità: {mode}")
    print("=" * 60)

    supabase = SupabaseClient()

    # --------------------------------------------------------
    # CREA SELENIUM
    # --------------------------------------------------------

    driver = create_driver()

    try:

        # ----------------------------------------------------
        # LOGIN UNA SOLA VOLTA
        # ----------------------------------------------------

        login(driver)

        # ----------------------------------------------------
        # MODALITÀ NEXT
        # ----------------------------------------------------

        if mode == "next":

            stagione, giornata = (
                supabase.get_next_missing(
                    SEASONS
                )
            )

            if not stagione:

                print()
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
                sys.exit(1)

        # ----------------------------------------------------
        # MODALITÀ ALL
        # ----------------------------------------------------

        else:

            for stagione in SEASONS:

                for giornata in range(1, 39):

                    # Già completata?
                    if supabase.is_completed(
                        stagione,
                        giornata,
                    ):
                        print(
                            f"⏭️ SKIP "
                            f"{stagione} G{giornata}"
                        )
                        continue

                    success = process_day(
                        driver,
                        supabase,
                        stagione,
                        giornata,
                    )

                    if not success:

                        print(
                            "⚠️ Giornata fallita."
                        )

                        # Passiamo alla successiva.
                        # Il log FAILED permetterà
                        # di ritentare alla prossima
                        # esecuzione.
                        continue

    finally:

        print()
        print("🌐 Chiusura browser...")

        driver.quit()

        print("🏁 Ingestion terminata.")


if __name__ == "__main__":
    main()
