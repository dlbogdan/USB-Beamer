# Architecture Diagrams for Video
**Purpose**: Visual aids to explain the USB-Beamer system and addon workflow  
**Tools**: Draw.io, Excalidraw, PowerPoint, Keynote, or similar

---

## DIAGRAM 1: System Architecture Overview

### Components to Show

```
┌─────────────────────────────────────────────────────────────┐
│                      Home Network                            │
│                                                              │
│  ┌──────────────────┐           ┌─────────────────────┐    │
│  │  Home Assistant  │           │  USB-Beamer Server  │    │
│  │   (HAOS/Docker)  │           │   (Raspberry Pi)     │    │
│  │                  │           │                      │    │
│  │  ┌────────────┐  │           │  ┌──────────────┐  │    │
│  │  │ USB Beamer │  │  SSH      │  │  USB/IP      │  │    │
│  │  │   Addon    │◄─┼───Tunnel──┼─►│  Daemon      │  │    │
│  │  │            │  │  (Port    │  │              │  │    │
│  │  │ (Auto-     │  │   3240)   │  │  (usbipd)    │  │    │
│  │  │ Discovery) │  │           │  └──────┬───────┘  │    │
│  │  └────────────┘  │           │         │          │    │
│  │                  │           │  ┌──────▼───────┐  │    │
│  │  USB devices    │           │  │ USB Dongles  │  │    │
│  │  appear local   │           │  │              │  │    │
│  │                  │           │  │ • Z-Wave     │  │    │
│  └──────────────────┘           │  │ • Zigbee     │  │    │
│                                  │  │ • Others     │  │    │
│         ▲                        │  └──────────────┘  │    │
│         │                        │                     │    │
│         │ Avahi/mDNS Discovery   │  ┌──────────────┐  │    │
│         └────────────────────────┼──┤ Web Interface│  │    │
│                                  │  │ (Port 5000)  │  │    │
│                                  │  └──────────────┘  │    │
│                                  └─────────────────────┘    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Key Points to Highlight
- **Avahi discovery**: No manual IP configuration needed
- **SSH tunnel**: Encrypted, secure communication
- **USB/IP protocol**: Kernel-level USB device sharing
- **Zero-config**: Addon handles everything automatically

### Visual Style
- Clean, modern look
- Use different colors for different layers:
  - **Green**: Home Assistant components
  - **Blue**: Network/communication layer
  - **Orange**: USB-Beamer server components
  - **Red**: Physical USB devices
- Use arrows to show data flow
- Add small icons for each component (USB symbol, lock for SSH, etc.)

---

## DIAGRAM 2: Setup Workflow (Step-by-Step)

### Step 1: Initial Setup
```
┌─────────────────────┐
│  Flash USB-Beamer   │
│  to Raspberry Pi    │
│  SD Card            │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Boot Raspberry Pi  │
│  Connect to Network │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Open Web Interface │
│  (beamer.local:5000)│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Select USB Devices │
│  to Share/Export    │
└─────────────────────┘
```

### Step 2: Home Assistant Integration
```
┌────────────────────────┐
│  Install USB Beamer    │
│  Addon in Home         │
│  Assistant             │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│  Addon Generates SSH   │
│  Key Pair on First     │
│  Start                 │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│  Copy Public Key from  │
│  Addon Log Tab         │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│  Paste Key into USB-   │
│  Beamer Web Interface  │
│  (Authorized Keys)     │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│  Addon Auto-Discovers  │
│  USB-Beamer via Avahi  │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│  SSH Tunnel Established│
│  (Encrypted Connection)│
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│  USB Devices           │
│  Automatically Attached│
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│  ✅ USB Devices Now    │
│  Available in Home     │
│  Assistant!            │
└────────────────────────┘
```

### Visual Style
- Use numbered steps (1, 2, 3...)
- Add checkmarks for completed steps during demo
- Show screenshots thumbnail next to each step
- Use timeline/progress bar at the bottom

---

## DIAGRAM 3: Problem vs. Solution (Before/After)

### BEFORE: Traditional USB Setup
```
                    ❌ PROBLEMS:
                    
┌──────────────┐    • 5-meter cable limit
│   Home       │    • Signal degradation
│   Assistant  │    • Cable mess
│   Server     │    • Physical proximity required
│   (Closet)   │
└──────┬───────┘
       │
       │ 📏 Long USB cable
       │    (limited distance)
       ▼
