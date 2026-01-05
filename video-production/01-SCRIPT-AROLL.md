# USB-Beamer Video Script (A-Roll)
**Target Duration**: 10-12 minutes  
**Tone**: Technical but accessible, enthusiastic  
**Audience**: Home Assistant users, self-hosters, makers

**Key Visual Element**: Custom 3D printed case showcased early to establish professional quality

---

## HOOK / INTRO (0:00 - 0:30)
**[VISUAL: Quick cuts of Home Assistant dashboard, USB dongles, rotating shot of the custom 3D printed case]**

Option 1
> "Trying to hook up that Z-Wave or Zigbee stick from the far side of your house to the Home Assistant box in the basement? Forget dragging long USB cables across the house—this project solves this properly."
Option 2
> "Trying to hook up that Z-Wave or Zigbee stick from the far side of your house to the Home Assistant box in the basement? Forget the long USB cables—I’m about to save your walls and your time by reusing your existing house wide-network, in the most elegant way you can imagine."

Option 3 (tight & confident)
> "Got a Z-Wave or Zigbee stick on the far side of the house and Home Assistant buried in the basement? Forget the USB spaghetti—I’ll show you how to ride your existing home network instead, cleanly and elegantly."
Option 4 (very punchy)
> "Z-Wave or Zigbee stick upstairs, Home Assistant in the basement? Ditch the USB cables—I’m about to put your existing home network to work, the right way." -- My currently prefered hook
Option 5 (slightly more dramatic)
> "Trying to bridge a Z-Wave or Zigbee stick upstairs to a Home Assistant box in the basement? Skip the ugly USB runs—I’ll show you how to let your home network do the heavy lifting, beautifully."


Original hook
> "What if you could take any USB device—a Z-Wave controller, a Zigbee stick — and share it across your network as if it were plugged directly into your machine? Today, I'm showing you USB-Beamer: a custom embedded Linux system that turns a Raspberry Pi into a network USB hub for Home Assistant."



**[VISUAL: Glamour shot of the finished device in the custom case, then project logo/title card]**

> "And stick around to the end, because I'll tease what's coming in the next video: a universal version that works with ANY client, including Windows machines."

---

## HARDWARE SHOWCASE (0:30 - 1:30)
**[VISUAL: Fusion 360 screen recording - rotating the 3D model]**

> "Before we dive into the problem this solves, let me show you what we're building. I designed this custom enclosure in Fusion 360 specifically for this project."

**[SCREEN RECORDING: Fusion 360 walkthrough of the case design]**

> "It houses a Raspberry Pi 3 A+, a compact USB hub with 4 ports, and a USB-C to micro-USB adapter—all in a clean, compact package. And yes, it works with other Pi models too if you need Ethernet."

**[B-ROLL: 3D printing timelapse]**

> "I 3D printed the case, and here's the result:"

**[B-ROLL: Smooth product shots of the assembled device - rotating, different angles, showing ports]**

> "A purpose-built appliance that looks as good as it works. No more bare circuit boards or messy setups—this is a  wife approved, professional solution you can proudly mount anywhere in your home."

**[B-ROLL: Hand holding the device, showing scale, plugging in USB dongles]**

> "Compact, clean, and ready to go. Now let's talk about WHY you'd want this."

---

## PROBLEM STATEMENT (1:30 - 2:30)
**[VISUAL: Home Assistant setup, USB cables everywhere, distance problems, then cut back to the clean USB-Beamer device]**

> "If you're running Home Assistant, you probably have USB dongles—Z-Wave, Zigbee, maybe a Bluetooth adapter. But here's the problem: those dongles need to be physically close to your devices AND plugged into your Home Assistant server. If your server is in a closet or data center, you're stuck running long USB cables or dealing with USB extenders because over long distances, we have signal losses to worry about"

**[B-ROLL: Messy cable management, USB extension limitations]**

> "USB has distance limits. Standard cables max out at 5 meters, and even with active extenders, you're fighting signal degradation. Plus, every time you need to access a different dongle, you're physically swapping cables or using a USB switch."

