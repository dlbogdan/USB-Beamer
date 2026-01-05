# ⚡ Quick Reference Card
**Print this page and keep it handy during production!**

---

## 🎯 Video Specs
- **Duration**: 8-12 minutes
- **Resolution**: 1080p minimum (4K preferred)
- **Frame Rate**: 24fps or 60fps (hardware shots)
- **Target Audience**: Home Assistant users, self-hosters

---

## 📝 Script Structure (Approximate Times)

| Section | Time | Key Points |
|---------|------|------------|
| **Hook** | 0:00-0:30 | Grab attention, show 3D printed case |
| **Hardware Showcase** | 0:30-1:30 | Fusion 360, 3D print, finished device |
| **Problem** | 1:30-2:30 | USB distance limits, cable mess |
| **Solution** | 2:30-4:00 | Introduce USB-Beamer, USB/IP |
| **Technical** | 4:00-7:30 | Architecture, HA integration |
| **Demo** | 7:30-10:00 | Live walkthrough |
| **Teaser** | 10:00-11:00 | Next video preview |
| **Outro** | 11:00-11:30 | CTA, links, subscribe |

---

## ✅ Pre-Flight Checklist

### Before Recording A-Roll
- [ ] Camera battery charged
- [ ] Microphone tested (record 30s test)
- [ ] Lights positioned (face should be well-lit)
- [ ] Background clean and professional
- [ ] Script printed/on tablet nearby
- [ ] Phone on silent (no interruptions!)

### Before Recording Screen B-Roll
- [ ] Desktop cleaned (hide icons)
- [ ] Terminal font size: 16-18pt minimum
- [ ] Browser extensions disabled (privacy)
- [ ] Notifications turned OFF
- [ ] Screen recording software ready (OBS/etc)
- [ ] Mouse cursor slowed down

### Before Recording Hardware B-Roll
- [ ] Clean workspace/surface (plain background)
- [ ] **Excellent lighting** (softbox or ring light - not optional!)
- [ ] Camera on tripod (stable shots)
- [ ] Turntable or lazy susan ready (for rotation shots)
- [ ] 3D printed case clean and polished (no fingerprints!)
- [ ] Devices charged/powered
- [ ] 60fps enabled (for slow-motion options)
- [ ] Fusion 360 project file open and ready

### Before Recording WiFi Setup (Phone)
- [ ] Fresh SD card flash (to trigger first-boot AP mode)
- [ ] Phone screen recording enabled (iOS: Settings→Control Center)
- [ ] Phone Do Not Disturb ON (no notifications during recording)
- [ ] Home WiFi credentials ready to type
- [ ] Good lighting if filming phone screen with camera

---

## 🎬 Filming Quick Tips

### A-Roll Recording
✅ Record in 30-second segments (easier to edit)  
✅ Say "Take 1, Take 2, Take 3" before each attempt  
✅ Smile! Energy is contagious  
✅ Look slightly above camera (more natural)  
✅ Pause 2 seconds before and after each take  

