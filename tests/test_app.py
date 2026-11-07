"""Control loop: detection fusion and command emission, without hardware."""

from __future__ import annotations

import numpy as np
import pytest

from robogame_vision.app import ControlLoop, CubeDetector, Detection, DetectionKind
from robogame_vision.camera import StaticFrames
from robogame_vision.config import AppConfig
from robogame_vision.geometry.cube_center import CubeEstimate
from robogame_vision.robot.controller import Controller
from robogame_vision.robot.link import FakeLink


class RecordingActuator:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    @staticmethod
    def _wire(value: object) -> str:
        return str(getattr(value, "value", value))

    def stay(self) -> None:
        self.calls.append(("stay",))

    def move(self, distance_mm: int, direction: str) -> None:
        self.calls.append(("move", int(distance_mm), self._wire(direction)))

    def grab(self, side: str) -> None:
        self.calls.append(("grab", self._wire(side)))

    def shoot(self) -> None:
        self.calls.append(("shoot",))


class StubDetector:
    def __init__(self, detection: Detection) -> None:
        self.detection = detection
        self.calls = 0

    def detect(self, left, right) -> Detection:
        self.calls += 1
        return self.detection


def _estimate(found: bool, center: tuple[float, float] | None = None) -> CubeEstimate:
    return CubeEstimate(found=found, center=center, overlapping=False)


@pytest.fixture
def detector_with(monkeypatch):
    """CubeDetector whose per-camera estimate is scripted by the test."""
    estimates: dict[str, CubeEstimate] = {}

    def fake_estimate(self, frame, model):
        return estimates[model]

    monkeypatch.setattr(CubeDetector, "estimate", fake_estimate)
    detector = CubeDetector(left_model="left", right_model="right")
    return detector, estimates


def test_left_near_cube_is_grasped_from_the_left(detector_with) -> None:
    detector, estimates = detector_with
    estimates["left"] = _estimate(True, (5.0, -10.0))

    result = detector.detect("L-frame", "R-frame")

    assert result.kind is DetectionKind.GRASP_LEFT
    assert result.offset == (5.0, -10.0)


def test_right_near_cube_is_grasped_from_the_right(detector_with) -> None:
    detector, estimates = detector_with
    estimates["left"] = _estimate(True, (200.0, 0.0))
    estimates["right"] = _estimate(True, (0.0, 20.0))

    assert detector.detect("L", "R").kind is DetectionKind.GRASP_RIGHT


def test_closest_of_two_distant_cubes_is_approached(detector_with) -> None:
    detector, estimates = detector_with
    estimates["left"] = _estimate(True, (100.0, 0.0))
    estimates["right"] = _estimate(True, (300.0, 0.0))

    result = detector.detect("L", "R")

    assert result.kind is DetectionKind.TOO_FAR
    assert result.offset == (100.0, 0.0)


def test_no_cube_in_either_camera(detector_with) -> None:
    detector, estimates = detector_with
    estimates["left"] = _estimate(False)
    estimates["right"] = _estimate(False)

    assert detector.detect("L", "R").kind is DetectionKind.NONE


def test_missing_frame_is_skipped(detector_with) -> None:
    detector, estimates = detector_with
    estimates["right"] = _estimate(True, (0.0, 0.0))

    assert detector.detect(None, "R").kind is DetectionKind.GRASP_RIGHT


def test_search_jogs_backwards_then_forwards() -> None:
    actuator = RecordingActuator()
    loop = ControlLoop(StaticFrames(None), actuator, StubDetector(Detection(DetectionKind.NONE)))

    loop.step(Detection(DetectionKind.NONE))
    loop.step(Detection(DetectionKind.NONE))

    assert actuator.calls == [("move", 200, "b"), ("move", 200, "f")]


def test_grasp_grabs_then_shoots() -> None:
    actuator = RecordingActuator()
    loop = ControlLoop(StaticFrames(None), actuator, StubDetector(Detection(DetectionKind.NONE)))

    action = loop.step(Detection(DetectionKind.GRASP_LEFT, (0.0, 0.0)))

    assert actuator.calls == [("grab", "l"), ("shoot",)]
    assert "grab l" in action


def test_approach_stays_inside_the_deadband() -> None:
    actuator = RecordingActuator()
    loop = ControlLoop(StaticFrames(None), actuator, StubDetector(Detection(DetectionKind.NONE)))

    loop.step(Detection(DetectionKind.TOO_FAR, (0.0, 0.0)))

    assert actuator.calls == [("stay",), ("stay",)]


def test_approach_moves_forward_and_left_for_negative_x() -> None:
    actuator = RecordingActuator()
    loop = ControlLoop(StaticFrames(None), actuator, StubDetector(Detection(DetectionKind.NONE)))

    loop.step(Detection(DetectionKind.TOO_FAR, (-50.0, 100.0)))

    assert actuator.calls == [("move", 100, "f"), ("move", 50, "l")]


def test_approach_moves_backwards_and_right() -> None:
    actuator = RecordingActuator()
    loop = ControlLoop(StaticFrames(None), actuator, StubDetector(Detection(DetectionKind.NONE)))

    loop.step(Detection(DetectionKind.TOO_FAR, (50.0, -100.0)))

    assert actuator.calls == [("move", 100, "b"), ("move", 50, "r")]


def test_loop_emits_serial_frames_through_the_controller() -> None:
    """End-to-end wiring: detection stub -> ControlLoop -> Controller -> link."""
    link = FakeLink()
    controller = Controller(link, sleep=lambda _seconds: None)
    loop = ControlLoop(
        StaticFrames(np.zeros((4, 4, 3), dtype=np.uint8)),
        controller,
        StubDetector(Detection(DetectionKind.NONE)),
        AppConfig(),
        idle_sleep_s=0.0,
    )

    steps = loop.run(max_steps=2)

    assert steps == 2
    assert link.written == ["1b0200", "1f0200"]


def test_loop_stops_when_there_are_no_frames() -> None:
    actuator = RecordingActuator()
    loop = ControlLoop(
        StaticFrames(None), actuator, StubDetector(Detection(DetectionKind.NONE)), idle_sleep_s=0.0
    )

    assert loop.run(max_steps=1) == 0
    assert actuator.calls == []
