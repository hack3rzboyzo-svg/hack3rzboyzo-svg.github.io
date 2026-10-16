import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

LOGIN_URL = "https://my20.awfatech.com/main/appstudent/adm/index.php?sysapp=iium&apps=student"

# New: button click AFTER filling prefix
BEGIN_BUTTON_XPATH = '//*[@id="section-0"]/div[3]/div[2]/div/div[2]/div/div/table/tbody/tr/td/table/tbody/tr[3]/td/button'

FIRST_BUTTON_XPATH  = '//*[@id="myform"]/div[2]/div/div[2]/div/fieldset/table/tbody/tr/td[3]/div/a/div/div'
SECOND_BUTTON_XPATH = '//*[@id="container"]/div/div/fieldset/a[1]/h3/i'

# Point these at the <select> itself, NOT at an <option> (Select() needs a <select>)
YEAR_SELECT_XPATH = '//*[@id="container"]/div[2]/div/div[1]/select'
YEAR_TEXT = "2026"          # select the year by its visible text
YEAR_FALLBACK_INDEX = 4     # option[5] -> 0-based index 4

EXAM_SELECT_XPATH = '//*[@id="container"]/div[2]/div/div[3]/select'
EXAM_VALUE = "PR"  # "SEMESTER I" -- selecting by value instead of position,
                   # since this option appears more than once at varying
                   # positions depending on how many exams a student has
EXAM_FALLBACK_INDEX = 2  # option[3] -> index 2, used if the value isn't found

GRADES_TEXT_XPATH = '//*[@id="stuinfo"]/div[2]/div/table[2]/tbody'
NAME_XPATH = '//*[@id="myform"]/div[2]/div/div[2]/div/fieldset/table/tbody/tr/td[2]/table/tbody/tr[1]/td[3]'
CLASS_XPATH = '//*[@id="container"]/div[2]/div/div[2]/select'
PREFIX_INPUT_XPATH = '//*[@id="section-0"]/div[3]/div[2]/div/div[2]/div/div/table/tbody/tr/td/table/tbody/tr[2]/td/input'

SUBMIT_WAIT_SECONDS = 0.3

HEADLESS = False
RESTART_EVERY_N = 50

PREFIXES_FILENAME = "prefixes.txt"
OUTPUT_FILENAME = "grades_output.txt"


def read_prefixes(path):
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def click_when_ready(driver, wait, xpath):
    el = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
    el.click()
    return el


def _as_select(el):
    """Accept either a <select> or an <option> and return a Select bound to
    the parent <select>. Selenium's Select() only works on <select> elements."""
    if el.tag_name.lower() == "option":
        el = el.find_element(By.XPATH, "./ancestor::select[1]")
    return Select(el)


def select_option_by_index(driver, wait, select_xpath, index):
    """Selects an option from a <select> by index using Selenium's Select
    helper, which fires the real 'change' event the page's JS listens for
    (a plain .click() on an <option> doesn't reliably do this)."""
    el = wait.until(EC.visibility_of_element_located((By.XPATH, select_xpath)))
    _as_select(el).select_by_index(index)


def select_option_and_verify(driver, wait, select_xpath, index, retries=5, pause=0.4):
    """Selects an option by index and confirms it actually stuck -- useful
    for cascading dropdowns where the target <select> may still be
    repopulating right after a prior dropdown change."""
    for _ in range(retries):
        el = wait.until(EC.visibility_of_element_located((By.XPATH, select_xpath)))
        select = _as_select(el)
        if len(select.options) > index:
            select.select_by_index(index)
            # compare the selected option ELEMENT to the one we asked for
            # (Chrome has no 'index' attribute on <option>)
            if select.first_selected_option == select.options[index]:
                return True
        time.sleep(pause)
    return False


def select_option_by_text_and_verify(driver, wait, select_xpath, text,
                                     retries=5, pause=0.4, fallback_index=None):
    """Selects an option by its visible text (whitespace-normalized). More
    robust than index when option order/positions can vary. Falls back to a
    fixed position if the text never matches."""
    for _ in range(retries):
        el = wait.until(EC.visibility_of_element_located((By.XPATH, select_xpath)))
        select = _as_select(el)
        try:
            select.select_by_visible_text(text)
            if select.first_selected_option.text.strip() == text:
                return True
        except Exception:
            pass
        time.sleep(pause)

    if fallback_index is not None:
        try:
            el = wait.until(EC.visibility_of_element_located((By.XPATH, select_xpath)))
            select = _as_select(el)
            if len(select.options) > fallback_index:
                select.select_by_index(fallback_index)
                return True
        except Exception:
            pass
    return False


