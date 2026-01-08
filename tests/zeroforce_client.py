#!/usr/bin/env python3

"""
Simple CLI client for testing the zeroforce pairing and USB APIs.

Usage examples:

  # Check if the device is ready to pair (pairing app, default port 5000)
  python zeroforce_client.py --base-url http://DEVICE_IP:5000 readytopair

  # Install/replace the SSH public key for the tunnel (reads key from stdin)
  cat id_ed25519.pub | python zeroforce_client.py --base-url http://DEVICE_IP:5000 setkey

  # List USB devices via the tunnel (USB app typically on localhost, port 6000)
  python zeroforce_client.py --base-url http://127.0.0.1:6000 lsusb

  # Bind devices by abstract IDs (see ids from lsusb output)
  python zeroforce_client.py --base-url http://127.0.0.1:6000 bind --ids 1 2

  # Bind devices by VID:PID pairs
  python zeroforce_client.py --base-url http://127.0.0.1:6000 bind --vidpid 1234:5678 1d6b:0002
"""

import argparse
import json
import sys
from typing import List

import requests


def make_url(base: str, path: str) -> str:
    return base.rstrip("/") + path


def cmd_readytopair(args: argparse.Namespace) -> int:
    url = make_url(args.base_url, "/zeroforce/readytopair")
    try:
        resp = requests.get(url, timeout=args.timeout)
    except requests.RequestException as exc:
        print(f"ERROR: request to {url} failed: {exc}", file=sys.stderr)
        return 1

    print(f"HTTP {resp.status_code}")
    print(resp.text.strip())
    return 0 if resp.ok else 1


def cmd_setkey(args: argparse.Namespace) -> int:
    url = make_url(args.base_url, "/zeroforce/setkey")

    key = args.key or ""
    if not key:
        # Read the key from stdin if not provided via --key.
        key = sys.stdin.read().strip()

    if not key:
        print("ERROR: no key provided via --key or stdin", file=sys.stderr)
        return 1

    try:
        # Use form-encoded data for maximum compatibility with existing apps.
        resp = requests.post(url, data={"key": key}, timeout=args.timeout)
    except requests.RequestException as exc:
        print(f"ERROR: request to {url} failed: {exc}", file=sys.stderr)
        return 1

    print(f"HTTP {resp.status_code}")
    print(resp.text.strip())
    return 0 if resp.ok else 1


def cmd_lsusb(args: argparse.Namespace) -> int:
    url = make_url(args.base_url, "/zeroforce/lsusb")
    try:
        resp = requests.get(url, timeout=args.timeout)
    except requests.RequestException as exc:
        print(f"ERROR: request to {url} failed: {exc}", file=sys.stderr)
        return 1

    print(f"HTTP {resp.status_code}")
    if not resp.ok:
        print(resp.text.strip())
        return 1

    try:
        data = resp.json()
    except json.JSONDecodeError:
        print("Non-JSON response:")
        print(resp.text)
        return 1

    print(json.dumps(data, indent=2, sort_keys=True))
    return 0


def _parse_vidpid_list(raw: List[str]) -> List[dict]:
    result: List[dict] = []
    for item in raw:
        item = item.strip()
        if not item:
            continue
        if ":" not in item:
            print(f"WARNING: ignoring invalid VID:PID '{item}'", file=sys.stderr)
            continue
        vid, pid = item.split(":", 1)
        vid = vid.strip()
        pid = pid.strip()
        if not vid or not pid:
            print(f"WARNING: ignoring invalid VID:PID '{item}'", file=sys.stderr)
            continue
        result.append({"vid": vid, "pid": pid})
    return result


def cmd_bind(args: argparse.Namespace) -> int:
    url = make_url(args.base_url, "/zeroforce/bind")

    ids = args.ids or []
    vidpids = _parse_vidpid_list(args.vidpid or [])

    payload: dict = {}
    if ids:
        payload["ids"] = ids
    if vidpids:
        payload["vidpids"] = vidpids

    if not payload:
        print("ERROR: you must provide at least one --ids or --vidpid value", file=sys.stderr)
        return 1

    try:
        resp = requests.post(url, json=payload, timeout=args.timeout)
    except requests.RequestException as exc:
        print(f"ERROR: request to {url} failed: {exc}", file=sys.stderr)
        return 1

    print(f"HTTP {resp.status_code}")
    try:
        data = resp.json()
        print(json.dumps(data, indent=2, sort_keys=True))
    except json.JSONDecodeError:
        print(resp.text.strip())

    return 0 if resp.ok else 1


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Test client for zeroforce pairing/USB APIs")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:5000",
        help=(
            "Base URL of the app. "
            "Use e.g. http://DEVICE_IP:5000 for pairing endpoints, "
            "or http://127.0.0.1:6000 for USB endpoints via SSH tunnel."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="HTTP request timeout in seconds (default: 5.0)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # /zeroforce/readytopair
    p_ready = subparsers.add_parser("readytopair", help="Check if device is in pairing mode")
    p_ready.set_defaults(func=cmd_readytopair)

    # /zeroforce/setkey
    p_setkey = subparsers.add_parser("setkey", help="Install/replace the tunnel SSH public key")
    p_setkey.add_argument(
        "--key",
        help="Public key string. If omitted, the key is read from stdin.",
    )
    p_setkey.set_defaults(func=cmd_setkey)

    # /zeroforce/lsusb
    p_lsusb = subparsers.add_parser(
        "lsusb",
        help="List USB devices (requires tunnel to USB app, usually on port 6000)",
    )
    p_lsusb.set_defaults(func=cmd_lsusb)

    # /zeroforce/bind
    p_bind = subparsers.add_parser(
        "bind",
        help="Bind USB devices by abstract IDs and/or VID:PID pairs",
    )
    p_bind.add_argument(
        "--ids",
        type=int,
        nargs="+",
        help="Abstract device IDs as reported by the /zeroforce/lsusb endpoint",
    )
    p_bind.add_argument(
        "--vidpid",
        nargs="+",
        help="One or more VID:PID pairs (e.g. 1d6b:0002 1234:5678)",
    )
    p_bind.set_defaults(func=cmd_bind)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

