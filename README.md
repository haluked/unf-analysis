# ⚡ Instagram Unfollower Tracker Pro (v2.0)

A modern, fast, multithreaded desktop tool for Instagram follower and unfollower analysis. Runs 100% locally on your machine with no third-party APIs or server leaks.

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Selenium 4](https://img.shields.io/badge/selenium-4.15%2B-green.svg)](https://www.selenium.dev/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

---

## 🌟 What's New in v2.0

- 🎯 **Dual Follower & Following Analysis**:
  - **🚫 Not Following Back**: People you follow who do *not* follow you back.
  - **📉 Lost Followers**: People who unfollowed you since your last scan.
  - **🌟 Fans**: People who follow you, but you don't follow back.
  - **🤝 Mutual Friends**: Accounts with mutual follow.
  - **📈 New Followers**: People who followed you since the previous scan.
- 🛡️ **Safe Isolated Browser Profile**:
  - Uses a dedicated browser profile in `%LOCALAPPDATA%\unf-analysis\browser_profile`.
  - **Never closes or kills your active browser sessions!** Your open tabs, downloads, and work remain completely untouched.
  - Keeps you logged in safely across runs so you don't have to enter credentials every time.
- 🌐 **Multi-Browser Support & Zero Driver Headaches**:
  - Automatically detects **Brave**, **Google Chrome**, and **Microsoft Edge**.
  - Powered by **Selenium 4 built-in Selenium Manager**: zero hardcoded driver versions, no driver mismatches or session crashes when your browser updates.
- ⚡ **Multithreaded Responsive GUI**:
  - Clean, dark-mode desktop interface built with Tkinter.
  - Background worker thread prevents "Not Responding" freezes.
  - Real-time console logs, progress indicators, and instant stop/cancellation.
- 🔍 **Interactive Results & Export**:
  - Real-time search/filter as you type.
  - Direct profile navigation (open in your default browser with one click).
  - One-click clipboard copy (single or full list).
  - One-click export to **CSV** (UTF-8 BOM compatible with Excel) and **JSON**.
- 📜 **Historical Tracking**:
  - Saves timestamped records of every scan so you can track follower trends over weeks and months.

---

## 🖥️ Supported Browsers

- **Brave Browser** (Recommended)
- **Google Chrome**
- **Microsoft Edge**
- *Or specify any custom Chromium executable path in the Settings tab.*

---

## 🚀 Quick Start

### 1. Requirements
Ensure you have **Python 3.10+** installed on your Windows system.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Application
```bash
python unf-analysis.py
```

---

## 💡 How to Use

1. **Enter Target Username**:
   Type the Instagram username you want to analyze.
2. **Login Options**:
   - **Option A (Recommended & Safest)**: Click **🔑 Browser Login Only**. This opens the isolated browser window where you can log in manually using 2FA, SMS code, or password. Once logged in, your session is saved permanently in your isolated profile.
   - **Option B**: Enter your password in the app and click **🚀 Start Full Analysis**.
3. **Select Mode**:
   - *Full Analysis (Followers & Following)*: Scrapes both lists and computes all metrics.
   - *Followers Only* or *Following Only*.
4. **View & Export**:
   - Switch to the **🎯 Analysis Results** tab.
   - Filter by category ("Not Following Back", "Lost Followers", etc.).
   - Use the search bar to locate specific usernames.
   - Click **Export CSV** or **Export JSON** to save your results to disk.

---

## 🧪 Running Tests

A complete unit test suite is included in `tests/`:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

---

## 🔒 Security & Privacy

- **100% Local**: No external servers, no cloud storage, no telemetry.
- **Your Data Stays Yours**: Scraped lists and session cookies reside solely on your local computer under `%LOCALAPPDATA%\unf-analysis\`.
- **Anti-Bot Evading**: Employs human-like scrolling jitter, randomized intervals, and evades `navigator.webdriver` flags.

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0** (GPL-3.0). See [LICENSE](LICENSE) for details.
