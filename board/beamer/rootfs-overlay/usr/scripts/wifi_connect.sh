#!/bin/sh

# Usage: wifi_connect.sh <iface> <wpa_conf_path> [timeout_seconds]
# Example: wifi_connect.sh wlan0 /etc/wpa_supplicant/wpa_supplicant-wlan0.conf 25

set -eu

IFACE=${1:-wlan0}
CONF_PATH=${2:-/etc/wpa_supplicant/wpa_supplicant-${IFACE}.conf}
TIMEOUT=${3:-25}

# Stop provisioning AP if running
/etc/init.d/S49provision stop >/dev/null 2>&1 || true

# Reset interface
ip link set "${IFACE}" down >/dev/null 2>&1 || true
ip addr flush dev "${IFACE}" >/dev/null 2>&1 || true
ip link set "${IFACE}" up >/dev/null 2>&1 || true

# Restart wpa_supplicant with provided config
killall wpa_supplicant >/dev/null 2>&1 || true
wpa_supplicant -B -i "${IFACE}" -c "${CONF_PATH}"

# DHCP (BusyBox udhcpc)
udhcpc -i "${IFACE}" -n -q -t 5 >/dev/null 2>&1 || true

# Wait for an IPv4 address
end_time=$(( $(date +%s) + TIMEOUT ))
while [ $(date +%s) -lt ${end_time} ]; do
  if ip -4 -o addr show dev "${IFACE}" | grep -q inet; then
    exit 0
  fi
  sleep 1
done

exit 1


