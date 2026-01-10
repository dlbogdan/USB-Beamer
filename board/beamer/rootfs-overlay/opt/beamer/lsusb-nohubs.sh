#!/bin/sh
#alternative to the expensive usbip list -l -p command
for d in /sys/bus/usb/devices/*; do
  b=$(basename "$d")
  [[ "$b" == *:* ]] && continue 
  [[ -f "$d/idVendor" ]] || continue # skip devices without VID:PID
  [[ "$(cat "$d/bDeviceClass")" == "09" ]] && continue # skip hubs
  echo "$b,$(cat "$d/idVendor"):$(cat "$d/idProduct")"
done
