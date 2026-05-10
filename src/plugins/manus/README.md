<!--
SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
SPDX-License-Identifier: Apache-2.0
-->

# Isaac Teleop Device Plugins — Manus

This folder provides a Linux-only example of using the Manus SDK for hand tracking within the Isaac Teleop framework.

## Components

- **Core Library** (`manus_plugin_core`): Interfaces with the Manus SDK (`libIsaacTeleopPluginsManus.so`).
- **Plugin Executable** (`manus_hand_plugin`): The main plugin executable that integrates with the Teleop system.
- **CLI Tool** (`manus_hand_tracker_printer`): A standalone tool that prints tracked joint data to the terminal **and** opens a real-time Vulkan visualizer window ("MANUS Data Visualizer") showing the hand skeleton from two orthographic views.

## Prerequisites

- **Linux** (x86_64 tested on Ubuntu 22.04/24.04)
- **Manus SDK** for Linux (automatically downloaded by install script)
- **System dependencies**: The install script installs required packages automatically

## Installation

Manus access has two halves: **device permissions** (kernel/udev, lives on the
host) and **SDK + plugin build** (lives wherever you build, typically a
container). The two scripts below split along that line.

### Step 1: grant the host access to the Manus dongle (one-time)

Run this **on the host machine**, not inside a container. udev rules are
processed by `systemd-udevd`, which does not run inside Docker — so installing
rules from a container has no effect.

```bash
cd src/plugins/manus
./install_udev_rules.sh
# then unplug + replug the Manus dongle
```

If you're using the Isaac ROS dev container (`isaac_ros run_dev`), it
bind-mounts `/dev/bus/usb` from the host, so once the host has the rules
applied the container will see the dongle with the right permissions.

### Step 2: build the SDK and plugin

Run this **inside the build environment** (devcontainer or Isaac ROS container):

```bash
cd src/plugins/manus
./install_manus.sh
```

The script will:
1. Install required system packages for MANUS Core Integrated
2. Automatically download the MANUS SDK v3.1.1
3. Extract and configure the SDK in the correct location
4. Build the plugin

When run inside a container, `install_manus.sh` skips the udev step and
reminds you to run `install_udev_rules.sh` on the host.

### Manual Installation

If you prefer to install manually:

1. Download the MANUS Core SDK from [MANUS Downloads](https://docs.manus-meta.com/3.1.1/Resources/)
2. Extract and place the `ManusSDK` folder inside `src/plugins/manus/`, or set the `MANUS_SDK_ROOT` environment variable to your installation path
3. Follow the [MANUS Getting Started guide for Linux](https://docs.manus-meta.com/3.1.1/Plugins/SDK/Linux/) to install the dependencies and setup device permissions.

Expected layout:
```text
src/plugins/manus/
  app/
    main.cpp
  core/
    manus_hand_tracking_plugin.cpp
  inc/
    core/
      manus_hand_tracking_plugin.hpp
  tools/
    manus_hand_tracker_printer.cpp
  ManusSDK/        <-- Placed here
    include/
    lib/
```

4. Build from the TeleopCore root:

```bash
cd ../../..  # Navigate to TeleopCore root
cmake -S . -B build
cmake --build build --target manus_hand_plugin manus_hand_tracker_printer -j
cmake --install build --component manus
```

## Running the Plugin

### 1. Setup CloudXR Environment
Before running the plugin, ensure CloudXR environment is configured:

The following environment variables must be set before running either the CLI tool or the plugin (adjust paths if your CloudXR installation differs from the defaults):

```bash
export NV_CXR_RUNTIME_DIR=~/.cloudxr/run
export XR_RUNTIME_JSON=~/.cloudxr/openxr_cloudxr.json
```

### 2. Verify with CLI Tool
Verify that the gloves are working using the CLI tool:

```bash
./build/bin/manus_hand_tracker_printer
```

The tool prints joint positions to the terminal and opens a **MANUS Data Visualizer** window with a top-down and side view of each hand.

### 3. Run the Plugin
The plugin is installed to the `install` directory, please ensure the CLI tool is not running when running the plugin.

```bash
./install/plugins/manus/manus_hand_plugin
```

## Controller positioning vs Optical hand tracking positioning
To position the MANUS gloves in 3D space two avenues are available:

- Use the MANUS Quest 3 controller adapters to attach the Quest 3 controllers to the MANUS Universal Mount on the back of the glove.
- Use the HMD's optical hand tracking to position the hands.

The system will switch dynamically based on the available tracking source. When using controllers it's advised to turn off hand tracking entirely or turn off automatic switching.

## Troubleshooting

- **SDK download fails**: Check your internet connection and try running the install script again
- **Manus SDK not found at build time**: If using manual installation, ensure `ManusSDK` is in `src/plugins/manus/` or `MANUS_SDK_ROOT` is set correctly
- **Manus SDK not found at runtime**: The CMake build configures RPATH to find the SDK libraries. If you moved the SDK, you may need to set `LD_LIBRARY_PATH`
- **No data available**: Ensure Manus Core is running and gloves are properly connected and calibrated
- **CloudXR runtime errors**: Make sure you've sourced `scripts/setup_cloudxr_env.sh` before running the plugin
- **Permission denied for USB devices**: udev rules must be installed on the
  host. Run `./install_udev_rules.sh` from the host (not inside a container),
  then unplug and replug the dongle. Verify on the host with `ls -l /dev/hidraw*`
  — entries for the Manus dongle should be mode `0666`.
- **`udevadm control --reload-rules` fails with "No such file or directory"**:
  You're inside a container. `systemd-udevd` doesn't run in containers, so this
  command can never succeed there. Run `install_udev_rules.sh` on the host
  instead.
- **Dongle not visible inside the Isaac ROS container** (`lsusb` doesn't show
  vendor `3325`): the container needs `/dev/bus/usb` bind-mounted from the
  host. The Isaac ROS dev container does this automatically; for a custom
  `docker run`, add `-v /dev/bus/usb:/dev/bus/usb` (or `--device=/dev/hidraw<N>`
  for a specific device).

## License

Source files are under their stated licenses. The Manus SDK is proprietary to Manus and is subject to its own license; it is not redistributed by this project.