### Screen Recording
✅ Move mouse SLOWLY (1/2 your normal speed)  
✅ Pause on important elements (3-5 seconds)  
✅ Use keyboard shortcuts deliberately  
✅ Record in real-time (don't speed up during recording)  

### Hardware B-Roll (3D Printed Case!)
✅ **HERO SHOTS FIRST** - Rotating 360° of finished device  
✅ Get multiple angles of each shot  
✅ Close-ups show detail (USB ports, LEDs, case texture)  
✅ Wide shots show context and scale  
✅ Action shots should be smooth and deliberate  
✅ **Lighting is critical** - Soft, diffused light prevents harsh shadows  
✅ Use a turntable or slowly rotate by hand (no shaking!)  
✅ Show the 3D printing timelapse if you have it  

---

## 🎨 Color-Coded Shot Priorities

### 🔴 CRITICAL (Must Have)
- **3D printed case hero shots** (rotating, multiple angles)
- **Fusion 360 screen recording** (model rotation, exploded view)
- **Phone WiFi setup screen recording** (AP mode → home WiFi)
- Hook/intro featuring the case
- Main demo working
- USB devices appearing in Home Assistant
- Web interface tour (including WiFi scanner)
- Architecture diagram

### 🟡 IMPORTANT (Should Have)
- 3D printing timelapse (if available)
- Case assembly process
- Hardware close-ups (ports, LEDs)
- Terminal commands (optional for advanced viewers)
- Configuration screens
- Before/after comparison (bare Pi vs. cased device)

### 🟢 NICE-TO-HAVE (If Time)
- Multiple angles of hardware
- Lifestyle shots
- Animated transitions
- Stock footage overlays

---

## 🎧 Audio Levels Reference

| Element | Level (dB) |
|---------|-----------|
| Voice (peak) | -6 to -3 dB |
| Voice (average) | -15 to -12 dB |
| Music | -25 to -20 dB |
| Sound FX | -12 to -8 dB |

**Rule of Thumb**: Music should be barely noticeable, voice should dominate.

---

## ⏱️ Time Estimates Per Task

| Task | Time |
|------|------|
| Record 1 min of A-roll | 15-20 min (multiple takes) |
| Record 10 B-roll shots | 30-45 min |
| 5 min screen recording | 15-20 min (setup + recording) |
| Edit 1 minute of video | 1-2 hours (first time) |
| Create 1 thumbnail | 20-30 min |
| Write description | 15-20 min |

---

## 🚨 Common Mistakes to Avoid

❌ **Recording too fast** - Slow down narration by 20%  
❌ **Moving mouse too fast** - Screen recordings need slow, deliberate movements  
❌ **Forgetting to record audio separately** - Backup audio is crucial  
❌ **Not backing up footage** - Copy files immediately after recording  
❌ **Editing before all footage is captured** - Finish filming first  
❌ **Weak hook** - First 10 seconds determine success  
❌ **No call-to-action** - Always ask viewers to subscribe/comment  
❌ **Uploading without thumbnail** - Thumbnail = 50% of clicks  

---

## 📱 Social Media Copy (Ready to Use)

### Reddit (r/homeassistant, r/selfhosted)
```
I built a custom embedded Linux system that turns a Raspberry Pi 
into a network-attached USB hub for Home Assistant. Share Z-Wave 
and Zigbee dongles over IP as if they were plugged in locally. 

WiFi setup via phone (AP mode captive portal), zero-config HA addon, 
custom 3D printed case—complete package. Full walkthrough video + 
open source code (including Fusion 360 files)!
```

### Twitter/X
```
🚀 USB-Beamer: Turn a $35 Raspberry Pi 3 A+ into a network USB hub 
for @home_assistant. 

📱 WiFi setup via phone
🔐 SSH tunnels for security  
🎯 Zero-config HA addon
🖨️ 3D printed case (F360 files included)

Full video: [LINK]
```

### Discord/Forums
```
Hey everyone! I just released a video about USB-Beamer - 
a project that lets you share USB dongles (Z-Wave, Zigbee, etc.) 
over your network using SSH tunnels and USB/IP on a tiny Raspberry Pi 3 A+. 

Features:
- Phone-based WiFi setup (AP mode captive portal)
- Home Assistant addon that auto-discovers and auto-connects
- Custom 3D printed case (Fusion 360 files included)
- Completely open source (Buildroot-based)

Perfect for HA setups where your server isn't near your smart home 
devices. No keyboard/monitor/Ethernet needed for setup! Check it out!
```

---

## 🔗 Essential Links to Include

In video description:
- GitHub repo (USB-Beamer server)
- GitHub repo (Home Assistant addon)
- Home Assistant addon installation guide
- Buildroot documentation
- Your social media
- Discord/forum for support
- Next video teaser

In pinned comment:
- **Timestamps** (chapter markers)
- **Parts list** (with affiliate links if applicable)
- **Common troubleshooting** link
- **FAQ** document

---

## 💾 Export Settings (Quick Reference)

### YouTube Upload (Recommended)
- **Format**: MP4 (H.264)
- **Resolution**: 1920x1080 or 3840x2160
- **Frame Rate**: Match source (24/30/60fps)
- **Bitrate**: 12-15 Mbps (1080p) / 40-50 Mbps (4K)
- **Audio**: AAC, 192-320 kbps

---

## 🎯 Success Metrics to Track

After publishing, monitor:
- **First 24h views** (indicates hook strength)
- **Average view duration** (indicates content quality)
- **CTR (Click-through rate)** from impressions (thumbnail quality)
- **Comments** (engagement level)
- **Shares** (indicates value to viewers)

Target for first video:
- 40%+ average view duration = Good
- 50%+ = Great
- 60%+ = Excellent

---

## 📞 Emergency Contacts

**Tech Support (if demos fail)**:
- Home Assistant Discord
- r/homeassistant subreddit
- USB/IP mailing list

**Equipment Backup Plans**:
- Camera fails → Use phone camera
- Mic fails → Use phone voice memo separately
- Lights fail → Record near window (natural light)
- Screen recorder crashes → Use built-in OS tools

---

## ✨ Final Pre-Upload Checklist

- [ ] Video rendered and plays without issues
- [ ] Audio levels consistent throughout
- [ ] No dead air longer than 3 seconds
- [ ] Thumbnail created (3-5 variations tested)
- [ ] Title optimized for search (<60 characters)
- [ ] Description includes links and timestamps
- [ ] Tags added (10-15 relevant tags)
- [ ] End screen configured (subscribe button + next video)
- [ ] Captions/subtitles added (auto-generated is fine)
- [ ] Pinned comment drafted

---

**You've got this! Now go create something awesome! 🎥🚀**

---

*Keep this page open during production for quick reference*

