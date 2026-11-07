"""Shared fixtures.

``tests/data/golden.json`` was produced by running the *pre-refactor* modules
before the rewrite (see ``docs/known-issues.md``).  It is the parity contract:
the refactored code must reproduce those numbers.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(__file__).resolve().parent / "data"
EXAMPLES = ROOT / "examples"
CALIBRATION = ROOT / "data" / "calibration"


@pytest.fixture(scope="session")
def golden() -> dict:
    with (DATA / "golden.json").open(encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="session")
def examples_dir() -> Path:
    return EXAMPLES


@pytest.fixture(scope="session")
def calibration_dir() -> Path:
    return CALIBRATION


@pytest.fixture(scope="session")
def left_model(calibration_dir):
    from robogame_vision.geometry.camera_model import GroundPlaneModel

    return GroundPlaneModel.load(calibration_dir / "left")


@pytest.fixture(scope="session")
def right_model(calibration_dir):
    from robogame_vision.geometry.camera_model import GroundPlaneModel

    return GroundPlaneModel.load(calibration_dir / "right")
