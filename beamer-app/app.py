#TTT
import os
import pwd
import subprocess
import json
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)

AUTHORIZED_KEYS_FILE = "/root/.ssh/authorized_keys"
SSH_DIR = os.path.dirname(AUTHORIZED_KEYS_FILE)
TUNNEL_USER = "root"
# Save persistent data to /data, which will be a mounted volume.
DATA_DIR = "/data"
EXPORTED_DEVICES_FILE = os.path.join(DATA_DIR, "exported_devices.json")

def get_usb_devices():
    """Fetches list of local USB devices using 'usbip'."""
    try:
        result = subprocess.run(
            ["usbip", "list", "-l", "-p"],
            capture_output=True, text=True, check=True
        )
        devices = []
        # Split the output by blank lines to process each device block.
        for device_block in result.stdout.strip().split('\n\n'):
            if not device_block:
                continue
            
            lines = device_block.strip().splitlines()
            if not lines:
                continue

            first_line_parts = lines[0].split()
            if len(first_line_parts) >= 3 and first_line_parts[1] == 'busid':
                busid = first_line_parts[2]
                
                info = "Unknown Device"
                if len(lines) > 1:
                    info = lines[1].strip()
                
                devices.append({"busid": busid, "info": f"{info} ({busid})"})

        app.logger.info(f"Discovered USB devices: {devices}")
        return devices
        
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        app.logger.error(f"Failed to list USB devices: {e}")
        return []

def get_exported_busids():
    """Loads the list of persistently exported device bus IDs."""
    if not os.path.exists(EXPORTED_DEVICES_FILE):
        return []
    try:
        with open(EXPORTED_DEVICES_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return [] # Return empty list if file is corrupt, empty, or not found.

def set_exported_devices(new_busids):
    """Binds/unbinds devices to match the new list, forcing a re-bind."""
    current_busids = set(get_exported_busids())
    new_busids = set(new_busids)

    # Unbind devices that are no longer selected
    for busid in current_busids - new_busids:
        try:
            # We don't check for errors here, as the device might not be bound.
            subprocess.run(["usbip", "unbind", "-b", busid], check=False, capture_output=True)
            app.logger.info(f"Unbound deselected device {busid}")
        except Exception as e:
            app.logger.error(f"An error occurred while unbinding {busid}: {e}")

    # For every selected device, force a re-bind to ensure a fresh connection state.
    for busid in new_busids:
        # 1. Unbind first to clear any stale state. This is allowed to fail if not bound.
        subprocess.run(["usbip", "unbind", "-b", busid], check=False, capture_output=True)
        
        # 2. Now, bind the device. This is expected to succeed.
        try:
            bind_result = subprocess.run(["usbip", "bind", "-b", busid], check=True, capture_output=True, text=True)
            app.logger.info(f"Successfully bound device {busid}")
        except subprocess.CalledProcessError as e:
            app.logger.error(f"Failed to bind {busid} after unbind: {e.stderr.strip()}")
    
    # Ensure data directory exists before trying to save the file.
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    # Persist the new list
    with open(EXPORTED_DEVICES_FILE, "w") as f:
        json.dump(list(new_busids), f)

def set_proper_permissions():
    """Ensures the .ssh directory and key file have correct ownership and permissions."""
    try:
        root_uid = pwd.getpwnam(TUNNEL_USER).pw_uid
        root_gid = pwd.getpwnam(TUNNEL_USER).pw_gid
        
        if not os.path.exists(SSH_DIR):
            os.makedirs(SSH_DIR)

        os.chown(SSH_DIR, root_uid, root_gid)
        os.chmod(SSH_DIR, 0o700)
        
        if not os.path.exists(AUTHORIZED_KEYS_FILE):
            open(AUTHORIZED_KEYS_FILE, 'a').close()

        os.chown(AUTHORIZED_KEYS_FILE, root_uid, root_gid)
        os.chmod(AUTHORIZED_KEYS_FILE, 0o600)

    except Exception as e:
        app.logger.error(f"Failed to set permissions: {e}")

@app.route("/", methods=["GET"])
def index():
    """Displays the current list of authorized keys and a form to add new ones."""
    try:
        with open(AUTHORIZED_KEYS_FILE, "r") as f:
            keys = f.readlines()
    except FileNotFoundError:
        keys = []
    
    usb_devices = get_usb_devices()
    exported_busids = get_exported_busids()
    
    return render_template("index.html", keys=keys, usb_devices=usb_devices, exported_busids=exported_busids)

@app.route("/export", methods=["POST"])
def export_devices():
    """Handles updating the exported USB devices."""
    selected_busids = request.form.getlist("busids")
    set_exported_devices(selected_busids)
    return redirect(url_for("index"))

@app.route("/add", methods=["POST"])
def add_key():
    """Adds a new public key and fixes permissions."""
    key = request.form.get("key", "").strip()
    if key and (key.startswith("ssh-rsa") or key.startswith("ssh-ed25519")):
        with open(AUTHORIZED_KEYS_FILE, "a") as f:
            f.write(key + "\n")
        set_proper_permissions()
    return redirect(url_for("index"))

@app.route("/api/exported-devices", methods=["GET"])
def api_exported_devices():
    """Returns the list of bus IDs configured for export."""
    return jsonify(get_exported_busids())

if __name__ == "__main__":
    # Set permissions on startup to guarantee correctness.
    set_proper_permissions()
    # On startup, re-apply the binding for persisted devices
    set_exported_devices(get_exported_busids())

    # Use environment variable for port, default to 5000
    port = int(os.environ.get("APP_PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True) 