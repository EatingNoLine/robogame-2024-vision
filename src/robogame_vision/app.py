"""The control loop: frames in, chassis commands out.

The 2024 ``main.py`` mixed camera threads, detection, state and serial commands
in one 282-line script driven by module-level globals.  The same decision logic
lives here behind two seams - a :class:`~robogame_vision.camera.FrameSource` and
an :class:`~robogame_vision.robot.controller.Actuator` - so it can be replayed
from files and asserted in tests without hardware.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import numpy as np

from .camera import FrameSource
from .config import AppConfig, ColorThresholds, ControlConfig, CubeGeometry
from .detection.cube import find_quads
from .geometry.camera_model import GroundPlaneModel
from .geometry.cube_center import CubeEstimate, top_face_center
from .robot.controller import Actuator
from .robot.protocol import ArmSide, Direction

__all__ = ["ControlLoop", "CubeDetector", "Detection", "DetectionKind"]

log = logging.getLogger(__name__)


class DetectionKind(str, Enum):
    """What the side cameras currently say about the cube."""

    NONE = "none"
    TOO_FAR = "too_far"
    GRASP_LEFT = "grasp_left"
    GRASP_RIGHT = "grasp_right"


@dataclass(frozen=True)
class Detection:
    """Outcome of one left+right detection pass."""

    kind: DetectionKind
    #: Cube offset from the robot frame origin, in millimetres, when known.
    offset: tuple[float, float] | None = None

    @property
    def found(self) -> bool:
        return self.kind is not DetectionKind.NONE


@dataclass(frozen=True)
class CubeDetector:
    """Colour segmentation + projection + top-face selection for both cameras."""

    left_model: GroundPlaneModel
    right_model: GroundPlaneModel
    thresholds: ColorThresholds = field(default_factory=ColorThresholds)
    cube: CubeGeometry = field(default_factory=CubeGeometry)
    control: ControlConfig = field(default_factory=ControlConfig)

    @classmethod
    def from_calibration(cls, directory: str | Path) -> CubeDetector:
        """Load ``<directory>/left`` and ``<directory>/right``."""
        root = Path(directory)
        return cls(
            left_model=GroundPlaneModel.load(root / "left"),
            right_model=GroundPlaneModel.load(root / "right"),
        )

    def estimate(self, frame: np.ndarray, model: GroundPlaneModel) -> CubeEstimate:
        """Find the top-face centre of the cube seen by one camera."""
        quads = find_quads(frame, self.thresholds)
        return top_face_center(quads, model.pixels_to_ground, self.cube)

    def detect(self, left: np.ndarray | None, right: np.ndarray | None) -> Detection:
        """Combine both cameras, preferring whichever cube is closer.

        Mirrors the 2024 order of evaluation: the left camera is checked first
        and wins immediately when it is close enough to grab.
        """
        best: tuple[float, Detection] | None = None
        candidates = (
            (left, self.left_model, DetectionKind.GRASP_LEFT),
            (right, self.right_model, DetectionKind.GRASP_RIGHT),
        )
        for frame, model, grasp_kind in candidates:
            if frame is None:
                continue
            estimate = self.estimate(frame, model)
            if not estimate.found or estimate.center is None:
                continue
            x, y = estimate.center
            distance_sq = x * x + y * y
            detection = Detection(grasp_kind, (x, y))
            if distance_sq <= self.control.grasp_tolerance_mm**2:
                return detection
            if best is None or distance_sq < best[0]:
                best = (distance_sq, Detection(DetectionKind.TOO_FAR, (x, y)))
        return best[1] if best is not None else Detection(DetectionKind.NONE)


class ControlLoop:
    """Turn detections into chassis commands until stopped."""

    def __init__(
        self,
        frames: FrameSource,
        actuator: Actuator,
        detector: CubeDetector,
        config: AppConfig | None = None,
        *,
        frame_timeout_s: float = 5.0,
        idle_sleep_s: float = 0.05,
    ) -> None:
        self.frames = frames
        self.actuator = actuator
        self.detector = detector
        self.config = config or AppConfig()
        self.frame_timeout_s = frame_timeout_s
        self.idle_sleep_s = idle_sleep_s
        self._jog_backward = True

    # -- one iteration ----------------------------------------------------
    def step(self, detection: Detection) -> str:
        """Execute the command for ``detection``; returns a short action name."""
        control = self.config.control
        if detection.kind is DetectionKind.NONE:
            direction = Direction.BACKWARD if self._jog_backward else Direction.FORWARD
            self._jog_backward = not self._jog_backward
            self.actuator.move(control.search_jog_mm, direction)
            return f"search {direction.value} {control.search_jog_mm}mm"

        if detection.kind in (DetectionKind.GRASP_LEFT, DetectionKind.GRASP_RIGHT):
            side = ArmSide.LEFT if detection.kind is DetectionKind.GRASP_LEFT else ArmSide.RIGHT
            self.actuator.grab(side)
            self.actuator.shoot()
            return f"grab {side.value} + shoot"

        if detection.offset is None:  # pragma: no cover - defensive
            return "no offset"
        x, y = detection.offset
        deadband = control.deadband_mm
        if abs(y) <= deadband:
            self.actuator.stay()
        else:
            self.actuator.move(int(abs(y)), Direction.BACKWARD if y < 0 else Direction.FORWARD)
        if abs(x) <= deadband:
            self.actuator.stay()
        else:
            self.actuator.move(int(abs(x)), Direction.LEFT if x < 0 else Direction.RIGHT)
        return f"approach ({x:.0f}, {y:.0f})mm"

    # -- loop -------------------------------------------------------------
    def run(self, stop: threading.Event | None = None, max_steps: int | None = None) -> int:
        """Run until ``stop`` is set (or ``max_steps`` iterations pass).

        Returns the number of *detections* that were turned into commands;
        iterations that had no frames yet are not counted.
        """
        stop = stop or threading.Event()
        steps = 0
        iterations = 0
        while not stop.is_set():
            if max_steps is not None and iterations >= max_steps:
                break
            iterations += 1
            left, right = self.frames.read(timeout=self.frame_timeout_s)
            if left is None and right is None:
                log.debug("no frames yet")
                time.sleep(self.idle_sleep_s)
                continue
            detection = self.detector.detect(left, right)
            action = self.step(detection)
            log.info("[%d] %s -> %s", steps, detection.kind.value, action)
            steps += 1
        return steps