def select_option_by_value_and_verify(driver, wait, select_xpath, value,
                                      retries=10, pause=0.5, fallback_index=None):
    """Selects an option by its underlying value (e.g. 'PS2') rather than
    position. More robust than index-based selection when the number or
    order of options can vary per student -- as long as the value exists
    somewhere in the list, this will find and select it correctly.
    If the value never appears, optionally fall back to a fixed position."""
    for _ in range(retries):
        el = wait.until(EC.visibility_of_element_located((By.XPATH, select_xpath)))
        select = _as_select(el)
        available_values = [opt.get_attribute("value") for opt in select.options]
        if value in available_values:
            select.select_by_value(value)
            if select.first_selected_option.get_attribute("value") == value:
                return True
        time.sleep(pause)

    if fallback_index is not None:
        try:
            el = wait.until(EC.visibility_of_element_located((By.XPATH, select_xpath)))
            select = _as_select(el)
            if len(select.options) > fallback_index:
                select.select_by_index(fallback_index)
                return True
        except Exception:
            pass
    return False


def reselect_current_value(driver, wait, select_xpath):
    """Re-selects a dropdown's already-current value to force a native
    'change' event to fire. Some dropdowns (like Class here) get their
    value auto-populated by the page itself rather than through a genuine
    user click, so no 'change' event ever fires on them -- which can stop
    a dependent dropdown (like Examination) from ever populating. Returns
    True if a value was found and reselected."""
    try:
        el = wait.until(EC.visibility_of_element_located((By.XPATH, select_xpath)))
        select = _as_select(el)
        current = select.first_selected_option
        if current is None:
            return False
        idx = select.options.index(current)   # locate the currently-selected option
        select.select_by_index(idx)           # re-select it to fire a real 'change'
        return True
    except Exception:
        return False


def extract_visible_text(driver, wait, xpath):
    el = wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))
    return driver.execute_script("return arguments[0].innerText;", el).strip()


def try_extract_visible_text(driver, wait, xpath):
    """Like extract_visible_text, but returns '' instead of raising if the
    element never appears/becomes visible (e.g. no grades are available for
    this student). Uses innerText via JS so only actually-rendered, visible
    text is captured (hidden rows/cells are excluded), which is more
    reliable under headless Chrome than relying purely on .text."""
    try:
        el = wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))
        return driver.execute_script("return arguments[0].innerText;", el).strip()
    except Exception:
        return ""


def try_extract_selected_option_text(driver, wait, select_xpath):
    """Reads the currently selected option's visible text from a <select>
    element. Returns '' if the dropdown never appears or has no selection."""
    try:
        el = wait.until(EC.visibility_of_element_located((By.XPATH, select_xpath)))
        select = _as_select(el)
        return select.first_selected_option.text.strip()
    except Exception:
        return ""


def debug_exam_options(driver, wait):
    """Prints the exam dropdown's options (value + text) so EXAM_VALUE can
    be confirmed. Call it once on the first student if needed."""
    try:
        el = wait.until(EC.visibility_of_element_located((By.XPATH, EXAM_SELECT_XPATH)))
        sel = _as_select(el)
        for i, o in enumerate(sel.options):
            print(i, "value=", repr(o.get_attribute("value")), "text=", repr(o.text))
    except Exception as e:
        print("debug error:", e)


def find_file(filename, start_dir):
    for root, _, files in os.walk(start_dir):
        if filename in files:
            return os.path.join(root, filename)
    return None


def build_chrome_options():
    chrome_options = Options()
    if HEADLESS:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    return chrome_options


def start_driver():
    driver = webdriver.Chrome(options=build_chrome_options())
    wait = WebDriverWait(driver, 20)
    # Give the browser window a moment to fully initialize before the first
    # real navigation -- right after launch (especially non-headless), the
    # window isn't always ready the instant Selenium hands back control,
    # which is what causes crashes on the very first attempt of a fresh run.
    try:
        driver.get("about:blank")
    except Exception:
        pass
    time.sleep(1.5)
    return driver, wait


