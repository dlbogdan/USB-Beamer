import os
import pwd
import logging
from logging.handlers import SysLogHandler
from flask import Flask, request


app = Flask(__name__)


def _setup_syslog_logging(application: Flask, tag: str) -> None:
    """
    Configure logging so that messages are sent to the system syslog daemon,
    which typically writes to /var/log/messages on the Beamer device.
    """
    root_logger = logging.getLogger()

    # Avoid adding multiple syslog handlers if this function is called twice.
    for handler in root_logger.handlers:
        if isinstance(handler, SysLogHandler):
            break
    else:
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

    # Ensure Flask's app logger is at least INFO.
    application.logger.setLevel(logging.INFO)


_setup_syslog_logging(app, "zeroforce-pairing")


# --- SSH / pairing configuration ------------------------------------------------

AUTHORIZED_KEYS_FILE = "/root/.ssh/authorized_keys"
SSH_DIR = os.path.dirname(AUTHORIZED_KEYS_FILE)
TUNNEL_USER = "root"

# Files maintained by the zeroforce tunnel monitor service.
PAIRING_RUN_DIR = "/run/zeroforce"
TUNNEL_ACTIVE_FLAG = os.path.join(PAIRING_RUN_DIR, "tunnel_active")
SINCE_CONNECTED_FILE = os.path.join(PAIRING_RUN_DIR, "since-connected")

# 5 minutes by default, as per api.md (can be overridden via env var).
PAIRING_TIMEOUT_SECONDS = int(os.environ.get("ZEROFORCE_PAIRING_TIMEOUT", "300"))


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
        app.logger.error("Failed to set SSH permissions: %s", exc)


def has_configured_key() -> bool:
    """
    Returns True if AUTHORIZED_KEYS_FILE exists and contains at least one
    non-empty line starting with an SSH key type (ssh-rsa / ssh-ed25519).

    This is used as a proxy for "has ever successfully paired/connected".
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
    Decide whether pairing mode is currently active, according to api.md:

      1. Pairing mode is active if there were never any successful
         connections to the tunnel SSH server.
         -> approximated by "no authorized key configured yet".
      2. Pairing mode is also active if it has been more than 5 minutes
         since the last successful connection to the tunnel SSH server.
         -> derived from since-connected file and tunnel-active flag.
    """
    # If there is an active tunnel connection, pairing is OFF.
    if has_active_tunnel_connections():
        return False

    # No active tunnel connection.
    if not has_configured_key():
        # Approximate "never any successful connections": no key configured.
        return True

    since = get_since_connected_seconds()
    if since is None:
        # Conservatively treat as "not in pairing mode" if we can't read a
        # sensible value.
        return False

    return since >= PAIRING_TIMEOUT_SECONDS


@app.route("/zeroforce/readytopair", methods=["GET"])
def zeroforce_ready_to_pair():
    """
    Returns "true" or "false" (lower-case) depending on whether pairing mode
    is currently active.
    """
    ready = is_in_pairing_mode()
    body = "true" if ready else "false"
    return app.response_class(body, mimetype="text/plain")


@app.route("/zeroforce/setkey", methods=["POST"])
def zeroforce_set_key():
    """
    Replace the SSH public key allowed to connect to the tunnel.

    - Only effective while in pairing mode; otherwise returns "NOK".
    - Expects a form field or JSON field named "key".
    - Replaces the content of AUTHORIZED_KEYS_FILE with this single key.
    """
    if not is_in_pairing_mode():
        return app.response_class("NOK", mimetype="text/plain"), 403

    key = ""
    if request.form:
        key = request.form.get("key", "").strip()
    if not key and request.is_json:
        payload = request.get_json(silent=True) or {}
        key = str(payload.get("key", "")).strip()

    if not key or not (key.startswith("ssh-rsa") or key.startswith("ssh-ed25519")):
        return app.response_class("NOK", mimetype="text/plain"), 400

    try:
        with open(AUTHORIZED_KEYS_FILE, "w") as f:
            f.write(key + "\n")
        set_proper_permissions()
        app.logger.info("Updated authorized_keys via /zeroforce/setkey")
    except Exception as exc:
        app.logger.error("Failed to write %s: %s", AUTHORIZED_KEYS_FILE, exc)
        return app.response_class("NOK", mimetype="text/plain"), 500

    return app.response_class("OK", mimetype="text/plain")


if __name__ == "__main__":
    # Ensure SSH permissions are correct on startup.
    set_proper_permissions()
    port = int(os.environ.get("PAIRING_APP_PORT", 5000))
    # Pairing app is exposed on all interfaces.
    app.run(host="0.0.0.0", port=port, debug=True)


