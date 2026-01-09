app description:
this app will replace legacy_app.py and will have the following behaviour.
two main states: 
    1. pairing mode active
    2. pairing mode inactive

Pairing mode active is decided if :
    - there were never any succesfull connections to the tunnel ssh server
    - it passed more than 5 minutes since the last successfull connection to the tunnel ssh server (see since-connected file and tunnel-active file created by the service)

pairing mode allows a client (such as a home assistant addon, or a standalone program) to send its public key to this server through an api endpoint (See below) so that this client (and only this) can connect to the tunnel ssh

this app also sends if requested (zeroforce/lsusb), the list of usb devices available on the host. the ids are abstracted. the client gets a list of devices and an id associated (a simple incrementig number, not the usb id) 
the client can then request binding one or more usb devices by using the abstracted ids above or [PID & VID], if so, this server will use usbip to bind these devices and export them to be binded.
the full object specification in the list of devices contains:
    - id [int]
    - PID
    - VID
    - device_name [string]

api endpoints: 

available anytime (either in pairing mode or not):
/zeroforce/readytopair -> true|false 
    if pairing mode is active returns true, else false

available only if pairing mode is true:
/zeroforce/setkey (key) -> OK | NOK
    Replaces any existing content of AUTHORIZED_KEYS_FILE with the
    provided key, so that only one client can use the tunnel.

available only for connected client, while pairing mode is false, so through the tunnel itself (maybe just bind these to localhost only? might be a solution)
/zeroforce/lsusb -> list-of-objects
    lists the devices as described above
/zeroforce/bind (list-of-ids or list-of-pidvids) 
    instructs server to export these usb devices and then the client can connect to them using usbip

i want the app to be stateless, so for example if rebooted, the client will re-request the binding after requesting the usb list.
i also want to have guardrails so if a device is plugged out and into another usb port, it will be reexported and then rebinded succesfully. 