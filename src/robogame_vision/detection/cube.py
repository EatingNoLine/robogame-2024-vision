"""Orange-cube segmentation: HSV mask -> contours -> polygon approximations."""

from __future__ import annotations

import cv2
import numpy as np

from ..config import ColorThresholds
from .color import orange_mask, sort_vertices_by_y

__all__ = ["find_quads"]


def find_quads(
    bgr: np.ndarray,
    thresholds: ColorThresholds | None = None,
) -> list[np.ndarray]:
    """Return the cube candidates in ``bgr`` as ``(N, 2)`` pixel-vertex arrays.

    A candidate is an orange contour whose area falls inside the tuned window,
    simplified by ``approxPolyDP`` and then sorted by ``v`` (see
    :func:`~robogame_vision.detection.color.sort_vertices_by_y`).
    """
    thresholds = thresholds or ColorThresholds()
    mask = orange_mask(bgr, thresholds)
    contours, _ = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

    quads: list[np.ndarray] = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if not thresholds.min_area_px < area < thresholds.max_area_px:
            continue
        epsilon = thresholds.polygon_epsilon * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        quads.append(sort_vertices_by_y(approx))
    return quads
