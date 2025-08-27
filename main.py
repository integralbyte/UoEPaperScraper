
import os, sys, json, time, warnings, logging, subprocess
from threading import Thread, Event
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.remote.remote_connection import LOGGER as SELENIUM_LOGGER
from selenium.webdriver.firefox.options import Options as FFOptions
from selenium.webdriver.firefox.service import Service as FFService

WAIT_SECONDS = 30
HEADLESS = True
LOGIN_URL = "https://www.myed.ed.ac.uk/uPortal/Login?refUrl=%2Fmyed-progressive%2F"
EXAMS_URL = "https://exampapers.ed.ac.uk/"

def input_password_asterisk(prompt="Password: "):
    try:
        import msvcrt
        print(prompt, end="", flush=True)
        buf = []
        while True:
            ch = msvcrt.getwch()
            if ch in ("\r", "\n"):
                print()
                break
            if ch == "\003":
                raise KeyboardInterrupt
            if ch == "\b":
                if buf:
                    buf.pop()
                    print("\b \b", end="", flush=True)
            else:
                buf.append(ch)
                print("*", end="", flush=True)
        return "".join(buf)
    except Exception:
        try:
            import termios, tty
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                print(prompt, end="", flush=True)
                buf = []
                while True:
                    ch = sys.stdin.read(1)
                    if ch in ("\r", "\n"):
                        print()
                        break
                    if ch == "\x03":
                        raise KeyboardInterrupt
                    if ch in ("\x7f", "\b"):
                        if buf:
                            buf.pop()
                            sys.stdout.write("\b \b")
                            sys.stdout.flush()
                    else:
                        buf.append(ch)
                        sys.stdout.write("*")
                        sys.stdout.flush()
                return "".join(buf)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
        except Exception:
            try:
                import getpass
                return getpass.getpass(prompt)
            except Exception:
                return input(prompt)

def make_driver():
    ff_opts = FFOptions()
    if HEADLESS:
        ff_opts.add_argument("-headless")

    ff_service = FFService(log_output=os.devnull)

    driver = webdriver.Firefox(options=ff_opts, service=ff_service)

    if HEADLESS:
        driver.set_window_size(1920, 1080)
    else:
        try:
            driver.maximize_window()
        except Exception:
            driver.set_window_size(1920, 1080)

    return driver

def wait_presence_soft(driver, by, locator, timeout=WAIT_SECONDS):
    try:
        return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, locator)))
    except TimeoutException:
        return None

def xpath_present(driver, by, locator) -> bool:
    try:
        return bool(driver.find_elements(by, locator))
    except Exception:
        return False

def click_if_present(driver, by, locator, timeout=None):
    try:
        if timeout:
            el = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by, locator))
            )
        else:
            el = driver.find_element(by, locator)

        el.click()
        return True
    except (TimeoutException, NoSuchElementException, WebDriverException):
        return False

def send_keys_if_present(driver, by, locator, keys, timeout=WAIT_SECONDS, clear_first=True):
    el = wait_presence_soft(driver, by, locator, timeout)
    if not el:
        return False
    try:
        if clear_first:
            try: el.clear()
            except Exception: pass
        el.send_keys(keys)
        return True
    except Exception:
        return False

def get_text_if_present(driver, by, locator, timeout=WAIT_SECONDS):
    el = wait_presence_soft(driver, by, locator, timeout)
    try:
        return (el.text or "").strip() if el else ""
    except Exception:
        return ""

def page_contains(driver, phrase: str) -> bool:
    try:
        return phrase.lower() in (driver.page_source or "").lower()
    except Exception:
        return False

def wait_until_source_contains_any(driver, phrases, timeout=WAIT_SECONDS, poll_interval=0.5):
    end = time.time() + timeout
    lowers = [p.lower() for p in phrases]
    while time.time() < end:
        try:
            src = (driver.page_source or "").lower()
            for i, p in enumerate(lowers):
                if p in src:
                    return phrases[i]
        except Exception:
            pass
        time.sleep(poll_interval)
    return None

def extract_name_from_welcome(raw: str) -> str | None:
    if not raw:
        return None
    t = raw.replace("\xa0", " ").strip()
    parts = [p.strip() for p in t.splitlines() if p.strip()]
    if not parts:
        return None
    if parts[0].lower().startswith("you are signed in as"):
        name = parts[-1]
    else:
        name = parts[-1]
    return name.strip() or None

def _boot_driver_and_open_login(holder: dict, ready_evt: Event):
    try:
        d = make_driver()
        d.get(LOGIN_URL)
        holder["driver"] = d
    except Exception as e:
        holder["error"] = e
    finally:
        ready_evt.set()

