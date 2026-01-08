# Buildroot Configuration for USB-Beamer-server

## Boot Partition Auto-Mount

This configuration automatically mounts the boot partition at boot time by dynamically detecting the device name.

### Files Created

1. **`board/rootfs-overlay/etc/init.d/S01mountboot`** - Init script that dynamically detects and mounts the boot partition
2. **`board/post-build.sh`** - Post-build script to set correct permissions

### Buildroot Configuration

Add these lines to your Buildroot `.config` or `defconfig`:

```
BR2_ROOTFS_OVERLAY="board/rootfs-overlay"
BR2_ROOTFS_POST_BUILD_SCRIPT="board/post-build.sh"
```

Or in `menuconfig`:
- **System configuration → Root filesystem overlay directories**: `board/rootfs-overlay`
- **System configuration → Custom scripts to run before creating filesystem images**: `board/post-build.sh`

### How It Works

The script (`S01mountboot`) will:
1. Read `/proc/cmdline` to find the root device
2. Derive the boot partition from the root device:
   - MMC/SD cards: `/dev/mmcblk0pX` → `/dev/mmcblk0p1`
   - SATA/USB drives: `/dev/sdaX` → `/dev/sda1`
   - NVMe drives: `/dev/nvme0n1pX` → `/dev/nvme0n1p1`
3. Mount the boot partition to `/boot`

### Testing

After booting your Buildroot system:

```bash
# Check if boot is mounted
mount | grep boot

# Verify contents
ls -la /boot
```

### Troubleshooting

If the boot partition doesn't mount:

```bash
# Check what the script detected
cat /proc/cmdline

# Manually run the init script with debug
sh -x /etc/init.d/S01mountboot start

# Check available block devices
ls -la /dev/sd* /dev/mmcblk* /dev/nvme* 2>/dev/null
```

## SSH Tunnel Pairing & Zeroforce API

The Beamer device exposes a small HTTP API used by the Home Assistant add‑on
to automatically provision the SSH public key that will be allowed to connect
to the dedicated SSH tunnel daemon (`beamer-sshd` on port 8007, configured by
`/opt/beamer/beamer-ssh-tunnel` and using `/root/.ssh/authorized_keys`).

### Pairing mode model

- **No persistent pairing state is stored on disk.** The device is either:
  - **In pairing mode**: it will accept a new public key from the client.
  - **Not in pairing mode**: it will reject attempts to change the key.
- **Pairing mode is derived from SSH tunnel activity**:
  - While there is an **active SSH connection** to the tunnel (from Home Assistant),
    the device is **not** in pairing mode.
  - If there is **no active SSH connection** for a configurable timeout (e.g. 10 minutes)
    after a previous connection dropped, the device **enters pairing mode**.
  - On the **very first connection after boot / initial setup**, pairing can be
    entered immediately once no client is connected, without waiting for the timeout.
- This behaviour is specifically chosen so that:
  - Normal Home Assistant restarts or short network blips do **not** immediately
    re‑open pairing.
  - A user can intentionally stop the tunnel and, after the timeout, re‑pair a
    new Home Assistant instance if needed.

### Zeroforce HTTP endpoints

These endpoints are served by the Beamer Flask app (`/opt/beamer/app.py`) on
its HTTP port (`APP_PORT`, default 5000).

#### `GET /zeroforce/readytopair`

- **Always available**, regardless of whether the device is currently in pairing mode.
- Returns whether the device is ready to accept a new SSH public key:
  - HTTP 200 with a simple body of `true` or `false` (lower‑case),
    indicating if the device is currently in pairing mode.
- Typical Home Assistant add‑on flow:
  1. Discover / connect to the Beamer device on the LAN.
  2. Call `/zeroforce/readytopair`.
  3. Only if the response body is `true`, proceed to call `/zeroforce/setkey`.

#### `POST /zeroforce/setkey`

- **Only effective while in pairing mode**:
  - If the device is not currently in pairing mode, the server should return
    an error (e.g. HTTP 403) and ignore the request.
- Input:
  - The request contains a single SSH public key (e.g. `ssh-ed25519 ...` or
    `ssh-rsa ...`) supplied by the Home Assistant add‑on.
  - The exact payload format is implementation‑defined (for example, the key
    can be sent as a form field named `key`, similar to the existing `/add`
    endpoint).
- Behaviour:
  - The implementation **replaces any existing key** in
    `AUTHORIZED_KEYS_FILE` with the provided key.
  - Only **one client key is kept at a time**; the Beamer tunnel is intended
    to be used by a single Home Assistant instance.
  - File permissions are set appropriately (directory `0700`, file `0600`) so
    that `beamer-sshd` running as `root` can read the key.
  - After a successful key update, future SSH connections to the tunnel must
    authenticate using this new key.

### Expected Home Assistant add‑on flow

1. The add‑on generates or loads its SSH key pair to use for the tunnel.
2. It discovers the Beamer device on the LAN (for example via the
   `_beamerzf._tcp` mDNS service published by `S91avahi-beamer`) or via a
   configured IP/hostname.
3. It calls `GET /zeroforce/readytopair`:
   - If the response is `false`, the add‑on waits and retries later.
   - If the response is `true`, it immediately calls `POST /zeroforce/setkey`
     with its SSH public key.
4. Once `setkey` succeeds, the add‑on establishes the SSH tunnel to the
   Beamer device on port 8007 using the corresponding private key.
5. As long as that SSH tunnel remains connected regularly, the Beamer will
   not re‑enter pairing mode, avoiding accidental re‑pairing during normal
   Home Assistant restarts.
