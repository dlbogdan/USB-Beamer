import os
import subprocess
import logging
from logging.handlers import SysLogHandler
from typing import List, Dict, Any, Tuple

from flask import Flask, jsonify, request

from pairing_utils import is_in_pairing_mode
from usb_reset import reset


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


SCRIPT_DIR = os.path.dirname(__file__)
LIST_PLUGGED_SCRIPT = os.path.join(SCRIPT_DIR, "list-plugged.sh")
GET_USB_INFO_SCRIPT = os.path.join(SCRIPT_DIR, "get-usb-info.sh")


# --- USB helpers (no direct usbip calls from API) --------------------------------

def _run_script(path: str, args: List[str] | None = None) -> Tuple[str, str, int]:
    """
    Run a helper script and return (stdout, stderr, returncode).
    """
    try:
        result = subprocess.run(
            [path, *(args or [])],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout, result.stderr, result.returncode
    except FileNotFoundError:
        return "", f"script missing: {path}", 127
    except Exception as exc:
        return "", str(exc), 1


def list_plugged_devices() -> List[Dict[str, Any]]:
    """
    Use list-plugged.sh to enumerate attached USB devices.
    Each line from the script is busid,VID:PID.
    For each busid, also fetch vendor/product strings.
    """
    stdout, stderr, code = _run_script(LIST_PLUGGED_SCRIPT)
    if code != 0:
        app.logger.error("list-plugged failed (%s): %s", code, stderr.strip())
        return []

    devices: List[Dict[str, Any]] = []
    for line in stdout.splitlines():
        raw = line.strip()
        if not raw or "," not in raw:
            continue
        busid_part, vidpid_part = raw.split(",", 1)
        if ":" not in vidpid_part:
            continue
        vid_raw, pid_raw = vidpid_part.split(":", 1)
        busid = busid_part.strip()
        vid = vid_raw.strip().upper()
        pid = pid_raw.strip().upper()
        if not busid or len(vid) != 4 or len(pid) != 4:
            continue
        info = get_usb_info(busid)
        devices.append(
            {
                "busid": busid,
                "vid": vid,
                "pid": pid,
                "vendor": info.get("vendor", "Unknown Vendor"),
                "product": info.get("product", "Unknown Device"),
            }
        )

    # Stable ordering for consistent IDs.
    devices.sort(key=lambda d: d["busid"])
    return devices


def get_usb_info(busid: str) -> Dict[str, str]:
    """
    Resolve vendor/product strings for a busid via get-usb-info.sh.
    """
    stdout, stderr, code = _run_script(GET_USB_INFO_SCRIPT, [busid])
    if code != 0:
        app.logger.warning("get-usb-info failed for %s: %s", busid, stderr.strip())
        return {"vendor": "Unknown Vendor", "product": "Unknown Device"}

    try:
        # Minimal parsing to avoid bringing in json module overhead; the script
        # produces stable keys.
        import json

        payload = json.loads(stdout)
        vendor = str(payload.get("vendor", "Unknown Vendor")).strip() or "Unknown Vendor"
        product = (
            str(payload.get("product", "Unknown Device")).strip() or "Unknown Device"
        )
        return {"vendor": vendor, "product": product}
    except Exception as exc:
        app.logger.warning("Failed to parse get-usb-info output for %s: %s", busid, exc)
        return {"vendor": "Unknown Vendor", "product": "Unknown Device"}


 
# --- HTTP API -------------------------------------------------------------------

@app.route("/zeroforce/list-devices", methods=["GET"])
def zeroforce_list_devices():
    """
    List USB devices using the helper scripts (no usbip calls).
    Intended to be called only by the connected client while pairing mode
    is inactive (enforced here).
    """
    if is_in_pairing_mode():
        return jsonify({"ok": False, "error": "Not available in pairing mode"}), 403

    devices = list_plugged_devices()
    return jsonify(devices)

@app.route("/zeroforce/reset-device", methods=["POST"])
def zeroforce_reset_device():
    """
    Reset a USB device.
    """
    data = request.json
    busid = data.get("busid")
    if not busid:
        return jsonify({"ok": False, "error": "Missing busid"}), 400
    try:
        reset(busid)
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

if __name__ == "__main__":
    # USB API should only listen on localhost; it is expected to be reached
    # via the SSH tunnel (local port forwarding).
    port = int(os.environ.get("USB_APP_PORT", 6000))
    from waitress import serve
    serve(app, host="127.0.0.1", port=port, threads=1)