def is_driver_alive(driver):
    """Cheap check to see if the browser session is still usable."""
    try:
        _ = driver.title
        return True
    except Exception:
        return False


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    prefixes_path = find_file(PREFIXES_FILENAME, base_dir)
    if not prefixes_path:
        raise FileNotFoundError(f"Could not find {PREFIXES_FILENAME} under: {base_dir}")

    output_path = os.path.join(base_dir, OUTPUT_FILENAME)
    prefixes = read_prefixes(prefixes_path)

    MAX_ATTEMPTS = 3
    driver, wait = start_driver()
    processed_count = 0

    with open(output_path, "a", encoding="utf-8") as out:
        for prefix in prefixes:
            last_exc = None

            # Proactively recycle the browser every N students to avoid
            # memory buildup over long runs, even if nothing has failed yet.
            if processed_count > 0 and processed_count % RESTART_EVERY_N == 0:
                print(f"[INFO] Restarting browser after {processed_count} students (scheduled recycle)")
                try:
                    driver.quit()
                except Exception:
                    pass
                driver, wait = start_driver()

            for attempt in range(1, MAX_ATTEMPTS + 1):
                try:
                    # If a previous attempt killed the session, get a fresh one
                    if not is_driver_alive(driver):
                        try:
                            driver.quit()
                        except Exception:
                            pass
                        print(f"[INFO] Browser session dead, restarting before retrying {prefix}")
                        driver, wait = start_driver()

                    driver.get(LOGIN_URL)

                    # Fill prefix input
                    input_box = wait.until(EC.visibility_of_element_located((By.XPATH, PREFIX_INPUT_XPATH)))
                    input_box.clear()
                    input_box.send_keys(prefix)

                    time.sleep(SUBMIT_WAIT_SECONDS)

                    # Click newest button (after filling prefix) -- this logs in
                    click_when_ready(driver, wait, BEGIN_BUTTON_XPATH)
                    time.sleep(SUBMIT_WAIT_SECONDS)

                    # Grab the name right away, while still on the post-login page
                    name_text = try_extract_visible_text(driver, wait, NAME_XPATH)

                    # FIRST button
                    click_when_ready(driver, wait, FIRST_BUTTON_XPATH)
                    time.sleep(SUBMIT_WAIT_SECONDS)

                    # SECOND button
                    click_when_ready(driver, wait, SECOND_BUTTON_XPATH)
                    time.sleep(SUBMIT_WAIT_SECONDS)

                    # Select year + examination (class auto-selected).
                    # Exam list depends on the year AND class, so verify
                    # each selection actually took before moving on.
                    year_ok = select_option_by_text_and_verify(
                        driver, wait, YEAR_SELECT_XPATH, YEAR_TEXT,
                        fallback_index=YEAR_FALLBACK_INDEX
                    )
                    if not year_ok:
                        raise RuntimeError(f"Could not confirm year selection for {prefix}")

                    # Class is auto-populated by the site itself (based on
                    # the student), so it never gets a genuine user-driven
                    # 'change' event. If the Examination list's population
                    # logic listens for a change on Class, it never fires
                    # otherwise -- so we force one here by reselecting the
                    # class's own current value.
                    reselect_current_value(driver, wait, CLASS_XPATH)
                    time.sleep(SUBMIT_WAIT_SECONDS)

                    exam_ok = select_option_by_value_and_verify(
                        driver, wait, EXAM_SELECT_XPATH, EXAM_VALUE,
                        retries=10, pause=0.5, fallback_index=EXAM_FALLBACK_INDEX
                    )

                    class_text = try_extract_selected_option_text(driver, wait, CLASS_XPATH)
                    name_line = name_text if name_text else "Nothing found"
                    class_line = class_text if class_text else "Nothing found"

                    if not exam_ok:
                        # After 10 retries the exam list has had time to fully
                        # populate -- if the target option still isn't there,
                        # this student most likely just doesn't have that
                        # exam recorded, rather than the page still loading.
                        # Treat it as a real (empty) result, not a crash.
                        out.write(f"{prefix}\n{name_line}\n{class_line}\nNothing found\n\n")
                        out.flush()
                        print(f"[OK] {prefix} saved (no exam option available)")
                        last_exc = None
                        break

                    display_text = try_extract_visible_text(driver, wait, GRADES_TEXT_XPATH)

                    if not display_text:
                        display_text = "Nothing found"

                    out.write(f"{prefix}\n{name_line}\n{class_line}\n{display_text}\n\n")
                    out.flush()
                    print(f"[OK] {prefix} saved")
                    last_exc = None
                    break  # success, no need to retry

                except Exception as e:
                    last_exc = e
                    print(f"[WARN] {prefix} attempt {attempt}/{MAX_ATTEMPTS} failed: "
                          f"{type(e).__name__}: {e}")
                    # brief pause before retrying / restarting
                    time.sleep(1)

            if last_exc is not None:
                out.write(f"{prefix}\nERROR: {type(last_exc).__name__}: {last_exc}\n\n")
                out.flush()
                print(f"[ERR] {prefix}: gave up after {MAX_ATTEMPTS} attempts "
                      f"({type(last_exc).__name__})")

            processed_count += 1

    driver.quit()


if __name__ == "__main__":
    main()