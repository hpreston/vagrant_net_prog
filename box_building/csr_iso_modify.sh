#!/bin/bash
#set -x

# Author: Ralph Schmieder (rschmied@cisco.com)
#   Script designed for Linux OS
#
# Designed to take as input an ISO image for a CSR 1000v
# (downloaded from cisco.com) that defaults to boot to VGA,
# and change to boot by default to SERIAL input.  Purpose
# of the change is to support automated/scripted configuraiton
# and deployment.
#
# Pre-requisites:
#   - mkisofs - installable with homebrew "brew install mkisofs"


[[ ! "$1" =~ .*\.iso ]] && { echo ".iso file name needed"; exit; }

# Create temp working directory
TEMP=$(mktemp -d)
PDIR=$(pwd)

# Build full SRC PATH
if [[ "$1" =~ ^/ ]]; then
    SRC=$1
else
    SRC=$PDIR/$1
fi

# Move to Temp directory
pushd $TEMP

# Create src mount and new ISO directories
mkdir mnt && mkdir iso

# Mount source ISO
sudo mount -o loop $SRC mnt

# Copy SRC ISO Content to Destination
cp -a mnt/* iso

# Updating Grub to Boot Serial by default
sed -i '/^default/s/0/1/' iso/boot/grub/menu.lst

# Create new ISO
mkisofs -R -b boot/grub/stage2_eltorito -no-emul-boot -boot-load-size 4 -boot-info-table -o "serial-$(basename $1)" iso

# Unmount SRC ISO
sudo umount mnt

# Move created ISO to original directory
mv *.iso $PDIR

# Return to original directory
popd

# Delete Temp Directory
rm -rf $TEMP
