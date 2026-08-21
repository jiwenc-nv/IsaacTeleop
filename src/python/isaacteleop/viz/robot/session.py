# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""The XR session and frame loop a :class:`RobotTwin` is drawn through."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterator

from .. import (
    DisplayMode,
    FrameInfo,
    PixelFormat,
    ProjectionLayer,
    ProjectionLayerConfig,
    Resolution,
    VizSession,
    VizSessionConfig,
)
from .frame_info import assert_frustum, clamp_dt, flatten_views, frame_clock
from .twin import RobotTwin

LOG = logging.getLogger(__name__)

# Stereo only: render() below is spelled out per eye, so a third view has nowhere
# to go and a monoscopic one would leave the right eye unwritten.
VIEW_COUNT = 2

# Alpha 0 means "show passthrough here", honoured at the runtime's discretion: the
# compositor sets the source-alpha blend bit only for a non-opaque environment, so a VR
# headset composites black instead, which is legible rather than broken.
_CLEAR_COLOR = (0.0, 0.0, 0.0, 0.0)


@dataclass(frozen=True)
class Frame:
    """One frame worth rendering. Only frames past ``should_render`` are handed out."""

    #: This frame's :class:`isaacteleop.viz.FrameInfo`; read views and timing off it.
    info: FrameInfo
    #: Seconds between this frame's predicted display time and the previous rendered
    #: frame's, clamped to :data:`MAX_DT_S`. 0.0 on the first.
    dt: float


class XrTwinSession:
    """Owns the compositor session and the frame loop; the twin owns the pixels.

    Single-threaded and driven by the caller: :meth:`frames` blocks in the runtime's
    frame wait, so the loop runs at display cadence.
    """

    def __init__(
        self,
        twin: RobotTwin,
        *,
        app_name: str,
        near_z: float,
        far_z: float,
        required_extensions: list[str],
        layer_name: str,
    ) -> None:
        """Configure the session.

        ``required_extensions`` must be complete before ``__enter__``, which calls
        ``xrCreateInstance``: an extension discovered afterwards cannot be added, and a
        tracker needing one is then silently dead rather than an error.
        """
        self._twin = twin
        self._near_z = near_z
        self._far_z = far_z
        self._session: VizSession | None = None
        self._layer: ProjectionLayer | None = None
        self._resolution: Resolution | None = None
        self._checked_frustum = False
        self._previous_clock: float | None = None

        self._config = VizSessionConfig()
        self._config.mode = DisplayMode.kXr
        self._config.app_name = app_name
        self._config.xr_near_z = near_z
        self._config.xr_far_z = far_z
        self._config.clear_color = _CLEAR_COLOR
        self._config.required_extensions = required_extensions
        self._layer_name = layer_name

    def __enter__(self) -> XrTwinSession:
        """Create the session and layer, then build the twin at the recommended size."""
        self._session = VizSession.create(self._config)
        try:
            resolution = self._session.get_recommended_resolution()
            self._resolution = resolution

            layer_config = ProjectionLayerConfig()
            layer_config.name = self._layer_name
            layer_config.view_resolution = resolution
            layer_config.color_format = PixelFormat.kRGBA8
            layer_config.depth_format = PixelFormat.kD32F
            layer_config.stereo = True
            self._layer = self._session.add_projection_layer(layer_config)

            # After VizSession.create, which cudaSetDevice's the GPU behind its Vulkan
            # device: a twin's context has to land on that same one.
            self._twin.create(
                resolution.width,
                resolution.height,
                VIEW_COUNT,
                near_z=self._near_z,
                far_z=self._far_z,
            )
        except Exception:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Innermost first: the twin's GPU objects need its context still alive.

        ``destroy()`` runs even when ``create()`` raised partway, so a twin that built a
        context before failing does not leak it. Both latches reset, so a reused instance
        does not carry a stale clock into its next first frame.
        """
        try:
            self._checked_frustum = False
            self._previous_clock = None
            self._resolution = None
            self._twin.destroy()
        finally:
            if self._session is not None:
                session, self._session = self._session, None
                self._layer = None
                session.destroy()

    @property
    def resolution(self) -> Resolution:
        """The per-view resolution the layer and the twin were built at."""
        if self._resolution is None:
            raise RuntimeError("Not entered. Use XrTwinSession as a context manager.")
        return self._resolution

    def oxr_handles(self) -> tuple[int, int, int, int]:
        """``(instance, session, space, proc_addr)``, for sharing this OpenXR session.

        Raises:
            RuntimeError: If the backend produced no handles, which means the XR
                backend did not initialize.
        """
        handles = self._require_session().get_oxr_handles()
        if handles is None:
            raise RuntimeError(
                "XrTwinSession is in kXr mode but produced no OpenXR handles; "
                "the backend did not initialize."
            )
        return handles

    def frames(self) -> Iterator[Frame]:
        """Yield every renderable frame, owning ``begin_frame``/``end_frame``.

        Pose the twin's scene from the yielded frame, then call :meth:`render` exactly
        once; the frame is spent as soon as the loop advances.

        Frames before ``should_render`` are consumed and not yielded: that is what keeps
        a caller's per-frame work -- including ``xrSyncActions`` through a teleop session
        sharing these handles -- off the unthrottled pre-kRunning burst.

        Raises:
            RuntimeError: If the runtime reports a view count this session was not built
                for, e.g. a quad-view runtime against a stereo layer.
        """
        session = self._require_session()
        while not session.should_close():
            info = session.begin_frame()
            try:
                if not info.should_render:
                    continue
                if len(info.views) != VIEW_COUNT:
                    raise RuntimeError(
                        "XrTwinSession is stereo-only but the runtime reported "
                        f"{len(info.views)} views; the twin was built for {VIEW_COUNT}."
                    )
                yield Frame(info=info, dt=self._advance_clock(info))
            finally:
                # Follows EVERY begin_frame(), including the not-rendered path and any
                # exception above. Skipping it wedges the frame loop.
                session.end_frame()

    def render(self, frame: Frame) -> None:
        """Draw the twin for this frame and hand both eyes to the compositor.

        Call once per frame from :meth:`frames`.
        """
        if self._layer is None:
            raise RuntimeError("Not entered. Use XrTwinSession as a context manager.")
        poses, fovs = flatten_views(frame.info)
        self._twin.render(poses, fovs)

        # First rendered frame only: the fov changes per frame, the convention does not.
        if not self._checked_frustum:
            for view in range(VIEW_COUNT):
                assert_frustum(
                    self._twin.frustum(view),
                    frame.info.views[view].fov,
                    self._near_z,
                    self._far_z,
                )
            LOG.info(
                "frustum verified on the first rendered frame (matches FrameInfo fov, "
                "clip planes agree with the session config)"
            )
            self._checked_frustum = True

        self._layer.submit(
            self._twin.color(0),
            self._twin.depth(0),
            self._twin.color(1),
            self._twin.depth(1),
        )

    def _advance_clock(self, info) -> float:
        """Seconds since the previous rendered frame; 0.0 across a frame carrying no time."""
        now = frame_clock(info)
        dt = (
            0.0
            if now is None or self._previous_clock is None
            else clamp_dt(now - self._previous_clock)
        )
        if now is not None:
            self._previous_clock = now
        return dt

    def _require_session(self) -> VizSession:
        if self._session is None:
            raise RuntimeError("Not entered. Use XrTwinSession as a context manager.")
        return self._session
