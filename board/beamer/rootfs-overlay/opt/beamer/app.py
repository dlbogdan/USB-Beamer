import os
import pwd
import subprocess
import json
import logging
from logging.handlers import SysLogHandler
from typing import List, Dict, Any

from flask import Flask, request, jsonify


app = Flask(__name__)


def _setup_syslog_logging(application: Flask, tag: str) -> None:
    """
    Configure logging so that messages are sent to the system syslog daemon,
    which typically writes to /var/log/messages on the Beamer device.
    """
    root_logger = logging.getLogger()

    syslog_handler: SysLogHandler | None = None

    # Avoid adding multiple syslog handlers if this function is called twice.
    for handler in root_logger.handlers:
        if isinstance(handler, SysLogHandler):
            syslog_handler = handler
            break

    if syslog_handler is None:
        try:
            syslog_handler = SysLogHandler(address="/dev/log")
        except OSError:
            # If /dev/log is not available, fall back to default stderr logging.
            application.logger.warning(
                "Syslog socket /dev/log not available; using default logging only"
            )
        else:
            formatter = logging.Formatter(f"{tag}: %(levelname)s: %(message)s")
            syslog_handler.setFormatter(formatter)
            syslog_handler.setLevel(logging.INFO)
            root_logger.addHandler(syslog_handler)
            root_logger.setLevel(logging.INFO)

    # Attach the syslog handler to the Flask app logger as well so app.logger.info
    # messages (like setkey updates) make it to syslog even when propagate=False.
    # When propagating to root, we don't need the app to hold its own syslog
    # handler (would cause duplicates). Drop any existing SysLogHandler on it.
    if syslog_handler:
        application.logger.handlers = [
            h for h in application.logger.handlers if not isinstance(h, SysLogHandler)
        ]

    application.logger.setLevel(logging.INFO)
    application.logger.propagate = True


_setup_syslog_logging(app, "zeroforce-usb")

# Silence noisy werkzeug development-server logs (startup, debugger, etc.).
# logging.getLogger("werkzeug").setLevel(logging.ERROR)


AUTHORIZED_KEYS_FILE = "/root/.ssh/authorized_keys"
TUNNEL_USER = "root"

PAIRING_RUN_DIR = "/run/zeroforce"
TUNNEL_ACTIVE_FLAG = os.path.join(PAIRING_RUN_DIR, "tunnel_active")
SINCE_CONNECTED_FILE = os.path.join(PAIRING_RUN_DIR, "since-connected")
PAIRING_TIMEOUT_SECONDS = int(os.environ.get("ZEROFORCE_PAIRING_TIMEOUT", "300"))


def has_configured_key() -> bool:
    """
    Returns True if AUTHORIZED_KEYS_FILE exists and contains at least one
    non-empty line starting with an SSH key type (ssh-rsa / ssh-ed25519).
    """
    try:
        with open(AUTHORIZED_KEYS_FILE, "r") as f:
            for line in f:
                s = line.strip()
                if s and (s.startswith("ssh-rsa") or s.startswith("ssh-ed25519")):
                    return True
    except FileNotFoundError:
        return False
    except Exception as exc:
        app.logger.error("Error reading %s: %s", AUTHORIZED_KEYS_FILE, exc)
        return False
    return False


def get_since_connected_seconds() -> int | None:
    """
    Read the number of seconds since the tunnel last went offline, as
    maintained by the zeroforce tunnel monitor service.
    Returns None if the value cannot be determined.
    """
    try:
        with open(SINCE_CONNECTED_FILE, "r") as f:
            raw = f.read().strip()
        if not raw:
            return None
        return int(raw)
    except FileNotFoundError:
        return None
    except ValueError:
        app.logger.warning("Invalid integer in %s: %r", SINCE_CONNECTED_FILE, raw)
        return None
    except Exception as exc:
        app.logger.error("Error reading %s: %s", SINCE_CONNECTED_FILE, exc)
        return None


def has_active_tunnel_connections() -> bool:
    """
    True if the monitor indicates that there is at least one active tunnel
    connection via the flag file.
    """
    return os.path.exists(TUNNEL_ACTIVE_FLAG)


def is_in_pairing_mode() -> bool:
    """
    Decide whether pairing mode is currently active, according to api.md.
    """
    if has_active_tunnel_connections():
        return False

    if not has_configured_key():
        return True

    since = get_since_connected_seconds()
    if since is None:
        return False

    return since >= PAIRING_TIMEOUT_SECONDS


# --- USB/IP helpers -------------------------------------------------------------

