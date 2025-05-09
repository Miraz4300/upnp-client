import miniupnpc
import yaml
import os
import signal
import atexit
import sys
import socket
import time
from datetime import datetime
import pyfiglet

CONFIG_PATH = '/config/ports.yaml'
active_mappings = []
start_time = datetime.now()
upnp = None

# validate the config file
def validate_entry(entry):
    required_fields = ['id', 'name', 'internal_port', 'external_port', 'protocol']
    for field in required_fields:
        if field not in entry:
            raise ValueError(f"Missing field '{field}' in entry: {entry}")
    if str(entry['protocol']).upper() not in ['TCP', 'UDP']:
        raise ValueError(f"Invalid protocol '{entry['protocol']}' for {entry.get('name')}")

# Cleanup function to remove port mappings
def cleanup():
    global upnp
    print("\n[!] Cleaning up port mappings...")

    if upnp is None:
        print("[i] UPnP object not initialized. No UPnP cleanup actions taken.")
        return

    if not active_mappings:
        print("[i] No active mappings to clean up.")
        return

    for ext_port, protocol in active_mappings:
        try:
            upnp.deleteportmapping(ext_port, protocol)
            print(f"[-] Removed {protocol} port {ext_port}")
        except Exception as e:
            print(f"[!] Failed to remove {protocol} port {ext_port}: {e}")

# Signal handler for cleanup on exit
def signal_handler(sig, frame):
    cleanup()
    sys.exit(0)

# Display banner with system information
def display_banner(upnp, mappings_count):
    print("\n" + "="*60)
    print(pyfiglet.figlet_format("UPnP Client"))
    print("="*60)
    print(f"[✔] Hostname: {socket.gethostname()}")
    print(f"[✔] LAN IP: {upnp.lanaddr}")
    try:
        print(f"[✔] Public IP (via UPnP): {upnp.externalipaddress()}")
    except Exception as e:
        print(f"[!] Failed to fetch public IP: {e}")
    print(f"[✔] Number of Port Mappings: {mappings_count}")
    print(f"[✔] Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")

# Check config file existence
if not os.path.exists(CONFIG_PATH):
    print("[!] Configuration file not found.")
    print("Exiting.")
    sys.exit(1)

with open(CONFIG_PATH, 'r') as f:
    try:
        config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"[!] Failed to parse YAML: {e}")
        print("Exiting.")
        sys.exit(1)

if not config or not isinstance(config, list):
    print(f"[!] Config file at {CONFIG_PATH} is empty, invalid, or not a list.")
    print("Exiting.")
    sys.exit(1)

# Register signal handlers only after config is valid
atexit.register(cleanup)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Setup UPnP with error handling
try:
    upnp = miniupnpc.UPnP()
    upnp.discover()
    upnp.selectigd()
    lan_ip = upnp.lanaddr
except Exception as e:
    print(f"[!] UPnP setup failed: {e}")
    sys.exit(1)

# Apply mappings
for entry in config:
    try:
        validate_entry(entry)
        internal_port = int(entry['internal_port'])
        external_port = int(entry['external_port'])
        protocol = entry['protocol'].upper()

        upnp.addportmapping(external_port, protocol, lan_ip, internal_port, f"UPnP Rule {entry['id']}", '')
        active_mappings.append((external_port, protocol))
        print(f"[+] Mapped {protocol} {external_port} -> {lan_ip}:{internal_port} (Name: {entry['name']})", flush=True)
    except Exception as e:
        print(f"[!] Skipping entry due to error: {e}", flush=True)

# Display banner
display_banner(upnp, len(active_mappings))

# Stay alive
print("[*] Port mappings applied. Container will now stay alive.")
try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    cleanup()
    sys.exit(0)
