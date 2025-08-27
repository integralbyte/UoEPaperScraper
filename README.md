# UoE Exam Paper Downloader (UoEPaperScraper)

A Python tool that signs in with **Microsoft SSO**, extracts the required **Shibboleth** cookie, and downloads **all available past exam papers** for a specified University of Edinburgh course.

> ⚠️ Requires a valid UoE login.

---

## Features

* ✅ Downloads **all available past papers** for a chosen course.
* ✅ Automatically organises files into a timestamped folder per course.
* ✅ Logs a clear success/failure summary in the terminal.
* ✅ Updated to work with **Microsoft SSO** (supports both **sign-in approval** and **one-time code** flows).
* ✅ Uses **Firefox + Geckodriver** for reliable automation.

---

## Requirements

* **Python** ≥ 3.10
* **Firefox** (latest stable recommended)
* **Geckodriver** available on your `PATH`
* **pip** to install Python packages

---

## Usage

```bash
python main.py
```

You’ll be prompted for:

* **University username** (enter just the ID like `s1234567`; the script appends `@ed.ac.uk`)
* **Password** (input is masked with asterisks)

Then:

1. The script opens the UoE SSO page and performs login.
2. If needed, it will guide you through Authenticator approval **or** one-time passcode.
3. On success, it extracts the **Shibboleth session cookie** and invokes `ExtractPapers.py`.
4. `ExtractPapers.py` handles the course selection and downloads the papers to a timestamped folder.

> The cookie is passed to `ExtractPapers.py` via the `COOKIE_HEADER` environment variable for the child process. Nothing is written to disk by `main.py`.

---

## Configuration

Open `main.py` and adjust:

```python
WAIT_SECONDS = 30   # increase this if your internet is slow
HEADLESS = True     # set to False to debug any errors (shows the browser)
```

---

## How It Works (High Level)

1. Starts **Firefox** via Selenium, maximises window (or sets a 1920×1080 size headless).
2. Navigates to the Login Page and submits credentials.
3. Following the Microsoft redirection, it handles either:
   * **Sign-in Code** (approval/number match), or
   * **One-Time 6-Digit Code** (user enters OTP), or
   * **“Trouble verifying your account”** → Happens when the user is rate-limited. It will continue retrying until one of the above methods succeeds.
4. Visits the exam papers site and grabs the **Shibboleth session** cookie.
5. Runs `ExtractPapers.py` with the `COOKIE_HEADER` set so it can download the papers.

---

## Tips & Troubleshooting

* **Incorrect credentials**
  If you see *“Incorrect user ID or password”*, re-run and double-check your UUN and password.

---

## Security & Privacy

* Password input is masked with asterisks.
* The script prints a minimal login status and does **not** save credentials or cookies to disk.
* The Shibboleth cookie is passed to `ExtractPapers.py` **in-memory** via an environment variable for the child process only.

---

## Notes

* This project currently targets **Firefox**.

---

## Disclaimer

* This tool is intended for **personal and educational use** by authorised University of Edinburgh users only.
* You are responsible for complying with university policies and copyright law.
* The author does **not** condone redistribution of exam materials or scraping for public upload.
* Any automation against Microsoft SSO must be **authorised and non-malicious**.
* The author accepts **no liability** for misuse or policy violations.

---

## License
MIT
