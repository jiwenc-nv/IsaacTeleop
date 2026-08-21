# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""The MuJoCo backend behind ``isaacteleop.viz.robot.RobotTwin``.

MuJoCo's own renderer (``mjr_render``) read back into CUDA-visible buffers, which is
what lets ``ProjectionLayer.submit()`` take the result with no copy through host memory.
"""

from __future__ import annotations

import mujoco

from . import _mujoco_xr


class MujocoTwin:
    """Draws an ``mjModel``/``mjData`` pair into the XR session's projection layer.

    Holds no scene state of its own: the caller poses ``data`` before each
    :meth:`render`, and geometry is uploaded once from the model address in :meth:`create`.
    """

    def __init__(self, model, data) -> None:
        """Bind to a compiled model. Nothing is allocated until :meth:`create`."""
        self._model = model
        self._data = data
        self._gl_context = None
        self._renderer = None

    @property
    def gl_backend(self) -> str:
        """Which OpenGL backend MuJoCo resolved, for the startup report."""
        return type(self._gl_context).__module__

    def create(
        self, width: int, height: int, view_count: int, *, near_z: float, far_z: float
    ) -> None:
        """Build the GL context and the renderer at the compositor's resolution."""
        self._gl_context = mujoco.GLContext(width, height)
        self._gl_context.make_current()

        # MuJoCo resolves multisample renderbuffers only inside mjr_readPixels, which
        # this path never calls, and a multisample source cannot be blitted with a y
        # flip in one step.
        self._model.vis.quality.offsamples = 0

        self._renderer = _mujoco_xr.Renderer(
            width=width,
            height=height,
            view_count=view_count,
            near_z=near_z,
            far_z=far_z,
            model_address=self._model._address,
        )

    def render(self, poses, fovs) -> None:
        """Update the scene from ``data``, then render every view.

        Raises:
            RuntimeError: If the scene overflowed ``maxgeom``.
        """
        self._renderer.update_scene(self._model._address, self._data._address)
        # mjv_updateScene truncates on overflow and returns normally, with only a
        # stderr warning nobody reads in a frame loop.
        if self._renderer.ngeom >= self._renderer.maxgeom:
            raise RuntimeError(
                f"mjvScene is full: ngeom={self._renderer.ngeom} "
                f"maxgeom={self._renderer.maxgeom}. Geometry is being dropped -- "
                "raise kMaxGeom in cpp/scene_renderer.cpp."
            )
        self._renderer.render(poses, fovs)

    def color(self, view: int):
        return self._renderer.color(view)

    def depth(self, view: int):
        return self._renderer.depth(view)

    def frustum(self, view: int):
        return self._renderer.frustum(view)

    def destroy(self) -> None:
        """Innermost first: the renderer's GL objects need a current context."""
        try:
            if self._renderer is not None:
                renderer, self._renderer = self._renderer, None
                renderer.close()
        finally:
            if self._gl_context is not None:
                gl_context, self._gl_context = self._gl_context, None
                gl_context.free()