**[VISUAL: Diagram showing the limitation]**

> "What if there was a better way? What if your USB devices could just... be on the network?"

---

## SOLUTION INTRO (2:30 - 4:00)
**[VISUAL: Clean diagram of USB-Beamer architecture]**

> "Enter USB-Beamer. This project uses USB/IP—a kernel-level protocol securely wrapped in a tunnel, that shares USB devices over TCP/IP—packaged into a tiny, bootable Linux system built with Buildroot."

**[B-ROLL: USB-Beamer device booting in its case, LED activity visible through case]**

> "You flash this image onto an SD card, boot the device, and on first boot it creates its own WiFi access point. Connect with your phone, enter your home WiFi credentials through a simple web interface, and you're done. Your USB dongles instantly appear on your network, and your Home Assistant instance connects to them as if they were local."

**[B-ROLL: Web interface loading]**

> "It comes with a simple web interface for configuration, SSH access for troubleshooting, and automatic discovery via Avahi. No complex setup. No Docker containers. Just a purpose-built appliance that does one thing really well."

---

## TECHNICAL DEEP DIVE (4:00 - 7:30)

### Architecture Overview (4:00 - 5:00)
**[VISUAL: Architecture diagram with layers]**

> "Let me break down how this works. At the core is Buildroot—a tool for creating custom embedded Linux systems. Instead of running a full Ubuntu or Raspbian, USB-Beamer boots into a minimal, less than 100MB image that only includes what's needed."

**[B-ROLL: Buildroot configuration screens]**

> "The system runs:
> - A USB/IP daemon that exposes connected USB devices
> - An Avahi daemon for automatic network discovery
> - A Flask-based web server for configuration
> - SSH for remote access
> - And that's it. No unnecessary services, no bloat."

### Home Assistant Integration (5:00 - 6:00)
**[VISUAL: Home Assistant addon interface]**

> "For Home Assistant users, this is a game-changer. I've built a companion addon that makes integration completely automatic. You install the USB Beamer addon from the add-on store, and it handles everything—service discovery, SSH tunneling, and device attachment."

**[SCREEN RECORDING: Installing the addon, viewing the log for public key]**

> "When the addon starts for the first time, it generates an SSH key pair. You'll see the public key in the addon's log tab. Copy that key, paste it into your USB-Beamer server's web interface, and you're done. The addon automatically discovers USB-Beamer servers on your network via Avahi and establishes secure SSH tunnels."

**[SCREEN RECORDING: Showing the web interface with key pasted, then addon attaching devices]**

> "From that point on, the addon continuously monitors the connection and automatically attaches all USB devices that you've enabled on the server. No manual commands, no configuration files—it just works."

**[B-ROLL: Z-Wave devices appearing in Home Assistant]**

> "The same process works for Zigbee, Thread, or any other USB device you need to share. The addon handles reconnects, monitors tunnel health, and even survives Home Assistant restarts."

### Configuration Options (6:00 - 7:00)
**[SCREEN RECORDING: Web interface tour]**

> "The web interface makes configuration dead simple. You can:
> - See all connected USB devices in real-time
> - Configure network settings using a Netplan-like format
> - Change WiFi networks on the fly—scan for networks, select, and connect
> - View system status and logs
> - Manage SSH keys for the Home Assistant addon"

**[SCREEN RECORDING: WiFi setup page with network scanner]**

> "The initial setup is particularly slick. On first boot, the device creates an open WiFi access point called 'Beamer' with the hostname. Your phone automatically detects it and opens the captive portal. Scan for your home WiFi network, enter the password, and the device automatically switches from AP mode to station mode and connects to your network. No keyboard, no monitor, no Ethernet cable needed."

**[B-ROLL: Phone screen showing the WiFi setup process]**

> "And because it's running from a read-only SD card boot partition, the system is resilient to power failures. You can unplug it anytime without corrupting the filesystem."

### Use Cases (7:00 - 7:30)
**[VISUAL: Split-screen examples]**

