import json
import re
import subprocess
import threading

HOTSPOT_SSID = "Momo-Setup"
HOTSPOT_PASSWORD = "momo1523"
HOTSPOT_CON_NAME = "momo-setup-hotspot"

STATUS_PATH = "/home/castlers/momo/wifi_status.json"

_connect_lock = threading.Lock()


def connectivity():
    result = subprocess.run(["nmcli", "networking", "connectivity"], capture_output=True, text=True, timeout=10)
    return result.stdout.strip()


def is_online():
    return connectivity() in ("full", "limited")


def current_ip():
    result = subprocess.run(["hostname", "-I"], capture_output=True, text=True, timeout=10)
    parts = result.stdout.strip().split()
    return parts[0] if parts else None


def active_ssid():
    result = subprocess.run(["nmcli", "-t", "-f", "active,ssid", "device", "wifi"], capture_output=True, text=True, timeout=10)
    for line in result.stdout.splitlines():
        if line.startswith("yes:"):
            return line.split(":", 1)[1]
    return None


def start_hotspot():
    subprocess.run(
        ["sudo", "nmcli", "device", "wifi", "hotspot", "ifname", "wlan0",
         "con-name", HOTSPOT_CON_NAME, "ssid", HOTSPOT_SSID, "password", HOTSPOT_PASSWORD],
        capture_output=True, text=True, timeout=30
    )
    write_status("hotspot")


def scan_networks():
    subprocess.run(["sudo", "nmcli", "device", "wifi", "rescan"], capture_output=True, text=True, timeout=15)
    result = subprocess.run(
        ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list"],
        capture_output=True, text=True, timeout=15
    )
    seen = {}
    for line in result.stdout.splitlines():
        parts = re.split(r"(?<!\\):", line)
        if len(parts) < 3:
            continue
        ssid = parts[0].replace("\\:", ":").strip()
        if not ssid or ssid == HOTSPOT_SSID:
            continue
        try:
            signal = int(parts[1])
        except ValueError:
            signal = 0
        security = parts[2]
        if ssid not in seen or seen[ssid]["signal"] < signal:
            seen[ssid] = {"ssid": ssid, "signal": signal, "secured": bool(security)}
    return sorted(seen.values(), key=lambda n: -n["signal"])


def connect(ssid, password):
    with _connect_lock:
        args = ["sudo", "nmcli", "device", "wifi", "connect", ssid]
        if password:
            args += ["password", password]
        result = subprocess.run(args, capture_output=True, text=True, timeout=45)
        success = result.returncode == 0
        if success:
            write_status("connected", ssid=ssid, ip=current_ip())
        else:
            start_hotspot()
        return success, (result.stdout.strip() or result.stderr.strip())


def connect_async(ssid, password, on_done=None):
    def _run():
        success, message = connect(ssid, password)
        if on_done:
            on_done(success, message)
    threading.Thread(target=_run, daemon=True).start()


def write_status(mode, ssid=None, ip=None):
    with open(STATUS_PATH, "w") as f:
        json.dump({"mode": mode, "ssid": ssid, "ip": ip}, f, indent=2)


def read_status():
    try:
        with open(STATUS_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"mode": "unknown", "ssid": None, "ip": None}
