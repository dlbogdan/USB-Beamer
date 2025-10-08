# Buildroot Configuration for USB-Beamer-server

## Boot Partition Auto-Mount

This configuration automatically mounts the boot partition at boot time by dynamically detecting the device name.

### Files Created

1. **`board/rootfs-overlay/etc/init.d/S01mountboot`** - Init script that dynamically detects and mounts the boot partition
2. **`board/post-build.sh`** - Post-build script to set correct permissions

### Buildroot Configuration

Add these lines to your Buildroot `.config` or `defconfig`:

```
BR2_ROOTFS_OVERLAY="board/rootfs-overlay"
BR2_ROOTFS_POST_BUILD_SCRIPT="board/post-build.sh"
```

Or in `menuconfig`:
- **System configuration → Root filesystem overlay directories**: `board/rootfs-overlay`
- **System configuration → Custom scripts to run before creating filesystem images**: `board/post-build.sh`

### How It Works

The script (`S01mountboot`) will:
1. Read `/proc/cmdline` to find the root device
2. Derive the boot partition from the root device:
   - MMC/SD cards: `/dev/mmcblk0pX` → `/dev/mmcblk0p1`
   - SATA/USB drives: `/dev/sdaX` → `/dev/sda1`
   - NVMe drives: `/dev/nvme0n1pX` → `/dev/nvme0n1p1`
3. Mount the boot partition to `/boot`

### Testing

After booting your Buildroot system:

```bash
# Check if boot is mounted
mount | grep boot

# Verify contents
ls -la /boot
```

### Troubleshooting

If the boot partition doesn't mount:

```bash
# Check what the script detected
cat /proc/cmdline

# Manually run the init script with debug
sh -x /etc/init.d/S01mountboot start

# Check available block devices
ls -la /dev/sd* /dev/mmcblk* /dev/nvme* 2>/dev/null
```

