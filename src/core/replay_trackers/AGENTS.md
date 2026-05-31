<!--
SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
SPDX-License-Identifier: Apache-2.0
-->

# Agent notes — `replay_trackers`

**CRITICAL (non-optional):** Before editing this package, complete the mandatory **`AGENTS.md` preflight** in [`../../../AGENTS.md`](../../../AGENTS.md) (read every applicable `AGENTS.md` on your paths, not just this file).

## Header layout

- **All** headers for this module live under `cpp/inc/replay_trackers/`; the **public API** is every header here *except* the `*_impl.hpp` ones, which are **PRIVATE** (never include a `*_impl.hpp` from another module). The `.cpp` files live directly in `cpp/`.
- How to spell an include depends on **where the including file lives** (quote includes resolve relative to that file's own directory, and `inc/` is the sole exported include root):
  1. From a `.cpp` in `cpp/`: prefix the quote with `inc/<module>/`, e.g. `#include "inc/replay_trackers/replay_hand_tracker_impl.hpp"` (bare `"replay_hand_tracker_impl.hpp"` would not resolve from `cpp/`).
  2. Between sibling headers both in `cpp/inc/replay_trackers/`: bare quote, e.g. `#include "replay_head_tracker_impl.hpp"`.
  3. Cross-module from anywhere: angle brackets, e.g. `#include <deviceio_trackers/hand_tracker.hpp>`.
- Honesty note: the public/private split is **convention only** — because `inc/` is the sole exported root, the build will not stop another module from including a `*_impl.hpp`, so keep the discipline yourself.

## Related docs

- Live counterpart: [`../live_trackers/AGENTS.md`](../live_trackers/AGENTS.md)
- Session update loop: [`../deviceio_session/AGENTS.md`](../deviceio_session/AGENTS.md)
- No OpenXR in base API: [`../deviceio_base/AGENTS.md`](../deviceio_base/AGENTS.md)
