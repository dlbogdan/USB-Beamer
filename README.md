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
//// TODO

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

(TODO: Add a license for the project.) 
