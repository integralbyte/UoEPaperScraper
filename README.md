# UoEPaperScraper
A Python script that downloads all available past exam papers for a specified course at the University of Edinburgh. Requires a valid university login.

# UoE Exam Paper Downloader:
A Python script that downloads all available past exam papers for a given University of Edinburgh course. 
> Requires a valid UoE login and session cookie.

## Features - 
Downloads **all available past papers** for a specified course. 
- Automatically organizes them into a folder named with the course code and timestamp.
- Logs download status (success/failure/unavailable) in a `logs.txt` file.

## How to Get the Session Cookie
To access the exam papers, you need a valid session cookie (`_shibsession_*`) from the [UoE Exam Paper Site](https://exampapers.ed.ac.uk).
There are two common ways to get this:
### Method 1: Using Browser Dev Tools 
1. Log in at [https://exampapers.ed.ac.uk](https://exampapers.ed.ac.uk). 
2. Right-click anywhere on the page and choose **Inspect** to open Developer Tools.
3. Go to the **Application** tab (or **Storage** tab in Firefox).
4. In the left sidebar, select **Cookies > https://exampapers.ed.ac.uk**.
5. Find a cookie whose name starts with `_shibsession_`.
6. Copy the **name** and **value** of that cookie.

### Method 2: Using a Browser Extension
Use a cookie viewer like: 
- [Cookie-Editor (Chrome)](https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)
- [Cookie-Editor (Firefox)](https://addons.mozilla.org/en-GB/firefox/addon/cookie-editor/)

Steps: 
1. Visit [https://exampapers.ed.ac.uk](https://exampapers.ed.ac.uk) and log in. 
2. Open the extension and locate the `_shibsession_*` cookie. 
3. Copy its **name** and **value**.

> Never share your session cookie. It provides temporary access to your university account.

## Troubleshooting 
- **"Invalid Course ID!"** Double-check the course ID. A valid Course ID is MATH08058. Check DRPS if you cannot find it. 
- **Papers not downloading?** Your session cookie might be expired. Log in again and get a fresh one.

## ⚠️ **Disclaimer**  
- This tool is intended for personal and educational use only by authorised users of the University of Edinburgh.  
- You are solely responsible for complying with university policies and copyright law.  
- The creator of this tool does **not condone or support** the redistribution of exam materials or scraping for public upload.
