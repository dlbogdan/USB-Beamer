#!/bin/sh

# Simple background monitor that watches for active SSH tunnel connections to
# the beamer-sshd instance and exposes a flag file in /run for other
# processes (such as the Flask app) to consume.
#
# It sets or removes /run/zeroforce/tunnel_active depending on whether there
# is at least one ESTABLISHED TCP connection on the configured tunnel port.

TUNNEL_PORT="${ZEROFORCE_TUNNEL_PORT:-8007}"
PAIRING_RUN_DIR="/run/zeroforce"
FLAG_FILE="${PAIRING_RUN_DIR}/tunnel_active"

mkdir -p "${PAIRING_RUN_DIR}"

has_active_tunnel_connections() {
  # Use netstat to detect ESTABLISHED TCP connections involving the tunnel
  # port. We don't care whether it's local or foreign, any established
  # connection on that port means the tunnel is in use.
  #
  # BusyBox netstat supports "-tn".
  if netstat -tn 2>/dev/null | grep ESTABLISHED | grep -q ":${TUNNEL_PORT} "; then
    return 0
  fi

  return 1
}

while true; do
  if has_active_tunnel_connections; then
    # Indicate that there is at least one active tunnel connection.
    : > "${FLAG_FILE}"
  else
    # No active tunnel connections detected.
    [ -e "${FLAG_FILE}" ] && rm -f "${FLAG_FILE}"
  fi

  sleep 5
done


