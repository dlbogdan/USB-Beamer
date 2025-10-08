#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

# Clean up stale pid files from previous runs to prevent startup errors.
rm -f /run/dbus/pid

# Start essential background services.
# The -D flag keeps them in the foreground, so we send them to the background with '&'
/usr/sbin/sshd -D -e &
# Use the PATH to find usbipd, as its location can vary.
usbipd -D &

# Start Avahi and publish the service.
mkdir -p /var/run/dbus
dbus-daemon --system
sleep 1 # Give D-Bus a moment.
avahi-daemon -D --no-chroot &
avahi-publish-service beamer-server _usbip._tcp ${TUNNEL_PORT} "USB Beamer Server" &

echo "All background services started."

# Use exec to replace the shell with the Python process.
# This ensures that the Flask app becomes PID 1 and handles signals correctly.
exec python3 /app/app.py 