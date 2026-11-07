"""Colour primitives for the orange cube.

These are the pure image-space helpers: no calibration, no robot commands, no
files written to disk.  The 2024 ``recognition.py`` drew over the caller's frame
and reordered vertices in place; here drawing is a separate, explicit call and
every function returns new arrays.
"""

from __future__ import annotations

import numpy as np

from ..config import ColorThresholds

__all__ = ["draw_quads", "orange_mask", "sort_vertices_by_y"]

try:  # OpenCV is a hard dependency, but keep the error readable if it is missing
    import cv2
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "robogame_vision needs OpenCV: pip install 'robogame-vision' (or opencv-python)"
    ) from exc


def orange_mask(bgr: np.ndarray, thresholds: ColorThresholds | None = None) -> np.ndarray:
    """Return the 8-bit mask of pixels inside the orange HSV window."""
    thresholds = thresholds or ColorThresholds()
    frame = np.asarray(bgr)
    if frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError(f"expected a BGR image of shape (h, w, 3), got {frame.shape}")

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(
        hsv,
        np.array(thresholds.lower, dtype=np.uint8),
        np.array(thresholds.upper, dtype=np.uint8),
    )
    kernel_size = int(thresholds.morph_kernel_px)
    if kernel_size > 1:
        kernel = np.ones((kernel_size, kernel_size), dtype=np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    return mask


def sort_vertices_by_y(quad: np.ndarray) -> np.ndarray:
    """Sort ``(N, 2)`` vertices by increasing ``v``.

    The 2024 code bubbled the vertices of every approximation into this order so
    that "the first five vertices" (see
    :func:`robogame_vision.geometry.cube_center.top_face_center`) is stable.
    A stable ``argsort`` produces the same permutation as that bubble sort,
    including for equal ``v``.
    """
    vertices = np.asarray(quad, dtype=np.float64).reshape(-1, 2)
    return vertices[np.argsort(vertices[:, 1], kind="stable")]


def draw_quads(
    bgr: np.ndarray,
    quads: list[np.ndarray],
    *,
    colour: tuple[int, int, int] = (0, 255, 0),
    radius: int = 5,
) -> np.ndarray:
    """Return a copy of ``bgr`` with the quads outlined, for debugging/READMEs.

    Quads are stored with their vertices sorted by ``v`` (that ordering is what
    the selector needs), so the outline is drawn as the convex hull of the
    vertices; the dots mark the detected vertices themselves.
    """
    canvas = np.array(bgr, copy=True)
    if canvas.ndim != 3:
        raise ValueError(f"expected a BGR image of shape (h, w, 3), got {canvas.shape}")
    for quad in quads:
        points = np.asarray(quad, dtype=np.float64).reshape(-1, 2)
        if len(points) < 2:
            continue
        vertices = np.round(points).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(canvas, [cv2.convexHull(vertices)], True, colour, 2)
        for u, v in vertices.reshape(-1, 2):
            cv2.circle(canvas, (int(u), int(v)), radius, (0, 0, 255), -1)
    return canvas
