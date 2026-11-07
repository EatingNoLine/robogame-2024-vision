"""Pixel -> ground-plane projection for the two side cameras.

The 2024 code had two nearly identical modules, ``realworld_L.py`` and
``realworld_R.py``, that differed only in the calibration directory.  They are
merged here into one immutable model; the arithmetic is unchanged and is pinned
by ``tests/test_camera_model.py`` against values produced by the original code.

How it works: a pixel is lifted onto a *fixed-depth* ray (``depth_scale``), moved
into the robot frame with the extrinsic translation/rotation, and finally mapped
onto the ground plane by a homography.  This is a calibrated approximation, not
a triangulation - there is no stereo baseline and no depth from the cube itself.
See ``docs/calibration.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

__all__ = ["CALIBRATION_FILES", "CalibrationError", "GroundPlaneModel"]

#: Files this model needs, in the names used by :func:`GroundPlaneModel.load`.
CALIBRATION_FILES = {
    "inverse_camera_matrix": "inverse_camera_matrix.npy",
    "inverse_rotation": "inverse_rotation.npy",
    "depth_scale": "depth_scale.npy",
    "translation": "translation.npy",
    "ground_homography": "ground_homography.npy",
}


class CalibrationError(RuntimeError):
    """The calibration directory is missing data or contains unusable arrays."""


@dataclass(frozen=True)
class GroundPlaneModel:
    """Calibrated pixel -> ground-plane map for one camera."""

    inverse_camera_matrix: np.ndarray
    inverse_rotation: np.ndarray
    depth_scale: float
    translation: np.ndarray
    ground_homography: np.ndarray

    @classmethod
    def load(cls, directory: str | Path) -> GroundPlaneModel:
        """Load ``directory/{left,right}`` calibration arrays."""
        root = Path(directory)
        if not root.is_dir():
            raise CalibrationError(f"calibration directory does not exist: {root}")

        arrays: dict[str, np.ndarray] = {}
        for key, filename in CALIBRATION_FILES.items():
            path = root / filename
            if not path.is_file():
                raise CalibrationError(f"missing calibration file: {path}")
            try:
                arrays[key] = np.load(path)
            except (OSError, ValueError) as exc:  # pragma: no cover - corrupt file
                raise CalibrationError(f"cannot read {path}: {exc}") from exc

        return cls(
            inverse_camera_matrix=_as_square(arrays["inverse_camera_matrix"], 3, root),
            inverse_rotation=_as_square(arrays["inverse_rotation"], 3, root),
            depth_scale=_as_scalar(arrays["depth_scale"], root),
            translation=_as_vector(arrays["translation"], 3, root),
            ground_homography=_as_square(arrays["ground_homography"], 3, root),
        )

    def pixels_to_ground(self, pixels: np.ndarray) -> np.ndarray:
        """Project an ``(N, 2)`` array of ``(u, v)`` pixels to ground ``(x, y)`` mm."""
        points = np.atleast_2d(np.asarray(pixels, dtype=np.float64))
        if points.ndim != 2 or points.shape[1] != 2:
            raise ValueError(f"pixels must have shape (N, 2), got {points.shape}")

        homogeneous = np.column_stack([points, np.ones(len(points))])
        # (depth_scale * uv) through the inverse camera matrix == ray in camera frame
        camera = (self.depth_scale * homogeneous) @ self.inverse_camera_matrix.T
        camera = camera - self.translation
        robot = camera @ self.inverse_rotation.T

        plane = np.column_stack([robot[:, 0], robot[:, 1], np.ones(len(robot))])
        mapped = plane @ self.ground_homography.T
        return mapped[:, :2] / mapped[:, 2:3]

    def pixel_to_ground(self, u: float, v: float) -> tuple[float, float]:
        """Project a single pixel; returns ``(x_mm, y_mm)`` in the robot frame."""
        x, y = self.pixels_to_ground([[u, v]])[0]
        return float(x), float(y)


def _as_square(array: np.ndarray, size: int, root: Path) -> np.ndarray:
    matrix = np.asarray(array, dtype=np.float64)
    if matrix.shape != (size, size):
        raise CalibrationError(f"expected a {size}x{size} matrix under {root}, got {matrix.shape}")
    return matrix


def _as_vector(array: np.ndarray, size: int, root: Path) -> np.ndarray:
    vector = np.asarray(array, dtype=np.float64).reshape(-1)
    if vector.size != size:
        raise CalibrationError(f"expected a {size}-element vector under {root}, got {vector.size}")
    return vector


def _as_scalar(array: np.ndarray, root: Path) -> float:
    values = np.asarray(array, dtype=np.float64).reshape(-1)
    if values.size != 1:
        raise CalibrationError(f"expected a scalar under {root}, got {values.size} values")
    return float(values[0])
