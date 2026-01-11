#!/bin/sh

# Usage: get-usb-info.sh <bus-port-id> (e.g. 1-1.3)
# Prints a human-readable vendor and product name, preferring udev's
# database strings and falling back to the device's own string descriptors.

DEV="$1"
[ -z "$DEV" ] && { echo "usage: $0 <bus-port-id>"; exit 1; }

SYS_PATH="/sys/bus/usb/devices/$DEV"
[ -d "$SYS_PATH" ] || { echo "no such device at $SYS_PATH" >&2; exit 1; }

props="$(udevadm info -q property -p "$SYS_PATH")"

get_prop() {
  echo "$props" | grep -E "^$1=" | head -1 | cut -d= -f2-
}

normalize_underscores() {
  echo "$1" | tr '_' ' '
}

json_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

vendor_db="$(get_prop ID_VENDOR_FROM_DATABASE)"
model_db="$(get_prop ID_MODEL_FROM_DATABASE)"
vendor_raw="$(get_prop ID_VENDOR)"
model_raw="$(get_prop ID_MODEL)"

# Fall back further to the raw sysfs string descriptors if udev props are empty.
[ -z "$vendor_raw" ] && vendor_raw="$(cat "$SYS_PATH/manufacturer" 2>/dev/null)"
[ -z "$model_raw" ] && model_raw="$(cat "$SYS_PATH/product" 2>/dev/null)"

vendor_out="${vendor_db:-$(normalize_underscores "$vendor_raw")}"
model_out="${model_db:-$(normalize_underscores "$model_raw")}"

# Trim extraneous whitespace
vendor_out="$(echo "$vendor_out" | sed -E 's/  +/ /g;s/^ //;s/ $//')"
model_out="$(echo "$model_out" | sed -E 's/  +/ /g;s/^ //;s/ $//')"

# JSON output
printf '{"vendor":"%s","product":"%s"}\n' \
  "$(json_escape "$vendor_out")" \
  "$(json_escape "$model_out")"
