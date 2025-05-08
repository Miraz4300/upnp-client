import miniupnpc
import yaml
import os
import signal
import atexit
import sys

CONFIG_PATH = '/config/ports.yaml'
active_mappings = []  # Store tuples for cleanup

def validate_entry(entry):
    required_fields = ['id', 'internal_port', 'external_port', 'protocol']
    for field in required_fields:
        if field not in entry:
            raise ValueError(f"Missing field '{field}' in entry: {entry}")

    if str(entry['protocol']).upper() not in ['TCP', 'UDP']:
        raise ValueError(f"Invalid protocol '{entry['protocol']}' for ID {entry.get('id')}")

def cleanup():
    print("\n[!] Cleaning up port mappings...")
    for ext_port, protocol in active_mappings:
        try:
            upnp.deleteportmapping(ext_port, protocol)
            print(f"[-] Removed {protocol} port {ext_port}")
        except Exception as e:
            print(f"[!] Failed to remove {protocol} port {ext_port}: {e}")

def signal_handler(sig, frame):
    cleanup()
    sys.exit(0)

# Register shutdown hooks
atexit.register(cleanup)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Load config
if not os.path.exists(CONFIG_PATH):
    raise FileNotFoundError(f"Missing config file: {CONFIG_PATH}")

with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

# Setup UPnP
upnp = miniupnpc.UPnP()
upnp.discover()
upnp.selectigd()
lan_ip = upnp.lanaddr

# Apply mappings
for entry in config:
    try:
        validate_entry(entry)
        internal_port = int(entry['internal_port'])
        external_port = int(entry['external_port'])
        protocol = entry['protocol'].upper()

        upnp.addportmapping(external_port, protocol, lan_ip, internal_port, f"UPnP Rule {entry['id']}", '')
        active_mappings.append((external_port, protocol))
        print(f"[+] Mapped {protocol} {external_port} -> {lan_ip}:{internal_port}")
    except Exception as e:
        print(f"[!] Skipping entry due to error: {e}")
