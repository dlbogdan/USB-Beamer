#!/usr/bin/env python3
"""
Netplan to /etc/network/interfaces Converter

Parses netplan-style YAML configuration and converts it to traditional
/etc/network/interfaces format with wpa_supplicant configuration files.
Designed for embedded Linux systems without systemd/networkd.
"""

import yaml
import argparse
import os
import sys
from pathlib import Path


class NetplanConverter:
    def __init__(self, netplan_config):
        """
        Initialize converter with netplan configuration dictionary.
        
        Args:
            netplan_config: Dictionary loaded from netplan YAML
        """
        self.config = netplan_config
        self.interfaces_content = []
        self.wpa_configs = {}  # interface -> wpa_supplicant config
        
    def convert(self):
        """
        Convert netplan config to /etc/network/interfaces format.
        
        Returns:
            tuple: (interfaces_content, wpa_configs_dict)
        """
        version = self.config.get('version', 2)
        if version != 2:
            raise ValueError(f"Unsupported netplan version: {version}")
        
        # Add loopback interface (always present)
        self.interfaces_content.extend([
            "auto lo",
            "iface lo inet loopback",
            ""  # blank line after interface
        ])
        
        # Process network section
        network = self.config.get('network', self.config)
        
        # Check if eth0 is explicitly configured
        eth0_configured = False
        if 'ethernets' in network:
            eth0_configured = 'eth0' in network['ethernets']
            self._process_ethernets(network['ethernets'])
        
        # Add default eth0 configuration if not explicitly configured
        if not eth0_configured:
            self.interfaces_content.extend([
                "auto eth0",
                "iface eth0 inet dhcp",
                ""  # blank line after interface
            ])
        
        # Process wifi interfaces
        if 'wifis' in network:
            self._process_wifis(network['wifis'])
        
        return '\n'.join(self.interfaces_content), self.wpa_configs
    
    def _process_ethernets(self, ethernets):
        """Process ethernet interface configurations."""
        # Skip 'renderer' if it's a top-level key
        for iface_name, iface_config in ethernets.items():
            if iface_name == 'renderer':
                continue
            
            self._add_interface_config(iface_name, iface_config, is_wifi=False)
    
    def _process_wifis(self, wifis):
        """Process WiFi interface configurations."""
        # Skip 'renderer' if it's a top-level key
        for iface_name, iface_config in wifis.items():
            if iface_name == 'renderer':
                continue
            
            self._add_interface_config(iface_name, iface_config, is_wifi=True)
    
    def _add_interface_config(self, iface_name, iface_config, is_wifi=False):
        """
        Add interface configuration to output.
        
        Args:
            iface_name: Name of the network interface (e.g., 'wlan0', 'eth0')
            iface_config: Configuration dictionary for the interface
            is_wifi: Boolean indicating if this is a WiFi interface
        """
        # Start building interface block
        lines = []
        
        # Check if interface should be brought up automatically
        #optional = iface_config.get('optional', False)
        #if not optional:
        #    lines.append(f"auto {iface_name}")
        lines.append(f"auto {iface_name}") # Always bring up the interface
        
        # Determine addressing method
        dhcp4 = iface_config.get('dhcp4', False)
        dhcp6 = iface_config.get('dhcp6', False)
        addresses = iface_config.get('addresses', [])
        
        if dhcp4:
            lines.append(f"iface {iface_name} inet dhcp")
        elif addresses:
            # Static IP configuration
            lines.append(f"iface {iface_name} inet static")
            for addr in addresses:
                # Parse CIDR notation (e.g., "192.168.1.100/24")
                if '/' in addr:
                    ip, prefix = addr.split('/')
                    netmask = self._cidr_to_netmask(int(prefix))
                    lines.append(f"    address {ip}")
                    lines.append(f"    netmask {netmask}")
                else:
                    lines.append(f"    address {addr}")
            
            # Add gateway if specified
            if 'gateway4' in iface_config:
                lines.append(f"    gateway {iface_config['gateway4']}")
            
            # Add nameservers if specified
            if 'nameservers' in iface_config:
                nameservers = iface_config['nameservers']
                if 'addresses' in nameservers:
                    dns_servers = ' '.join(nameservers['addresses'])
                    lines.append(f"    dns-nameservers {dns_servers}")
        else:
            # Manual configuration
            lines.append(f"iface {iface_name} inet manual")
        
        # Handle WiFi-specific configuration
        if is_wifi and 'access-points' in iface_config:
            access_points = iface_config['access-points']
            
            # Generate wpa_supplicant configuration
            wpa_conf_path = f"/etc/wpa_supplicant/wpa_supplicant-{iface_name}.conf"
            self.wpa_configs[iface_name] = self._generate_wpa_supplicant_config(
                access_points
            )
            
            # Add wpa_supplicant directives to interface config
            lines.append(f"    wpa-driver wext")
            lines.append(f"    wpa-conf {wpa_conf_path}")
        
        # Add MTU if specified
        if 'mtu' in iface_config:
            lines.append(f"    mtu {iface_config['mtu']}")
        
        # Add routes if specified
        if 'routes' in iface_config:
            for route in iface_config['routes']:
                if 'to' in route and 'via' in route:
                    lines.append(f"    up route add -net {route['to']} gw {route['via']}")
                    lines.append(f"    down route del -net {route['to']} gw {route['via']}")
        
        # Add the interface block to output
        self.interfaces_content.extend(lines)
        self.interfaces_content.append("")  # Blank line between interfaces
    
    def _generate_wpa_supplicant_config(self, access_points):
        """
        Generate wpa_supplicant.conf content for access points.
        
        Args:
            access_points: Dictionary of SSID -> config
            
        Returns:
            str: wpa_supplicant.conf content
        """
        lines = [
            #"ctrl_interface=/var/run/wpa_supplicant",
            #"ctrl_interface_group=0",
            "update_config=1",
            ""
        ]
        
        # Add each access point as a network block
        for ssid, ap_config in access_points.items():
            lines.append("network={")
            lines.append(f'    ssid="{ssid}"')
            
            # Handle password/PSK
            if 'password' in ap_config:
                password = ap_config['password']
                # Check if it's a pre-hashed PSK (64 hex chars) or plaintext
                if len(password) == 64 and all(c in '0123456789abcdefABCDEF' for c in password):
                    # Pre-hashed PSK (no quotes)
                    lines.append(f'    psk={password}')
                else:
                    # Plaintext password (with quotes)
                    lines.append(f'    psk="{password}"')
            
            # Handle hidden networks
            if ap_config.get('hidden', False):
                lines.append('    scan_ssid=1')
            
            # Handle network priority (higher = more preferred)
            if 'priority' in ap_config:
                lines.append(f'    priority={ap_config["priority"]}')
            
            # Handle security mode
            mode = ap_config.get('mode', 'infrastructure')
            if mode == 'adhoc':
                lines.append('    mode=1')
            
            # Handle auth/key management
            if 'auth' in ap_config:
                auth = ap_config['auth']
                if auth == 'open':
                    lines.append('    key_mgmt=NONE')
            
            lines.append("}")
            lines.append("")
        
        return '\n'.join(lines)
    
    @staticmethod
    def _cidr_to_netmask(prefix_len):
        """
        Convert CIDR prefix length to dotted decimal netmask.
        
        Args:
            prefix_len: Integer prefix length (e.g., 24)
            
        Returns:
            str: Dotted decimal netmask (e.g., "255.255.255.0")
        """
        mask = (0xffffffff >> (32 - prefix_len)) << (32 - prefix_len)
        return '.'.join([
            str((mask >> 24) & 0xff),
            str((mask >> 16) & 0xff),
            str((mask >> 8) & 0xff),
            str(mask & 0xff)
        ])


