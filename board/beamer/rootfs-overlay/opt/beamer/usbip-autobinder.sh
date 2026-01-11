#!/bin/sh

# Auto-bind all plugged devices that are not yet bound with usbip.
# Runs in a loop via a service, checking every 10 seconds.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

while true; do
  devices="$("$SCRIPT_DIR/list-plugged.sh")"
  bounded="$("$SCRIPT_DIR/usbip-listbounded.sh")"

  # devices format example: 1-1.4,0658:0200
  for device in $devices; do
    busid=$(echo "$device" | cut -d',' -f1)
    [ -n "$busid" ] || continue
    # bounded list only contains busids, so compare on busid alone
    if ! printf '%s\n' "$bounded" | grep -q "^$busid$"; then
      usbip bind -b "$busid"
    fi
  done

  sleep 10
done