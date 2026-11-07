"""AprilTag pose: analytic geometry and the two legacy bugs that were fixed."""

from __future__ import annotations

import numpy as np
import pytest

from robogame_vision.config import TagConfig
from robogame_vision.geometry.tag_pose import TagPose, estimate_tag_pose

IMAGE_SIZE = (1080, 1920)
DEFAULT = TagConfig()


def _square(cx: float, cy: float, half: float, angle_deg: float = 0.0) -> np.ndarray:
    """Corners TL, TR, BR, BL rotated about the centre."""
    radians = np.deg2rad(angle_deg)
    cos, sin = np.cos(radians), np.sin(radians)
    base = [(-half, -half), (half, -half), (half, half), (-half, half)]
    return np.array(
        [[cx + x * cos - y * sin, cy + x * sin + y * cos] for x, y in base], dtype=np.float64
    )


def _trapezoid() -> np.ndarray:
    """Yawed tag: 400 px vertical extent with a 320 px bottom edge."""
    return np.array(
        [[700.0, 300.0], [1100.0, 300.0], [1020.0, 700.0], [700.0, 700.0]], dtype=np.float64
    )


def test_centred_square_has_zero_yaw() -> None:
    pose = estimate_tag_pose(_square(960, 540, 200), image_size=IMAGE_SIZE, tag_id=2)

    assert isinstance(pose, TagPose)
    assert pose.tag_id == 2
    assert pose.yaw_deg == pytest.approx(0.0, abs=1e-9)
    assert pose.crooked is False


def test_yaw_comes_from_the_edge_to_height_ratio() -> None:
    pose = estimate_tag_pose(_trapezoid(), image_size=IMAGE_SIZE, tag_id=1)

    expected = -np.degrees(np.arccos(320.0 / 400.0))
    assert pose.yaw_deg == pytest.approx(expected, abs=1e-9)
    assert pose.crooked is True


def test_yaw_sign_follows_the_camera_side() -> None:
    left = _trapezoid()
    right = left + np.array([960.0, 0.0])

    left_pose = estimate_tag_pose(left, image_size=IMAGE_SIZE)
    right_pose = estimate_tag_pose(right, image_size=IMAGE_SIZE)

    assert left_pose.yaw_deg < 0 < right_pose.yaw_deg
    assert left_pose.yaw_deg == pytest.approx(-right_pose.yaw_deg, abs=1e-9)


def test_crooked_tolerance_is_configurable() -> None:
    corners = _trapezoid()

    strict = estimate_tag_pose(
        corners, image_size=IMAGE_SIZE, config=TagConfig(crooked_tolerance_deg=10)
    )
    lenient = estimate_tag_pose(
        corners, image_size=IMAGE_SIZE, config=TagConfig(crooked_tolerance_deg=80)
    )

    assert strict.crooked is True
    assert lenient.crooked is False


def test_distance_uses_the_documented_legacy_formula() -> None:
    corners = _trapezoid()
    config = DEFAULT

    pose = estimate_tag_pose(corners, image_size=IMAGE_SIZE, config=config)

    # Not face-right: p1 = BL (index 3), p4 = TR (index 1).
    diagonal = float(np.linalg.norm(corners[3] - corners[1]))
    centre_x = float(corners[:, 0].mean())
    expected_to_centre = config.tag_size_mm * config.focal_length_mm / diagonal
    expected = np.sqrt(expected_to_centre**2 - abs(centre_x / IMAGE_SIZE[1] - 0.5) ** 2)

    assert pose.distance == pytest.approx(float(expected), rel=1e-12)


def test_tag_count_is_passed_through() -> None:
    pose = estimate_tag_pose(_square(600, 500, 150), image_size=IMAGE_SIZE, tag_count=3)

    assert pose.tag_count == 3


def test_high_tag_ids_do_not_crash() -> None:
    """The 2024 code indexed a fixed six-slot list and raised IndexError for id 7."""
    pose = estimate_tag_pose(_square(960, 540, 200), image_size=IMAGE_SIZE, tag_id=7)

    assert pose.tag_id == 7


def test_degenerate_corners_are_rejected() -> None:
    collapsed = np.zeros((4, 2), dtype=np.float64)

    with pytest.raises(ValueError, match="degenerate"):
        estimate_tag_pose(collapsed, image_size=IMAGE_SIZE)


def test_invalid_image_size_is_rejected() -> None:
    with pytest.raises(ValueError, match="image size"):
        estimate_tag_pose(_square(0, 0, 10), image_size=(0, 0))


def test_zero_vertical_extent_is_clamped_instead_of_dividing_by_zero() -> None:
    flat = np.array([[100.0, 500.0], [500.0, 500.0], [500.0, 500.0], [100.0, 500.0]])

    pose = estimate_tag_pose(flat, image_size=IMAGE_SIZE)

    assert pose.yaw_deg == pytest.approx(0.0)