> "Beyond Home Assistant, you can use this for:
> - Sharing a USB projector (hence the name 'Beamer')
> - Network-attached USB storage
> - Remote programming of microcontrollers
> - Lab equipment access
> - Basically anywhere you need USB over distance"

---

## BUILD & DEMO (7:30 - 10:00)

### Quick Build Overview (7:30 - 8:30)
**[SCREEN RECORDING: Terminal commands]**

> "Building this yourself is straightforward if you want to customize it. The repo includes everything:
> ```bash
> git clone --recursive https://github.com/your-username/USB-Beamer-server.git
> cd USB-Beamer-server
> make config
> make build
> ```
> Buildroot handles the rest. You'll get a bootable image that you flash to an SD card."

**[B-ROLL: SD card flashing process]**

> "Or, if you just want to use it, I'll link to pre-built images in the description."

**[B-ROLL: Quick shots of 3D printed case assembly]**

> "And if you want to build the case, the Fusion 360 files and STL files are all in the repo. Print, assemble, and you've got a production-ready device. This build uses a Pi 3 A+ for its compact size and built-in WiFi, but the image works on any Raspberry Pi—including models with Ethernet if you prefer a wired connection."

### Live Demo (8:30 - 10:00)
**[SCREEN RECORDING: Full workflow]**

> "Let me show you this in action. Here's my USB-Beamer device running with two dongles connected: a Z-Wave stick and a Zigbee coordinator."

**[B-ROLL: Show the physical device with dongles plugged in, LEDs active]**

**[Show web interface with devices listed]**

> "First, I'll select which devices to share on the USB-Beamer web interface—let's enable both the Z-Wave and Zigbee dongles."

**[Show Home Assistant addon interface]**

> "Now, over in Home Assistant, I've installed the USB Beamer addon. In the log tab, I can see it generated an SSH key pair on first start. I'll copy that public key..."

**[Show pasting key into USB-Beamer web interface]**

> "...and paste it here in the USB-Beamer server's authorized keys section."

**[Show addon log showing auto-discovery and connection]**

> "Watch this—the addon immediately discovers the USB-Beamer server via Avahi, establishes an SSH tunnel, and automatically attaches all the enabled USB devices. You can see it in the logs: 'Discovered beamer.local', 'SSH tunnel established', 'Attached Z-Wave dongle', 'Attached Zigbee coordinator'."

**[Show Home Assistant detecting and configuring the devices]**

> "And just like that, both devices appear in Home Assistant. I can now add the Z-Wave integration and the Zigbee integration—they detect the dongles as if they were plugged in locally. Full control, zero latency issues, and the dongles are 20 feet away in another room."

---

## NEXT VIDEO TEASER (10:00 - 11:00)
**[VISUAL: Exciting graphics/animations]**

> "Now, this version is optimized for Home Assistant and Linux clients. But what if you're on Windows? What if you want to share USB devices between ANY machines on your network?"

**[B-ROLL: Windows logo, macOS logo, generic USB devices]**

> "In the next video, I'm releasing a universal version of USB-Beamer. Windows clients. macOS support. Better web interface with live device switching. Think of it as a software KVM for USB devices."

**[VISUAL: Preview screenshots/mockups]**

> "I'll show you how to share a USB drive, a webcam, even a hardware security key across your network. If you want to see that, subscribe and hit the bell icon."

---

## CALL TO ACTION / OUTRO (11:00 - 11:30)
**[VISUAL: Back to talking head]**

> "If you found this useful, drop a like and let me know in the comments what USB devices YOU want to share over the network. The code is on GitHub—link in the description—and I'd love to see what you build with it."

**[VISUAL: GitHub link, social media handles]**

> "Thanks for watching, and I'll see you in the next one where we take this to the next level."

**[END SCREEN: Subscribe button, next video preview, other content]**

---

## NOTES FOR DELIVERY
- Pace: Keep energy high but not rushed
- Emphasize the "why" before the "how"
- Smile and show enthusiasm for the tech
- Use hand gestures to emphasize key points
- Pause after important statements to let them land
- Avoid filler words ("um", "uh", "like")
- Re-record any sections that don't feel natural

