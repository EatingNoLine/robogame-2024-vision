"""Frame acquisition: capture wrapper, static source and the latest-frame thread."""

from __future__ import annotations

import numpy as np

from robogame_vision.camera import Camera, CameraPair, LatestFrames, StaticFrames
from robogame_vision.config import CameraConfig

FRAME = np.zeros((4, 6, 3), dtype=np.uint8)


class FakeCapture:
    def __init__(self, frame: np.ndarray | None = FRAME, opened: bool = True) -> None:
        self.frame = frame
        self.opened = opened
        self.released = False
        self.sets: list[tuple[int, int]] = []

    def set(self, prop: int, value: int) -> None:
        self.sets.append((prop, value))

    def read(self) -> tuple[bool, np.ndarray | None]:
        return self.frame is not None, self.frame

    def release(self) -> None:
        self.released = True

    def isOpened(self) -> bool:
        return self.opened


class FakeSource:
    def __init__(self, frames: tuple[np.ndarray | None, np.ndarray | None]) -> None:
        self.frames = frames
        self.closed = False

    def read(self) -> tuple[np.ndarray | None, np.ndarray | None]:
        return self.frames

    def close(self) -> None:
        self.closed = True


def test_camera_reads_and_closes() -> None:
    capture = FakeCapture()
    camera = Camera(CameraConfig("20"), capture_factory=lambda path: capture)

    assert camera.is_open() is True
    np.testing.assert_array_equal(camera.read(), FRAME)
    camera.close()

    assert capture.released is True


def test_camera_returns_none_when_the_device_stalls() -> None:
    camera = Camera(CameraConfig("20"), capture_factory=lambda path: FakeCapture(frame=None))

    assert camera.read() is None


def test_camera_reports_a_closed_device() -> None:
    camera = Camera(CameraConfig("20"), capture_factory=lambda path: FakeCapture(opened=False))

    assert camera.is_open() is False


def test_camera_pair_reads_both_sides() -> None:
    left = Camera(CameraConfig("20"), capture_factory=lambda path: FakeCapture())
    right = Camera(CameraConfig("22"), capture_factory=lambda path: FakeCapture(frame=FRAME + 1))
    pair = CameraPair(left, right)

    first, second = pair.read()

    np.testing.assert_array_equal(first, FRAME)
    np.testing.assert_array_equal(second, FRAME + 1)
    pair.close()
    assert left._capture.released and right._capture.released


def test_static_frames_never_change() -> None:
    source = StaticFrames(FRAME)

    assert source.read() == (FRAME, None)
    source.close()


def test_latest_frames_without_start_returns_none() -> None:
    frames = LatestFrames(FakeSource((FRAME, FRAME)))

    assert frames.read() == (None, None)


def test_latest_frames_publishes_the_first_pair_and_stops() -> None:
    source = FakeSource((FRAME, None))

    with LatestFrames(source) as frames:
        left, right = frames.read(timeout=2.0)
        assert left is not None
        assert right is None

    assert source.closed is True


def test_latest_frames_keeps_the_newest_pair() -> None:
    source = FakeSource((FRAME, FRAME))

    with LatestFrames(source) as frames:
        frames.read(timeout=2.0)
        newer = np.full_like(FRAME, 9)
        source.frames = (newer, newer)
        left, _ = frames.read(timeout=2.0)
        assert left is not None
