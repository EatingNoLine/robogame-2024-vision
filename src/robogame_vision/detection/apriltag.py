"""AprilTag detection wrapper.

The detector is an optional dependency and is imported on first use, so the rest
of the package works without a C toolchain.  Two backends are accepted, because
the original ``apriltag`` package needs a compiler while ``pupil-apriltags``
ships wheels and exposes the same ``detect(gray)``/``.tag_id``/``.corners`` API:

    pip install 'robogame-vision[apriltag]'     # swatbotics apriltag
    pip install pupil-apriltags                 # maintained fork, wheels

``AprilTagDetector.backend`` records which one is in use.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

__all__ = ["AprilTagDetector", "TagDetection", "render_detections"]

_BACKENDS = ("apriltag", "pupil_apriltags")


@dataclass(frozen=True)
class TagDetection:
    """One detected tag: its family id and four ``(u, v)`` corners."""

    tag_id: int
    corners: np.ndarray


def _open_detector(families: str) -> tuple[str, object]:
    """Instantiate whichever AprilTag backend is installed."""
    try:
        import apriltag
    except ImportError:
        pass
    else:
        return "apriltag", apriltag.Detector(apriltag.DetectorOptions(families=families))

    try:
        from pupil_apriltags import Detector
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise ImportError(
            "AprilTag support needs a detector backend; install either "
            "pip install 'robogame-vision[apriltag]' (needs a C compiler) or "
            "pip install pupil-apriltags (wheels available)"
        ) from exc
    return "pupil_apriltags", Detector(families=families)


class AprilTagDetector:
    """Detect ``tag36h11`` tags in a BGR frame."""

    def __init__(self, families: str = "tag36h11") -> None:
        self.families = families
        self.backend, self._detector = _open_detector(families)

    def detect(self, bgr: np.ndarray) -> list[TagDetection]:
        frame = np.asarray(bgr)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        return [
            TagDetection(tag_id=int(tag.tag_id), corners=np.asarray(tag.corners, dtype=np.float64))
            for tag in self._detector.detect(gray)
        ]


def render_detections(
    bgr: np.ndarray,
    detections: list[TagDetection],
    *,
    radius: int = 10,
) -> np.ndarray:
    """Return a copy of ``bgr`` with corners and tag centres marked."""
    canvas = np.array(bgr, copy=True)
    if canvas.ndim == 2:
        canvas = cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGR)
    for detection in detections:
        corners = np.round(detection.corners).astype(np.int32)
        cv2.polylines(canvas, [corners.reshape(-1, 1, 2)], True, (255, 0, 0), 2)
        for u, v in corners:
            cv2.circle(canvas, (int(u), int(v)), radius, (0, 0, 255), -1)
        centre = corners.mean(axis=0).astype(int)
        cv2.putText(
            canvas,
            str(detection.tag_id),
            (int(centre[0]) + 12, int(centre[1]) - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )
    return canvas
