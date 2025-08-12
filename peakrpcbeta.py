from pathlib import Path
import platform
from pypresence import Presence
from PIL import Image
import tkinter as tk
from tkinter import messagebox, Tk
import subprocess
import threading
import sys
import os
import io
from datetime import datetime
import json
import webbrowser
import base64
import time
import re
import requests
import glob
import traceback
from dotenv import load_dotenv

load_dotenv()

class TeeOutput:
    def __init__(self, *streams):
        self.streams = [s for s in streams if s is not None]

    def write(self, data):
        for s in self.streams:
            try:
                s.write(data)
            except Exception:
                pass  # ignore if a stream is somehow invalid during runtime

    def flush(self):
        for s in self.streams:
            try:
                s.flush()
            except Exception:
                pass

log_buffer = io.StringIO()
original_stdout = sys.stdout if sys.stdout is not None else io.StringIO()
original_stderr = sys.stderr if sys.stderr is not None else io.StringIO()
sys.stdout = TeeOutput(original_stdout, log_buffer)
sys.stderr = TeeOutput(original_stderr, log_buffer)

def global_exception_handler(exc_type, exc_value, exc_traceback):
    print("[DEBUG] Exception hook triggered")
    print(f"[FATAL ERROR] Unhandled exception: {exc_value}")
    sys.stdout = original_stdout
    sys.stderr = original_stderr

    log_path = save_log_to_file()

    traceback.print_exception(exc_type, exc_value, exc_traceback)

    try:
        # Try showing the messagebox using existing root if already created
        if tk._default_root:
            messagebox.showerror("Unhandled Error", f"An error occurred.\nLog saved at:\n{log_path}")
        else:
            # Create a temporary root for messagebox
            root = Tk()
            root.withdraw()
            messagebox.showerror("Unhandled Error", f"An error occurred.\nLog saved at:\n{log_path}")
            root.destroy()
    except Exception as e:
        print(f"[!] Could not show popup, but log saved at: {log_path} | Error: {e}")

def patched_report_callback_exception(self, exc, val, tb):
    global_exception_handler(exc, val, tb)

tk.Tk.report_callback_exception = patched_report_callback_exception

sys.excepthook = global_exception_handler

def thread_exception_handler(args):
    global_exception_handler(args.exc_type, args.exc_value, args.exc_traceback)

threading.excepthook = thread_exception_handler

def save_log_to_file():
    log_buffer.flush()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Use a user Documents folder when packaged
    if getattr(sys, 'frozen', False):  # PyInstaller bundle check
        log_dir = Path.home() / "Documents" / "PeakRPC_Logs"
    else:
        log_dir = Path("error_logs")

    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / f"error_{timestamp}.log"
    with open(path, "w", encoding="utf-8") as f:
        f.write(log_buffer.getvalue())

    log_buffer.close()
    print(f"[LOG] Saving error log to: {path}")
    print(f"[LOG] Full absolute path: {path.resolve()}")

    # --- Add this for step 4 ---
    if platform.system() == "Windows":
        try:
            os.startfile(path.resolve())  # Opens the log file automatically
        except Exception as e:
            print(f"[LOG] Could not open log file automatically: {e}")

    return str(path)

class ShutdownDetected(Exception):
    """Raised when 'ShutdownInProgress' is found in the log."""
    pass



def save_config():
    pass

