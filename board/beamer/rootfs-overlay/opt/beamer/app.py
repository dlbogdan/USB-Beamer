#TTT
import os
import pwd
import subprocess
import json
import time
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)

AUTHORIZED_KEYS_FILE = "/root/.ssh/authorized_keys"
SSH_DIR = os.path.dirname(AUTHORIZED_KEYS_FILE)
TUNNEL_USER = "root"
# Save persistent data to /data, which will be a mounted volume.
DATA_DIR = "/data"
EXPORTED_DEVICES_FILE = os.path.join(DATA_DIR, "exported_devices.json")

# Pairing behaviour: how long after the last seen SSH tunnel connection we
# wait before re-entering pairing mode (in seconds) once there has been at
# least one connection in the past. Can be overridden with an env var.
PAIRING_TIMEOUT_SECONDS = int(os.environ.get("ZEROFORCE_PAIRING_TIMEOUT", "600"))

# In-memory tracking of whether we've ever observed an active tunnel
# connection and when we last observed that there were no active connections.
_has_ever_seen_tunnel_connection = False
_last_no_connection_timestamp = None

# Flag file written by the zeroforce tunnel monitor service to indicate
# whether there is at least one active SSH tunnel connection.
TUNNEL_ACTIVE_FLAG = "/run/zeroforce/tunnel_active"


def has_active_tunnel_connections() -> bool:
    """
    Detect whether there is at least one active SSH connection to the
    beamer-sshd tunnel by checking the flag file maintained by the
    zeroforce tunnel monitor service.
    """
    return os.path.exists(TUNNEL_ACTIVE_FLAG)


def is_in_pairing_mode(now: float | None = None) -> bool:
    """
    Decide whether the device is currently in "pairing mode" according to
    the design documented in board/beamer/README.md.

    Rules:
      - If there is an active SSH tunnel connection, pairing mode is OFF.
      - If there has never been an active connection yet, pairing mode is ON
        immediately whenever there are no active connections.
      - Once at least one connection has been seen, pairing mode only turns
        back ON after PAIRING_TIMEOUT_SECONDS of *no* active connections.

    This function maintains a small amount of in-memory state to determine
    whether "at least one connection" has ever been seen and when we last
    observed that there were no active connections.
    """
    global _has_ever_seen_tunnel_connection, _last_no_connection_timestamp

    if now is None:
        now = time.time()

    active = has_active_tunnel_connections()

    if active:
        # Any active connection means pairing is definitely off and that we
        # have seen at least one connection in this process lifetime.
        if not _has_ever_seen_tunnel_connection:
            app.logger.info("Detected first active tunnel connection; disabling pairing mode")
        _has_ever_seen_tunnel_connection = True
        _last_no_connection_timestamp = None
        return False

    # No active connections.
    if not _has_ever_seen_tunnel_connection:
        # Before any connection has ever been seen, we allow immediate pairing
        # when there is no active connection.
        return True

    # We have seen at least one connection before. Require a quiet period
    # before re-entering pairing mode.
    if _last_no_connection_timestamp is None:
        _last_no_connection_timestamp = now
        return False

    if now - _last_no_connection_timestamp >= PAIRING_TIMEOUT_SECONDS:
        return True

    return False

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


@app.route("/zeroforce/readytopair", methods=["GET"])
def zeroforce_ready_to_pair():
    """
    Simple text API to indicate whether the device is currently in pairing mode.

    Returns the literal text "true" or "false" (lower-case) so that the
    Home Assistant add-on can easily poll it.
    """
    ready = is_in_pairing_mode()
    # Return as plain text, not JSON.
    body = "true" if ready else "false"
    return app.response_class(body, mimetype="text/plain")


@app.route("/zeroforce/setkey", methods=["POST"])
def zeroforce_set_key():
    """
    Pairing endpoint used by the Home Assistant add-on to install/replace
    the single authorized SSH public key for the tunnel.

    Behaviour:
      - Only effective while in pairing mode; otherwise returns HTTP 403.
      - Replaces any existing content of AUTHORIZED_KEYS_FILE with the
        provided key, so that only one client can use the tunnel.
    """
    if not is_in_pairing_mode():
        # Not in pairing mode: refuse to change the key.
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "Not in pairing mode; refusing to change authorized key",
                }
            ),
            403,
        )

    key = request.form.get("key", "").strip()
    if not key or not (key.startswith("ssh-rsa") or key.startswith("ssh-ed25519")):
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "Missing or invalid SSH public key",
                }
            ),
            400,
        )

    try:
        # Replace any existing keys with this single key.
        with open(AUTHORIZED_KEYS_FILE, "w") as f:
            f.write(key + "\n")
        set_proper_permissions()
        app.logger.info("Updated authorized_keys via /zeroforce/setkey")
    except Exception as exc:
        app.logger.error("Failed to write authorized_keys in /zeroforce/setkey: %s", exc)
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "Failed to write authorized_keys",
                }
            ),
            500,
        )

    return jsonify({"ok": True})

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