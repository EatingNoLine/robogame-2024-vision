"""Frame acquisition.

The 2024 ``CapThread`` read both cameras in a tight loop and wrote every frame to
``./images/input/<device>.jpg`` - a 3 ms disk write per frame, per camera, with
no way to stop the thread.  :class:`LatestFrames` keeps the same "always have the
newest frame" behaviour but never touches the disk, can be stopped, and lets a
consumer wait for the first frame instead of racing on ``None``.

``FrameSource`` is the seam used by tests and by ``--replay``: anything that
implements ``read()`` can drive the control loop.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Protocol, runtime_checkable

import numpy as np

from .config import CameraConfig

__all__ = ["Camera", "CameraPair", "FrameSource", "LatestFrames", "StaticFrames"]

Frames = tuple[np.ndarray | None, np.ndarray | None]


@runtime_checkable
class FrameSource(Protocol):
    """Anything that can hand the control loop a left/right frame pair."""

    def read(self, timeout: float | None = None) -> Frames:
        """Return the most recent ``(left, right)`` frames, ``None`` if not yet."""

    def close(self) -> None:
        """Release the underlying devices."""


class Camera:
    """One V4L2 camera behind a small, replaceable capture callable."""

    def __init__(
        self,
        config: CameraConfig,
        *,
        capture_factory: Callable[[str], object] | None = None,
    ) -> None:
        self.config = config
        self._cv2 = None
        if capture_factory is None:  # pragma: no cover - needs a real device
            import cv2

            capture_factory = cv2.VideoCapture
            self._cv2 = cv2
        self._capture = capture_factory(config.path)
        self._configure()

    def _configure(self) -> None:
        # ``VideoCapture.set`` silently no-ops on devices that cannot do the
        # requested resolution, which is exactly what the 2024 code relied on.
        if self._cv2 is None:  # fake capture in tests
            return
        self._capture.set(self._cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
        self._capture.set(self._cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)

    def is_open(self) -> bool:
        opened = getattr(self._capture, "isOpened", None)
        return True if opened is None else bool(opened())

    def read(self) -> np.ndarray | None:
        ok, frame = self._capture.read()
        return frame if ok else None

    def close(self) -> None:
        release = getattr(self._capture, "release", None)
        if release is not None:
            release()


class CameraPair:
    """The two side cameras, read one after the other (as in 2024)."""

    def __init__(self, left: Camera, right: Camera) -> None:
        self.left = left
        self.right = right

    def read(self, timeout: float | None = None) -> Frames:
        return self.left.read(), self.right.read()

    def close(self) -> None:
        self.left.close()
        self.right.close()


class StaticFrames:
    """A frame source that replays a fixed pair - no hardware, no threads."""

    def __init__(self, left: np.ndarray | None, right: np.ndarray | None = None) -> None:
        self._frames: Frames = (left, None if right is None else right)

    def read(self, timeout: float | None = None) -> Frames:
        return self._frames

    def close(self) -> None:
        return None


class LatestFrames:
    """Background thread keeping only the newest left/right frame pair."""

    def __init__(self, source: FrameSource) -> None:
        self._source = source
        self._condition = threading.Condition()
        self._frames: Frames = (None, None)
        self._updated = False
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> LatestFrames:
        self._thread = threading.Thread(target=self._run, name="frames", daemon=True)
        self._thread.start()
        return self

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                frames = self._source.read()
            except Exception:  # pragma: no cover - driver dependent
                frames = (None, None)
            with self._condition:
                self._frames = frames
                self._updated = frames[0] is not None or frames[1] is not None
                self._condition.notify_all()

    def read(self, timeout: float | None = None) -> Frames:
        """Block until the first pair arrives, then always return the newest."""
        with self._condition:
            if not self._updated and timeout is not None and self._thread is not None:
                self._condition.wait_for(lambda: self._updated, timeout=timeout)
            return self._frames

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._source.close()

    def __enter__(self) -> LatestFrames:
        return self.start()

    def __exit__(self, *exc_info: object) -> None:
        self.stop()
