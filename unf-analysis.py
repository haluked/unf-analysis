# -*- coding: utf-8 -*-
"""
Instagram Unfollower & Follower Tracker (Pro Edition v2.0)
==========================================================
A modern, multithreaded desktop tool for Instagram follower & unfollower analysis.

Key Upgrades in v2.0:
- Dual Analysis: Computes 'Not Following Back', 'Fans', 'Mutuals', 'Lost Followers', and 'New Followers'
- Zero Hardcoded Drivers: Uses modern Selenium 4 built-in Selenium Manager for Chrome, Brave, and Edge
- Safe Isolated Profile: Uses a dedicated browser profile in LocalAppData (never kills running browsers)
- Multithreaded GUI: Fully responsive Tkinter interface that never freezes, with real-time cancellation
- Robust DOM Virtualization: Smart scroll engine with viewport unstuck and regex user extraction
- Data Export: Instant CSV and JSON export, search filtering, and direct profile navigation
"""

import os
import sys
import time
import json
import random
import re
import csv
import queue
import shutil
import threading
import webbrowser
from datetime import datetime

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    WebDriverException,
)

# App Directory Structure
APP_DIR = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'unf-analysis')
PROFILE_DIR = os.path.join(APP_DIR, 'browser_profile')
CONFIG_FILE = os.path.join(APP_DIR, 'config.json')
HISTORY_FILE = os.path.join(APP_DIR, 'analysis_history.json')
EXPORTS_DIR = os.path.join(APP_DIR, 'exports')

for d in [APP_DIR, PROFILE_DIR, EXPORTS_DIR]:
    os.makedirs(d, exist_ok=True)

RESERVED_ROUTES = {
    'p', 'reel', 'reels', 'stories', 'explore', 'direct', 'accounts', 'about',
    'help', 'legal', 'privacy', 'terms', 'developer', 'directory', 'blog',
    'jobs', 'api', 'meta', 'static', 'threads', 'support', 'graphql', 'emails',
    'settings', 'notifications'
}

def detect_browsers():
    """Detect available browsers on the Windows system."""
    browsers = {}
    
    # Brave
    brave_paths = [
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
        os.path.join(os.environ.get('LOCALAPPDATA', ''), r"BraveSoftware\Brave-Browser\Application\brave.exe")
    ]
    for p in brave_paths:
        if p and os.path.isfile(p):
            browsers['Brave'] = p
            break
            
    # Chrome
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.join(os.environ.get('LOCALAPPDATA', ''), r"Google\Chrome\Application\chrome.exe")
    ]
    for p in chrome_paths:
        if p and os.path.isfile(p):
            browsers['Chrome'] = p
            break
            
    # Edge
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.join(os.environ.get('LOCALAPPDATA', ''), r"Microsoft\Edge\Application\msedge.exe")
    ]
    for p in edge_paths:
        if p and os.path.isfile(p):
            browsers['Edge'] = p
            break

    return browsers


