# USB-Beamer-server

This project aims to provide a way to share a USB-connected beamer over the network using Buildroot to create a custom embedded Linux system.

## Description

A Buildroot-based system that provides USB/IP functionality to share USB-connected devices (projectors/beamers) over the network, with a web interface for configuration and management.

## Project Structure

- `beamer-app/` - Main application code (Flask web server)
- `netplan_converter.py` - Network configuration converter script
- `board/beamer/rootfs-overlay/` - Root filesystem overlay for target system
  - `etc/init.d/` - System initialization scripts
  - `etc/ssh/` - SSH server configuration
  - `opt/beamer/` - Symlink to `beamer-app/` (deployed to target)
  - `usr/scripts/` - System scripts (netplan_converter.py symlink)
- `configs/beamer_defconfig` - Buildroot configuration
- `buildroot/` - Buildroot git submodule

## Development

### Application Structure
- **Application code**: `beamer-app/` (work here directly)
- **Init scripts**: `board/beamer/rootfs-overlay/etc/init.d/` (actual files)
- **System scripts**: `board/beamer/rootfs-overlay/usr/scripts/` (actual files)
- **System configs**: `board/beamer/rootfs-overlay/etc/`

### Optional: Create Development Symlinks

For easier access to scripts, you can create a local `scripts/` directory with symlinks (not tracked in Git):

**Linux/macOS:**
```bash
mkdir -p scripts/init
cd scripts
ln -s ../board/beamer/rootfs-overlay/usr/scripts/netplan_converter.py netplan_converter.py
cd init
for script in ../../board/beamer/rootfs-overlay/etc/init.d/S*; do
    ln -s "$script" "$(basename "$script")"
done
cd ../..
```

**Windows (PowerShell as Administrator):**
```powershell
mkdir scripts\init
cd scripts
cmd /c mklink netplan_converter.py ..\board\beamer\rootfs-overlay\usr\scripts\netplan_converter.py
cd init
cmd /c mklink S01mountboot ..\..\board\beamer\rootfs-overlay\etc\init.d\S01mountboot
cmd /c mklink S30netplan_convert ..\..\board\beamer\rootfs-overlay\etc\init.d\S30netplan_convert
cmd /c mklink S90usbipd ..\..\board\beamer\rootfs-overlay\etc\init.d\S90usbipd
cmd /c mklink S91avahi-beamer ..\..\board\beamer\rootfs-overlay\etc\init.d\S91avahi-beamer
cmd /c mklink S92beamer-sshd ..\..\board\beamer\rootfs-overlay\etc\init.d\S92beamer-sshd
cmd /c mklink S93beamer-app ..\..\board\beamer\rootfs-overlay\etc\init.d\S93beamer-app
cd ..\..
```

### Development Workflow

1. Edit application code in `beamer-app/app.py` or any files in `beamer-app/`
2. Test locally: `cd beamer-app && python app.py`
3. Edit init scripts in `board/beamer/rootfs-overlay/etc/init.d/` (or via `scripts/init/` symlinks if created)
4. Edit system scripts in `board/beamer/rootfs-overlay/usr/scripts/` (or via `scripts/` symlinks if created)
5. Build target image: `make build`

## Building for Target

### First Time Setup

1. Clone the repository with submodules:
   ```bash
   git clone --recursive https://github.com/your-username/USB-Beamer-server.git
   cd USB-Beamer-server
   ```

2. Load the default configuration:
   ```bash
   make config
   ```

3. Build the image:
   ```bash
   make build
   ```

4. Output will be in: `buildroot/output/images/`

### Make Targets

- `make config` - Load beamer_defconfig
- `make menuconfig` - Open Buildroot configuration menu
- `make build` - Build the complete system image
- `make clean` - Clean build artifacts
- `make savedefconfig` - Save current configuration back to defconfig

## Configuration Changes

If you modify the Buildroot configuration:

```bash
make menuconfig          # Make your changes
make savedefconfig       # Save back to configs/beamer_defconfig
git add configs/beamer_defconfig
git commit -m "Update defconfig"
```

## Updating Buildroot Version

```bash
cd buildroot
git fetch
git checkout <new-version>
cd ..
git add buildroot
git commit -m "Update Buildroot to <version>"
```

## Docker Development (Optional)

For local testing without building the full image:

```bash
    docker build -t usb-beamer-server .
    docker run -p 2222:22 -p 5000:5000 usb-beamer-server
    ```

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

(TODO: Add a license for the project.) 