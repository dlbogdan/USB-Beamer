import json
import logging
import os
import subprocess
from logging.handlers import SysLogHandler
from typing import Any, Dict, List, Set, Tuple

import anyio
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.websockets import WebSocket, WebSocketDisconnect

from pairing_utils import is_in_pairing_mode
from usb_reset import reset


def _setup_syslog_logging(tag: str) -> logging.Logger:
    """
    Configure logging so messages are sent to syslog (/dev/log) when available.
    Returns a logger tagged for this app.
    """
    root_logger = logging.getLogger()
    syslog_handler: SysLogHandler | None = None

    for handler in root_logger.handlers:
        if isinstance(handler, SysLogHandler):
            syslog_handler = handler
            break

    if syslog_handler is None:
        try:
            syslog_handler = SysLogHandler(address="/dev/log")
        except OSError:
            logging.getLogger(tag).warning(
                "Syslog socket /dev/log not available; using default logging only"
            )
        else:
            formatter = logging.Formatter(f"{tag}: %(levelname)s: %(message)s")
            syslog_handler.setFormatter(formatter)
            syslog_handler.setLevel(logging.INFO)
            root_logger.addHandler(syslog_handler)
            root_logger.setLevel(logging.INFO)

    logger = logging.getLogger(tag)
    logger.setLevel(logging.INFO)
    logger.propagate = True
    return logger


logger = _setup_syslog_logging("zeroforce-usb")
app = Starlette(debug=False)


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
        logger.error("list-plugged failed (%s): %s", code, stderr.strip())
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
        logger.warning("get-usb-info failed for %s: %s", busid, stderr.strip())
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
        logger.warning("Failed to parse get-usb-info output for %s: %s", busid, exc)
        return {"vendor": "Unknown Vendor", "product": "Unknown Device"}


# --- WebSocket support ---------------------------------------------------------

ws_clients: Set[WebSocket] = set()


async def broadcast(payload: Dict[str, Any]) -> None:
    """
    Send a JSON payload to all connected WebSocket clients.
    """
    message = json.dumps(payload)
    dead: List[WebSocket] = []
    for ws in list(ws_clients):
        try:
            await ws.send_text(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        ws_clients.discard(ws)


# --- HTTP & WebSocket API -----------------------------------------------------

@app.route("/zeroforce/list-devices", methods=["GET"])
async def zeroforce_list_devices(request: Request) -> JSONResponse:
    """
    List USB devices using helper scripts (no usbip calls). Not available in pairing mode.
    """
    if is_in_pairing_mode():
        return JSONResponse({"ok": False, "error": "Not available in pairing mode"}, status_code=403)

    devices = await anyio.to_thread.run_sync(list_plugged_devices)
    return JSONResponse(devices)


@app.route("/zeroforce/reset-device", methods=["POST"])
async def zeroforce_reset_device(request: Request) -> JSONResponse:
    """
    Reset a USB device and notify WebSocket clients.
    """
    data = await request.json()
    busid = data.get("busid") if isinstance(data, dict) else None
    if not busid:
        return JSONResponse({"ok": False, "error": "Missing busid"}, status_code=400)

    try:
        await anyio.to_thread.run_sync(reset, busid)
        await broadcast({"type": "reset", "busid": busid, "ok": True})
        return JSONResponse({"ok": True})
    except Exception as exc:
        logger.exception("reset failed for %s", busid)
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


@app.websocket_route("/zeroforce/ws")
async def zeroforce_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    if is_in_pairing_mode():
        await websocket.send_text(json.dumps({"type": "error", "error": "Not available in pairing mode"}))
        await websocket.close()
        return

    ws_clients.add(websocket)
    try:
        devices = await anyio.to_thread.run_sync(list_plugged_devices)
        await websocket.send_text(json.dumps({"type": "devices", "devices": devices}))
        while True:
            msg = await websocket.receive_text()
            if msg == "list":
                devices = await anyio.to_thread.run_sync(list_plugged_devices)
                await websocket.send_text(json.dumps({"type": "devices", "devices": devices}))
    except WebSocketDisconnect:
        pass
    finally:
        ws_clients.discard(websocket)


if __name__ == "__main__":
    # USB API should only listen on localhost; it is expected to be reached
    # via the SSH tunnel (local port forwarding).
    port = int(os.environ.get("USB_APP_PORT", 6000))
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=port)