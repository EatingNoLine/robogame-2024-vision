"""Top-face selection: legacy parity plus the behaviour it is documented to have."""

from __future__ import annotations

import numpy as np
import pytest

from robogame_vision.detection.cube import find_quads
from robogame_vision.geometry.cube_center import CubeEstimate, top_face_center

cv2 = pytest.importorskip("cv2")


def _quads(raw: list[list[list[float]]]) -> list[np.ndarray]:
    return [np.asarray(quad, dtype=np.float64) for quad in raw]


def _assert_estimate(estimate: CubeEstimate, expected: dict, atol: float = 1e-3) -> None:
    # 1e-3 mm absorbs the float32 -> float64 depth-scale change; see
    # tests/test_camera_model.py.
    assert estimate.found is expected["found"]
    assert estimate.overlapping is expected["n_cube"]
    if expected["center"] is None:
        assert estimate.center is None
    else:
        assert estimate.center == pytest.approx(tuple(expected["center"]), abs=atol)


@pytest.mark.parametrize("side", ["left", "right"])
def test_synthetic_square_matches_legacy(golden, side, request) -> None:
    model = request.getfixturevalue(f"{side}_model")
    quads = _quads(golden["segmentation"][f"synthetic_square5_{side}"])
    expected = golden["cube_center"][f"synthetic_square5_{side}"]

    estimate = top_face_center(quads, model.pixels_to_ground)

    _assert_estimate(estimate, expected)


@pytest.mark.parametrize("side", ["left", "right"])
def test_ten_vertex_contour_flags_overlap_without_a_centre(golden, side, request) -> None:
    model = request.getfixturevalue(f"{side}_model")
    quads = _quads(golden["segmentation"][f"synthetic_square10_overlap_{side}"])
    expected = golden["cube_center"][f"synthetic_square10_overlap_{side}"]

    estimate = top_face_center(quads, model.pixels_to_ground)

    _assert_estimate(estimate, expected)


@pytest.mark.parametrize("side", ["left", "right"])
def test_overlap_and_centre_can_coexist(golden, side, request) -> None:
    model = request.getfixturevalue(f"{side}_model")
    overlapping = _quads(golden["segmentation"][f"synthetic_square10_overlap_{side}"])
    plain = _quads(golden["segmentation"][f"synthetic_square5_{side}"])
    expected = golden["cube_center"][f"synthetic_square5_plus_overlap_{side}"]

    estimate = top_face_center([*overlapping, *plain], model.pixels_to_ground)

    _assert_estimate(estimate, expected)


def test_empty_input_reports_nothing(left_model) -> None:
    estimate = top_face_center([], left_model.pixels_to_ground)

    assert estimate == CubeEstimate(found=False, center=None, overlapping=False)


def test_no_matching_triangle_is_not_found(left_model) -> None:
    quad = np.array([[100, 200], [900, 210], [950, 300], [120, 320], [500, 700]], dtype=np.float64)

    estimate = top_face_center([quad], left_model.pixels_to_ground)

    assert estimate.found is False
    assert estimate.center is None


@pytest.mark.parametrize("side", ["left", "right"])
def test_real_frame_matches_legacy(golden, examples_dir, side, request) -> None:
    model = request.getfixturevalue(f"{side}_model")
    image = cv2.imread(str(examples_dir / "cube_sample.jpg"))
    assert image is not None

    estimate = top_face_center(find_quads(image), model.pixels_to_ground)
    expected = golden["cube_center"][f"cube_sample.jpg:{side}"]

    _assert_estimate(estimate, expected)


def test_degenerate_contour_returns_first_vertex_in_pixels() -> None:
    """Documented legacy quirk: fewer than five vertices bypasses projection."""
    quad = np.array([[10.0, 20.0], [30.0, 40.0], [50.0, 60.0]])
    calls: list[np.ndarray] = []

    def projector(pixels: np.ndarray) -> np.ndarray:
        calls.append(pixels)
        return pixels

    estimate = top_face_center([quad], projector)

    assert estimate == CubeEstimate(found=True, center=(10.0, 20.0), overlapping=False)
    assert calls == []


def test_nearest_candidate_wins_with_identity_projection() -> None:
    def projector(pixels: np.ndarray) -> np.ndarray:
        return pixels

    near = np.array(
        [[0, 0], [101.08, 0], [101.08, 101.08], [0, 101.08], [50, 50]], dtype=np.float64
    )
    far = near + np.array([500.0, 0.0])

    estimate = top_face_center([far, near], projector)

    assert estimate.found is True
    assert estimate.center == pytest.approx((50.54, 50.54), abs=1e-9)


def test_only_the_first_five_vertices_are_considered() -> None:
    """A legacy constraint kept on purpose: vertices 6..N never take part."""

    def projector(pixels: np.ndarray) -> np.ndarray:
        return pixels

    face = [[0, 0], [101.08, 0], [101.08, 101.08], [0, 101.08], [50, 50]]
    quad = np.array(face + [[10, 900], [20, 900]], dtype=np.float64)

    estimate = top_face_center([quad], projector)

    assert estimate.center == pytest.approx((50.54, 50.54), abs=1e-9)
