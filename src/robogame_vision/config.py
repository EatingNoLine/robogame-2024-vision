"""Tunables for the vision stack.

Every magic number that used to be scattered through the 2024 scripts lives
here, named and documented.  The values themselves are unchanged: they were
tuned on the real arena and there is no hardware available to re-derive them.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "AppConfig",
    "CameraConfig",
    "ColorThresholds",
    "ControlConfig",
    "CubeGeometry",
    "SerialConfig",
    "TagConfig",
    "default_calibration_dir",
]


@dataclass(frozen=True)
class CameraConfig:
    """A V4L2 capture device on the Orange Pi.

    ``device`` accepts either a bare alias (``"20"``) or a full path
    (``"/dev/video20"``).
    """

    device: str
    width: int = 1920
    height: int = 1080

    @property
    def path(self) -> str:
        if self.device.startswith("/dev/"):
            return self.device
        return f"/dev/video{self.device}"


@dataclass(frozen=True)
class ColorThresholds:
    """HSV window (OpenCV scale: H in 0-179) used to find the orange cube."""

    lower: tuple[int, int, int] = (5, 100, 0)
    upper: tuple[int, int, int] = (20, 255, 255)
    # Contours outside this pixel-area window are ignored; the window is what
    # separates "a cube" from noise and from a cube that fills the whole frame.
    min_area_px: float = 10_000.0
    max_area_px: float = 350_000.0
    morph_kernel_px: int = 5
    # epsilon for approxPolyDP, as a fraction of the contour perimeter.
    polygon_epsilon: float = 0.008


@dataclass(frozen=True)
class CubeGeometry:
    """Geometry of the cube's top face, in millimetres.

    The top face is a square of roughly 100 mm; the selector keys on the
    right-isosceles triangle formed by three of its corners, i.e. two edges of
    ``top_face_edge_mm`` and the ``top_face_diagonal_mm`` between them.
    """

    top_face_edge_mm: float = 101.08
    top_face_diagonal_mm: float = 142.93
    # Distances are accepted when (observed - expected) ** 2 < this value,
    # i.e. within +-24.5 mm.  Kept squared to match the tuned behaviour exactly.
    length_tolerance_sq_mm2: float = 600.0


@dataclass(frozen=True)
class ControlConfig:
    """Thresholds for turning a detected offset into motor commands."""

    # Below this distance to the required position the cube counts as graspable.
    grasp_tolerance_mm: float = 40.0
    # Offsets smaller than this are ignored (the arm cannot do better).
    deadband_mm: float = 15.0
    # Length of the blind forward/backward jog used while searching.
    search_jog_mm: int = 200


@dataclass(frozen=True)
class TagConfig:
    """AprilTag geometry and the empirically fitted distance scale."""

    tag_size_mm: float = 400.0
    # NOT a focal length in pixels: 2.163 is the constant the 2024 code fitted
    # to make `distance = tag_size * FOCAL / diagonal_px` roughly agree with the
    # arena.  See docs/known-issues.md - the resulting unit is not millimetres.
    focal_length_mm: float = 2.163
    crooked_tolerance_deg: float = 10.0


@dataclass(frozen=True)
class SerialConfig:
    """Serial link to the STM32 chassis board."""

    port: str = "/dev/my_serial0"
    baudrate: int = 115200
    # How long to wait for the "OK" acknowledgement before giving up.
    ack_timeout_s: float = 5.0
    # Settling delay the firmware needs after grab/move/shoot.
    settle_s: float = 0.3


def default_calibration_dir() -> Path:
    """Best guess for ``data/calibration`` (override with ``$ROBOGAME_CALIBRATION``)."""
    env = os.environ.get("ROBOGAME_CALIBRATION")
    if env:
        return Path(env)
    # src/robogame_vision/config.py -> repository root
    candidate = Path(__file__).resolve().parents[2] / "data" / "calibration"
    if candidate.is_dir():
        return candidate
    return Path("data/calibration")


@dataclass(frozen=True)
class AppConfig:
    """Everything the control loop needs, in one immutable object."""

    left_camera: CameraConfig = field(default_factory=lambda: CameraConfig("20"))
    right_camera: CameraConfig = field(default_factory=lambda: CameraConfig("22"))
    calibration_dir: Path = field(default_factory=default_calibration_dir)
    thresholds: ColorThresholds = field(default_factory=ColorThresholds)
    cube: CubeGeometry = field(default_factory=CubeGeometry)
    control: ControlConfig = field(default_factory=ControlConfig)
    tags: TagConfig = field(default_factory=TagConfig)
    serial: SerialConfig = field(default_factory=SerialConfig)
