for d in /sys/bus/usb/devices/*; do
  b=$(basename "$d")
  [[ "$b" == *:* ]] && continue
  [[ -f "$d/idVendor" ]] || continue
  [[ "$(cat "$d/bDeviceClass")" == "09" ]] && continue
  echo "$b,$(cat "$d/idVendor"):$(cat "$d/idProduct")"
done
