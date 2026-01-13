import json
import logging
import os
import pwd
import time
from logging.handlers import SysLogHandler

import anyio
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse

from pairing_utils import AUTHORIZED_KEYS_FILE, TUNNEL_USER, is_in_pairing_mode


def _setup_syslog_logging(tag: str) -> logging.Logger:
    """
    Configure logging so that messages are sent to syslog when available.
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


logger = _setup_syslog_logging("zeroforce-pairing")
app = Starlette(debug=False)

# --- SSH / pairing configuration ------------------------------------------------

SSH_DIR = os.path.dirname(AUTHORIZED_KEYS_FILE)
DEV_MODE_FLAG = "/boot/devmode"


def _ok(payload: dict, status_code: int = 200) -> JSONResponse:
    """Shortcut for successful JSON responses."""
    return JSONResponse(payload, status_code=status_code)


def _error(reason: str, status_code: int) -> JSONResponse:
    """Consistent error JSON responses."""
    return JSONResponse({"status": "error", "reason": reason}, status_code=status_code)


def set_proper_permissions() -> None:
    """
    Ensure the .ssh directory and authorized_keys file have safe ownership
    and permissions so that beamer-sshd running as root can read them.
    """
    try:
        root_info = pwd.getpwnam(TUNNEL_USER)
        root_uid = root_info.pw_uid
        root_gid = root_info.pw_gid

        if not os.path.exists(SSH_DIR):
            os.makedirs(SSH_DIR, exist_ok=True)

        os.chown(SSH_DIR, root_uid, root_gid)
        os.chmod(SSH_DIR, 0o700)

        if not os.path.exists(AUTHORIZED_KEYS_FILE):
            open(AUTHORIZED_KEYS_FILE, "a").close()

        os.chown(AUTHORIZED_KEYS_FILE, root_uid, root_gid)
        os.chmod(AUTHORIZED_KEYS_FILE, 0o600)
    except Exception as exc:
        logger.error("Failed to set SSH permissions: %s", exc)


def _write_key(key: str) -> None:
    with open(AUTHORIZED_KEYS_FILE, "w") as f:
        f.write(key + "\n")
    set_proper_permissions()
    logger.info("Updated authorized_keys via /zeroforce/setkey")

@app.route("/zeroforce/info", methods=["GET"])
async def zeroforce_info(request: Request) -> JSONResponse:
    """
    Get information about the beamer.
    """
    # for not just send if it's in devmode or not, pairing mode and uptime
    info = {
        "version": "0.1.0", # TODO: get version from package.json
        "hostname": os.uname().nodename,
        "devmode": os.path.exists(DEV_MODE_FLAG),
        "pairing_mode": is_in_pairing_mode(),
        "uptime": time.time() - os.path.getmtime("/proc/uptime"),
    }
    return _ok(info)

@app.route("/zeroforce/readytopair", methods=["GET"])
async def zeroforce_ready_to_pair(request: Request) -> JSONResponse:
    """
    Returns "true" or "false" (lower-case) depending on whether pairing mode
    is currently active.
    """
    ready = is_in_pairing_mode()
    return _ok({"ready": ready})


@app.route("/zeroforce/setkey", methods=["POST"])
async def zeroforce_set_key(request: Request) -> JSONResponse:
    """
    Replace the SSH public key allowed to connect to the tunnel.

    - Only effective while in pairing mode; otherwise returns "NOK".
    - Expects a form field or JSON field named "key".
    - Replaces the content of AUTHORIZED_KEYS_FILE with this single key.
    """
    if not is_in_pairing_mode():
        return _error("pairing_mode_disabled", status_code=403)

    key = ""

    # Prefer JSON if content-type says so; otherwise try form, then fall back to JSON.
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        if isinstance(payload, dict):
            key = str(payload.get("key", "")).strip()
    if not key:
        try:
            form = await request.form()
            key = str(form.get("key", "")).strip()
        except Exception:
            # Ignore parsing errors and fall back to JSON
            pass
    if not key:
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        if isinstance(payload, dict):
            key = str(payload.get("key", "")).strip()

    if not key or not (key.startswith("ssh-rsa") or key.startswith("ssh-ed25519")):
        return _error("invalid_key", status_code=400)

    try:
        await anyio.to_thread.run_sync(_write_key, key)
    except Exception as exc:
        logger.error("Failed to write %s: %s", AUTHORIZED_KEYS_FILE, exc)
        return _error("write_failed", status_code=500)

    return _ok({"status": "ok"})


@app.on_event("startup")
async def _ensure_permissions_on_start() -> None:
    # Ensure SSH permissions are correct when running under a process manager
    await anyio.to_thread.run_sync(set_proper_permissions)


if __name__ == "__main__":
    # Ensure SSH permissions are correct on startup.
    set_proper_permissions()
    port = int(os.environ.get("PAIRING_APP_PORT", 5000))
    # Pairing app is exposed on all interfaces.
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=port)
