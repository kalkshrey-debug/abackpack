from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import re
import socket
import subprocess
import sys
from urllib.parse import unquote
import qrcode

# Enable ANSI colors in Windows CMD/Terminal
os.system("")

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

PORT = 8765
CURRENT_DEVICE_NAME = "Mobile_Device"

WATERMARK = rf"""{CYAN}{BOLD}
 █████╗ ██████╗  █████╗  ██████╗██╗  ██╗██████╗  █████╗  ██████╗██╗  ██╗
██╔══██╗██╔══██╗██╔══██╗██╔════╝██║ ██╔╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝
███████║██████╔╝███████║██║     █████╔╝ ██████╔╝███████║██║     █████╔╝ 
██╔══██║██╔══██╗██╔══██║██║     ██╔═██╗ ██╔═══╝ ██╔══██║██║     ██╔═██╗ 
██║  ██║██████╔╝██║  ██║╚██████╗██║  ██╗██║     ██║  ██║╚██████╗██║  ██╗
╚═╝  ╚═╝╚═════╝ ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
{GREEN}                                                                By Shrey{RESET}
"""

SETUP_GUIDE = f"""{YELLOW}{BOLD}
[!] No Authorized Android Device Detected! Follow these exact steps:{RESET}

{CYAN}Step 1: Enable Developer Options{RESET}
  1. Open {BOLD}Settings{RESET} on your phone and scroll down to {BOLD}About phone{RESET}.
  2. Tap {BOLD}Software information{RESET} (Samsung/OnePlus) or find {BOLD}Build number{RESET} directly.
  3. Tap {BOLD}Build number{RESET} 7 times continuously until it says {GREEN}"You are now a developer!"{RESET}.

{CYAN}Step 2: Enable USB Debugging{RESET}
  1. Go back to main {BOLD}Settings{RESET} and open {BOLD}Developer options{RESET} at the bottom.
  2. Scroll down to Debugging and turn ON {BOLD}USB debugging{RESET} -> tap {BOLD}OK{RESET}.

{CYAN}Step 3: Connect & Authorize PC{RESET}
  1. Connect your phone via a data-capable USB cable and select {BOLD}File Transfer (MTP){RESET}.
  2. Keep your phone screen unlocked and tap {GREEN}Allow{RESET} on {BOLD}"Allow USB debugging?"{RESET}.
"""

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ABACKPACK Wireless Link</title>
    <style>
        body {
            background-color: #0d1117;
            color: #e6edf3;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
            box-sizing: border-box;
        }
        .card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 16px;
            padding: 24px;
            max-width: 400px;
            width: 100%;
            text-align: center;
            box-shadow: 0 8px 24px rgba(0,0,0,0.4);
        }
        h1 { color: #58a6ff; margin: 0 0 6px 0; font-size: 24px; }
        .badge {
            display: inline-block;
            background: rgba(46, 160, 67, 0.15);
            color: #3fb950;
            border: 1px solid rgba(46, 160, 67, 0.4);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 18px;
        }
        .file-box {
            border: 2px dashed #30363d;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 16px;
            background: #0d1117;
        }
        input[type="file"] {
            width: 100%;
            color: #8b949e;
        }
        button {
            background: #238636;
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            width: 100%;
            cursor: pointer;
        }
        button:disabled {
            background: #21262d;
            color: #8b949e;
        }
        #status {
            margin-top: 14px;
            font-size: 13px;
            color: #8b949e;
            line-height: 1.5;
        }
    </style>
</head>
<body>
    <div class="card">
        <h1>ABACKPACK</h1>
        <div class="badge">100% Offline Local Wi-Fi Link</div>

        <div class="file-box">
            <p style="margin-top:0; font-size:14px; color:#c9d1d9;">Select Photos, Videos, Docs, or APKs</p>
            <input type="file" id="fileInput" multiple>
        </div>

        <button id="uploadBtn" onclick="startBackup()">Start Backup to PC</button>
        <div id="status">Connected! Keep this screen open during transfer.</div>
    </div>

    <script>
        let wakeLock = null;

        async function requestWakeLock() {
            if ("wakeLock" in navigator) {
                try {
                    wakeLock = await navigator.wakeLock.request("screen");
                } catch (err) {}
            }
        }

        window.onload = async function() {
            await requestWakeLock();
            let exactModel = "";
            if (navigator.userAgentData && navigator.userAgentData.getHighEntropyValues) {
                try {
                    const hints = await navigator.userAgentData.getHighEntropyValues(["model"]);
                    if (hints.model) {
                        exactModel = hints.model;
                    }
                } catch (e) {}
            }

            const deviceInfo = {
                exactModel: exactModel,
                userAgent: navigator.userAgent,
                screen: window.screen.width + "x" + window.screen.height,
                cores: navigator.hardwareConcurrency || "Unknown"
            };

            fetch("/device-info", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(deviceInfo)
            }).catch(() => {});
        };

        async function startBackup() {
            await requestWakeLock();
            const input = document.getElementById("fileInput");
            const btn = document.getElementById("uploadBtn");
            const status = document.getElementById("status");

            if (!input.files.length) {
                status.innerText = "Please select at least 1 file first!";
                return;
            }

            btn.disabled = true;
            const total = input.files.length;

            try {
                for (let i = 0; i < total; i++) {
                    const file = input.files[i];
                    status.innerText = `Backing up (${i + 1}/${total}): ${file.name}...`;

                    await fetch("/upload-file", {
                        method: "POST",
                        headers: {
                            "X-File-Name": encodeURIComponent(file.name)
                        },
                        body: file
                    });
                }

                status.style.color = "#3fb950";
                status.innerText = `Done! All ${total} files saved to PC in 100% original quality.`;
                input.value = "";
            } catch (err) {
                status.style.color = "#f85149";
                status.innerText = "Transfer interrupted (screen locked or disconnected). Try again.";
            } finally {
                btn.disabled = false;
            }
        }
    </script>
