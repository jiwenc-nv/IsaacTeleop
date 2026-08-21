# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Adapters from a ``viz.FrameInfo`` to what a twin's renderer takes.

Every function reads duck-typed fields off the frame, so this module imports nothing
from ``isaacteleop.viz`` -- keep it that way. Note the guarantee is file-level: the
package ``__init__`` reaches ``viz``, which needs the compiled compositor.
"""

from __future__ import annotations

import math

import numpy as np

#: Wall-clock ceiling for one advance of a twin's clock.
MAX_DT_S = 0.1

#: Below this a quaternion carries no usable orientation. Matches the SO-101 clutch's
#: own degenerate-quaternion threshold (``clutch_retargeter.py``).
MIN_QUAT_NORM = 1e-6


def clamp_dt(dt: float) -> float:
    """NaN-safe clamp into ``[0, MAX_DT_S]``.

    Comparisons, not min/max: ``max(nan, 0)`` is nan, so the obvious form passes NaN
    through both limits and into whatever accumulates it.
    """
    if dt > 0:
        return MAX_DT_S if dt > MAX_DT_S else dt
    return 0.0


def frame_clock(info) -> float | None:
    """Seconds from ``predicted_display_time``, or None when the frame carries no time.

    viz zeroes ``predicted_display_time`` along with ``should_render`` on every frame
    before kRunning. Skip the sample rather than recording a zero, or the next real
    frame computes dt from 0 and :func:`clamp_dt` reports a full ``MAX_DT_S`` stall.
    """
    if info.predicted_display_time == 0:
        return None
    return info.predicted_display_time / 1e9


def head_pose(info) -> np.ndarray | None:
    """``views[0]`` as a 7-D XR pose ``[x, y, z, qx, qy, qz, qw]``, or None if unusable.

    The left eye, not a head centre, which the runtime does not report; the ~32 mm
    between them is below what anything anchoring to this is authored to.
    """
    if len(info.views) == 0:
        return None
    view = info.views[0]
    px, py, pz = view.pose.position
    qw, qx, qy, qz = view.pose.orientation
    pose = np.array([px, py, pz, qx, qy, qz, qw], dtype=float)
    if (
        not np.all(np.isfinite(pose))
        or float(np.linalg.norm(pose[3:7])) < MIN_QUAT_NORM
    ):
        return None
    return pose


def flatten_views(info) -> tuple[list[float], list[float]]:
    """``info.views`` -> the flat ``(poses, fovs)`` arrays a renderer takes.

    Field by field, never sliced: ``viz.Pose3D.orientation`` is (w,x,y,z) while a
    controller's ``GRIP_ORIENTATION`` is (x,y,z,w).
    """
    poses: list[float] = []
    fovs: list[float] = []
    for view in info.views:
        px, py, pz = view.pose.position
        qw, qx, qy, qz = view.pose.orientation
        poses.extend((px, py, pz, qw, qx, qy, qz))
        fovs.extend(
            (
                view.fov.angle_left,
                view.fov.angle_right,
                view.fov.angle_up,
                view.fov.angle_down,
            )
        )
    return poses, fovs


def assert_frustum(f, fov, near: float, far: float) -> None:
    """Check a renderer's frustum against the fov it came from.

    ``f`` is ``(center, half_width, bottom, top, near, far)``. The projection's shape is
    the renderer's business; which numbers reached it is this check's.
    """
    center, half_width, bottom, top, f_near, f_far = f

    # At zero half_width MuJoCo derives the horizontal extent from the viewport
    # aspect, rendering something plausible from a fov carrying nothing.
    assert half_width > 0.0 and top > bottom, (
        f"degenerate frustum {f}: a zeroed Fov reached the camera"
    )
    # float32 tolerances throughout: the frustum crosses as C floats, so an exact
    # comparison against a Python float fails on rounding alone.
    for name, got, want in (
        ("left", center - half_width, near * math.tan(fov.angle_left)),
        ("right", center + half_width, near * math.tan(fov.angle_right)),
        ("bottom", bottom, near * math.tan(fov.angle_down)),
        ("top", top, near * math.tan(fov.angle_up)),
    ):
        assert abs(got - want) <= 1e-6 * max(1.0, abs(want)), (
            f"frustum {name}={got}, expected {want}"
        )

    # viz's XrCompositionLayerDepthInfoKHR pair must be the encoding pair, or the
    # runtime reprojects against the wrong range.
    assert abs(f_near - near) <= 1e-6 * near and abs(f_far - far) <= 1e-6 * far, (
        f"clip planes drifted: camera has ({f_near}, {f_far}), viz was told ({near}, {far})"
    )
