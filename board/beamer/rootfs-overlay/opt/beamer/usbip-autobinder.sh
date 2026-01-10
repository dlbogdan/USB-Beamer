#!/bin/sh

# This scripts auto binds all devices returned from lsusb-nohubs.sh that are not yet bounded with usbip
# it is run as a service that runs every 10 seconds to check for new devices and bind them if needed

# loop forever
while true; do

# get the list of devices from lsusb-nohubs.sh
devices=$(./lsusb-nohubs.sh)
#format is for example 1-1.4,0658:0200
# get the list of bounded devices from usbip-listbounded.sh
bounded=$(./usbip-listbounded.sh)

# compare the two lists and bind the devices that are not bounded
for device in $devices; do   #format is for example 1-1.4,0658:0200
    busid=$(echo "$device" | cut -d ',' -f 1)
    # bounded list only contains busids, so compare on busid alone
    if ! printf '%s\n' "$bounded" | grep -q "^$busid$"; then
        usbip bind -b "$busid"
    fi
done

# sleep for 10 seconds
sleep 10

done