┌──────────────┐
│   Z-Wave     │
│   Dongle     │
│   (Living    │
│    Room)     │
└──────────────┘

OR use USB extenders (unreliable)
OR move server (inconvenient)
```

### AFTER: USB-Beamer Solution
```
                    ✅ BENEFITS:
                    
┌──────────────┐    • Unlimited network distance
│   Home       │    • No signal issues
│   Assistant  │    • Clean cable management
│   Server     │    • Remote placement
│   (Closet)   │    • Multiple dongles easy
└──────┬───────┘
       │
       │ 🌐 Network (Ethernet/WiFi)
       │    SSH Tunnel (Secure)
       │
       ▼
┌──────────────┐
│  USB-Beamer  │
│  (Raspberry  │
│   Pi)        │
└──────┬───────┘
       │
       │ USB (local)
       │
       ▼
┌──────────────┐
│   Z-Wave     │
│   Zigbee     │
│   Other USB  │
│   Dongles    │
└──────────────┘
```

### Visual Style
- Side-by-side comparison
- Red X's for problems
- Green checkmarks for benefits
- Visual clutter on left (tangled cables)
- Clean and organized on right

---

## DIAGRAM 4: SSH Tunnel Security Layer

### Visual Representation
```
Home Assistant                      USB-Beamer Server
┌─────────────┐                    ┌─────────────┐
│             │   🔐 ENCRYPTED     │             │
│  USB Beamer │   SSH TUNNEL       │   usbipd    │
│    Addon    ├────────────────────┤   daemon    │
│             │   Port 3240        │             │
│             │   (Firewalled)     │             │
└─────────────┘                    └─────────────┘
      ▲                                    │
      │                                    ▼
      │                            ┌──────────────┐
      │                            │  USB Devices │
      │                            └──────────────┘
      │
      │ USB/IP Protocol
      │ (Tunneled over SSH)
      │
      └─────── Appears Local ───────┘
```

### Key Security Points to Annotate
- **SSH Key Authentication**: No passwords, more secure
- **Encrypted Traffic**: All USB data is encrypted
- **Firewalled Ports**: Only SSH accessible externally
- **Automatic Key Management**: Addon handles key generation

---

## DIAGRAM 5: Multi-Device Scenario

### Showing Scalability
```
        Home Assistant Server
┌────────────────────────────────┐
│                                │
│  USB Beamer Addon              │
│  (Single Installation)         │
│                                │
└───┬───────────┬────────────┬───┘
    │           │            │
    │ SSH       │ SSH        │ SSH
    │ Tunnel    │ Tunnel     │ Tunnel
    │           │            │
    ▼           ▼            ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│ Beamer  │ │ Beamer  │ │ Beamer  │
│   #1    │ │   #2    │ │   #3    │
│         │ │         │ │         │
│ Living  │ │ Bedroom │ │ Garage  │
│ Room    │ │         │ │         │
└────┬────┘ └────┬────┘ └────┬────┘
     │           │           │
     ▼           ▼           ▼
  Z-Wave      Zigbee     Thread
  Dongle      Dongle     Dongle
