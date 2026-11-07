"""Colour segmentation on real frames and synthetic images.

The parity check compares against quads produced by the 2024 ``recognition.py``
on the exact files shipped in ``examples/``.  Vertex order inside a contour is
not part of the contract (OpenCV versions may rotate it), so vertices are
matched as a set with a one-pixel tolerance.
"""

from __future__ import annotations

import numpy as np
import pytest

from robogame_vision.config import ColorThresholds
from robogame_vision.detection.color import draw_quads, orange_mask, sort_vertices_by_y
from robogame_vision.detection.cube import find_quads

cv2 = pytest.importorskip("cv2")


def assert_quads_close(actual: list[np.ndarray], expected: list, atol: float = 1.0) -> None:
    assert len(actual) == len(expected), f"expected {len(expected)} quads, got {len(actual)}"
    remaining = [np.asarray(quad, dtype=np.float64) for quad in expected]
    for quad in actual:
        vertices = np.asarray(quad, dtype=np.float64)
        for index, candidate in enumerate(remaining):
            same_size = vertices.shape == candidate.shape
            if same_size and np.allclose(vertices, candidate, atol=atol, rtol=0):
                remaining.pop(index)
                break
        else:
            raise AssertionError(f"no golden quad matches {vertices.tolist()}")
    assert remaining == []


def test_real_frame_matches_legacy_segmentation(golden, examples_dir) -> None:
    image = cv2.imread(str(examples_dir / "cube_sample.jpg"))
    assert image is not None

    quads = find_quads(image)

    assert_quads_close(quads, golden["segmentation"]["cube_sample.jpg"])


def test_tag_wall_produces_no_cube_candidates(golden, examples_dir) -> None:
    image = cv2.imread(str(examples_dir / "arena_tags.jpg"))
    assert image is not None

    quads = find_quads(image)

    assert_quads_close(quads, golden["segmentation"]["arena_tags.jpg"])


def test_synthetic_orange_square_yields_one_quad() -> None:
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    frame[60:180, 100:220] = (0, 140, 255)  # BGR of the orange cube

    quads = find_quads(frame)

    assert len(quads) == 1
    quad = quads[0]
    assert quad.shape == (4, 2)
    assert quad[:, 0].min() == pytest.approx(100, abs=2)
    assert quad[:, 0].max() == pytest.approx(219, abs=2)
    assert quad[:, 1].min() == pytest.approx(60, abs=2)
    assert quad[:, 1].max() == pytest.approx(179, abs=2)


def test_vertices_are_sorted_by_v() -> None:
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    frame[60:180, 100:220] = (0, 140, 255)

    quad = find_quads(frame)[0]

    assert np.all(np.diff(quad[:, 1]) >= 0)


def test_small_blobs_are_ignored() -> None:
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    frame[10:20, 10:20] = (0, 140, 255)  # 100 px, far below min_area_px

    assert find_quads(frame) == []


def test_orange_mask_is_binary_and_same_size() -> None:
    frame = np.zeros((64, 48, 3), dtype=np.uint8)
    frame[16:32, 16:32] = (0, 140, 255)

    mask = orange_mask(frame)

    assert mask.shape == (64, 48)
    assert mask.dtype == np.uint8
    assert set(np.unique(mask)) <= {0, 255}
    assert mask[24, 24] == 255
    assert mask[0, 0] == 0


def test_orange_mask_rejects_grayscale() -> None:
    with pytest.raises(ValueError, match="BGR"):
        orange_mask(np.zeros((10, 10), dtype=np.uint8))


def test_thresholds_are_configurable() -> None:
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    frame[60:180, 100:220] = (0, 140, 255)

    # An HSV window that excludes orange must find nothing.
    blue_only = ColorThresholds(lower=(90, 100, 0), upper=(130, 255, 255))

    assert find_quads(frame, blue_only) == []


def test_sort_vertices_by_y_is_stable() -> None:
    quad = np.array([[5, 9], [1, 2], [7, 2], [3, 9]], dtype=np.float64)

    sorted_quad = sort_vertices_by_y(quad)

    np.testing.assert_allclose(sorted_quad[:, 1], [2, 2, 9, 9])
    # Equal v keeps the original relative order.
    np.testing.assert_allclose(sorted_quad[:, 0], [1, 7, 5, 3])


def test_draw_quads_copies_the_input() -> None:
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    original = frame.copy()
    quad = np.array([[10, 10], [60, 10], [60, 60], [10, 60]], dtype=np.float64)

    canvas = draw_quads(frame, [quad])

    np.testing.assert_array_equal(frame, original)
    assert canvas.shape == frame.shape
    assert not np.array_equal(canvas, original)
