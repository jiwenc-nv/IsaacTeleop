# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Rendering a digital twin of a teleoperated robot into a Televiz XR session.

Scoped to that job on purpose: this is not a general scene-graph or viewer API. The
scene backend sits behind :class:`RobotTwin`, and nothing re-exported here imports it.
:mod:`~isaacteleop.viz.robot.mj` is absent from that list by design and is imported by
name.
"""

from .frame_info import (
    MAX_DT_S,
    MIN_QUAT_NORM,
    assert_frustum,
    clamp_dt,
    flatten_views,
    frame_clock,
    head_pose,
)
from .session import VIEW_COUNT, Frame, XrTwinSession
from .twin import RobotTwin

__all__ = [
    "MAX_DT_S",
    "MIN_QUAT_NORM",
    "VIEW_COUNT",
    "Frame",
    "RobotTwin",
    "XrTwinSession",
    "assert_frustum",
    "clamp_dt",
    "flatten_views",
    "frame_clock",
    "head_pose",
]
