import tkinter as tk
from tkinter import messagebox, scrolledtext
import json
import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- SETTINGS ---
DB_FILE = "followers_db.json"
CONFIG_FILE = "config.json"
# Windows username is fetched dynamically (Brave User Data path)
DEFAULT_USER_DATA = os.path.join(os.environ['LOCALAPPDATA'], r"BraveSoftware\Brave-Browser\User Data")
BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe" 

class InstaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Instagram Tracker (Pro Edition)")
        self.root.geometry("600x650")

        # Load config
        self.config = self.load_config()

        tk.Label(root, text="Username:").pack(pady=5)
        self.entry_user = tk.Entry(root, width=40)
        self.entry_user.pack(pady=5)
        
        # Fill in saved username if exists
        if self.config.get("username"):
            self.entry_user.insert(0, self.config["username"])

        tk.Label(root, text="Password:").pack(pady=5)
        self.entry_pass = tk.Entry(root, width=40, show="*")
        self.entry_pass.pack(pady=5)
        
        # Fill in saved password if exists
        if self.config.get("password"):
            self.entry_pass.insert(0, self.config["password"])

        # Checkbox variable
        self.save_creds_var = tk.IntVar(value=1) 
        tk.Checkbutton(root, text="Save Credentials to Config File", variable=self.save_creds_var).pack(pady=5)

        self.btn_run = tk.Button(root, text="Start Analysis", command=self.start_process, bg="red", fg="white")
        self.btn_run.pack(pady=20)

        tk.Label(root, text="Process Logs:").pack()
        self.log_area = scrolledtext.ScrolledText(root, width=70, height=15, bg="black", fg="#00ff00")
        self.log_area.pack(pady=10)

        self.log("System ready. Config loaded.")

    def log(self, message):
        timestamp = datetime.now().strftime('%H:%M:%S')
        full_msg = f"[{timestamp}] {message}\n"
        self.log_area.insert(tk.END, full_msg)
        self.log_area.see(tk.END)
        self.root.update()
        print(full_msg)

    # --- HELPER FUNCTIONS ---
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_config_file(self, username, password):
        self.config["username"] = username
        self.config["password"] = password
        if "brave_path" not in self.config:
            self.config["brave_path"] = BRAVE_PATH
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=4)
    # --------------------------------------

    def load_old_data(self):
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
            except:
                return set()
        return set()

    def save_data(self, data_set):
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(data_set), f, ensure_ascii=False, indent=4)

    def scroll_follower_modal(self, driver, container, log_callback, max_attempts=5, safety_limit=60):
        """
        STRATEGY: Instead of scrolling the container, use 'scrollIntoView' on the last found element.
        This method works even if Instagram changes its div structure.
        """
        attempts = 0
        scroll_iterations = 0
        loaded_hrefs = set()
        
        log_callback("Smart Scroll (Element-Focused) starting...")
        
        while True:
            scroll_iterations += 1
            
            try:
                # Find all user links in the dialog
                user_links = driver.find_elements(By.XPATH, "//div[@role='dialog']//a[contains(@href, '/') and not(contains(@href, '/p/'))]")
                
                if user_links:
                    # Select the LAST element
                    last_user = user_links[-1]
                    # Bring the last element into view (triggers loading of new elements)
                    driver.execute_script("arguments[0].scrollIntoView(false);", last_user)
                else:
                    # Fallback to page down key if links aren't found yet
                    actions = webdriver.ActionChains(driver)
                    actions.send_keys(Keys.PAGE_DOWN).perform()

            except Exception as e:
                pass

            # Wait for content to load (mimics human behavior)
            time.sleep(2)
            
            try:
                # Re-count elements
                current_links = driver.find_elements(By.XPATH, "//div[@role='dialog']//a[contains(@href, '/') and not(contains(@href, '/p/'))]")
                
                current_hrefs = set()
                for link in current_links:
                    try:
                        href = link.get_attribute('href')
                        if href:
                            current_hrefs.add(href)
                    except:
                        pass
                
                new_users = len(current_hrefs - loaded_hrefs)
                
                if new_users > 0:
                    loaded_hrefs.update(current_hrefs)
                    attempts = 0
                    log_callback(f"Loaded {new_users} new users. Total: {len(loaded_hrefs)}")
                else:
                    attempts += 1
                    log_callback(f"No new data. Attempt: {attempts}/{max_attempts}")
                    
                    # If stuck, try scrolling slightly up and then down to trigger loading
                    if attempts == 2 and user_links:
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", user_links[-1])
                        time.sleep(1)

            except Exception as e:
                log_callback(f"Counting error: {e}")
                attempts += 1
            
            # --- Exit Conditions ---
            if attempts >= max_attempts:
                log_callback(f"Reached end of list. Captured {len(loaded_hrefs)} users.")
                break
                
            if scroll_iterations >= safety_limit:
                log_callback(f"Safety limit exceeded.")
                break
        
        return loaded_hrefs

    def start_process(self):
        username = self.entry_user.get()
        password = self.entry_pass.get()

        if not username:
            messagebox.showerror("Error", "Username is required.")
            return

        # Save credentials
        if self.save_creds_var.get() == 1:
            self.save_config_file(username, password)

        self.log("System cleaning... (Closing open Brave instances)")
        try:
            # Force close Brave (Windows)
            os.system("taskkill /F /IM brave.exe /T >nul 2>&1")
            time.sleep(2) # Wait for file lock to release
        except:
            pass

        self.log("Starting Brave browser (Profile Mode)...")
        
        options = webdriver.ChromeOptions()
        options.binary_location = BRAVE_PATH 
        options.add_argument("--disable-notifications")
        options.add_argument("--window-size=1000,900")
        
        # --- CRITICAL SETTINGS (TO PREVENT CRASHES) ---
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--remote-debugging-port=9222") # Prevents port conflicts
        
        # --- Profile Usage ---
        if os.path.exists(DEFAULT_USER_DATA):
            options.add_argument(f"--user-data-dir={DEFAULT_USER_DATA}")
            options.add_argument("--profile-directory=Default")
            self.log("Connecting to existing Brave profile...")
        else:
            self.log("WARNING: Brave profile not found, opening temporary profile.")

        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            service = Service(ChromeDriverManager(driver_version="143.0.7499.146").install())
            driver = webdriver.Chrome(service=service, options=options)
            wait = WebDriverWait(driver, 15)

            self.log("Navigating to Instagram...")
            driver.get("https://www.instagram.com/")
            time.sleep(5)

            # --- Session Control ---
            is_logged_in = False
            try:
                # Look for icons visible after login
                wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(@aria-label, 'Ana Sayfa') or contains(@aria-label, 'Home') or contains(@aria-label, 'Search') or @href='/']")))
                self.log("Already logged in. Skipping login screen.")
                is_logged_in = True
            except:
                self.log("Session does not appear active. Attempting login...")

            if not is_logged_in:
                if not password:
                    messagebox.showerror("Error", "Session not active and no password provided!")
                    driver.quit()
                    return

                self.log("Logging in...")
                try:
                    # Handle cookie popup if it exists
                    try:
                        cookie_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Allow all cookies' or text()='Tüm çerezlere izin ver']")))
                        cookie_btn.click()
                    except: pass

                    user_input = wait.until(EC.presence_of_element_located((By.NAME, "username")))
                    user_input.clear()
                    user_input.send_keys(username)
                    
                    pass_input = driver.find_element(By.NAME, "password")
                    pass_input.clear()
                    pass_input.send_keys(password)
                    
                    login_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
                    driver.execute_script("arguments[0].click();", login_btn)
                    
                    time.sleep(8)
                except Exception as e:
                    self.log(f"Login error: {e}")
                    driver.quit()
                    return

            self.log(f"Navigating to profile: {username}...")
            driver.get(f"https://www.instagram.com/{username}/")
            time.sleep(5)

            self.log("Clicking followers button...")
            try:
                followers_link = wait.until(EC.element_to_be_clickable((By.XPATH, f"//a[contains(@href, '/followers/')]")))
                followers_link.click()
                self.log("Followers modal opened")
            except:
                self.log("Button not found, navigating via URL...")
                driver.get(f"https://www.instagram.com/{username}/followers/")
            
            time.sleep(4)
            
            # --- Scroll Start ---
            self.log("Loading all followers...")
            all_hrefs = self.scroll_follower_modal(driver, None, self.log)
            
            self.log(f"Found {len(all_hrefs)} total links. Processing names...")
            
            current_followers = set()
            for href in all_hrefs:
                if href and f"instagram.com/{username}/" not in href and '/p/' not in href:
                    parts = href.strip('/').split('/')
                    if len(parts) >= 2:
                        u_name = parts[-1] if parts[-1] else parts[-2]
                        if u_name and u_name != username and not u_name.isdigit():
                            current_followers.add(u_name)
            
            self.log(f"Cleaned follower count: {len(current_followers)}")
            
            old_followers = self.load_old_data()
            
            if not old_followers:
                self.log("--- FIRST RECORD ---")
                self.save_data(current_followers)
                self.log(f"{len(current_followers)} followers saved.")
            else:
                unfollowers = old_followers - current_followers
                new_followers = current_followers - old_followers
                
                self.log("--- RESULTS ---")
                if unfollowers:
                    self.log(f"!!! UNFOLLOWERS ({len(unfollowers)}) !!!")
                    for user in list(unfollowers):
                        self.log(f"  → {user}")
                else:
                    self.log("No one has unfollowed.")
                
                if new_followers:
                    self.log(f"NEW FOLLOWERS ({len(new_followers)})")
                    for user in list(new_followers):
                        self.log(f"  + {user}")
                
                self.save_data(current_followers)

            messagebox.showinfo("Success", f"Operation complete! Analyzed {len(current_followers)} followers.")

        except Exception as e:
            self.log(f"CRITICAL ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Error during process: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = InstaApp(root)
    root.mainloop()