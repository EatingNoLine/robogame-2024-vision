"""Wire protocol: the exact frames the chassis board expects."""

from __future__ import annotations

import pytest

from robogame_vision.robot import protocol


@pytest.mark.parametrize(
    ("distance_mm", "gear"),
    [
        (1, 1),
        (200, 1),
        (500, 1),
        (501, 2),
        (1200, 2),
        (1201, 3),
        (2500, 3),
        (2501, 4),
        (3000, 4),
        (3001, 5),
        (4000, 5),
    ],
)
def test_gear_boundaries(distance_mm: int, gear: int) -> None:
    assert protocol.gear_for(distance_mm) == gear


@pytest.mark.parametrize("distance_mm", [-1, 0, 4001, 10_000])
def test_gear_rejects_out_of_range(distance_mm: int) -> None:
    with pytest.raises(protocol.ProtocolError):
        protocol.gear_for(distance_mm)


@pytest.mark.parametrize(
    ("distance_mm", "direction", "frame"),
    [
        (400, "b", "1b0400"),
        (200, "f", "1f0200"),
        (1000, "l", "2l1000"),
        (2000, "r", "3r2000"),
        (2800, "f", "4f2800"),
        (3500, "b", "5b3500"),
    ],
)
def test_move_frames(distance_mm: int, direction: str, frame: str) -> None:
    assert protocol.move(distance_mm, direction) == frame


def test_fixed_width_frames_are_six_characters() -> None:
    assert protocol.stay() == "000000"
    assert protocol.shoot() == "800000"
    assert protocol.grab("l") == "6l0000"
    assert protocol.grab("r") == "6r0000"
    for frame in (protocol.stay(), protocol.shoot(), protocol.grab("l"), protocol.move(400, "f")):
        assert len(frame) == 6


def test_hello_is_not_fixed_width() -> None:
    assert protocol.hello() == "hello"
    assert protocol.ACK == "OK\n"


def test_direction_and_side_enums_accept_wire_letters() -> None:
    assert protocol.Direction("f") is protocol.Direction.FORWARD
    assert protocol.ArmSide("r") is protocol.ArmSide.RIGHT
    with pytest.raises(ValueError):
        protocol.Direction("x")


def test_rotate_is_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        protocol.rotate()


def test_move_rejects_bad_direction() -> None:
    with pytest.raises(ValueError):
        protocol.move(400, "q")
