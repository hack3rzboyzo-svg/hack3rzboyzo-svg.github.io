import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

SUCCESS_URL = "https://my20.awfatech.com/main/appstudent/main/index.php"
FORM_URL    = "https://my20.awfatech.com/main/appstudent/adm/index.php?sysapp=iium&apps=student"
OUTPUT_FILE = "/Users/parvinabaleava/Downloads/output.txt"

INPUT_XPATH  = "//*[@id=\"section-0\"]/div[3]/div[2]/div/div[2]/div/div/table/tbody/tr/td/table/tbody/tr[2]/td/input"
BUTTON_XPATH = "//button[@type='button']"
EXTRA_XPATH  = '//*[@id="myform"]/div[2]/div/div[2]/div/fieldset/table/tbody/tr/td[2]/table/tbody/tr[4]/td[3]'

# A class with no name, e.g. " / 2026", "/2026", "2026"
EMPTY_CLASS_RE = re.compile(r'^\s*/?\s*\d{4}\s*$')


def generate_prefix(number):
    return f"IS{str(number).zfill(4)}"


def log_success(prefix, name, extra):
    with open(OUTPUT_FILE, "a") as f:
        f.write(f"{prefix} | {name} | {extra}\n")
    print(f"[SUCCESS] {prefix} | {name} | {extra} — logged")


def is_empty_class(extra):
    return bool(EMPTY_CLASS_RE.match(extra or ""))


def get_student_name(driver):
    try:
        el = WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".text-white.text-uppercase")))
        return el.text.strip()
    except Exception:
        return "UNKNOWN"


def get_extra_field(driver, timeout=6):
    """Poll briefly so any JS-populated value has time to appear."""
    end = time.time() + timeout
    last = "UNKNOWN"
    while time.time() < end:
        for e in driver.find_elements(By.XPATH, EXTRA_XPATH):
            t = (e.get_attribute("textContent") or "").strip()
            if t:
                last = t
                if any(c.isalpha() for c in t):   # real class name present
                    return t
        time.sleep(0.2)
    return last


def attempt(driver, prefix):
    box = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.XPATH, INPUT_XPATH)))
    box.clear()
    box.send_keys(prefix)

    btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, BUTTON_XPATH)))
    btn.click()

    WebDriverWait(driver, 6).until(lambda d: (d.current_url or "") != FORM_URL)

    if SUCCESS_URL in (driver.current_url or ""):
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete")
        return True, get_student_name(driver), get_extra_field(driver)
    return False, None, None


def attempt_with_retry(driver, prefix, tries=2):
    last = None
    for _ in range(tries):
        try:
            return attempt(driver, prefix)
        except StaleElementReferenceException as e:
            last = e
    raise last


def main():
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)

    try:
        driver.get(FORM_URL)

        for number in range(2775, 10000):
            prefix = generate_prefix(number)
            try:
                ok, name, extra = attempt_with_retry(driver, prefix)
                if not ok:
                    print(f"[FAIL] {prefix} — not enrolled")
                elif is_empty_class(extra):
                    print(f"[SKIP] {prefix} — empty class ({extra!r})")
                else:
                    log_success(prefix, name, extra)
            except TimeoutException:
                print(f"[FAIL] {prefix} — no redirect")
            except Exception as e:
                print(f"[ERR] {prefix} — {e}")
            finally:
                try:
                    driver.get(FORM_URL)
                except Exception:
                    pass

    except Exception as e:
        print("Fatal:", e)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