def start_rpc():
    client_id = os.getenv("CLIENT_ID")
    print(client_id)
    log_candidates = glob.glob(os.path.expandvars(r"%USERPROFILE%\AppData\LocalLow\LandCrab\PEAK\Player.log"))

    if not log_candidates:
        print("[ERROR] Could not find Player.log")
    else:
        log_path = log_candidates[0]

    # Global state tracking
    img_url = None
    last_state = None
    start_time = int(time.time())
    max_player_count = 0  # start with 1 as default
    player_list = []
    player_name = "Unknown"
    statekey = 0
    character_uploaded = False
    character_image_url = None
    char_attrs = {
        "color": 0,
        "eyes": 0,
        "mouth": 0,
        "accessory": 0,
        "outfit": 0,
        "hat": 0
    }
    # Deux boutons fixes pour la Rich Presence
    buttons = [
        {
            "label": "Buy the game here",
            "url": "https://store.steampowered.com/app/3527290/PEAK/"
        },
        {
            "label": "Project GitHub",
            "url": "https://github.com/h3pha/PEAK-Discord-RPC"
        }
    ]

    def resource_path(relative_path):
        """ Get absolute path to resource, works for dev and PyInstaller """
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)

    RPC = Presence(client_id)
    try:
        print("[LOG] Attempting to connect to Discord RPC...")
        RPC.connect()
    except Exception as e:
        print(f"[ERROR] Could not connect to Discord RPC: {e}")
        exit(1)

    # Rendre l'utilisation du webhook Discord optionnelle
    webhook_url = os.getenv("WEBHOOK_URL")

    def launch_peak_game():
        try:
            subprocess.Popen([
                r"C:\Program Files (x86)\Steam\steam.exe",
                "-applaunch", "3527290", "-force-d3d12"
            ])
            print("[LOG] PEAK launched via Steam with DX12(Note: Broken and will launch with Vulkan unless you launched with DX12 through Steam or PEAK creators update game).")
        except Exception as e:
            print(f"[ERROR] Failed to launch PEAK: {e}")

    def wait_for_log_refresh(log_path, timeout=30):
        print("[LOG] Waiting for Player.log to refresh...")
        start_time = time.time()
        try:
            initial_mtime = os.path.getmtime(log_path)
        except FileNotFoundError:
            initial_mtime = 0

        while time.time() - start_time < timeout:
            if os.path.exists(log_path):
                new_mtime = os.path.getmtime(log_path)
                if new_mtime > initial_mtime:
                    print("[LOG] Player.log has been refreshed.")
                    min_lines = 30
                    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                    if len(lines) >= min_lines:
                        nonlocal character_uploaded
                        nonlocal char_attrs
                        nonlocal player_name
                        nonlocal max_player_count
                        nonlocal player_list
                        nonlocal statekey
                        nonlocal key_to_state
                        nonlocal last_state
                        nonlocal img_url
                        print("[LOG] Starting Player.log simulation:")
                        print(f"[LOG] Player.log simulation ready with {len(lines)} lines.")
                        for line in lines:
                            if "ShutdownInProgress" in line:
                                raise ShutdownDetected()
                            if not character_uploaded:
                                if "color:" in line:
                                    char_attrs["color"] = int(line.split(":")[-1])
                                elif "eyes:" in line:
                                    char_attrs["eyes"] = int(line.split(":")[-1])
                                elif "Mouth:" in line:
                                    char_attrs["mouth"] = int(line.split(":")[-1])
                                elif "Accessory:" in line:
                                    char_attrs["accessory"] = int(line.split(":")[-1])
                                elif "outfit:" in line:
                                    char_attrs["outfit"] = int(line.split(":")[-1])
                                elif "Hat:" in line:
                                    char_attrs["hat"] = int(line.split(":")[-1])
                            if player_name == "Unknown":
                                if "Setting Player Data for:" in line:
                                    match = re.search(r"Setting Player Data for:\s*(.+)", line)
                                    if match:
                                        player_name = match.group(1).strip()
                                        print(f"[LOG] Detected player name: {player_name}")
                            if "Initialized with name:" in line:
                                match = re.search(r"Initialized with name:\s*(\w+)", line)
                                if match:
                                    player_name = match.group(1)
                                    print(f"[LOG] Detected player name: {player_name}")
                                max_player_count = 1  # reset counter when a new session starts
                                player_list.clear()
                                if player_name not in player_list:
                                    player_list.append(player_name)
                                character_uploaded = False

                            match1 = re.search(r"There are (\d+) Players\.", line)
                            match2 = re.search(r"Characters in radius:\s*(\d+)", line)
                            match3 = re.search(r"Registering Player object for (.+?) *:", line)
                            if match1:
                                count = int(match1.group(1))
                                if count > max_player_count:
                                    max_player_count = count
                            elif match2:
                                count = int(match2.group(1))
                                if count > max_player_count:
                                    max_player_count = count
                            elif match3:
                                player_name_temp = str(match3.group(1))
                                if player_name_temp not in player_list:
                                    print(f"[LOG] Adding player: {player_name_temp}")
                                    player_list.append(player_name_temp)
                                    max_player_count = len(player_list)
                                if statekey == 1:
                                    update_presence("Airport", player_name, img_url)

                            if "SETTING FADE OUT:" in line and not character_uploaded:
                                print("[LOG] Detected Run Started — generating character image.")
                                character_image_path = generate_character_image(
                                    char_attrs["color"],
                                    char_attrs["eyes"],
                                    char_attrs["mouth"],
                                    char_attrs["accessory"],
                                    char_attrs["outfit"],
                                    char_attrs["hat"]
                                )
                                character_image_url = upload_to_discord_webhook(character_image_path, "https://discord.com/api/webhooks/1392849874063462420/SuGoCMMgW3mo-aEDjL5XQ2g2Q6abopfDjUpGJPT2SXcuaVFRBStaNI2HeWJjUKbjkV1l", player_name)
                                character_uploaded = True
                                img_url = upload_to_catbox(character_image_path)
                            statekey = get_state_from_line(line,statekey)
                            state = key_to_state[statekey]
                            if state and state != last_state:
                                last_state = state
                                update_presence(state, player_name, img_url)
                        print("[LOG] Ending Player.log simulation.")
                    return True
            time.sleep(0.5)

        print("[ERROR] Player.log did not refresh within timeout.")
        return False

    def upload_to_catbox(file_path):
        url = "https://catbox.moe/user/api.php"
        files = {'fileToUpload': open(file_path, 'rb')}
        data = {
            'reqtype': 'fileupload'
        }

        try:
            response = requests.post(url, files=files, data=data)
            if response.status_code == 200:
                direct_url = response.text.strip()
                print(f"[Catbox.moe] Upload successful: {direct_url}")
                return direct_url
            else:
                print(f"[Catbox.moe] Upload failed with status code: {response.status_code}")
                print(response.text)
                return None
        except Exception as e:
            print(f"[Catbox.moe] Error uploading: {e}")
            return None

    def upload_to_discord_webhook(image_path, webhook_url, player_name):
        with open(image_path, 'rb') as f:
            files = {
                'file': (os.path.basename(image_path), f)
            }
            payload = {
                'content': f'Character image for **{player_name}**'
            }
            response = requests.post(webhook_url, data={'payload_json': json.dumps(payload)}, files=files)

        if response.status_code == 204:
            print("[LOG] Uploaded to Discord successfully (no response body).")
            return None  # Discord doesn't return a URL here
        elif response.status_code == 200:
            try:
                data = response.json()
                attachment_url = data['attachments'][0]['url']
                print(f"[LOG] Image URL: {attachment_url}")
                return attachment_url
            except Exception as e:
                print(f"[ERROR] Could not parse response JSON: {e}")
                return None
        else:
            print(f"[ERROR] Failed to upload: {response.status_code} — {response.text}")
            return None

    def generate_character_image(color, eyes, mouth, accessory, outfit, hat, output_filename="character.png"):
        base_path = resource_path("assets")
        output_dir = os.path.expandvars(r"%USERPROFILE%\Documents\PeakRPC_Logs")
        os.makedirs(output_dir, exist_ok=True)

        output_path = os.path.join(output_dir, output_filename)

        hatr = str(hat)
        if hat == 0 or hat == 1:
            hatr = f"{hat}_{outfit}"

        layers = [
            f"{base_path}/color/color_{color}.png",
            f"{base_path}/eyes/eyes_{eyes}.png",
            f"{base_path}/mouth/mouth_{mouth}.png",
            f"{base_path}/accessory/accessory_{accessory}.png",
            f"{base_path}/outfit/outfit_{outfit}.png",
            f"{base_path}/hat/hat_{hatr}.png"
        ]

        for layer in layers:
            if not os.path.exists(layer):
                print(f"[Log] Missing file: {layer}")
                return None # Exit the function early

        base = Image.open(layers[0]).convert("RGBA")
        for layer_path in layers[1:]:
            layer = Image.open(layer_path).convert("RGBA")
            base = Image.alpha_composite(base, layer)

        base.save(output_path)
        return output_path

    # Map each state to an image asset key
    state_to_image = {
        "Menu": "menu_logo",
        "Airport": "airport_logo",
        "Shores": "shores_logo",
        "Tropics": "tropics_logo",
        "Alpine": "alpine_logo",
        "Caldera": "caldera_logo",
        "Kiln": "kiln_logo"
    }
    key_to_state = {
        0: "Menu",
        1: "Airport",
        2: "Shores",
        3: "Tropics",
        4: "Alpine",
        5: "Caldera",
        6: "Kiln"
    }



    def tail_file(path):
        with open(path, 'r', encoding='utf-8') as file:
            file.seek(0, 2)  # move to end
            while True:
                line = file.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                yield line.strip()

    def get_state_from_line(line, statekey):
        if "Creating morale boost" in line:
            return statekey + 1
        elif "Initialized with name:" in line:
            return 0  # Menu
        elif "Update current scene: Airport" in line or ": Airport" in line:
            max_player_count = 1  # reset counter when a new session starts
            player_list.clear()
            if player_name not in player_list and player_name != "Unknown":
                player_list.append(player_name)
            character_uploaded = False
            return 1  # Airport
        elif "SETTING FADE OUT: 1" in line:
            return 2  # Shores
        elif "Spawning items in Jungle_Campfire" in line:
            return 3  # Tropics (host only)
        elif "Spawning items in Snow_Campfire" in line:
            return 4  # Alpine (host only)
        elif "NO CAMPFIRE SEGMENT" in line:
            return 5  # Caldera (host only)
        return statekey  # No change if nothing matches

    def update_presence(state, player_name, img_url):
        global start_time
        start_time = int(time.time())
        image_key = state_to_image.get(state, "peak_logo")
        print(f"[RPC] Updating presence: In {state}")
        playing = "On a Solo Expedition"
        if max_player_count > 1:
            playing = "In a Party ("+str(max_player_count)+" of 4)"
        RPC.update(
            details=f"In the {state}",
            state=playing,
            start=start_time,
            large_image=image_key,
            large_text=state,
            small_image=img_url,
            small_text=player_name,
            buttons=buttons if buttons else None  # Only add buttons if list is not empty
        )

    # Monitor the log
    launch_peak_game()

    if not wait_for_log_refresh(log_path):
        sys.exit(1)
    try:
        print("[LOG] Watching Player.log for scene changes...")
        for line in tail_file(log_path):
            if "ShutdownInProgress" in line:
                raise ShutdownDetected()
            if not character_uploaded:
                if "color:" in line:
                    char_attrs["color"] = int(line.split(":")[-1])
                elif "eyes:" in line:
                    char_attrs["eyes"] = int(line.split(":")[-1])
                elif "Mouth:" in line:
                    char_attrs["mouth"] = int(line.split(":")[-1])
                elif "Accessory:" in line:
                    char_attrs["accessory"] = int(line.split(":")[-1])
                elif "outfit:" in line:
                    char_attrs["outfit"] = int(line.split(":")[-1])
                elif "Hat:" in line:
                    char_attrs["hat"] = int(line.split(":")[-1])
            if player_name == "Unknown":
                if "Setting Player Data for:" in line:
                    match = re.search(r"Setting Player Data for:\s*(.+)", line)
                    if match:
                        player_name = match.group(1).strip()
                        print(f"[LOG] Detected player name: {player_name}")
            if "Initialized with name:" in line:
                match = re.search(r"Initialized with name:\s*(\w+)", line)
                if match:
                    player_name = match.group(1)
                    print(f"[LOG] Detected player name: {player_name}")
                max_player_count = 1  # reset counter when a new session starts
                player_list.clear()
                if player_name not in player_list:
                    player_list.append(player_name)
                character_uploaded = False

            match1 = re.search(r"There are (\d+) Players\.", line)
            match2 = re.search(r"Characters in radius:\s*(\d+)", line)
            match3 = re.search(r"Registering Player object for (.+?) *:", line)
            if match1:
                count = int(match1.group(1))
                if count > max_player_count:
                    max_player_count = count
            elif match2:
                count = int(match2.group(1))
                if count > max_player_count:
                    max_player_count = count
            elif match3:
                player_name_temp = str(match3.group(1))
                if player_name_temp not in player_list:
                    print(f"[LOG] Adding player: {player_name_temp}")
                    player_list.append(player_name_temp)
                    max_player_count = len(player_list)
                if statekey == 1:
                   update_presence("Airport", player_name, img_url)

            if "SETTING FADE OUT:" in line and not character_uploaded:
                print("[LOG] Detected Run Started — generating character image.")
                character_image_path = generate_character_image(
                    char_attrs["color"],
                    char_attrs["eyes"],
                    char_attrs["mouth"],
                    char_attrs["accessory"],
                    char_attrs["outfit"],
                    char_attrs["hat"]
                )
                if webhook_url and webhook_url != "None":
                    character_image_url = upload_to_discord_webhook(character_image_path, webhook_url, player_name)
                else:
                    character_image_url = None
                character_uploaded = True
                img_url = upload_to_catbox(character_image_path)
            statekey = get_state_from_line(line,statekey)
            state = key_to_state[statekey]
            if state and state != last_state:
                last_state = state
                update_presence(state, player_name, img_url)
    except ShutdownDetected:
        print("[LOG] Shutdown detected. Stopping presence updates.")

def show_log_window():
    log_content = log_buffer.getvalue()
    log_win = tk.Tk()
    log_win.title("PEAK Discord RPC Logs")
    log_win.geometry("700x500")
    text = tk.Text(log_win, wrap="word")
    text.insert("1.0", log_content)
    text.config(state="disabled")
    text.pack(expand=True, fill="both")
    tk.Button(log_win, text="Fermer", command=log_win.destroy).pack(pady=10)
    log_win.mainloop()

def launch_and_show_log():
    save_config()
    window.destroy()
    try:
        start_rpc()
    finally:
        show_log_window()

window = tk.Tk()
window.title("PEAK Discord RPC Launcher")
window.geometry("400x200")
window.resizable(False, False)
tk.Label(window, text="PEAK Discord RPC", font=("Helvetica", 18)).pack(pady=10)
tk.Button(window, text="Start", font=("Helvetica", 14), width=20, command=launch_and_show_log).pack(pady=40)
try:
    window.mainloop()
except Exception:
    global_exception_handler(*sys.exc_info())
