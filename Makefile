BUILDROOT_DIR := $(CURDIR)/buildroot
DEFCONFIG_PATH := $(CURDIR)/configs/beamer_defconfig

.PHONY: all config menuconfig build clean savedefconfig help

all: build

config:
	$(MAKE) -C $(BUILDROOT_DIR) defconfig BR2_DEFCONFIG=$(DEFCONFIG_PATH)

menuconfig:
	$(MAKE) -C $(BUILDROOT_DIR) menuconfig

build:
	$(MAKE) -C $(BUILDROOT_DIR)

clean:
	$(MAKE) -C $(BUILDROOT_DIR) clean

savedefconfig:
	$(MAKE) -C $(BUILDROOT_DIR) savedefconfig BR2_DEFCONFIG=$(DEFCONFIG_PATH)

help:
	@echo "USB Beamer Buildroot Build System"
	@echo "=================================="
	@echo "make config       - Load beamer_defconfig"
	@echo "make menuconfig   - Configure Buildroot"
	@echo "make build        - Build the image"
	@echo "make clean        - Clean build artifacts"
	@echo "make savedefconfig - Save current config"