</body>
</html>
"""


def get_base_dir():
    return os.path.dirname(
        os.path.abspath(
            sys.executable if getattr(sys, "frozen", False) else __file__
        )
    )


def get_adb_path():
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    local_adb = os.path.join(base_path, "adb", "adb.exe")
    return local_adb if os.path.exists(local_adb) else "adb"


ADB = get_adb_path()


def run_adb(command_list):
    try:
        result = subprocess.run(
            [ADB] + command_list,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None
    except FileNotFoundError:
        print(
            f"{RED}Error: adb.exe not found! Please check the 'adb' folder.{RESET}"
        )
        return None


def get_connected_device():
    output = run_adb(["devices"])
    if not output:
        return None, None, "error"

    lines = output.splitlines()[1:]
    connected = [line.split("\t") for line in lines if "\tdevice" in line]
    unauthorized = [
        line.split("\t") for line in lines if "\tunauthorized" in line
    ]

    if connected:
        first_entry = connected.pop(0)
        device_id = str(first_entry.pop(0))
        model = (
            run_adb(["-s", device_id, "shell", "getprop", "ro.product.model"])
            or "Android_Device"
        )
        return device_id, model.replace(" ", "_"), "authorized"

    if unauthorized:
        return None, None, "unauthorized"

    return None, None, "disconnected"


def create_usb_backup_dir(model_name):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = os.path.join(
        get_base_dir(), "Backups", f"{model_name}_USB_{timestamp}"
    )
    os.makedirs(backup_path, exist_ok=True)
    return backup_path


def pull_folder(device_id, phone_path, dest_folder):
    check = run_adb(["-s", device_id, "shell", f"ls -d '{phone_path}'"])
    if not check:
        print(f"{YELLOW}Skipped (Not found):{RESET} {phone_path}")
        return

    print(f"Backing up {phone_path} ...")
    os.makedirs(dest_folder, exist_ok=True)
    subprocess.run(
        [ADB, "-s", device_id, "pull", phone_path, dest_folder],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"{GREEN}Completed:{RESET} {phone_path}")


def backup_all_folders_filtered(device_id, backup_root):
    print("Scanning top-level folders in /sdcard/ (Filtering root images)...")
    dirs_raw = run_adb(
        ["-s", device_id, "shell", "find /sdcard/ -maxdepth 1 -mindepth 1 -type d"]
    )
    if not dirs_raw:
        print("No folders found in /sdcard/.")
        return

    folders = [d.strip() for d in dirs_raw.splitlines() if d.strip()]
    filtered_folders = [f for f in folders if not f.endswith("/Android")]

    print(f"Found {len(filtered_folders)} folders (Root images excluded).\n")
    for folder in filtered_folders:
        pull_folder(device_id, folder, os.path.join(backup_root, "All_Folders"))


def backup_root_files(device_id, backup_root):
    print("Scanning root level (/sdcard/) for files & images...")
    files_raw = run_adb(
        ["-s", device_id, "shell", "find /sdcard/ -maxdepth 1 -type f"]
    )
    if not files_raw:
        print("No files found in root directory.")
        return

    root_files = [f.strip() for f in files_raw.splitlines() if f.strip()]
    root_dest = os.path.join(backup_root, "Root_Files")
    os.makedirs(root_dest, exist_ok=True)

    print(f"Found {len(root_files)} root files. Pulling...")
    for file_path in root_files:
        subprocess.run(
            [ADB, "-s", device_id, "pull", file_path, root_dest],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"{GREEN}Saved Root File:{RESET} {os.path.basename(file_path)}")


def backup_apks(device_id, dest_folder):
    print("Fetching installed user apps...")
    apk_dest = os.path.join(dest_folder, "APKs")
    os.makedirs(apk_dest, exist_ok=True)

    packages_raw = run_adb(["-s", device_id, "shell", "pm list packages -3"])
    if not packages_raw:
        print("No third-party apps found.")
        return

    packages = [
        line.replace("package:", "").strip()
        for line in packages_raw.splitlines()
    ]
    print(f"Found {len(packages)} user apps. Extracting APKs...\n")

    for pkg in packages:
        path_raw = run_adb(["-s", device_id, "shell", f"pm path {pkg}"])
        if path_raw:
            apk_paths = [
                p.replace("package:", "").strip() for p in path_raw.splitlines()
            ]
            base_apk = next(
                (p for p in apk_paths if "base.apk" in p), apk_paths.pop(0)
            )
            target_file = os.path.join(apk_dest, f"{pkg}.apk")
            subprocess.run(
                [ADB, "-s", device_id, "pull", base_apk, target_file],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"{GREEN}Saved APK:{RESET} {pkg}.apk")


def run_wired_usb_mode():
    print(f"\n{CYAN}{BOLD}--- Mode 1: Wired USB Backup (Android ADB) ---{RESET}")
    while True:
        device_id, model, status = get_connected_device()
        if status == "authorized":
            break
        elif status == "unauthorized":
            print(
                f"\n{YELLOW}[!] Phone detected, waiting for permission!{RESET}"
            )
            print(
                "Please unlock your phone and tap 'Allow' on the 'Allow USB debugging?' pop-up."
            )
        else:
            print(SETUP_GUIDE)

        retry = (
            input(
                f"\n{BOLD}Press ENTER after completing the steps to scan again (or 'b' for Main Menu): {RESET}"
            )
            .strip()
            .lower()
        )
        if retry == "b":
            return

    masked_id = (
        f"{device_id[:3]}*****{device_id[-3:]}" if len(device_id) > 6 else "***"
    )
    print(f"\n{GREEN}Connected:{RESET} {BOLD}{model}{RESET} (ID: {masked_id})\n")

    print("Select Folders/Options to Backup (e.g., 1,2 or 4):")
    print("1. DCIM (Full DCIM folder)")
    print("2. Camera (DCIM/Camera only)")
    print("3. Documents & Download")
    print("4. All Folders (Filters out root images & Android system cache)")
    print("5. Backup Root (Pulls files & images from /sdcard/ root only)")
    print("6. Installed APKs (All user-installed apps)")

    raw_choices = input("\nEnter choices separated by comma: ").strip()
    choices = [c.strip() for c in raw_choices.split(",") if c.strip()]

    if not choices:
        print("No option selected. Returning to menu.")
        return

    backup_root = create_usb_backup_dir(model)
    print(f"\nBackup Folder Created: {CYAN}{backup_root}{RESET}\n" + "-" * 72)

    if "4" in choices:
        backup_all_folders_filtered(device_id, backup_root)
    else:
        if "1" in choices:
            pull_folder(
                device_id,
                "/sdcard/DCIM",
                os.path.join(backup_root, "Selected_Folders"),
            )
        if "2" in choices:
            pull_folder(
                device_id,
                "/sdcard/DCIM/Camera",
                os.path.join(backup_root, "Selected_Folders"),
            )
        if "3" in choices:
            pull_folder(
                device_id,
                "/sdcard/Documents",
                os.path.join(backup_root, "Selected_Folders"),
            )
            pull_folder(
                device_id,
                "/sdcard/Download",
                os.path.join(backup_root, "Selected_Folders"),
            )

    if "5" in choices:
        backup_root_files(device_id, backup_root)

    if "6" in choices:
        backup_apks(device_id, backup_root)

    print("-" * 72)
    print(
        f"{GREEN}{BOLD}Backup Completed Safely (Zero files deleted, 100% Original Quality)!{RESET}"
    )
    print(f"Saved Location: {CYAN}{backup_root}{RESET}")


# --- Wireless QR Mode Helpers ---

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        sock_info = s.getsockname()
        ip = str(sock_info[0])
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def print_terminal_qr(url):
    qr = qrcode.QRCode(border=2)
    qr.add_data(url)
    qr.make(fit=True)
    qr.print_ascii(invert=True)


def get_qr_backup_folder(device_name):
    date_tag = datetime.now().strftime("%Y-%m-%d_%H-%M")
    folder = os.path.join(
        get_base_dir(), "Backups", f"{device_name}_QR_{date_tag}"
    )
    os.makedirs(folder, exist_ok=True)
    return folder


class QuietHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        exc_type, exc_value, _ = sys.exc_info()
        if isinstance(
            exc_value, (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)
        ):
            print(
                f"{YELLOW}[!] Phone disconnected or screen locked ({client_address[0]}). Waiting for reconnect...{RESET}"
            )
        else:
            print(
                f"{YELLOW}[!] Network interruption ignored ({exc_type.__name__}).{RESET}"
            )


class QRBackupHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def handle(self):
        try:
            super().handle()
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            pass

    def do_GET(self):
        try:
            if self.path == "/":
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(HTML_PAGE.encode("utf-8"))
            else:
                self.send_response(404)
                self.end_headers()
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            pass

    def do_POST(self):
        global CURRENT_DEVICE_NAME

        try:
            if self.path == "/device-info":
                content_length = int(self.headers.get("Content-Length", 0))
                post_data = self.rfile.read(content_length)
                info = json.loads(post_data.decode("utf-8"))

                client_ip = self.client_address[0]
                ua = info.get("userAgent", "Unknown")
                exact_model = info.get("exactModel", "").strip()

                device_model = "Android_Device"
                if exact_model and exact_model != "K":
                    device_model = exact_model.replace(" ", "_")
                elif "iPhone" in ua:
                    device_model = "iPhone"
                elif "iPad" in ua:
                    device_model = "iPad"
                else:
                    match = re.search(r"Android [^;]+;\s*([^)]+)\)", ua)
                    if match:
                        parsed = match.group(1).strip()
                        if parsed and parsed != "K":
                            device_model = parsed.replace(" ", "_")

                CURRENT_DEVICE_NAME = device_model

                print(f"\n{GREEN}{BOLD}[+] Phone Connected via QR Code!{RESET}")
                print(f"  {CYAN}Device Name  :{RESET} {device_model}")
                print(f"  {CYAN}Local IP     :{RESET} {client_ip}")
                print(f"  {CYAN}Screen Res   :{RESET} {info.get('screen')}")
                print(f"  {CYAN}CPU Cores    :{RESET} {info.get('cores')}")
                print("-" * 55)
                print(
                    f"{YELLOW}Waiting for file selection on your phone screen...{RESET}\n"
                )

                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))

            elif self.path == "/upload-file":
                raw_name = self.headers.get("X-File-Name", "unknown_file")
                filename = os.path.basename(unquote(raw_name))
                content_length = int(self.headers.get("Content-Length", 0))

                dest_dir = get_qr_backup_folder(CURRENT_DEVICE_NAME)
                dest_path = os.path.join(dest_dir, filename)

                remaining = content_length
                with open(dest_path, "wb") as f:
                    while remaining > 0:
                        chunk_size = min(65536, remaining)
                        chunk = self.rfile.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        remaining -= len(chunk)

                print(f"{GREEN}Saved File (100% Original):{RESET} {filename}")

                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"saved": filename}).encode("utf-8"))
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            print(
                f"{YELLOW}[!] Transfer paused: Phone disconnected or locked.{RESET}"
            )


def run_wireless_qr_mode():
    print(f"\n{CYAN}{BOLD}--- Mode 2: Wireless QR Backup (Android & iOS) ---{RESET}")
    local_ip = get_local_ip()
    if local_ip == "127.0.0.1":
        print(
            f"{RED}[!] Error: PC is not connected to Wi-Fi or Hotspot.{RESET}"
        )
        print("Connect PC and Phone to the same Wi-Fi/Hotspot and try again.")
        return

    local_url = f"http://{local_ip}:{PORT}"
    print(f"Local Network Link: {GREEN}{BOLD}{local_url}{RESET}")
    print(
        f"{YELLOW}Scan this QR code with your phone camera (on same Wi-Fi/Hotspot):{RESET}\n"
    )

    print_terminal_qr(local_url)

    print(f"\nWaiting for phone scan... (Press Ctrl+C to return to Main Menu)")
    server = QuietHTTPServer(("0.0.0.0", PORT), QRBackupHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Wireless QR Server stopped.{RESET}")
        server.server_close()


def main():
    while True:
        print(WATERMARK)
        print(f"{CYAN}{'=' * 72}{RESET}")
        print(f"{BOLD}Select Connection Mode:{RESET}")
        print(
            f"  {GREEN}1.{RESET} {BOLD}Wired USB Mode{RESET} (Android Phones)"
        )
        print(
            f"  {CYAN}2.{RESET} {BOLD}Wireless QR Mode{RESET} (Every Phone, iOS Devices)"
        )
        print(f"  {RED}3.{RESET} Exit")

        mode = input("\nEnter choice (1-3): ").strip()

        if mode == "1":
            run_wired_usb_mode()
            input("\nPress ENTER to return to Main Menu...")
        elif mode == "2":
            run_wireless_qr_mode()
            input("\nPress ENTER to return to Main Menu...")
        elif mode == "3":
            print("Exiting ABACKPACK. Stay safe!")
            break
        else:
            print(f"{RED}Invalid choice. Please enter 1, 2, or 3.{RESET}\n")


if __name__ == "__main__":
    main()
