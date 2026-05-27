"""
Auto Form Filler using Selenium
---------------------------------
Fills text boxes on a website and clicks a submit button.
Cycles indefinitely until Ctrl+C.

Requirements:
    pip install selenium webdriver-manager

Usage:
    python attempt.py
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
# CONFIGURATION
# ─────────────────────────────────────────────

TARGET_URL = "https://bcmuslimschool.ca/contact-us/"  # Target website URL

TEXT_LIST = [
    "first entry",
    "second entry",
    "third entry",
]

TXT_FILE = None  # Set to filename (e.g. "entries.txt") to load entries from file, or None to use TEXT_LIST

FIELDS = [
    {
        "xpath": '//*[@id="wpforms-3549-field_2"]',  # tell us about your kids
        "value": "pls speed i need this my moms kinda homeless",
    },
    {
        "xpath": '//*[@id="wpforms-3549-field_3"]',  # phone number
        "value": "67676767",
    },
    {
        "xpath": '//*[@id="wpforms-3549-field_1"]',  # email
        "value": "zaidoali11@gmail.com",
    },
    {
        "xpath": '//*[@id="wpforms-3549-field_0"]',  # firstname
        "value": "john",
    },
    {
        "xpath": '//*[@id="wpforms-3549-field_0-last"]',  # lastname
        "value": "pork",
    },
]

SUBMIT_XPATH       = '//*[@id="wpforms-submit-3549"]'  # Submit button XPath

DELAY_BETWEEN_KEYS = 0  # Seconds between keystrokes (0 = instant)
DELAY_AFTER_SUBMIT = 1.5   # Seconds to wait after submit before refresh
WAIT_TIMEOUT       = 3    # Seconds to wait for elements
HEADLESS           = False # Set to True for headless mode

# If True, browser stays open after an error so you can inspect it
KEEP_OPEN_ON_ERROR = True


# ─────────────────────────────────────────────
# LOAD TEXT
# ─────────────────────────────────────────────

def load_entries() -> list[str]:  # Load entries from file or TEXT_LIST
    if TXT_FILE:
        with open(TXT_FILE, "r", encoding="utf-8") as f:
            entries = [line.strip() for line in f if line.strip()]
        print(f"📄 Loaded {len(entries)} entries from {TXT_FILE}")
    else:
        entries = TEXT_LIST
        print(f"📝 Using {len(entries)} hardcoded entries")

    return entries


# ─────────────────────────────────────────────
# BROWSER SETUP
# ─────────────────────────────────────────────

def create_driver() -> webdriver.Chrome:  # Create and configure Chrome driver
    options = Options()

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")

    options.add_experimental_option(
        "excludeSwitches",
        ["enable-automation"]
    )

    options.add_experimental_option(
        "useAutomationExtension",
        False
    )

    if HEADLESS:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
    else:
        options.add_argument("--start-maximized")

    service = (
        Service(ChromeDriverManager().install())
        if ChromeDriverManager
        else Service()
    )

    driver = webdriver.Chrome(
        service=service,
        options=options
    )

    # Hide webdriver detection
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
            """
        }
    )

    return driver


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def wait_page_loaded(driver) -> None:  # Wait for page to fully load
    WebDriverWait(driver, WAIT_TIMEOUT).until(
        lambda d: d.execute_script(
            "return document.readyState"
        ) == "complete"
    )


def fill_field(driver, xpath: str, value: str) -> None:  # Fill a form field with value

    print(f"  ✏ Filling: {xpath}")

    # Wait for element to exist
    element = WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.presence_of_element_located((By.XPATH, xpath))
    )

    # Scroll into view
    driver.execute_script(
        "arguments[0].scrollIntoView({block:'center'});",
        element
    )

    # Wait until clickable
    WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.element_to_be_clickable((By.XPATH, xpath))
    )

    time.sleep(0.2)

    # Click field
    element.click()

    time.sleep(0.1)

    # Select all text (Mac)
    element.send_keys(Keys.COMMAND + "a")

    time.sleep(0.1)

    # Delete old content
    element.send_keys(Keys.DELETE)

    time.sleep(0.1)

    # Extra clear
    element.clear()

    time.sleep(0.2)

    # Type text
    if DELAY_BETWEEN_KEYS > 0:
        for char in value:
            element.send_keys(char)
            time.sleep(DELAY_BETWEEN_KEYS)
    else:
        element.send_keys(value)

    time.sleep(0.2)


def click_submit(driver) -> None:  # Click the submit button

    print("  🖱 Clicking submit...")

    btn = WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.element_to_be_clickable(
            (By.XPATH, SUBMIT_XPATH)
        )
    )

    driver.execute_script(
        "arguments[0].scrollIntoView({block:'center'});",
        btn
    )

    time.sleep(0.3)

    driver.execute_script(
        "arguments[0].click();",
        btn
    )


# ─────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────

def run() -> None:  # Main automation loop

    entries = load_entries()

    driver = create_driver()

    total = 0
    cycle = 0
    error_occurred = False

    try:

        print(f"\n🌐 Opening {TARGET_URL}")

        driver.get(TARGET_URL)

        wait_page_loaded(driver)

        time.sleep(1)

        while True:

            cycle += 1

            print(
                f"\n════ Cycle {cycle} "
                f"— {total} submissions so far ════"
            )

            for i, text in enumerate(entries):

                print(
                    f"\n── Entry {i+1}/{len(entries)} "
                    f"'{text}' ──"
                )

                # Fill every field
                for field in FIELDS:

                    value = field["value"].replace(
                        "{text}",
                        text
                    )

                    try:

                        fill_field(
                            driver,
                            field["xpath"],
                            value
                        )

                    except Exception as e:

                        print(f"  ⚠ Skipping field: {e}")
                        # Continue to next field instead of raising
                        continue

                # Submit form
                try:

                    click_submit(driver)

                    total += 1

                    print(f"✅ Submitted ({total})")

                except Exception as e:

                    print(f"  ⚠ Submit failed (will retry next cycle): {e}")
                    # Continue to refresh instead of raising

                # Wait after submit
                time.sleep(DELAY_AFTER_SUBMIT)

                # Close browser and open a new one
                print("  🔄 Closing browser...")
                try:
                    driver.quit()
                except Exception as e:
                    print(f"  ⚠ Close failed: {e}")

                time.sleep(1)

                print("  🌐 Opening new browser...")
                try:
                    driver = create_driver()
                    driver.get(TARGET_URL)
                    wait_page_loaded(driver)
                    print("  ✅ New browser ready")
                except Exception as e:
                    print(f"  ⚠ Failed to open new browser: {e}")
                    time.sleep(2)
                    driver = create_driver()
                    driver.get(TARGET_URL)
                    wait_page_loaded(driver)

                time.sleep(1)

    except KeyboardInterrupt:

        print(
            f"\n⚠ Stopped by user "
            f"(Total submissions: {total})"
        )

    except Exception as e:

        error_occurred = True

        print("\n❌ FATAL ERROR")
        print(e)

        import traceback
        traceback.print_exc()

    finally:

        if error_occurred and KEEP_OPEN_ON_ERROR:

            print("\n🔍 Browser left open for debugging.")
            input("Press Enter to close browser...")

        driver.quit()

        print("🔒 Browser closed.")


# ─────────────────────────────────────────────
# START
# ─────────────────────────────────────────────

if __name__ == "__main__":
    run()