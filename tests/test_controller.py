"""Acknowledged controller: frame emission, ACK handling and bounded timeouts."""

from __future__ import annotations

import pytest

from robogame_vision.robot import ACK, RobotTimeout
from robogame_vision.robot.controller import Controller
from robogame_vision.robot.link import FakeLink


class _Sleeps:
    """Records requested sleeps and advances a fake clock."""

    def __init__(self) -> None:
        self.now = 0.0
        self.calls: list[float] = []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.calls.append(seconds)
        self.now += seconds


def _controller(link: FakeLink, **kwargs) -> tuple[Controller, _Sleeps]:
    sleeps = _Sleeps()
    controller = Controller(link, clock=sleeps.clock, sleep=sleeps.sleep, **kwargs)
    return controller, sleeps


def test_move_sends_one_frame_and_settles() -> None:
    link = FakeLink()
    controller, sleeps = _controller(link)

    controller.move(400, "b")

    assert link.written == ["1b0400"]
    assert sleeps.calls == [0.3]


def test_stay_does_not_settle() -> None:
    link = FakeLink()
    controller, sleeps = _controller(link)

    controller.stay()

    assert link.written == ["000000"]
    assert sleeps.calls == []


def test_all_commands_emit_expected_frames() -> None:
    link = FakeLink()
    controller, _ = _controller(link)

    controller.grab("l")
    controller.grab("r")
    controller.shoot()

    assert link.written == ["6l0000", "6r0000", "800000"]


def test_banner_lines_are_skipped_until_ack() -> None:
    link = FakeLink(replies=["24Robo chassis v1\n", "\n", ACK])
    controller, _ = _controller(link)

    controller.move(200, "f")

    assert link.written == ["1f0200"]


def test_missing_ack_raises_instead_of_hanging() -> None:
    link = FakeLink(default="")
    controller, sleeps = _controller(link, timeout_s=1.0, poll_s=0.1)

    with pytest.raises(RobotTimeout, match="move"):
        controller.move(400, "b")

    assert sleeps.now >= 1.0
    assert link.written == ["1b0400"]


def test_ack_timeout_is_capped_by_the_deadline() -> None:
    link = FakeLink(default="garbage\n")
    controller, sleeps = _controller(link, timeout_s=0.5, poll_s=0.1)

    with pytest.raises(RobotTimeout):
        controller.shoot()

    # A non-empty unexpected line does not sleep, so the fake clock only moves
    # through the poll sleeps - it must still stop at the deadline.
    assert sleeps.now <= 0.5 + 0.1


def test_hello_returns_the_banner() -> None:
    link = FakeLink(replies=["24Robo chassis v1\n"])
    controller, _ = _controller(link)

    assert controller.hello() == "24Robo chassis v1\n"
    assert link.written == ["hello"]


def test_close_closes_the_link() -> None:
    link = FakeLink()
    controller, _ = _controller(link)

    controller.close()

    assert link.closed is True


def test_context_manager_closes_the_link() -> None:
    link = FakeLink()
    with Controller(link):
        pass
    assert link.closed is True
