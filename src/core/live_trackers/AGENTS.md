<!--
SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
SPDX-License-Identifier: Apache-2.0
-->

# Agent notes — `live_trackers`

**CRITICAL (non-optional):** Before editing this package, complete the mandatory **`AGENTS.md` preflight** in [`../../../AGENTS.md`](../../../AGENTS.md) (read every applicable `AGENTS.md` on your paths, not just this file).

## Time and OpenXR

- Store **`last_update_time_` as `int64_t`** (monotonic ns), not **`XrTime`**.
- **Once per `update` call:** `const XrTime xr_time = time_converter_.convert_monotonic_ns_to_xrtime(monotonic_time_ns);` then use **`xr_time`** for every **`xrLocate*`** / hand / body call **and** for MCAP (see below). **Do not** call **`convert_monotonic_ns_to_xrtime`** again in the MCAP block.
- **Full-body limp mode:** if the body tracker handle is null and you **return early**, **do not** compute **`xr_time`** first—only convert after you know you will call OpenXR.

## `DeviceDataTimestamp` (MCAP)

- **Fields 1–2:** monotonic ns (e.g. **`last_update_time_`, `last_update_time_`**).
- **Field 3 (`sample_time_raw_device_clock`):** the **same** **`xr_time`** variable used for OpenXR this frame (not a second conversion).

## Header layout

- **All** headers for this module live under `cpp/inc/live_trackers/`; the **public API** is every header here *except* the `*_impl.hpp` ones, which are **PRIVATE** (never include a `*_impl.hpp` from another module). The `.cpp` files live directly in `cpp/`.
- How to spell an include depends on **where the including file lives** (quote includes resolve relative to that file's own directory, and `inc/` is the sole exported include root):
  1. From a `.cpp` in `cpp/`: prefix the quote with `inc/<module>/`, e.g. `#include "inc/live_trackers/live_hand_tracker_impl.hpp"` (bare `"live_hand_tracker_impl.hpp"` would not resolve from `cpp/`).
  2. Between sibling headers both in `cpp/inc/live_trackers/`: bare quote, e.g. the moved impl headers include `#include "schema_tracker.hpp"`.
  3. Cross-module from anywhere: angle brackets, e.g. `#include <deviceio_trackers/hand_tracker.hpp>`.
- Honesty note: the public/private split is **convention only** — because `inc/` is the sole exported root, the build will not stop another module from including a `*_impl.hpp`, so keep the discipline yourself.

## Includes

- In headers that need both: **`#include <oxr_utils/oxr_funcs.hpp>`** comes **before** any bare **`#include <openxr/openxr.h>`**. `oxr_funcs.hpp` defines **`XR_NO_PROTOTYPES`** then includes OpenXR; including **`openxr.h`** first fights that policy.
- In **`.cpp`** files that construct **`DeviceDataTimestamp`**, include **`#include <schema/timestamp_generated.h>`** explicitly.
- **`.cpp`** files should include headers for **symbols the TU uses** (e.g. **`oxr_funcs.hpp`** for **`createReferenceSpace`**), not only what the matching **`.hpp`** happens to pull in.

## CMake

- **`live_trackers`** should **`PUBLIC` link `oxr::oxr_utils`** (OpenXR headers come through that INTERFACE target) because headers/sources use OpenXR / oxr types.

## New tracker MCAP checklist

When adding MCAP support to a new tracker impl, all of the following are required together—missing any one causes a build failure or wrong timestamps:

1. Add `XrTimeConverter time_converter_` and `int64_t last_update_time_ = 0` members to the impl header (which lives in `cpp/inc/live_trackers/`).
2. Initialize `time_converter_(handles)` in the constructor initializer list.
3. Declare `update(int64_t monotonic_time_ns) override` (not `XrTime`)—they are the same C++ type (`int64_t`) but semantically different; the base interface uses monotonic ns.
4. At the top of `update()`: store `last_update_time_ = monotonic_time_ns` and compute `const XrTime xr_time = time_converter_.convert_monotonic_ns_to_xrtime(monotonic_time_ns)`.
5. Use `DeviceDataTimestamp(last_update_time_, last_update_time_, xr_time)` — not `(time, time, time)`.
6. Add `MessageChannelRecordingTraits` (or equivalent) to `recording_traits.hpp`.
7. **Always build** (`cmake --build <build_dir> -- -j$(nproc)`) before treating work as done. Pre-commit alone does not catch compile errors or clang-format violations enforced at build time.
8. Read `AGENTS.md` before starting. Not after CI breaks.

## Related docs

- Session update loop: [`../deviceio_session/AGENTS.md`](../deviceio_session/AGENTS.md)
- No OpenXR in base API: [`../deviceio_base/AGENTS.md`](../deviceio_base/AGENTS.md)
