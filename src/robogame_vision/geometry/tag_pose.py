"""AprilTag-based wall distance and yaw.

The 2024 detector reported ``(tag_id, tag_count, distance, crooked, theta)``
through a recursive function that re-detected on a de-rotated copy of the frame.
That recursion is here replaced by a single pass, the tuple by :class:`TagPose`,
and two bugs are fixed (both documented in ``docs/known-issues.md``):

* the sign of the vertical extent made the clamping always fire, so the yaw was
  *always* ``0.0`` and ``crooked`` was never ``True``;
* tag ids above ``5`` raised :class:`IndexError` because the corners were
  binned into a fixed six-entry list.

The distance formula and its constants are unchanged - including the fact that
``focal_length_mm`` is an empirically fitted number whose output is *not*
strictly millimetres.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..config import TagConfig

__all__ = ["TagPose", "estimate_tag_pose"]


@dataclass(frozen=True)
class TagPose:
    """What the front camera sees of one AprilTag."""

    tag_id: int | None
    tag_count: int
    #: Legacy distance estimate; see the module docstring about its unit.
    distance: float
    yaw_deg: float
    crooked: bool


def estimate_tag_pose(
    corners: np.ndarray,
    *,
    image_size: tuple[int, int],
    tag_id: int | None = None,
    tag_count: int = 1,
    config: TagConfig | None = None,
) -> TagPose:
    """Estimate distance and yaw for one tag from its four ``(u, v)`` corners.

    ``corners`` must be in cyclic order around the tag (either direction, as
    returned by both supported detectors); indices 1/3 and 0/2 are then opposite
    corners, which is what the diagonal and edge selections assume.

    ``image_size`` is ``(height, width)``, matching ``frame.shape[:2]``.
    """
    config = config or TagConfig()
    quad = np.asarray(corners, dtype=np.float64).reshape(4, 2)
    height, width = image_size
    if width <= 0 or height <= 0:
        raise ValueError(f"invalid image size: {image_size}")

    centre = quad.mean(axis=0)
    faces_right = centre[0] > width / 2.0
    # Corner indices were chosen so that p1 -> p4 is a diagonal of the tag and
    # p1 -> p2 / p3 -> p1 are the two sides used for the yaw ratio.
    p1, p2, p3, p4 = (2, 3, 1, 0) if faces_right else (3, 2, 0, 1)

    diagonal_px = float(np.linalg.norm(quad[p1] - quad[p4]))
    if diagonal_px <= 0.0:
        raise ValueError("degenerate tag corners: zero diagonal")

    distance_to_centre = config.tag_size_mm * config.focal_length_mm / diagonal_px
    # The offset below is the *normalised* pixel offset, so this mixes units -
    # it is part of the legacy formula and is kept for parity.
    lateral = abs(centre[0] / width - 0.5)
    distance = float(np.sqrt(max(distance_to_centre**2 - lateral**2, 0.0)))

    vertical_extent = abs(float(quad[p3][1] - quad[p1][1]))
    edge_px = float(np.linalg.norm(quad[p1] - quad[p2]))
    ratio = 1.0 if vertical_extent <= 0.0 else min(edge_px / vertical_extent, 1.0)
    yaw = float(np.degrees(np.arccos(ratio)))
    if not faces_right:
        yaw = -yaw

    return TagPose(
        tag_id=tag_id,
        tag_count=tag_count,
        distance=distance,
        yaw_deg=yaw,
        crooked=abs(yaw) > config.crooked_tolerance_deg,
    )