class InstagramAutomation:
    """Handles browser initialization and Instagram DOM navigation."""

    def __init__(self, browser_name, binary_path=None, log_func=None):
        self.browser_name = browser_name
        self.binary_path = binary_path
        self.log = log_func or print
        self.driver = None

    def start_driver(self):
        """Initializes a Selenium WebDriver instance with anti-detection and profile persistence."""
        self.log(f"Launching {self.browser_name} with isolated profile...")

        if self.browser_name in ['Brave', 'Chrome']:
            options = ChromeOptions()
            if self.binary_path and os.path.isfile(self.binary_path):
                options.binary_location = self.binary_path
            
            # Anti-detection arguments
            options.add_argument("--disable-notifications")
            options.add_argument("--window-size=1150,920")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Isolated profile
            options.add_argument(f"--user-data-dir={PROFILE_DIR}")
            options.add_argument("--profile-directory=Default")
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
            
            # Selenium 4 uses Selenium Manager automatically to match drivers
            self.driver = webdriver.Chrome(options=options)
            
        elif self.browser_name == 'Edge':
            options = EdgeOptions()
            if self.binary_path and os.path.isfile(self.binary_path):
                options.binary_location = self.binary_path
                
            options.add_argument("--disable-notifications")
            options.add_argument("--window-size=1150,920")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument(f"--user-data-dir={PROFILE_DIR}")
            options.add_argument("--profile-directory=Default")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            self.driver = webdriver.Edge(options=options)
        else:
            raise ValueError(f"Unsupported browser: {self.browser_name}")

        # Evade navigator.webdriver detection
        try:
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
            )
        except Exception:
            pass

        return self.driver

    def check_is_logged_in(self, timeout=8):
        """Determines if the user has an active Instagram session."""
        if not self.driver:
            return False
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//*[contains(@aria-label, 'Home') or contains(@aria-label, 'Ana Sayfa') or "
                    "contains(@aria-label, 'Search') or contains(@aria-label, 'Ara') or "
                    "contains(@aria-label, 'Direct') or contains(@aria-label, 'Messages') or "
                    "contains(@aria-label, 'Profil') or contains(@aria-label, 'Profile') or "
                    "//a[contains(@href, '/direct/inbox')]]"
                ))
            )
            return True
        except TimeoutException:
            # Also check if login form elements exist
            login_forms = self.driver.find_elements(By.NAME, "username")
            return len(login_forms) == 0 and "instagram.com/accounts/login" not in self.driver.current_url

    def perform_login(self, username, password):
        """Attempts to log in with provided credentials if required."""
        self.driver.get("https://www.instagram.com/accounts/login/")
        time.sleep(3)

        # Handle cookie banner if present
        try:
            cookie_btn = WebDriverWait(self.driver, 4).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Allow') or contains(text(), 'İzin') or contains(text(), 'Accept') or contains(text(), 'Kabul')]"))
            )
            cookie_btn.click()
            time.sleep(1)
        except Exception:
            pass

        if self.check_is_logged_in(timeout=3):
            self.log("Existing active session found! Skipping login form.")
            return True

        self.log(f"Entering credentials for @{username}...")
        try:
            wait = WebDriverWait(self.driver, 10)
            user_input = wait.until(EC.presence_of_element_located((By.NAME, "username")))
            user_input.clear()
            user_input.send_keys(username)
            time.sleep(0.5)

            pass_input = self.driver.find_element(By.NAME, "password")
            pass_input.clear()
            pass_input.send_keys(password)
            time.sleep(0.5)

            submit_btn = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            submit_btn.click()
            self.log("Submitted login form. Waiting for authentication...")

            # Wait up to 15 seconds for login completion
            for _ in range(15):
                time.sleep(1)
                if self.check_is_logged_in(timeout=2):
                    self.log("Successfully logged in!")
                    return True

            # Check for 2FA / checkpoint
            if "checkpoint" in self.driver.current_url or "two_factor" in self.driver.current_url:
                self.log("Two-Factor Authentication (2FA) or Security Check detected!")
                self.log("Please complete the challenge in the browser window...")
                # Give user 60 seconds to solve 2FA
                for _ in range(60):
                    time.sleep(1)
                    if self.check_is_logged_in(timeout=2):
                        self.log("Security challenge passed!")
                        return True

            return self.check_is_logged_in(timeout=3)
        except Exception as e:
            self.log(f"Login failed: {e}")
            return False

    def extract_users_from_modal(self, target_username, list_type, progress_callback=None, stop_event=None, max_attempts=8):
        """
        Navigates to the modal dialog for followers/following,
        scrolls through the virtualized DOM, and extracts all clean usernames.
        """
        self.log(f"Navigating to @{target_username} profile...")
        self.driver.get(f"https://www.instagram.com/{target_username}/")
        time.sleep(4)

        # Open the modal
        self.log(f"Opening {list_type} modal...")
        modal_opened = False
        try:
            wait = WebDriverWait(self.driver, 8)
            link = wait.until(EC.element_to_be_clickable((By.XPATH, f"//a[contains(@href, '/{list_type}/')]")))
            link.click()
            modal_opened = True
            time.sleep(3)
        except Exception:
            self.log(f"Direct click failed. Navigating to https://www.instagram.com/{target_username}/{list_type}/...")
            self.driver.get(f"https://www.instagram.com/{target_username}/{list_type}/")
            time.sleep(4)
            modal_opened = True

        # Wait for modal dialog
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']"))
            )
        except TimeoutException:
            self.log("Warning: role='dialog' not found, searching main page content...")

        collected_users = set()
        consecutive_stalls = 0
        scroll_count = 0
        max_scrolls = 600

        self.log(f"Beginning smart scroll collection for {list_type}...")

        while scroll_count < max_scrolls:
            if stop_event and stop_event.is_set():
                self.log("Operation cancelled by user.")
                break

            scroll_count += 1

            # 1. Harvest links from dialog or page
            try:
                links = self.driver.find_elements(By.XPATH, "//div[@role='dialog']//a[@href]")
                if not links:
                    links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/') and not(contains(@href, '/p/'))]")
                
                prev_count = len(collected_users)
                for link in links:
                    try:
                        href = link.get_attribute('href')
                        if not href:
                            continue
                        
                        # Match /username/ pattern
                        parts = [p for p in href.strip('/').split('/') if p]
                        if parts:
                            u = parts[-1]
                            if (
                                u not in RESERVED_ROUTES
                                and u.lower() != target_username.lower()
                                and not u.isdigit()
                                and re.match(r'^[a-zA-Z0-9._]+$', u)
                            ):
                                collected_users.add(u)
                    except StaleElementReferenceException:
                        continue
                    except Exception:
                        continue

                new_count = len(collected_users)
                delta = new_count - prev_count

                if progress_callback:
                    progress_callback(list_type, new_count)

                if delta > 0:
                    consecutive_stalls = 0
                    if scroll_count % 3 == 0 or delta >= 10:
                        self.log(f"[{list_type}] Captured {new_count} users (+{delta})")
                else:
                    consecutive_stalls += 1

                # If stalled, attempt unstuck scrolling
                if consecutive_stalls >= max_attempts:
                    self.log(f"[{list_type}] Reached end of list or rate limit. Total collected: {new_count}")
                    break

            except Exception as e:
                self.log(f"Error during link collection: {e}")
                consecutive_stalls += 1

            # 2. Perform scrolling
            try:
                # Execute JavaScript scroll on the scrollable container inside dialog
                scrolled = self.driver.execute_script("""
                    const dialog = document.querySelector("div[role='dialog']");
                    if (!dialog) return false;
                    const scrollables = Array.from(dialog.querySelectorAll('div')).filter(el => {
                        const style = window.getComputedStyle(el);
                        return (style.overflowY === 'auto' || style.overflowY === 'scroll') && el.scrollHeight > el.clientHeight;
                    });
                    if (scrollables.length > 0) {
                        const target = scrollables[0];
                        target.scrollTop = target.scrollHeight;
                        return true;
                    }
                    return false;
                """)

                if not scrolled:
                    # Fallback to scrolling last link into view
                    if links:
                        self.driver.execute_script("arguments[0].scrollIntoView(false);", links[-1])
                    else:
                        actions = webdriver.ActionChains(self.driver)
                        actions.send_keys(Keys.PAGE_DOWN).perform()

                # If stalled, nudge scroll up slightly then down
                if consecutive_stalls == 2:
                    self.driver.execute_script("""
                        const dialog = document.querySelector("div[role='dialog']");
                        if (dialog) {
                            const scrollable = Array.from(dialog.querySelectorAll('div')).find(el => el.scrollHeight > el.clientHeight);
                            if (scrollable) scrollable.scrollTop -= 250;
                        }
                    """)
                    time.sleep(0.8)

            except Exception:
                pass

            # Random jitter to simulate natural browsing and avoid rate-limiting
            time.sleep(random.uniform(1.2, 2.0))

        self.log(f"Finished {list_type} scan: {len(collected_users)} unique users.")
        return collected_users

    def close(self):
        """Safely terminates the browser session."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            finally:
                self.driver = None


class InstaTrackerApp:
    """Tkinter Modern Desktop Application for Unfollower Analysis."""

    def __init__(self, root):
        self.root = root
        self.root.title("Instagram Unfollower Tracker Pro v2.0")
        self.root.geometry("1050x760")
        self.root.minsize(850, 600)

        # Threading and Communication
        self.log_queue = queue.Queue()
        self.progress_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.worker_thread = None
        self.active_engine = None

        # Data Cache
        self.current_results = {
            "not_following_back": set(),
            "fans": set(),
            "mutuals": set(),
            "lost_followers": set(),
            "new_followers": set(),
            "followers": set(),
            "following": set(),
        }

        # Config
        self.config = self.load_config()
        self.detected_browsers = detect_browsers()

        # Build UI
        self.setup_styles()
        self.build_ui()

        # Start periodic queue polling
        self.root.after(100, self.process_queues)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_styles(self):
        """Configure ttk styles for a modern aesthetic."""
        self.style = ttk.Style()
        try:
            self.style.theme_use('clam')
        except Exception:
            pass

        # Color Palette
        self.colors = {
            'bg_dark': '#1e1e2e',
            'bg_card': '#252538',
            'accent': '#6366f1',
            'accent_hover': '#4f46e5',
            'danger': '#ef4444',
            'success': '#10b981',
            'warning': '#f59e0b',
            'text_main': '#f8fafc',
            'text_muted': '#94a3b8',
        }

        self.style.configure('TNotebook', background='#181825')
        self.style.configure('TNotebook.Tab', padding=[14, 8], font=('Segoe UI', 10, 'bold'))
        self.style.configure('Card.TFrame', background=self.colors['bg_card'], relief='flat')

    def build_ui(self):
        """Creates the header, tabs, and layout."""
        # Top Header
        header_frame = tk.Frame(self.root, bg=self.colors['bg_dark'], height=60)
        header_frame.pack(fill='x', side='top')

        title_lbl = tk.Label(
            header_frame,
            text="⚡ Instagram Unfollower Tracker Pro",
            font=('Segoe UI', 16, 'bold'),
            fg=self.colors['text_main'],
            bg=self.colors['bg_dark']
        )
        title_lbl.pack(side='left', padx=20, pady=12)

        ver_lbl = tk.Label(
            header_frame,
            text="v2.0 • Safe Isolated Profile • Dual Analysis",
            font=('Segoe UI', 9),
            fg=self.colors['accent'],
            bg=self.colors['bg_dark']
        )
        ver_lbl.pack(side='right', padx=20, pady=12)

        # Notebook (Tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # Tab 1: Dashboard
        self.tab_dashboard = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_dashboard, text=" 📊 Dashboard & Run ")
        self.build_dashboard_tab()

        # Tab 2: Results
        self.tab_results = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_results, text=" 🎯 Analysis Results ")
        self.build_results_tab()

        # Tab 3: History
        self.tab_history = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_history, text=" 📜 History ")
        self.build_history_tab()

        # Tab 4: Settings
        self.tab_settings = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_settings, text=" ⚙️ Settings ")
        self.build_settings_tab()

    def build_dashboard_tab(self):
        """Dashboard containing setup, execution controls, progress, and logs."""
        container = tk.Frame(self.tab_dashboard, bg='#181825')
        container.pack(fill='both', expand=True, padx=10, pady=10)

        # Left Column: Inputs & Controls
        left_col = tk.Frame(container, bg='#1e1e2e', width=380, padx=15, pady=15)
        left_col.pack(side='left', fill='y', padx=(0, 10))

        tk.Label(left_col, text="Analysis Configuration", font=('Segoe UI', 12, 'bold'), fg='#ffffff', bg='#1e1e2e').pack(anchor='w', pady=(0, 12))

        # Username Input
        tk.Label(left_col, text="Target Instagram Username:", font=('Segoe UI', 9, 'bold'), fg='#94a3b8', bg='#1e1e2e').pack(anchor='w')
        self.entry_user = ttk.Entry(left_col, width=32, font=('Segoe UI', 10))
        self.entry_user.pack(fill='x', pady=(4, 10))
        if self.config.get("username"):
            self.entry_user.insert(0, self.config["username"])

        # Password Input (Optional)
        tk.Label(left_col, text="Password (Optional - for auto-login):", font=('Segoe UI', 9, 'bold'), fg='#94a3b8', bg='#1e1e2e').pack(anchor='w')
        self.entry_pass = ttk.Entry(left_col, width=32, show="*", font=('Segoe UI', 10))
        self.entry_pass.pack(fill='x', pady=(4, 6))
        if self.config.get("password"):
            self.entry_pass.insert(0, self.config["password"])

        tip_lbl = tk.Label(
            left_col,
            text="Tip: You can leave password blank and log in manually via the browser window.",
            font=('Segoe UI', 8),
            fg='#64748b',
            bg='#1e1e2e',
            wraplength=320,
            justify='left'
        )
        tip_lbl.pack(anchor='w', pady=(0, 12))

        # Browser Selector
        tk.Label(left_col, text="Browser Engine:", font=('Segoe UI', 9, 'bold'), fg='#94a3b8', bg='#1e1e2e').pack(anchor='w')
        browser_options = list(self.detected_browsers.keys()) or ['Chrome', 'Brave', 'Edge']
        self.combo_browser = ttk.Combobox(left_col, values=browser_options, state='readonly', font=('Segoe UI', 9))
        self.combo_browser.pack(fill='x', pady=(4, 12))
        
        saved_b = self.config.get("browser")
        if saved_b in browser_options:
            self.combo_browser.set(saved_b)
        elif 'Brave' in browser_options:
            self.combo_browser.set('Brave')
        elif 'Chrome' in browser_options:
            self.combo_browser.set('Chrome')
        else:
            self.combo_browser.set(browser_options[0])

        # Mode Selector
        tk.Label(left_col, text="Analysis Mode:", font=('Segoe UI', 9, 'bold'), fg='#94a3b8', bg='#1e1e2e').pack(anchor='w')
        self.combo_mode = ttk.Combobox(
            left_col,
            values=[
                "Full Analysis (Followers & Following)",
                "Followers Only",
                "Following Only"
            ],
            state='readonly',
            font=('Segoe UI', 9)
        )
        self.combo_mode.set("Full Analysis (Followers & Following)")
        self.combo_mode.pack(fill='x', pady=(4, 15))

        # Checkbox Save Config
        self.save_creds_var = tk.IntVar(value=1 if self.config.get("save_credentials", True) else 0)
        chk = tk.Checkbutton(
            left_col,
            text="Remember settings & credentials",
            variable=self.save_creds_var,
            bg='#1e1e2e',
            fg='#cbd5e1',
            activebackground='#1e1e2e',
            activeforeground='#ffffff',
            selectcolor='#0f172a'
        )
        chk.pack(anchor='w', pady=(0, 15))

        # Action Buttons
        self.btn_run = tk.Button(
            left_col,
            text="🚀 Start Full Analysis",
            command=self.start_analysis_thread,
            bg='#6366f1',
            fg='#ffffff',
            font=('Segoe UI', 11, 'bold'),
            relief='flat',
            cursor='hand2',
            pady=8
        )
        self.btn_run.pack(fill='x', pady=(0, 8))

        self.btn_manual_login = tk.Button(
            left_col,
            text="🔑 Browser Login Only",
            command=self.start_manual_login_thread,
            bg='#334155',
            fg='#ffffff',
            font=('Segoe UI', 9),
            relief='flat',
            cursor='hand2',
            pady=6
        )
        self.btn_manual_login.pack(fill='x', pady=(0, 8))

        self.btn_stop = tk.Button(
            left_col,
            text="⏹️ Cancel / Stop",
            command=self.stop_process,
            bg='#ef4444',
            fg='#ffffff',
            font=('Segoe UI', 9, 'bold'),
            relief='flat',
            cursor='hand2',
            state='disabled',
            pady=6
        )
        self.btn_stop.pack(fill='x', pady=(0, 10))

        # Right Column: Status & Live Log
        right_col = tk.Frame(container, bg='#1e1e2e', padx=15, pady=15)
        right_col.pack(side='right', fill='both', expand=True)

        # Status Bar
        status_bar = tk.Frame(right_col, bg='#1e1e2e')
        status_bar.pack(fill='x', pady=(0, 10))

        self.lbl_status = tk.Label(
            status_bar,
            text="Status: Ready",
            font=('Segoe UI', 10, 'bold'),
            fg='#38bdf8',
            bg='#1e1e2e'
        )
        self.lbl_status.pack(side='left')

        self.progress_bar = ttk.Progressbar(status_bar, mode='indeterminate', length=200)
        self.progress_bar.pack(side='right', padx=5)

        # Log Terminal
        tk.Label(right_col, text="Execution Console Logs:", font=('Segoe UI', 10, 'bold'), fg='#ffffff', bg='#1e1e2e').pack(anchor='w', pady=(0, 5))

        self.log_area = scrolledtext.ScrolledText(
            right_col,
            wrap='word',
            bg='#0f172a',
            fg='#10b981',
            insertbackground='white',
            font=('Consolas', 9),
            relief='flat',
            padx=10,
            pady=10
        )
        self.log_area.pack(fill='both', expand=True)
        self.log("Instagram Unfollower Tracker v2.0 initialized.")
        self.log(f"Isolated Browser Profile: {PROFILE_DIR}")
        self.log(f"Detected Browsers: {', '.join(self.detected_browsers.keys()) if self.detected_browsers else 'None found automatically'}")

    def build_results_tab(self):
        """Displays categorized lists, metric tiles, search filter, and export options."""
        container = tk.Frame(self.tab_results, bg='#181825', padx=10, pady=10)
        container.pack(fill='both', expand=True)

        # Metric Tiles Header
        tiles_frame = tk.Frame(container, bg='#181825')
        tiles_frame.pack(fill='x', pady=(0, 10))

        self.metric_cards = {}
        metrics_def = [
            ("not_following_back", "🚫 Not Following Back", "#ef4444"),
            ("lost_followers", "📉 Lost Followers", "#f97316"),
            ("fans", "🌟 Fans (Don't Follow)", "#06b6d4"),
            ("mutuals", "🤝 Mutual Friends", "#10b981"),
            ("new_followers", "📈 New Followers", "#8b5cf6"),
        ]

        for key, label, color in metrics_def:
            card = tk.Frame(tiles_frame, bg='#1e1e2e', padx=12, pady=8, highlightbackground=color, highlightthickness=1)
            card.pack(side='left', expand=True, fill='x', padx=4)

            lbl_t = tk.Label(card, text=label, font=('Segoe UI', 8, 'bold'), fg='#94a3b8', bg='#1e1e2e')
            lbl_t.pack(anchor='w')

            lbl_val = tk.Label(card, text="0", font=('Segoe UI', 16, 'bold'), fg=color, bg='#1e1e2e')
            lbl_val.pack(anchor='w')
            self.metric_cards[key] = lbl_val

        # Main Table Area
        table_container = tk.Frame(container, bg='#1e1e2e', padx=10, pady=10)
        table_container.pack(fill='both', expand=True)

        # Search Bar & Filter
        filter_bar = tk.Frame(table_container, bg='#1e1e2e')
        filter_bar.pack(fill='x', pady=(0, 8))

        tk.Label(filter_bar, text="View Category:", font=('Segoe UI', 9, 'bold'), fg='#ffffff', bg='#1e1e2e').pack(side='left', padx=(0, 6))
        self.combo_result_cat = ttk.Combobox(
            filter_bar,
            values=[
                "Not Following Back",
                "Lost Followers (Unfollowed You)",
                "Fans (You Don't Follow Back)",
                "Mutual Followers",
                "New Followers",
                "All Followers",
                "All Following"
            ],
            state='readonly',
            font=('Segoe UI', 9),
            width=28
        )
        self.combo_result_cat.set("Not Following Back")
        self.combo_result_cat.pack(side='left', padx=(0, 15))
        self.combo_result_cat.bind("<<ComboboxSelected>>", lambda e: self.update_results_table())

        tk.Label(filter_bar, text="🔍 Search:", font=('Segoe UI', 9, 'bold'), fg='#ffffff', bg='#1e1e2e').pack(side='left', padx=(0, 6))
        self.entry_search = ttk.Entry(filter_bar, font=('Segoe UI', 9), width=24)
        self.entry_search.pack(side='left')
        self.entry_search.bind("<KeyRelease>", lambda e: self.update_results_table())

        self.lbl_table_count = tk.Label(filter_bar, text="0 users", font=('Segoe UI', 9), fg='#38bdf8', bg='#1e1e2e')
        self.lbl_table_count.pack(side='right')

        # Treeview
        columns = ("Username", "Category", "Profile URL")
        self.tree = ttk.Treeview(table_container, columns=columns, show='headings', selectmode='extended')
        self.tree.heading("Username", text="Username")
        self.tree.heading("Category", text="Category")
        self.tree.heading("Profile URL", text="Instagram Profile URL")

        self.tree.column("Username", width=220, anchor='w')
        self.tree.column("Category", width=200, anchor='w')
        self.tree.column("Profile URL", width=420, anchor='w')

        scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Action Buttons Footer
        footer = tk.Frame(container, bg='#181825')
        footer.pack(fill='x', pady=(10, 0))

        btn_open = tk.Button(
            footer,
            text="🌐 Open in Browser",
            command=self.open_selected_profile,
            bg='#3b82f6',
            fg='#ffffff',
            font=('Segoe UI', 9, 'bold'),
            relief='flat',
            padx=10,
            pady=5,
            cursor='hand2'
        )
        btn_open.pack(side='left', padx=(0, 8))

        btn_copy = tk.Button(
            footer,
            text="📋 Copy Selected",
            command=self.copy_selected_users,
            bg='#475569',
            fg='#ffffff',
            font=('Segoe UI', 9),
            relief='flat',
            padx=10,
            pady=5,
            cursor='hand2'
        )
        btn_copy.pack(side='left', padx=(0, 8))

        btn_copy_all = tk.Button(
            footer,
            text="📋 Copy All in List",
            command=self.copy_all_users,
            bg='#475569',
            fg='#ffffff',
            font=('Segoe UI', 9),
            relief='flat',
            padx=10,
            pady=5,
            cursor='hand2'
        )
        btn_copy_all.pack(side='left', padx=(0, 8))

        btn_export_csv = tk.Button(
            footer,
            text="💾 Export CSV",
            command=self.export_csv,
            bg='#10b981',
            fg='#ffffff',
            font=('Segoe UI', 9, 'bold'),
            relief='flat',
            padx=12,
            pady=5,
            cursor='hand2'
        )
        btn_export_csv.pack(side='right', padx=(8, 0))

        btn_export_json = tk.Button(
            footer,
            text="💾 Export JSON",
            command=self.export_json,
            bg='#10b981',
            fg='#ffffff',
            font=('Segoe UI', 9, 'bold'),
            relief='flat',
            padx=12,
            pady=5,
            cursor='hand2'
        )
        btn_export_json.pack(side='right')

    def build_history_tab(self):
        """History tab showing past scans with timestamps and statistics."""
        container = tk.Frame(self.tab_history, bg='#181825', padx=10, pady=10)
        container.pack(fill='both', expand=True)

        header = tk.Frame(container, bg='#181825')
        header.pack(fill='x', pady=(0, 10))

        tk.Label(header, text="Past Analysis Scans", font=('Segoe UI', 12, 'bold'), fg='#ffffff', bg='#181825').pack(side='left')

        btn_refresh = tk.Button(
            header,
            text="🔄 Refresh",
            command=self.load_history_table,
            bg='#334155',
            fg='#ffffff',
            relief='flat',
            font=('Segoe UI', 9),
            cursor='hand2'
        )
        btn_refresh.pack(side='right', padx=(6, 0))

        btn_clear = tk.Button(
            header,
            text="🗑️ Clear History",
            command=self.clear_history,
            bg='#ef4444',
            fg='#ffffff',
            relief='flat',
            font=('Segoe UI', 9),
            cursor='hand2'
        )
        btn_clear.pack(side='right')

        cols = ("Date", "Account", "Followers", "Following", "Not Following Back", "Lost", "Gained")
        self.history_tree = ttk.Treeview(container, columns=cols, show='headings', selectmode='browse')
        for c in cols:
            self.history_tree.heading(c, text=c)
            self.history_tree.column(c, width=120, anchor='center')
        self.history_tree.column("Date", width=180, anchor='w')
        self.history_tree.column("Account", width=150, anchor='w')

        sb = ttk.Scrollbar(container, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=sb.set)
        self.history_tree.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')

        self.load_history_table()

    def build_settings_tab(self):
        """Settings tab for path overrides and folder management."""
        container = tk.Frame(self.tab_settings, bg='#181825', padx=20, pady=20)
        container.pack(fill='both', expand=True)

        card = tk.Frame(container, bg='#1e1e2e', padx=20, pady=20)
        card.pack(fill='x', pady=(0, 15))

        tk.Label(card, text="Custom Browser Path Override", font=('Segoe UI', 11, 'bold'), fg='#ffffff', bg='#1e1e2e').pack(anchor='w', pady=(0, 6))
        
        row_b = tk.Frame(card, bg='#1e1e2e')
        row_b.pack(fill='x', pady=(0, 10))
        self.entry_browser_path = ttk.Entry(row_b, font=('Segoe UI', 9))
        self.entry_browser_path.pack(side='left', fill='x', expand=True, padx=(0, 8))
        if self.config.get("custom_browser_path"):
            self.entry_browser_path.insert(0, self.config["custom_browser_path"])

        btn_browse = tk.Button(
            row_b,
            text="Browse...",
            command=self.browse_browser_path,
            bg='#334155',
            fg='#ffffff',
            relief='flat',
            cursor='hand2'
        )
        btn_browse.pack(side='right')

        # Storage & Profile Folder Operations
        card_dirs = tk.Frame(container, bg='#1e1e2e', padx=20, pady=20)
        card_dirs.pack(fill='x')

        tk.Label(card_dirs, text="Storage & Profile Management", font=('Segoe UI', 11, 'bold'), fg='#ffffff', bg='#1e1e2e').pack(anchor='w', pady=(0, 10))

        tk.Label(card_dirs, text=f"Profile Path: {PROFILE_DIR}", font=('Consolas', 8), fg='#94a3b8', bg='#1e1e2e').pack(anchor='w', pady=(0, 10))

        btn_open_prof = tk.Button(
            card_dirs,
            text="📂 Open Profile Folder",
            command=lambda: os.startfile(PROFILE_DIR) if sys.platform == 'win32' else None,
            bg='#3b82f6',
            fg='#ffffff',
            relief='flat',
            cursor='hand2',
            pady=4
        )
        btn_open_prof.pack(side='left', padx=(0, 10))

        btn_open_exp = tk.Button(
            card_dirs,
            text="📁 Open Exports Folder",
            command=lambda: os.startfile(EXPORTS_DIR) if sys.platform == 'win32' else None,
            bg='#334155',
            fg='#ffffff',
            relief='flat',
            cursor='hand2',
            pady=4
        )
        btn_open_exp.pack(side='left', padx=(0, 10))

        btn_reset_prof = tk.Button(
            card_dirs,
            text="⚠️ Reset Session Profile",
            command=self.reset_profile,
            bg='#ef4444',
            fg='#ffffff',
            relief='flat',
            cursor='hand2',
            pady=4
        )
        btn_reset_prof.pack(side='right')

    # --- LOGGING & QUEUE HANDLING ---
    def log(self, message):
        """Thread-safe logging method."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        full_msg = f"[{timestamp}] {message}"
        self.log_queue.put(full_msg)

    def process_queues(self):
        """Pulls log and progress updates from the worker thread into Tkinter."""
        while not self.log_queue.empty():
            try:
                msg = self.log_queue.get_nowait()
                self.log_area.insert(tk.END, msg + "\n")
                self.log_area.see(tk.END)
            except queue.Empty:
                break

        while not self.progress_queue.empty():
            try:
                status_text, is_busy = self.progress_queue.get_nowait()
                self.lbl_status.config(text=f"Status: {status_text}")
                if is_busy:
                    self.progress_bar.start(10)
                else:
                    self.progress_bar.stop()
            except queue.Empty:
                break

        self.root.after(100, self.process_queues)

    # --- CONFIG & HISTORY IO ---
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_config(self):
        if self.save_creds_var.get() == 1:
            self.config["username"] = self.entry_user.get().strip()
            self.config["password"] = self.entry_pass.get()
            self.config["browser"] = self.combo_browser.get()
            self.config["custom_browser_path"] = self.entry_browser_path.get().strip()
            self.config["save_credentials"] = True
        else:
            self.config = {
                "browser": self.combo_browser.get(),
                "save_credentials": False
            }
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
        except Exception:
            pass

    def load_history_data(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def save_history_snapshot(self, username, followers, following, not_following, lost, gained):
        history = self.load_history_data()
        record = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "account": username,
            "followers_count": len(followers),
            "following_count": len(following),
            "not_following_count": len(not_following),
            "lost_count": len(lost),
            "gained_count": len(gained),
            "followers": list(followers),
            "following": list(following),
        }
        history.append(record)
        try:
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=4)
        except Exception as e:
            self.log(f"History save error: {e}")

    def load_history_table(self):
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        history = self.load_history_data()
        for r in reversed(history):
            self.history_tree.insert("", "end", values=(
                r.get("timestamp", ""),
                r.get("account", ""),
                r.get("followers_count", 0),
                r.get("following_count", 0),
                r.get("not_following_count", 0),
                r.get("lost_count", 0),
                r.get("gained_count", 0)
            ))

    def clear_history(self):
        if messagebox.askyesno("Confirm", "Clear all saved analysis history?"):
            if os.path.exists(HISTORY_FILE):
                os.remove(HISTORY_FILE)
            self.load_history_table()
            self.log("History cleared.")

    # --- SETTINGS TAB ACTIONS ---
    def browse_browser_path(self):
        filename = filedialog.askopenfilename(
            title="Select Browser Executable",
            filetypes=[("Executable Files", "*.exe"), ("All Files", "*.*")]
        )
        if filename:
            self.entry_browser_path.delete(0, tk.END)
            self.entry_browser_path.insert(0, filename)

    def reset_profile(self):
        if messagebox.askyesno("Confirm Reset", "Reset browser profile? You will need to log in to Instagram again."):
            try:
                if os.path.exists(PROFILE_DIR):
                    shutil.rmtree(PROFILE_DIR, ignore_errors=True)
                os.makedirs(PROFILE_DIR, exist_ok=True)
                messagebox.showinfo("Success", "Browser profile reset successfully.")
                self.log("Browser profile has been reset.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to reset profile: {e}")

    # --- WORKER THREAD OPERATIONS ---
    def start_analysis_thread(self):
        username = self.entry_user.get().strip()
        password = self.entry_pass.get()

        if not username:
            messagebox.showerror("Error", "Please enter your Instagram username.")
            return

        self.save_config()
        self.stop_event.clear()

        self.btn_run.config(state='disabled')
        self.btn_manual_login.config(state='disabled')
        self.btn_stop.config(state='normal')

        self.worker_thread = threading.Thread(
            target=self.run_analysis_worker,
            args=(username, password, self.combo_mode.get(), self.combo_browser.get()),
            daemon=True
        )
        self.worker_thread.start()

    def start_manual_login_thread(self):
        self.save_config()
        self.stop_event.clear()

        self.btn_run.config(state='disabled')
        self.btn_manual_login.config(state='disabled')
        self.btn_stop.config(state='normal')

        self.worker_thread = threading.Thread(
            target=self.run_manual_login_worker,
            args=(self.combo_browser.get(),),
            daemon=True
        )
        self.worker_thread.start()

    def stop_process(self):
        self.stop_event.set()
        self.log("Stopping process, cleaning up browser...")
        if self.active_engine:
            self.active_engine.close()

    def run_manual_login_worker(self, browser_choice):
        self.progress_queue.put(("Opening browser for manual login...", True))
        custom_p = self.entry_browser_path.get().strip() or self.detected_browsers.get(browser_choice)
        engine = InstagramAutomation(browser_choice, custom_p, log_func=self.log)
        self.active_engine = engine

        try:
            driver = engine.start_driver()
            driver.get("https://www.instagram.com/accounts/login/")
            self.log("Browser open! Please log in to your Instagram account.")
            self.log("When you are finished logging in, you may close the browser or click Stop.")

            while not self.stop_event.is_set():
                if engine.check_is_logged_in(timeout=2):
                    self.log("Active login detected! Session is saved to isolated profile.")
                    break
                time.sleep(1)

        except Exception as e:
            self.log(f"Browser error: {e}")
        finally:
            engine.close()
            self.active_engine = None
            self.progress_queue.put(("Ready", False))
            self.root.after(0, self.reset_buttons)

    def run_analysis_worker(self, username, password, mode, browser_choice):
        self.progress_queue.put(("Initializing browser...", True))
        custom_p = self.entry_browser_path.get().strip() or self.detected_browsers.get(browser_choice)
        engine = InstagramAutomation(browser_choice, custom_p, log_func=self.log)
        self.active_engine = engine

        followers = set()
        following = set()

        try:
            driver = engine.start_driver()
            driver.get("https://www.instagram.com/")
            time.sleep(3)

            # Check Login
            if not engine.check_is_logged_in(timeout=5):
                if password:
                    self.progress_queue.put(("Logging in...", True))
                    logged_in = engine.perform_login(username, password)
                    if not logged_in:
                        self.log("Login could not be verified automatically.")
                        self.log("Please ensure 2FA challenges are completed if prompted.")
                else:
                    self.log("No password provided. Waiting for manual login in browser window (up to 45s)...")
                    for _ in range(45):
                        if self.stop_event.is_set():
                            break
                        if engine.check_is_logged_in(timeout=2):
                            break
                        time.sleep(1)

            if self.stop_event.is_set():
                return

            # Scrape Following
            if "Following" in mode:
                self.progress_queue.put(("Scraping Following list...", True))
                following = engine.extract_users_from_modal(
                    username,
                    "following",
                    progress_callback=lambda t, n: self.progress_queue.put((f"Scraping following ({n} found)...", True)),
                    stop_event=self.stop_event
                )

            if self.stop_event.is_set():
                return

            # Scrape Followers
            if "Followers" in mode:
                self.progress_queue.put(("Scraping Followers list...", True))
                followers = engine.extract_users_from_modal(
                    username,
                    "followers",
                    progress_callback=lambda t, n: self.progress_queue.put((f"Scraping followers ({n} found)...", True)),
                    stop_event=self.stop_event
                )

            if self.stop_event.is_set():
                return

            # Compute Analytics
            self.progress_queue.put(("Analyzing results...", True))
            self.compute_and_display_results(username, followers, following)

        except Exception as e:
            self.log(f"Fatal Analysis Error: {e}")
            traceback.print_exc()
            self.root.after(0, lambda: messagebox.showerror("Analysis Error", str(e)))
        finally:
            engine.close()
            self.active_engine = None
            self.progress_queue.put(("Ready", False))
            self.root.after(0, self.reset_buttons)

    def reset_buttons(self):
        self.btn_run.config(state='normal')
        self.btn_manual_login.config(state='normal')
        self.btn_stop.config(state='disabled')

    def compute_and_display_results(self, username, current_followers, current_following):
        """Calculates differences, updates metric badges and table."""
        # Find past run for comparison
        history = self.load_history_data()
        past_record = None
        for r in reversed(history):
            if r.get("account", "").lower() == username.lower():
                past_record = r
                break

        past_followers = set(past_record.get("followers", [])) if past_record else set()

        not_following = current_following - current_followers
        fans = current_followers - current_following
        mutuals = current_followers & current_following
        lost_followers = past_followers - current_followers if past_followers else set()
        new_followers = current_followers - past_followers if past_followers else set()

        self.current_results = {
            "not_following_back": not_following,
            "fans": fans,
            "mutuals": mutuals,
            "lost_followers": lost_followers,
            "new_followers": new_followers,
            "followers": current_followers,
            "following": current_following,
        }

        # Save snapshot to history
        self.save_history_snapshot(username, current_followers, current_following, not_following, lost_followers, new_followers)

        # Update UI Elements on Main Thread
        def update_gui():
            self.metric_cards["not_following_back"].config(text=str(len(not_following)))
            self.metric_cards["lost_followers"].config(text=str(len(lost_followers)))
            self.metric_cards["fans"].config(text=str(len(fans)))
            self.metric_cards["mutuals"].config(text=str(len(mutuals)))
            self.metric_cards["new_followers"].config(text=str(len(new_followers)))

            self.update_results_table()
            self.load_history_table()
            self.notebook.select(self.tab_results)

            summary = (
                f"Analysis Complete for @{username}!\n\n"
                f"• Not Following Back: {len(not_following)}\n"
                f"• Fans (Don't Follow): {len(fans)}\n"
                f"• Mutual Friends: {len(mutuals)}\n"
                f"• Lost Followers: {len(lost_followers)}\n"
                f"• New Followers: {len(new_followers)}"
            )
            self.log(summary)
            messagebox.showinfo("Analysis Complete", summary)

        self.root.after(0, update_gui)

    def update_results_table(self):
        """Populates the Treeview based on category selection and search query."""
        category_map = {
            "Not Following Back": ("not_following_back", "Not Following Back"),
            "Lost Followers (Unfollowed You)": ("lost_followers", "Lost Follower"),
            "Fans (You Don't Follow Back)": ("fans", "Fan"),
            "Mutual Followers": ("mutuals", "Mutual Friend"),
            "New Followers": ("new_followers", "New Follower"),
            "All Followers": ("followers", "Follower"),
            "All Following": ("following", "Following"),
        }

        selected_cat_name = self.combo_result_cat.get()
        key, cat_label = category_map.get(selected_cat_name, ("not_following_back", "Not Following Back"))
        users = sorted(list(self.current_results.get(key, set())))

        search_query = self.entry_search.get().strip().lower()
        if search_query:
            users = [u for u in users if search_query in u.lower()]

        for item in self.tree.get_children():
            self.tree.delete(item)

        for u in users:
            self.tree.insert("", "end", values=(u, cat_label, f"https://www.instagram.com/{u}/"))

        self.lbl_table_count.config(text=f"{len(users)} users")

    def open_selected_profile(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Notice", "Please select a user from the list first.")
            return
        for item in selected:
            vals = self.tree.item(item, "values")
            if len(vals) >= 3:
                webbrowser.open(vals[2])

    def copy_selected_users(self):
        selected = self.tree.selection()
        if not selected:
            return
        names = [self.tree.item(item, "values")[0] for item in selected]
        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(names))
        messagebox.showinfo("Copied", f"Copied {len(names)} username(s) to clipboard.")

    def copy_all_users(self):
        children = self.tree.get_children()
        names = [self.tree.item(item, "values")[0] for item in children]
        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(names))
        messagebox.showinfo("Copied", f"Copied {len(names)} username(s) to clipboard.")

    def export_csv(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_file = os.path.join(EXPORTS_DIR, f"instagram_analysis_{timestamp}.csv")

        try:
            with open(target_file, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(["Username", "Category", "Profile URL"])

                for cat_key, label in [
                    ("not_following_back", "Not Following Back"),
                    ("lost_followers", "Lost Follower"),
                    ("fans", "Fan"),
                    ("mutuals", "Mutual"),
                    ("new_followers", "New Follower")
                ]:
                    for u in sorted(list(self.current_results.get(cat_key, set()))):
                        writer.writerow([u, label, f"https://www.instagram.com/{u}/"])

            messagebox.showinfo("Export Successful", f"Exported results to:\n{target_file}")
            self.log(f"Exported CSV: {target_file}")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))

    def export_json(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_file = os.path.join(EXPORTS_DIR, f"instagram_analysis_{timestamp}.json")

        export_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "not_following_back": sorted(list(self.current_results.get("not_following_back", set()))),
            "lost_followers": sorted(list(self.current_results.get("lost_followers", set()))),
            "fans": sorted(list(self.current_results.get("fans", set()))),
            "mutuals": sorted(list(self.current_results.get("mutuals", set()))),
            "new_followers": sorted(list(self.current_results.get("new_followers", set()))),
        }

        try:
            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=4)
            messagebox.showinfo("Export Successful", f"Exported results to:\n{target_file}")
            self.log(f"Exported JSON: {target_file}")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))

    def on_closing(self):
        if self.worker_thread and self.worker_thread.is_alive():
            if messagebox.askyesno("Exit", "An analysis is currently running. Cancel and exit?"):
                self.stop_process()
                self.root.destroy()
        else:
            self.root.destroy()


def main():
    root = tk.Tk()
    app = InstaTrackerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