```

### Key Points
- Single addon can manage multiple servers
- Auto-discovery finds all servers automatically
- Each server can have different dongles
- Strategic placement throughout house

---

## DIAGRAM 6: Technical Stack Layers

### Layer Visualization
```
┌─────────────────────────────────────────┐
│  User Layer: Home Assistant Dashboard  │
│  (Z-Wave, Zigbee integrations)          │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  Addon Layer: USB Beamer Addon          │
│  (Python, Discovery, SSH Management)    │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  Protocol Layer: USB/IP over SSH        │
│  (Encrypted Tunnel, Port 3240)          │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  Server Layer: USB-Beamer (Buildroot)   │
│  (usbipd, Avahi, Flask, SSH Server)     │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  Hardware Layer: Raspberry Pi + USB     │
│  (USB Dongles, Ethernet/WiFi)           │
└─────────────────────────────────────────┘
```

---

## Animation Suggestions

### For Video B-Roll

1. **Connection Animation**
   - Show dotted line between HA and USB-Beamer
   - Line becomes solid when connection established
   - Add "lock" icon to show encryption

2. **Discovery Animation**
   - Ripple/pulse effect from USB-Beamer
   - "Found!" notification appears at Home Assistant
   - Beamer icon pops up

3. **Device Attachment Animation**
   - USB device icon moves from server to Home Assistant
   - Smooth transition with arrow
   - Checkmark appears when attached

4. **Data Flow Animation**
   - Animated dots/particles flowing through SSH tunnel
   - Bidirectional flow
   - Pulsing to show active communication

---

## Tools & Resources

### Diagramming Software

#### ⭐ Best for Wacom Tablets (Hand-Drawn Style)
- **Concepts** (paid, ~$10/month or $100 lifetime) - **HIGHLY RECOMMENDED for Wacom**
  - Infinite canvas, vector-based (scales perfectly for 4K)
  - Excellent pressure sensitivity
  - Professional yet hand-drawn look
  - Perfect for technical diagrams with personality
  - Export to PNG/SVG at any resolution
  
- **Krita** (free, open source) - **Best FREE option for Wacom**
  - Exceptional tablet support and brush engine
  - Great for more artistic/illustrated diagrams
  - Raster-based (use large canvas size: 3840x2160 for 4K)
  - Huge brush library
  
- **Affinity Designer** (one-time $70) - **Best professional alternative**
  - Full Wacom pressure sensitivity
  - Vector-based (infinitely scalable)
  - Mix vector and raster elements
  - Cheaper than Adobe Illustrator
  
- **Adobe Illustrator** (if you have Creative Cloud)
  - Industry standard, full tablet support
  - Perfect for clean, professional diagrams with hand-drawn elements
  - Can mix precise shapes with freehand annotations

#### Traditional Mouse/Keyboard Tools
- **Draw.io** (free, web-based) - Quick and simple
- **Excalidraw** (free, web-based) - Hand-drawn look without drawing
- **Lucidchart** (paid) - Professional templates
- **PowerPoint/Keynote** - Simple shapes and animations
- **Figma** (free for basic) - Modern, collaborative

### Icons & Assets
- **Noun Project** - Free icons (USB, network, lock, etc.)
- **Flaticon** - Device icons
- **Font Awesome** - Simple line icons
- **Material Design Icons** - Clean, modern look

### Color Palette Suggestion
- **Primary**: `#2196F3` (Blue - network/technology)
- **Secondary**: `#4CAF50` (Green - Home Assistant)
- **Accent**: `#FF9800` (Orange - USB-Beamer)
- **Danger**: `#F44336` (Red - problems/warnings)
- **Background**: `#FAFAFA` (Light gray)
- **Text**: `#212121` (Dark gray)

---

## Tips for Creating Video Diagrams

### General Tips
1. **Keep it Simple**: Don't overwhelm with details
2. **Use Animation**: Build diagrams step-by-step
3. **High Contrast**: Ensure readability on all screens
4. **Large Text**: Minimum 24pt font for labels
5. **Consistent Style**: Use same icon set throughout
6. **Export at 4K**: Even if video is 1080p (allows zoom)
7. **White Space**: Don't crowd elements
8. **Test on Mobile**: Many viewers watch on phones

### Wacom Tablet-Specific Tips
1. **Hand-Drawn Advantage**: Sketchy diagrams feel more personal and engaging on video
2. **Layer Strategy**: 
   - Bottom layer: Clean geometric shapes (rectangles, circles)
   - Top layer: Hand-drawn arrows and annotations with tablet
   - Creates "explaining on whiteboard" feel
3. **Pressure Sensitivity**: Use varying line weights for emphasis
   - Thick lines for main components
   - Thin lines for connections
   - Medium for annotations
4. **Animation-Friendly**: Draw elements on separate layers for easy animation
5. **Canvas Size**: Start with 3840x2160 (4K) even for raster tools
6. **Brush Recommendations**:
   - Use slightly textured brush (not perfectly smooth)
   - Adds warmth and personality
   - Avoid too sketchy (hard to read)
7. **Hybrid Approach**: 
   - Use ruler/shape tools for boxes and lines
   - Add hand-drawn arrows, callouts, and emphasis marks with tablet
   - Best of both worlds: professional + personal

---

**Time Estimate**: 2-3 hours to create all diagrams  
**Pro Tip**: Create a template with your colors/fonts first, then duplicate for each diagram

