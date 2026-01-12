import logging
import os


# SSH pairing state files shared by pairing_app and app.
AUTHORIZED_KEYS_FILE = "/root/.ssh/authorized_keys"
TUNNEL_USER = "root"
PAIRING_RUN_DIR = "/run/zeroforce"
DEV_MODE_FLAG = "/boot/devmode"
TUNNEL_ACTIVE_FLAG = os.path.join(PAIRING_RUN_DIR, "tunnel_active")
SINCE_CONNECTED_FILE = os.path.join(PAIRING_RUN_DIR, "since-connected")
PAIRING_TIMEOUT_SECONDS = int(os.environ.get("ZEROFORCE_PAIRING_TIMEOUT", "300"))

_logger = logging.getLogger(__name__)


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
        _logger.error("Error reading %s: %s", AUTHORIZED_KEYS_FILE, exc)
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
        _logger.warning("Invalid integer in %s: %r", SINCE_CONNECTED_FILE, raw)
        return None
    except Exception as exc:
        _logger.error("Error reading %s: %s", SINCE_CONNECTED_FILE, exc)
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
 
    if not has_active_tunnel_connections() and os.path.exists(DEV_MODE_FLAG):
        return True

    if not has_configured_key():
        return True

    since = get_since_connected_seconds()
    if since is None:
        return False

    return since >= PAIRING_TIMEOUT_SECONDS
