import os
import pwd
import logging
from logging.handlers import SysLogHandler
from flask import Flask, request

from pairing_utils import AUTHORIZED_KEYS_FILE, TUNNEL_USER, is_in_pairing_mode


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
    # messages reach syslog even when propagate=False.
    # When propagating to root, we don't need the app to hold its own syslog
    # handler (would cause duplicates). Drop any existing SysLogHandler on it.
    if syslog_handler:
        application.logger.handlers = [
            h for h in application.logger.handlers if not isinstance(h, SysLogHandler)
        ]

    application.logger.setLevel(logging.INFO)
    application.logger.propagate = True


_setup_syslog_logging(app, "zeroforce-pairing")

# Silence noisy werkzeug development-server logs (startup, debugger, etc.).
# logging.getLogger("werkzeug").setLevel(logging.ERROR)


# --- SSH / pairing configuration ------------------------------------------------

SSH_DIR = os.path.dirname(AUTHORIZED_KEYS_FILE)


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
    from waitress import serve
    serve(app, host="0.0.0.0", port=port, threads=1)


