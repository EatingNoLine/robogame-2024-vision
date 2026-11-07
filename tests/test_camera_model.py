"""Calibration loading and pixel -> ground-plane projection (legacy parity)."""

from __future__ import annotations

import numpy as np
import pytest

from robogame_vision.geometry.camera_model import (
    CALIBRATION_FILES,
    CalibrationError,
    GroundPlaneModel,
)


def test_projection_matches_the_legacy_implementation(
    golden: dict, left_model: GroundPlaneModel, right_model: GroundPlaneModel
) -> None:
    # The legacy code scaled the homogeneous pixel by a float32 depth-scale
    # array; this implementation stays in float64, which shifts the result by at
    # most 6e-5 mm.  1e-3 mm is the parity budget.
    for side, model in (("left", left_model), ("right", right_model)):
        case = golden["projection"][side]
        pixels = np.asarray(case["pixels"], dtype=np.float64)
        expected = np.asarray(case["plane"], dtype=np.float64)

        actual = model.pixels_to_ground(pixels)

        np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-3, err_msg=side)


def test_single_pixel_helper_agrees_with_the_batch_api(left_model: GroundPlaneModel) -> None:
    batch = left_model.pixels_to_ground([[960.0, 540.0]])[0]
    single = left_model.pixel_to_ground(960.0, 540.0)

    assert single == pytest.approx((float(batch[0]), float(batch[1])), abs=1e-12)


def test_projection_does_not_mutate_its_input(left_model: GroundPlaneModel) -> None:
    pixels = np.array([[10.0, 20.0], [30.0, 40.0]])
    original = pixels.copy()

    left_model.pixels_to_ground(pixels)

    np.testing.assert_array_equal(pixels, original)


def test_formula_on_identity_calibration() -> None:
    identity = np.eye(3)
    model = GroundPlaneModel(
        inverse_camera_matrix=identity,
        inverse_rotation=identity,
        depth_scale=1.0,
        translation=np.zeros(3),
        ground_homography=identity,
    )

    assert model.pixel_to_ground(12.0, 34.0) == pytest.approx((12.0, 34.0))


def test_translation_is_subtracted_before_projection() -> None:
    identity = np.eye(3)
    model = GroundPlaneModel(
        inverse_camera_matrix=identity,
        inverse_rotation=identity,
        depth_scale=1.0,
        translation=np.array([10.0, 0.0, 0.0]),
        ground_homography=identity,
    )

    assert model.pixel_to_ground(12.0, 34.0) == pytest.approx((2.0, 34.0))


def test_homography_is_normalised_by_its_third_component() -> None:
    identity = np.eye(3)
    model = GroundPlaneModel(
        inverse_camera_matrix=identity,
        inverse_rotation=identity,
        depth_scale=1.0,
        translation=np.zeros(3),
        ground_homography=2.0 * identity,
    )

    assert model.pixel_to_ground(12.0, 34.0) == pytest.approx((12.0, 34.0))


def test_load_rejects_missing_directory(tmp_path) -> None:
    with pytest.raises(CalibrationError, match="does not exist"):
        GroundPlaneModel.load(tmp_path / "nope")


def test_load_rejects_missing_file(tmp_path) -> None:
    for filename in list(CALIBRATION_FILES.values())[1:]:
        np.save(tmp_path / filename, np.eye(3))
    with pytest.raises(CalibrationError, match="missing calibration file"):
        GroundPlaneModel.load(tmp_path)


def test_load_rejects_wrong_shapes(tmp_path, calibration_dir) -> None:
    for filename in CALIBRATION_FILES.values():
        np.save(tmp_path / filename, np.load(calibration_dir / "left" / filename))
    np.save(tmp_path / "inverse_camera_matrix.npy", np.eye(2))

    with pytest.raises(CalibrationError, match="3x3"):
        GroundPlaneModel.load(tmp_path)


def test_load_rejects_wrong_translation_length(tmp_path, calibration_dir) -> None:
    for filename in CALIBRATION_FILES.values():
        np.save(tmp_path / filename, np.load(calibration_dir / "left" / filename))
    np.save(tmp_path / "translation.npy", np.zeros(4))

    with pytest.raises(CalibrationError, match="vector"):
        GroundPlaneModel.load(tmp_path)


def test_pixels_must_be_n_by_2(left_model: GroundPlaneModel) -> None:
    with pytest.raises(ValueError, match="shape"):
        left_model.pixels_to_ground(np.zeros((3, 3)))


def test_loaded_matrices_have_the_expected_shapes(left_model: GroundPlaneModel) -> None:
    assert left_model.inverse_camera_matrix.shape == (3, 3)
    assert left_model.inverse_rotation.shape == (3, 3)
    assert left_model.ground_homography.shape == (3, 3)
    assert left_model.translation.shape == (3,)
    assert left_model.depth_scale > 0


def test_left_and_right_calibrations_differ(left_model, right_model) -> None:
    assert not np.allclose(left_model.ground_homography, right_model.ground_homography)
