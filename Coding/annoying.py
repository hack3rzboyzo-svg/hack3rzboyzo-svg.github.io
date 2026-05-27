"""
Auto Form Filler using Selenium
---------------------------------
Fills text boxes on a website and clicks a submit button.
Cycles indefinitely until Ctrl+C.

Requirements:
    pip install selenium webdriver-manager

Usage:
    python anoying.py
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import time

try:
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    ChromeDriverManager = None


# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────

TARGET_URL = "https://bcmuslimschool.ca/contact-us/"

TEXT_LIST = [
    "first entry",
    "second entry",
    "third entry",
]

TXT_FILE = None  # e.g. "entries.txt" — set to None to use TEXT_LIST

FIELDS = [
    {
        "xpath": '//*[@id="wpforms-3549-field_2"]',#tell us about your kids
        "value": "pls speed i need this my moms kinda homeless",
    },
    {
        "xpath": '//*[@id="wpforms-3549-field_3"]',#phone number
        "value": "67676767",
    },
    {
        "xpath": '//*[@id="wpforms-3549-field_1"]',#email
        "value": "zaidoali11@gmail.com",
    },
    {
        "xpath": '//*[@id="wpforms-3549-field_0"]',#firstname
        "value": "john",
    },
    {
        "xpath": '//*[@id="wpforms-3549-field_0-last"]',#lastname
        "value": "pork",
    },
]

SUBMIT_XPATH       = '//*[@id="wpforms-submit-3549"]'
DELAY_BETWEEN_KEYS = 0.05  # Seconds between keystrokes (0 = instant)
DELAY_AFTER_SUBMIT = 1.5   # Seconds to wait after submit before refresh
WAIT_TIMEOUT       = 10    # Seconds to wait for elements
HEADLESS           = False

# If True, browser stays open after an error so you can inspect it
KEEP_OPEN_ON_ERROR = True


# ─────────────────────────────────────────────
#  LOAD TEXT
# ─────────────────────────────────────────────

def load_entries() -> list[str]:
    if TXT_FILE:
        with open(TXT_FILE, "r", encoding="utf-8") as f:
            entries = [line.strip() for line in f if line.strip()]
        print(f"📄 Loaded {len(entries)} entries from {TXT_FILE}")
    else:
        entries = TEXT_LIST
        print(f"📝 Using {len(entries)} hardcoded entries")
    return entries


# ─────────────────────────────────────────────
#  BROWSER SETUP
# ─────────────────────────────────────────────

def create_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    if HEADLESS:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
    else:
        options.add_argument("--start-maximized")

    service = Service(ChromeDriverManager().install()) if ChromeDriverManager else Service()
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver


# ─────────────────────────────────────────────
#  FORM ACTIONS
# ─────────────────────────────────────────────

def fill_field(driver, xpath: str, value: str):
    element = WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.element_to_be_clickable((By.XPATH, xpath))
    )
    element.click()
    element.send_keys(Keys.CONTROL + "a")
    element.send_keys(Keys.DELETE)
    if DELAY_BETWEEN_KEYS > 0:
        for char in value:
            element.send_keys(char)
            time.sleep(DELAY_BETWEEN_KEYS)
    else:
        element.send_keys(value)


def click_submit(driver):
    btn = WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.element_to_be_clickable((By.XPATH, SUBMIT_XPATH))
    )
    driver.execute_script("arguments[0].click();", btn)


# ─────────────────────────────────────────────
#  MAIN LOOP
# ─────────────────────────────────────────────

def run():
    entries = load_entries()
    driver  = create_driver()
    total   = 0
    error_occurred = False

    try:
        print(f"\n🌐 Opening {TARGET_URL} ...")
        driver.get(TARGET_URL)
        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(1)

        cycle = 0
        while True:
            cycle += 1
            print(f"\n════ Cycle {cycle} — {total} submissions so far (Ctrl+C to stop) ════")

            for i, text in enumerate(entries):
                print(f"\n── Entry {i + 1}/{len(entries)}: '{text}' ──")

                for field in FIELDS:
                    value = field["value"].replace("{text}", text)
                    print(f"  ✏ {field['xpath']} → '{value}'")
                    try:
                        fill_field(driver, field["xpath"], value)
                    except Exception as e:
                        print(f"  ⚠ Could not fill field: {e} — skipping field")
                    time.sleep(0.1)

                print(f"  🖱 Submitting...")
                try:
                    click_submit(driver)
                    total += 1
                except Exception as e:
                    print(f"  ⚠ Could not click submit: {e} — retrying after refresh")

                time.sleep(DELAY_AFTER_SUBMIT)

                print(f"  🔄 Refreshing...")
                driver.get(TARGET_URL)
                WebDriverWait(driver, 15).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                time.sleep(1)

    except KeyboardInterrupt:
        print(f"\n⚠ Stopped by user. Total submissions: {total}")
    except Exception as e:
        error_occurred = True
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if error_occurred and KEEP_OPEN_ON_ERROR:
            print("\n🔍 Browser kept open for inspection (KEEP_OPEN_ON_ERROR=True)")
            print("   Close it manually when done.")
            input("   Press Enter to close browser and exit...\n")
        driver.quit()
        print("🔒 Browser closed.")


if __name__ == "__main__":
    run()