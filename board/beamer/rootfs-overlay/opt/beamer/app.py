import asyncio
import json
import logging
import os
import re
import subprocess
from logging.handlers import SysLogHandler
from typing import Any, Dict, List, Set, Tuple

import anyio
# import time
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


logger = _setup_syslog_logging("beamer-api")
app = Starlette(debug=False)


SCRIPT_DIR = os.path.dirname(__file__)
LIST_PLUGGED_SCRIPT = os.path.join(SCRIPT_DIR, "list-plugged.sh")
GET_USB_INFO_SCRIPT = os.path.join(SCRIPT_DIR, "get-usb-info.sh")
DEV_MODE_FLAG = "/boot/devmode"
LOG_PATH = "/var/log/messages"
LOG_QUEUE_MAX = 20 # todo: make this configurable


def _ok(payload: Dict[str, Any], status_code: int = 200) -> JSONResponse:
    """Shortcut for successful JSON responses."""
    return JSONResponse(payload, status_code=status_code)


def _error(reason: str, status_code: int, extra: Dict[str, Any] | None = None) -> JSONResponse:
    """Consistent error JSON responses."""
    body: Dict[str, Any] = {"status": "error", "reason": reason}
    if extra:
        body.update(extra)
    return JSONResponse(body, status_code=status_code)


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
log_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=LOG_QUEUE_MAX)


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


async def watch_devices(interval: float = 2.0) -> None:
    """
    Poll the device list and broadcast when it changes.
    """
    last_snapshot: list[tuple[str, str, str, str, str]] | None = None
    while True:
        try:
            devices = await anyio.to_thread.run_sync(list_plugged_devices)
            snapshot = [
                (
                    d.get("busid", ""),
                    d.get("vid", ""),
                    d.get("pid", ""),
                    d.get("vendor", ""),
                    d.get("product", ""),
                )
                for d in devices
            ]
            if snapshot != last_snapshot:
                await broadcast({"type": "devices", "devices": devices})
                logger.info("broadcasted device change to %d clients", len(ws_clients))
                last_snapshot = snapshot
        except Exception:
            logger.exception("device watcher failed")
        await asyncio.sleep(interval)


def _extract_level(line: str) -> str:
    """
    Best-effort log level extraction from a syslog-like line.
    """
    m = re.search(r"\b(emerg|alert|crit|err|error|warn|warning|notice|info|debug)\b", line, re.IGNORECASE)
    return m.group(1).lower() if m else "info"


def _should_emit_log(level: str) -> bool:
    """
    Decide whether to emit a log line based on dev mode and level.
    """
    if os.path.exists(DEV_MODE_FLAG):
        return True
    return level in {"err", "error", "warn", "warning", "crit", "alert", "emerg"}


async def _enqueue_log(payload: Dict[str, Any]) -> None:
    """
    Enqueue a log payload with bounded buffering (drops oldest on overflow).
    """
    try:
        log_queue.put_nowait(payload)
    except asyncio.QueueFull:
        try:
            log_queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
        try:
            log_queue.put_nowait(payload)
        except asyncio.QueueFull:
            pass


async def log_sender() -> None:
    """
    Drain log queue and broadcast to connected clients.
    """
    while True:
        payload = await log_queue.get()
        await broadcast(payload)


async def log_watcher() -> None:
    """
    Tail system logs and push over WebSocket. Sends all logs in devmode,
    otherwise only warnings/errors and above.
    """
    if not os.path.exists(LOG_PATH):
        logger.warning("log watcher skipped; %s missing", LOG_PATH)
        return

    cmd = ["tail", "-n", "0", "-F", LOG_PATH]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
    except FileNotFoundError:
        logger.warning("tail not found; log watcher disabled")
        return
    except Exception as exc:
        logger.exception("failed to start log watcher: %s", exc)
        return

    logger.info("log watcher started")
    try:
        while True:
            line = await proc.stdout.readline()
            if not line:
                if proc.returncode is not None:
                    logger.warning("log watcher exited with code %s", proc.returncode)
                    break
                await asyncio.sleep(0.2)
                continue
            text = line.decode(errors="replace").rstrip("\r\n")
            level = _extract_level(text)
            if not _should_emit_log(level):
                continue
            await _enqueue_log({"type": "log", "level": level, "line": text})
    except Exception:
        logger.exception("log watcher failed")
    finally:
        if proc.returncode is None:
            proc.terminate()


def reboot() -> None:
    """
    Reboot the beamer.
    """
    subprocess.run(["reboot"], check=False)
    broadcast({"type": "warning", "message": "rebooting beamer"})
    logger.info("rebooted beamer")

# --- HTTP & WebSocket API -----------------------------------------------------
@app.route("/api/uptime", methods=["GET"])
async def api_uptime(request: Request) -> JSONResponse:
    """
    Get the uptime of the beamer.
    """
    uptime = os.path.getmtime("/proc/uptime")
    return _ok({"uptime": uptime})

@app.route("/api/reboot-beamer", methods=["GET"])
async def api_reboot_beamer(request: Request) -> JSONResponse:
    """
    Reboot the beamer.
    """
    try:
        await anyio.to_thread.run_sync(reboot)
        return _ok({"status": "ok"})
    except Exception as exc:
        logger.exception("reboot failed")
        return _error("reboot_failed", status_code=500, extra={"detail": str(exc)})

@app.route("/api/list-devices", methods=["GET"])
async def api_list_devices(request: Request) -> JSONResponse:
    """
    List USB devices using helper scripts (no usbip calls). Not available in pairing mode.
    """
    if is_in_pairing_mode():
        return _error("pairing_mode_enabled", status_code=403)

    devices = await anyio.to_thread.run_sync(list_plugged_devices)
    return _ok({"devices": devices})


@app.route("/api/reset-device", methods=["POST"])
async def api_reset_device(request: Request) -> JSONResponse:
    """
    Reset a USB device and notify WebSocket clients.
    """
    try:
        data = await request.json()
    except json.JSONDecodeError:
        data = {}
    busid = data.get("busid") if isinstance(data, dict) else None
    if not busid:
        return _error("missing_busid", status_code=400)

    try:
        await anyio.to_thread.run_sync(reset, busid)
        await broadcast({"type": "reset", "busid": busid, "ok": True})
        return _ok({"status": "ok"})
    except Exception as exc:
        logger.exception("reset failed for %s", busid)
        return _error("reset_failed", status_code=500, extra={"detail": str(exc)})


@app.websocket_route("/api/ws")
async def api_ws(websocket: WebSocket) -> None:
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
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ws_clients.discard(websocket)


@app.on_event("startup")
async def _start_watch() -> None:
    asyncio.create_task(watch_devices())
    asyncio.create_task(log_watcher())
    asyncio.create_task(log_sender())


if __name__ == "__main__":
    # USB API should only listen on localhost; it is expected to be reached
    # via the SSH tunnel (local port forwarding).
    port = int(os.environ.get("USB_APP_PORT", 6000))
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=port)