def main():
    ready = Event()
    holder = {}
    Thread(target=_boot_driver_and_open_login, args=(holder, ready), daemon=True).start()

    print("University username (e.g., s1234567): ", end="", flush=True)
    try:
        username = input().strip() + "@ed.ac.uk"
    except EOFError:
        username = ""
    password = input_password_asterisk("Enter your password: ").strip()

    ready.wait()
    if "error" in holder:
        raise RuntimeError(f"Failed to start browser: {holder['error']}")
    driver = holder["driver"]

    try:
        send_keys_if_present(driver, By.ID, "userNameInput", username)
        send_keys_if_present(driver, By.ID, "passwordInput", password)

        click_if_present(driver, By.ID, "submitButton")

        
        wait_until_source_contains_any(
            driver,
            phrases=["lightboxTemplateContainer", "Incorrect user ID or password"],
            timeout=WAIT_SECONDS,
            poll_interval=0.5
        )
        
        if page_contains(driver, "Incorrect user ID or password"):
            print("Incorrect user ID or password")
            sys.exit()

        wait_presence_soft(driver, By.XPATH, '//*[@id="idSIButton9"]')
        click_if_present(driver, By.XPATH, '//*[@id="idSIButton9"]')

        wait_until_source_contains_any(
            driver,
            phrases=["trouble verifying your account", "Open your Authenticator", "Enter the code displayed"],
            timeout=WAIT_SECONDS,
            poll_interval=0.5
        )

        if page_contains(driver, "trouble verifying your account"):
            proof1 = '//*[@id="idDiv_SAOTCS_Proofs"]/div[1]/div'
            proof2 = '//*[@id="idDiv_SAOTCS_Proofs"]/div[2]/div'

            while True:
                has1 = xpath_present(driver, By.XPATH, proof1)
                has2 = xpath_present(driver, By.XPATH, proof2)

                # Exit when neither XPath is on the page
                if not (has1 or has2):
                    # print("breaking")
                    break

                if has1:
                    # print("found 1")
                    while True:
                        if page_contains(driver, "lightbox-cover disable-lightbox"):
                            # print("1: loading wait")
                            time.sleep(0.5)
                        else:
                            break
                    # print("broke 1")
                    click_if_present(driver, By.XPATH, proof1)

                if has2:
                    # print("found 2")
                    while True:
                        if page_contains(driver, "lightbox-cover disable-lightbox"):
                            # print("2: loading wait")
                            time.sleep(0.5)
                        else:
                            break
                    # print("broke 2")
                    click_if_present(driver, By.XPATH, proof2)

                time.sleep(0.5)

            wait_until_source_contains_any(
            driver,
            phrases=["Open your Authenticator", "Enter the code displayed"],
            timeout=WAIT_SECONDS,
            poll_interval=0.5
            )
            
        if page_contains(driver, "Enter the code displayed"):
            try:
                print("Enter the one-time code in your authenticator app, then press Enter: ", end="", flush=True)
                otp_code = input().strip()
            except EOFError:
                otp_code = ""
            send_keys_if_present(driver, By.XPATH, '//*[@id="idTxtBx_SAOTCC_OTC"]', otp_code)

            wait_presence_soft(driver, By.ID, "idSubmit_SAOTCC_Continue")
            if not click_if_present(driver, By.ID, "idSubmit_SAOTCC_Continue"):
                wait_presence_soft(driver, By.XPATH, '//*[@id="idSubmit_SAOTCC_Continue"]')
                click_if_present(driver, By.XPATH, '//*[@id="idSubmit_SAOTCC_Continue"]')

            wait_presence_soft(driver, By.ID, "idSIButton9")
            click_if_present(driver, By.ID, "idSIButton9")

        elif page_contains(driver, "Open your Authenticator"):
            ctx_text = get_text_if_present(driver, By.ID, "idRichContext_DisplaySign")
            if ctx_text:
                print("Sign-in code: " + ctx_text)
            print("Open your Authenticator and approve the sign-in.")
            click_if_present(driver, By.ID, "idSIButton9", timeout=120)
            print("Sign-in Approved!")

        wait_presence_soft(driver, By.ID, "notification-icon")

        welcome_raw = get_text_if_present(driver, By.XPATH, '//*[@id="region-eyebrow"]/div/div[2]/div/div[3]') or ""
        name = extract_name_from_welcome(welcome_raw)
        if name:
            print(f"Login Successful. Welcome {name}!\nFetching account cookies!")
        else:
            print("Login Successful.")

        driver.get(EXAMS_URL)
        wait_presence_soft(
            driver, By.XPATH,
            "/html/body/ds-app/ds-themed-root/ds-root/div/div/main/div/ds-themed-home-page/ds-home-page/div/ds-themed-search-form/ds-search-form/form/div/div/input"
        )

        try:
            cookies = driver.get_cookies()
            shib = next((c for c in cookies if "shibsession" in (c.get("name") or "").lower()), None)
            if shib and shib.get("name") and shib.get("value"):
                print("Login Cookie Extracted!")
                env = os.environ.copy()
                env["COOKIE_HEADER"] = f"{shib['name']}={shib['value']}"
                base_dir = Path(__file__).resolve().parent
                subprocess.run([sys.executable, "ExtractPapers.py"], cwd=base_dir, env=env, check=True)
            else:
                print("Shibsession cookie not found.")
        except Exception as e:
            print(f"Failed to pass cookie to ExtractPapers.py: {e}")

    finally:
        try:
            driver.quit()
        except Exception:
            pass

if __name__ == "__main__":
    main()
