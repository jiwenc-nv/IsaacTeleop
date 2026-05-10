#!/bin/bash
# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Install the Manus udev rules on the HOST machine.
#
# udev rules are processed by systemd-udevd, which does not run inside Docker
# containers. They must therefore be installed on the host so that device nodes
# (/dev/hidraw*, /dev/bus/usb/.../...) come up with the permissions the Manus
# SDK needs. Once installed on the host, any container that bind-mounts
# /dev/bus/usb (or /dev) inherits the correct permissions.
#
# Run this once on the host, then unplug + replug the Manus dongle.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RULES_SRC="$SCRIPT_DIR/70-manus-hid.rules"
RULES_DST="/etc/udev/rules.d/70-manus-hid.rules"

if [ ! -f "$RULES_SRC" ]; then
    echo "Error: rules file not found at $RULES_SRC" >&2
    exit 1
fi

# Refuse to run inside a container — the udevadm reload would silently no-op
# and the user would think it worked.
if [ -f /.dockerenv ] || grep -qE '(docker|containerd|kubepods)' /proc/1/cgroup 2>/dev/null; then
    echo "Error: this script must be run on the HOST, not inside a container." >&2
    echo "       udev rules are kernel/host-level state; installing them here has no effect." >&2
    exit 1
fi

# Pre-authenticate sudo if it would prompt for a password. Skipping `sudo -v`
# entirely on NOPASSWD setups — `sudo -v` always validates the password, even
# when the rules grant passwordless sudo, which would break unattended runs.
if ! sudo -n true 2>/dev/null; then
    echo "This script needs sudo to write to /etc/udev/rules.d/."
    sudo -v || { echo "Error: sudo authentication failed." >&2; exit 1; }
fi

echo "Installing Manus udev rules to $RULES_DST..."
sudo install -m 0644 "$RULES_SRC" "$RULES_DST"

echo "Reloading udev rules..."
sudo udevadm control --reload-rules
sudo udevadm trigger

echo ""
echo "=== Done ==="
echo "Now unplug and replug the Manus dongle so the new rules apply."
echo "Verify with:  ls -l /dev/hidraw*   # should be mode 0666 for vendor 3325"
