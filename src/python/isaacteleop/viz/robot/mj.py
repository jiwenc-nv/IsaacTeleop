# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""XR yaw and anchoring math, using MuJoCo as the quaternion library.

Every pose here is in a gravity-aligned Y-up XR reference space -- ``LOCAL``,
``LOCAL_FLOOR``, ``STAGE`` or ``UNBOUNDED`` -- where +Y is world up. A ``VIEW``-space pose
yields a silently wrong bearing rather than an error. Poses stay correct across a runtime
recentre; a yaw LATCHED across one does not, so re-anchor on
``XrEventDataReferenceSpaceChangePending``.

Needs the ``robot-viz`` extra. Deliberately not re-exported from the package ``__init__``:
importing it is what pulls MuJoCo in, so the rest of ``viz.robot`` stays usable without
the extra installed.
"""

from __future__ import annotations

import math

import mujoco
import numpy as np


def yaw_of_direction(forward_xr: np.ndarray, fallback_xr: np.ndarray) -> np.ndarray:
    """The horizontal bearing of an XR direction, as a wxyz quaternion about +Y.

    ``forward_xr`` must be unit length: the near-vertical test below is an absolute
    1e-6, so a magnified direction a hair off vertical never reaches the fallback and
    returns a garbage bearing.
    ``fallback_xr`` covers a direction within a hair of vertical, which has no bearing to
    report -- callers pass the pose's own up-vector, which is what holds heading up to
    and at vertical (past it, the bearing reverses). This is the single definition of bearing, so anything built on it
    tracks a world-vertical turn 1:1.
    """
    forward = np.asarray(forward_xr, dtype=float)
    if abs(forward[0]) < 1e-6 and abs(forward[2]) < 1e-6:
        # Straight up or down -- a headset face-down on a desk, a controller held
        # muzzle-up. The fallback then points along the horizon: forwards when the
        # direction points down, backwards when up.
        forward = -math.copysign(1.0, forward[1]) * np.asarray(fallback_xr, dtype=float)

    q_yaw = np.empty(4)
    mujoco.mju_axisAngle2Quat(
        q_yaw, np.array([0.0, 1.0, 0.0]), math.atan2(-forward[0], -forward[2])
    )
    return q_yaw


def yaw_of_axis(q_xyzw: np.ndarray, forward_local: np.ndarray) -> np.ndarray:
    """The horizontal facing of an XR orientation, as a wxyz quaternion about +Y.

    ``forward_local`` names which axis of the pose is its facing, in the pose's own
    frame. No default: each axis is blind to rotation about itself and sensitive to the
    rest, so it must be chosen against the motions the reading has to ignore.
    """
    q_wxyz = np.asarray(q_xyzw, dtype=float)[[3, 0, 1, 2]]
    # mju_rotVecQuat lerps toward the identity for a non-unit quaternion rather than
    # scaling the result, so a short one silently SHRINKS the bearing and stays
    # horizontal: measured on mujoco 3.11.0, norm 0.9 turns a 30 deg yaw into 24.4 deg
    # with nothing to notice it by. Raise on genuinely broken input, absorb float drift.
    norm = float(np.linalg.norm(q_wxyz))
    if abs(norm - 1.0) > 1e-3:
        raise ValueError(f"q_xyzw must be a unit quaternion; norm is {norm}")
    q_wxyz = q_wxyz / norm
    forward = np.empty(3)
    mujoco.mju_rotVecQuat(forward, np.asarray(forward_local, dtype=float), q_wxyz)
    up = np.empty(3)
    mujoco.mju_rotVecQuat(up, np.array([0.0, 1.0, 0.0]), q_wxyz)
    return yaw_of_direction(forward, up)


def yaw_of(q_xyzw: np.ndarray) -> np.ndarray:
    """The horizontal facing of a HEAD pose, reading its -Z as the view direction."""
    return yaw_of_axis(q_xyzw, np.array([0.0, 0.0, -1.0]))


def anchor_from_head(
    head_pose_xr: np.ndarray, offset_xr: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Where content anchored to the operator goes, from a 7-D head pose.

    Takes ``(position, xyzw)`` in XR and an offset in the head's yaw frame; returns the
    XR position and the head's YAW as a wxyz quaternion. The same yaw does both jobs:
    it carries ``offset_xr`` onto the head's facing, and the caller turns its content by
    it. The returned orientation is gravity-aligned: head pitch and roll are discarded.
    Content whose correct pose is not level -- an inclined base, a wall mount -- needs
    full SO(3) and cannot be placed by this.
    """
    pose = np.asarray(head_pose_xr, dtype=float)
    q_yaw = yaw_of(pose[3:7])
    offset = np.empty(3)
    mujoco.mju_rotVecQuat(offset, np.asarray(offset_xr, dtype=float), q_yaw)
    return pose[:3] + offset, q_yaw