def load_netplan_config(file_path):
    """
    Load netplan configuration from YAML file.
    
    Args:
        file_path: Path to netplan YAML file
        
    Returns:
        dict: Parsed configuration
    """
    with open(file_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def write_output_files(interfaces_content, wpa_configs, output_dir, dry_run=False):
    """
    Write generated configuration files to disk.
    
    Args:
        interfaces_content: Content for /etc/network/interfaces
        wpa_configs: Dictionary of interface -> wpa_supplicant config
        output_dir: Directory to write files to (None = actual system paths)
        dry_run: If True, print to stdout instead of writing files
    """
    if dry_run:
        print("=" * 60)
        print("Generated /etc/network/interfaces:")
        print("=" * 60)
        print(interfaces_content)
        print()
        
        for iface_name, wpa_content in wpa_configs.items():
            print("=" * 60)
            print(f"Generated /etc/wpa_supplicant/wpa_supplicant-{iface_name}.conf:")
            print("=" * 60)
            print(wpa_content)
            print()
    else:
        # Determine output paths
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            interfaces_path = output_dir / "interfaces"
            wpa_dir = output_dir / "wpa_supplicant"
            wpa_dir.mkdir(exist_ok=True)
        else:
            interfaces_path = Path("/etc/network/interfaces")
            wpa_dir = Path("/etc/wpa_supplicant")
            wpa_dir.mkdir(parents=True, exist_ok=True)
        
        # Write /etc/network/interfaces
        print(f"Writing {interfaces_path}...")
        with open(interfaces_path, 'w') as f:
            f.write(interfaces_content)
        
        # Write wpa_supplicant configs
        for iface_name, wpa_content in wpa_configs.items():
            wpa_path = wpa_dir / f"wpa_supplicant-{iface_name}.conf"
            print(f"Writing {wpa_path}...")
            with open(wpa_path, 'w') as f:
                f.write(wpa_content)
            # Set restrictive permissions on WiFi config (contains passwords)
            os.chmod(wpa_path, 0o600)
        
        print("Configuration files written successfully!")


def main():
    parser = argparse.ArgumentParser(
        description='Convert netplan YAML to /etc/network/interfaces format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run - print to stdout
  %(prog)s network-config.yaml --dry-run
  
  # Write to custom output directory
  %(prog)s network-config.yaml --output-dir ./output
  
  # Write directly to system paths (requires root)
  sudo %(prog)s network-config.yaml
        """
    )
    
    parser.add_argument(
        'input_file',
        help='Path to netplan YAML configuration file'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        help='Output directory for generated files (default: write to /etc)',
        default=None
    )
    
    parser.add_argument(
        '-d', '--dry-run',
        action='store_true',
        help='Print generated configs to stdout instead of writing files'
    )
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found", file=sys.stderr)
        sys.exit(1)
    
    # Check for root privileges if writing to system paths
    if not args.dry_run and not args.output_dir and os.geteuid() != 0:
        print("Error: Root privileges required to write to /etc", file=sys.stderr)
        print("Try: sudo python3 netplan_converter.py <input_file>", file=sys.stderr)
        print("Or use --output-dir to write to a custom directory", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Load and parse netplan config
        print(f"Loading configuration from {args.input_file}...")
        config = load_netplan_config(args.input_file)
        
        # Convert to interfaces format
        print("Converting configuration...")
        converter = NetplanConverter(config)
        interfaces_content, wpa_configs = converter.convert()
        
        # Write output files
        write_output_files(
            interfaces_content,
            wpa_configs,
            args.output_dir,
            args.dry_run
        )
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

