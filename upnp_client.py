import miniupnpc
import yaml
import os
import signal
import atexit
import sys
import socket
import time
import threading

CONFIG_PATH = '/config/ports.yml'
active_mappings = []
upnp = None
cleanup_done = False

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
    global upnp, cleanup_done
    if cleanup_done:
        return
    cleanup_done = True
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
    print("""
 _   _ ____        ____     ____ _ _            _   
| | | |  _ \\ _ __ |  _ \\   / ___| (_) ___ _ __ | |_ 
| | | | |_) | '_ \\| |_) | | |   | | |/ _ \\ '_ \\| __|
| |_| |  __/| | | |  __/  | |___| | |  __/ | | | |_ 
 \\___/|_|   |_| |_|_|      \\____|_|_|\\___|_| |_|\\__|
""")
    print("="*55)
    print(f"[✔] Hostname: {socket.gethostname()}")
    print(f"[✔] Router: {router_info}")
    print(f"[✔] LAN IP: {upnp.lanaddr}")
    try:
        print(f"[✔] Public IP (via UPnP): {upnp.externalipaddress()}")
    except Exception as e:
        print(f"[!] Failed to fetch public IP: {e}")
    print(f"[✔] Number of Port Mappings: {mappings_count}")
    print("="*55)

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

# Function to get router information
def get_router_info(upnp):
    try:
        # Access the IGD data which contains router information
        router_parts = []
        
        # Check if upnp object has these attributes with safe access
        if hasattr(upnp, 'igddata'):
            if isinstance(upnp.igddata, dict):
                manufacturer = upnp.igddata.get('manufacturer', '')
                model_name = upnp.igddata.get('modelName', '')
                model_description = upnp.igddata.get('modelDescription', '')
                friendly_name = upnp.igddata.get('friendlyName', '')
                
                if manufacturer:
                    router_parts.append(manufacturer)
                if model_name:
                    router_parts.append(model_name)
                if model_description and model_description not in router_parts:
                    router_parts.append(model_description)
                if friendly_name and friendly_name not in router_parts:
                    router_parts.append(friendly_name)
        
        # If IGD data didn't provide enough info, try to get more
        if not router_parts and hasattr(upnp, 'services'):
            for service in upnp.services:
                if service:
                    router_parts.append(str(service).split('/')[-1])
                    break
                    
        # As a last resort, use root device URL if available
        if not router_parts and hasattr(upnp, 'urlbase') and upnp.urlbase:
            router_parts.append(upnp.urlbase.split('//')[1].split(':')[0])
        
        router_name = " ".join(router_parts) if router_parts else "Unknown Router"
        return router_name
    except Exception as e:
        print(f"[!] Failed to get router information: {e}")
        return "Unknown Router"

# Setup UPnP with error handling
try:
    upnp = miniupnpc.UPnP()
    upnp.discover()
    upnp.selectigd()
    lan_ip = upnp.lanaddr
    router_info = get_router_info(upnp)
except Exception as e:
    print(f"[!] UPnP setup failed: {e}")
    sys.exit(1)

# Store messages
mapping_messages = []

# Function to check if a port mapping exists
def mapping_exists(external_port, protocol, lan_ip, internal_port):
    try:
        mapping = upnp.getspecificportmapping(external_port, protocol)
        if mapping is None:
            return False
        # mapping: (internalClient, internalPort, desc, enabled, leaseDuration)
        internalClient, internalPort = mapping[0], int(mapping[1])
        return internalClient == lan_ip and internalPort == internal_port
    except Exception:
        return False

# Function to refresh port mappings
REFRESH_INTERVAL = 1800  # 30 minutes
def refresh_mappings():
    while True:
        time.sleep(REFRESH_INTERVAL)
        print("[*] Started port refreshing system...", flush=True)
        for entry in config:
            try:
                internal_port = int(entry['internal_port'])
                external_port = int(entry['external_port'])
                protocol = entry['protocol'].upper()
                if not mapping_exists(external_port, protocol, lan_ip, internal_port):
                    upnp.addportmapping(external_port, protocol, lan_ip, internal_port, f"UPnP Rule {entry['id']}", '')
                    print(f"[+] Refreshed mapping [{entry['name']}]: {external_port}/{protocol}", flush=True)
                else:
                    print(f"[i] Mapping for [{entry['name']}]: {external_port}/{protocol} still exists. No refresh needed.", flush=True)
            except Exception as e:
                entry_name = entry.get('name', entry.get('id', 'Unknown Entry'))
                print(f"[!] Failed to refresh mapping for '{entry_name}': {e}", flush=True)

# Apply mappings
for entry in config:
    try:
        validate_entry(entry)
        internal_port = int(entry['internal_port'])
        external_port = int(entry['external_port'])
        protocol = entry['protocol'].upper()
        if not mapping_exists(external_port, protocol, lan_ip, internal_port):
            upnp.addportmapping(external_port, protocol, lan_ip, internal_port, f"UPnP Rule {entry['id']}", '')
            active_mappings.append((external_port, protocol))
            mapping_messages.append(f"[+] Mapped [{entry['name']}]: {external_port}/{protocol} -> {lan_ip}:{internal_port}")
        else:
            mapping_messages.append(f"[i] Mapping for [{entry['name']}]: {external_port}/{protocol} -> {lan_ip}:{internal_port} already exists. Skipping.")
    except Exception as e:
        entry_name = entry.get('name', entry.get('id', 'Unknown Entry'))
        mapping_messages.append(f"[!] Skipping entry '{entry_name}' due to error: {e}")

# Display banner
display_banner(upnp, len(active_mappings))

# Print stored messages
if mapping_messages:
    print("\n[i] Port Mapping Status:")
    for msg in mapping_messages:
        print(msg, flush=True)

# Background thread to refresh mappings
refresh_thread = threading.Thread(target=refresh_mappings, daemon=True)
refresh_thread.start()

# Stay alive
print("\n[*] Container will now stay alive!")
try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    cleanup()
    sys.exit(0)
