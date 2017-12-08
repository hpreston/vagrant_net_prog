#!/bin/bash
#set -x

# Author: Ralph Schmieder (rschmied@cisco.com)
#   Original script designed for Linux OS
#   This version adapted for execution on Mac OS X
#   by Hank Preston (hank.preston@gmail.com)
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

# Create new ISO director
mkdir mkdir iso

# Mount source ISO
hdiutil mount $SRC

# Copy SRC ISO Content to Destination
cp -a /Volumes/CDROM/* iso

# Updating Grub to Boot Serial by default
sed -i '.bak' '/^default/s/0/1/' iso/boot/grub/menu.lst

# Create new ISO
mkisofs -R -b boot/grub/stage2_eltorito -no-emul-boot -boot-load-size 4 -boot-info-table -o "serial-$(basename $1)" iso

# Unmount SRC ISO
hdiutil unmount /Volumes/CDROM

# Move created ISO to original directory
mv *.iso $PDIR

# Return to original directory
popd

# Delete Temp Directory
rm -rf $TEMP
