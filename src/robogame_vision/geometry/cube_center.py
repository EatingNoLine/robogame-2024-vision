"""Pick the centre of the cube's top face out of a partially seen contour.

The selector is the interesting piece of the 2024 vision code and is kept
behaviour-identical.  The idea: the top face is a square of ~101 mm, so three of
its corners form a right-isosceles triangle whose legs are one edge and whose
hypotenuse is the diagonal.  The midpoint of that hypotenuse *is* the centre of
the face, which saves having to solve a PnP problem on a 5-vertex contour.

Input contours come from :func:`robogame_vision.detection.cube.find_quads` and
have their vertices sorted by ``v``, so "the first five vertices" is stable.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from itertools import combinations

import numpy as np

from ..config import CubeGeometry

__all__ = ["CubeEstimate", "Projector", "top_face_center"]

#: Maps ``(N, 2)`` pixels to ``(N, 2)`` millimetres in the robot frame.
Projector = Callable[[np.ndarray], np.ndarray]


@dataclass(frozen=True)
class CubeEstimate:
    """Result of the top-face selector."""

    found: bool
    center: tuple[float, float] | None
    #: True when a contour had more than eight vertices, i.e. two cubes overlap.
    overlapping: bool


def top_face_center(
    quads: Sequence[np.ndarray] | np.ndarray,
    project: Projector,
    geometry: CubeGeometry | None = None,
) -> CubeEstimate:
    """Locate the top-face centre among ``quads`` (pixel coordinates).

    ``project`` turns pixels into millimetres; pass
    :meth:`~robogame_vision.geometry.camera_model.GroundPlaneModel.pixels_to_ground`.
    """
    geometry = geometry or CubeGeometry()
    centres: list[tuple[float, float]] = []
    overlapping = False
    found = False

    for quad in quads:
        vertices = np.asarray(quad, dtype=np.float64).reshape(-1, 2)
        count = len(vertices)
        if count > 8:
            overlapping = True
        if 4 < count < 9:
            projected = np.asarray(project(vertices[:5]), dtype=np.float64).reshape(-1, 2)
            centre = _match_top_face(projected, geometry)
            if centre is not None:
                found = True
                centres.append(centre)
        elif count < 5:
            # Degenerate contour: the original code returned the first vertex,
            # which is still in *pixels*.  Preserved as-is; see docs/known-issues.md.
            found = True
            centres.append((float(vertices[0][0]), float(vertices[0][1])))

    if not found:
        return CubeEstimate(found=False, center=None, overlapping=overlapping)

    closest = min(centres, key=lambda point: point[0] ** 2 + point[1] ** 2)
    return CubeEstimate(found=True, center=closest, overlapping=overlapping)


def _match_top_face(points: np.ndarray, geometry: CubeGeometry) -> tuple[float, float] | None:
    """Return the midpoint of the triangle's hypotenuse, if it looks like a face."""
    tolerance = geometry.length_tolerance_sq_mm2
    for combo in combinations(range(len(points)), 3):
        a, b, c = (points[index] for index in combo)
        sides = sorted(
            (
                (float(np.linalg.norm(b - c)), b, c),
                (float(np.linalg.norm(a - c)), a, c),
                (float(np.linalg.norm(a - b)), a, b),
            ),
            key=lambda side: side[0],
            reverse=True,
        )
        if (
            (sides[0][0] - geometry.top_face_diagonal_mm) ** 2 < tolerance
            and (sides[1][0] - geometry.top_face_edge_mm) ** 2 < tolerance
            and (sides[2][0] - geometry.top_face_edge_mm) ** 2 < tolerance
        ):
            _, first, second = sides[0]
            return (
                float((first[0] + second[0]) / 2.0),
                float((first[1] + second[1]) / 2.0),
            )
    return None
