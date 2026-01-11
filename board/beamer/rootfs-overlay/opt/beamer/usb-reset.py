#!/usr/bin/env python3
import fcntl, os, sys

USBDEVFS_RESET = ord("U") << 8 | 20  # _IO('U', 20)

def resolve_devpath(arg: str) -> str:
    """Return /dev/bus/usb/BBB/DDD from either a device path or a sysfs-style USB id."""
    if arg.startswith("/dev/bus/usb/"):
        return arg

    base = arg.split(":")[0]  # drop interface suffix like :1.0
    sysdev = f"/sys/bus/usb/devices/{base}"
    busnum_path = f"{sysdev}/busnum"
    devnum_path = f"{sysdev}/devnum"

    if not (os.path.isfile(busnum_path) and os.path.isfile(devnum_path)):
        raise ValueError(f"Not a known USB device id: {arg}")

    with open(busnum_path) as f:
        bus = int(f.read().strip())
    with open(devnum_path) as f:
        dev = int(f.read().strip())

    return f"/dev/bus/usb/{bus:03d}/{dev:03d}"


def reset(devpath: str):
    fd = os.open(devpath, os.O_WRONLY)
    try:
        fcntl.ioctl(fd, USBDEVFS_RESET, 0)
        print(f"Reset OK: {devpath}")
    finally:
        os.close(fd)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            f"Usage: {sys.argv[0]} /dev/bus/usb/BBB/DDD | <usb-id like 1-2.3[:1.0]>",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        path = resolve_devpath(sys.argv[1])
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)
    reset(path)