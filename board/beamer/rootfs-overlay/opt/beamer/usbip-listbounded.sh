#!/bin/sh
find /sys/bus/usb/drivers/usbip-host/ -maxdepth 1 -type l -exec basename {} \;