def parse_usbip_list() -> List[Dict[str, Any]]:
    """
    Parse the output of `usbip list -l -p` into a list of device dicts with:
      - busid: str
      - vid: str (hex, upper-case)
      - pid: str (hex, upper-case)
      - device_name: str
    """
    try:
        result = subprocess.run(
            ["usbip", "list", "-l", "-p"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        app.logger.error("Failed to run 'usbip list': %s", exc)
        return []

    devices: List[Dict[str, Any]] = []
    for block in result.stdout.strip().split("\n\n"):
        if not block.strip():
            continue
        lines = block.strip().splitlines()
        if not lines:
            continue

        first = lines[0].strip()
        parts = first.split()
        if len(parts) < 3 or parts[1] != "busid":
            continue
        busid = parts[2]

        # Default values
        vid = ""
        pid = ""
        device_name = "Unknown Device"

        # Try to extract VID:PID and name from the first or second line.
        search_lines = lines[:2]
        for line in search_lines:
            line = line.strip()
            # Heuristic: find (VID:PID) inside parentheses.
            if "(" in line and ")" in line:
                inside = line[line.find("(") + 1 : line.find(")")]
                if ":" in inside:
                    v, p = inside.split(":", 1)
                    if len(v) == 4 and len(p) == 4:
                        vid = v.upper()
                        pid = p.upper()
            # Use the second line as a human-readable device name when present.
            if line and line is not first:
                device_name = line

        devices.append(
            {
                "busid": busid,
                "vid": vid,
                "pid": pid,
                "device_name": device_name,
            }
        )

    return devices


def build_lsusb_payload() -> List[Dict[str, Any]]:
    """
    Build the payload for /zeroforce/lsusb:
      [
        {
          "id": int,
          "PID": str,
          "VID": str,
          "device_name": str,
          "busid": str,
        },
        ...
      ]
    """
    devices = parse_usbip_list()

    payload: List[Dict[str, Any]] = []
    next_id = 1
    for dev in devices:
        payload.append(
            {
                "id": next_id,
                "PID": dev.get("pid", ""),
                "VID": dev.get("vid", ""),
                "device_name": dev.get("device_name", "Unknown Device"),
                "busid": dev.get("busid", ""),
            }
        )
        next_id += 1

    return payload


def resolve_target_busids(
    ids: List[int] | None, vidpids: List[Dict[str, str]] | None
) -> set[str]:
    """
    Resolve a list of abstract IDs and/or PID/VID pairs to concrete busids.
    """
    devices = parse_usbip_list()

    # Map id -> busid (id is 1-based index over current device list).
    id_to_busid: Dict[int, str] = {}
    for idx, dev in enumerate(devices, start=1):
        id_to_busid[idx] = dev.get("busid", "")

    target_busids: set[str] = set()

    if ids:
        for i in ids:
            busid = id_to_busid.get(int(i))
            if busid:
                target_busids.add(busid)

    if vidpids:
        # Build a map vid:pid -> list of busids.
        vp_to_busids: Dict[tuple[str, str], List[str]] = {}
        for dev in devices:
            vid = dev.get("vid", "").upper()
            pid = dev.get("pid", "").upper()
            busid = dev.get("busid", "")
            if not vid or not pid or not busid:
                continue
            key = (vid, pid)
            vp_to_busids.setdefault(key, []).append(busid)

        for entry in vidpids:
            vid = str(entry.get("vid", "")).upper()
            pid = str(entry.get("pid", "")).upper()
            key = (vid, pid)
            for busid in vp_to_busids.get(key, []):
                target_busids.add(busid)

    return target_busids


def apply_bind_configuration(target_busids: set[str]) -> None:
    """
    Apply the desired binding configuration by forcing a re-bind of each
    requested busid. We no longer attempt to track/export "current" binding
    state on the server.
    """
    # For each desired device, force a re-bind.
    for busid in target_busids:
        # 1. Unbind first to clear stale state; ignore failures.
        subprocess.run(
            ["usbip", "unbind", "-b", busid],
            check=False,
            capture_output=True,
        )
        # 2. Bind the device; log any error.
        try:
            subprocess.run(
                ["usbip", "bind", "-b", busid],
                check=True,
                capture_output=True,
                text=True,
            )
            app.logger.info("Bound %s via usbip", busid)
        except subprocess.CalledProcessError as exc:
            app.logger.error(
                "Failed to bind %s via usbip: %s", busid, exc.stderr.strip()
            )


# --- HTTP API -------------------------------------------------------------------

@app.route("/zeroforce/lsusb", methods=["GET"])
def zeroforce_lsusb():
    """
    List USB devices as described in api.md.
    Intended to be called only by the connected client while pairing mode
    is inactive (enforced here).
    """
    if is_in_pairing_mode():
        return jsonify({"ok": False, "error": "Not available in pairing mode"}), 403

    payload = build_lsusb_payload()
    return jsonify(payload)


@app.route("/zeroforce/bind", methods=["POST"])
def zeroforce_bind():
    """
    Bind USB devices for export via usbip.

    Input (JSON):
      {
        "ids": [1, 2, 3],                  # optional
        "vidpids": [                       # optional
          {"vid": "1234", "pid": "5678"},
          ...
        ]
      }

    The server:
      - Resolves these to concrete busids.
      - Unbinds any previously bound devices not in the selection.
      - Rebinds all selected devices.
    """
    if is_in_pairing_mode():
        return jsonify({"ok": False, "error": "Not available in pairing mode"}), 403

    if not request.is_json:
        return jsonify({"ok": False, "error": "Expected JSON body"}), 400

    payload = request.get_json(silent=True) or {}
    raw_ids = payload.get("ids") or []
    raw_vidpids = payload.get("vidpids") or []

    try:
        ids = [int(x) for x in raw_ids]
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Invalid 'ids' list"}), 400

    if not isinstance(raw_vidpids, list):
        return jsonify({"ok": False, "error": "Invalid 'vidpids' list"}), 400

    vidpids: List[Dict[str, str]] = []
    for entry in raw_vidpids:
        if not isinstance(entry, dict):
            continue
        vid = entry.get("vid")
        pid = entry.get("pid")
        if not vid or not pid:
            continue
        vidpids.append({"vid": str(vid), "pid": str(pid)})

    target_busids = resolve_target_busids(ids, vidpids)
    if not target_busids:
        return jsonify({"ok": False, "error": "No matching devices for selection"}), 400

    apply_bind_configuration(target_busids)
    return jsonify({"ok": True, "busids": sorted(target_busids)})


if __name__ == "__main__":
    # USB API should only listen on localhost; it is expected to be reached
    # via the SSH tunnel (local port forwarding).
    port = int(os.environ.get("USB_APP_PORT", 6000))
    from waitress import serve
    serve(app, host="127.0.0.1", port=port, threads=1)


