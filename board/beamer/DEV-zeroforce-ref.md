## Zeroforce SSH Tunnel Pairing – Developer Notes

This document captures the **internal design** for the Zeroforce SSH tunnel
pairing mechanism between the Beamer device (server) and the Home Assistant
add-on (client). It is meant as **developer-facing documentation** and may
describe behaviour that is not yet fully wired up in production images.

---

### High-level goals

- Allow the Home Assistant add-on to **automatically provision** the SSH
  public key used for the dedicated tunnel (`beamer-sshd` on port `8007`).
- Avoid storing complex pairing state on disk; instead, derive “pairing mode”
  from **tunnel activity**.
- Ensure that **only one client key** is active at any given time.
- Keep tunnel-activity detection **out of the Flask app** and in a separate
  small service.

---

### Components

- **Dedicated SSH daemon**
  - Config file: `/opt/beamer/beamer-ssh-tunnel`
  - Listens on port `8007` by default.
  - Uses `/root/.ssh/authorized_keys` (or another `AuthorizedKeysFile`) to
    decide which client key may open the tunnel.

- **Tunnel activity monitor**
  - Script: `/opt/beamer/zeroforce_tunnel_monitor.sh`
  - (Previously had an OpenRC init script `S92zeroforce-monitor`; may be
    reintroduced to run the monitor as a background service.)
  - Purpose:
    - Periodically checks for **ESTABLISHED TCP connections** to the tunnel
      port using `netstat`.
    - Maintains a **flag file** in `/run` to represent “tunnel active”.

- **Application layer (Flask)**
  - Exposes HTTP endpoints for the Home Assistant add-on.
  - Implements pairing-mode logic **based on the monitor’s flag file**, *not*
    by inspecting the network stack directly.

---

### Tunnel activity monitor details

File: `board/beamer/rootfs-overlay/opt/beamer/zeroforce_tunnel_monitor.sh`

- **Environment / configuration**
  - `ZEROFORCE_TUNNEL_PORT` (optional): tunnel port, defaults to `8007`.

- **Runtime behaviour**
  - Creates runtime directory and flag:
    - Directory: `/run/zeroforce`
    - Flag file: `/run/zeroforce/tunnel_active`
  - Loop:
    - Every 5 seconds:
      - Runs `netstat -tn` (BusyBox-compatible).
      - Greps for `ESTABLISHED` lines involving `:${TUNNEL_PORT} `.
      - If at least one such line exists:
        - `touch /run/zeroforce/tunnel_active`
      - Otherwise:
        - `rm -f /run/zeroforce/tunnel_active`

- **Semantics of the flag file**
  - **Exists**: there is **at least one active SSH tunnel connection**.
  - **Absent**: no active tunnel connection detected in the last check.

The monitor is the **only code** that talks to `netstat` and interprets
kernel connection state.

---

### Pairing mode semantics

The Flask app (or equivalent application layer) uses the monitor’s flag file
to derive “pairing mode” as follows.

- **Inputs**
  - `has_active_tunnel_connections()`:
    - Returns `True` if `/run/zeroforce/tunnel_active` exists.
  - In-memory state:
    - `_has_ever_seen_tunnel_connection: bool`
    - `_last_no_connection_timestamp: float | None`
  - `PAIRING_TIMEOUT_SECONDS`:
    - Environment variable `ZEROFORCE_PAIRING_TIMEOUT`, default `600`
      (10 minutes).

- **Rules**
  - If there is an **active tunnel connection**:
    - Pairing mode is **OFF**.
    - `_has_ever_seen_tunnel_connection = True`
    - `_last_no_connection_timestamp = None`
  - If there is **no active tunnel connection** and
    `_has_ever_seen_tunnel_connection` is **False**:
    - Pairing mode is **ON immediately**.
    - This covers “first setup” or “no client has ever connected” cases.
  - If there is **no active connection** and
    `_has_ever_seen_tunnel_connection` is **True**:
    - On the **first observation** of no connections,
      `_last_no_connection_timestamp = now` and pairing remains **OFF**.
    - Once `now - _last_no_connection_timestamp >= PAIRING_TIMEOUT_SECONDS`:
      - Pairing mode becomes **ON** again.

- **Motivation**
  - Home Assistant restarts / short disruptions do **not immediately** reopen
    pairing.
  - A user can intentionally stop the tunnel and, after the timeout, re-pair
    a **new** Home Assistant instance.

---

### Zeroforce HTTP API (intended behaviour)

Note: exact implementation may live in `legacy_app.py` or a future refactor.
This section documents the intended contract with the Home Assistant add-on.

#### `GET /zeroforce/readytopair`

- **Purpose**: allow the add-on to poll whether the device is currently ready
  to accept a new SSH public key.
- **Response**:
  - HTTP 200
  - Body: literal text `true` or `false` (lower-case), not JSON.
    - `true`: in pairing mode (no active tunnel and timeout satisfied).
    - `false`: not in pairing mode.

#### `POST /zeroforce/setkey`

- **Purpose**: install or replace the single SSH public key that is allowed to
  connect to the tunnel.
- **Behaviour**:
  - If **not** in pairing mode:
    - Returns HTTP 403 with a JSON body such as:
      - `{ "ok": false, "error": "Not in pairing mode; refusing to change authorized key" }`
  - If in pairing mode:
    - Expects an SSH public key (e.g. `ssh-ed25519 ...` or `ssh-rsa ...`) in
      a request field (e.g. form field named `key`).
    - **Replaces** the contents of `AUTHORIZED_KEYS_FILE` with that single
      key.
    - Re-applies secure ownership and permissions (e.g. directory `0700`,
      file `0600`).
    - Returns HTTP 200 JSON:
      - `{ "ok": true }`

- **Constraints**
  - Exactly **one key** is kept; the Beamer tunnel is intended for a single
    Home Assistant instance.
  - Any future SSH tunnel connection must authenticate with this new key.

---

### Expected Home Assistant add-on flow

1. Generate or load the SSH key pair used to connect to the tunnel.
2. Discover the Beamer device on the LAN (e.g. via `_usbip._tcp` mDNS) or via
   configured IP/hostname.
3. Periodically call `GET /zeroforce/readytopair`:
   - If body is `false`, wait and retry later.
   - If body is `true`, immediately call `POST /zeroforce/setkey` with the
     public key.
4. After a successful `setkey`, establish the SSH tunnel to port `8007` using
   the corresponding private key.
5. Keep the tunnel connected under normal operation; as long as there are
   regular connections, the device will **not** re-enter pairing mode.

---

### Open questions / future improvements

- Whether to persist any lightweight “ever paired” marker to survive process
  restarts (current design keeps this purely in memory).
- Whether to add an **explicit “factory reset pairing”** mechanism (e.g. a
  button or special URL) that forces pairing mode regardless of tunnel state.
- Tightening security further with a short **pairing PIN** or token exchanged
  out-of-band between the Beamer UI and the Home Assistant add-on.


