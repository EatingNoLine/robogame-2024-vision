"""High-level chassis controller: turns intents into acknowledged serial frames.

The 2024 script fired a frame and then looped forever on ``readline()`` until
``OK`` arrived, which hangs the process when the board is unplugged.  Here the
wait is bounded by ``SerialConfig.ack_timeout_s`` and raises
:class:`RobotTimeout` instead.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Protocol, runtime_checkable

from . import protocol
from .link import SerialLink
from .protocol import ACK, ArmSide, Direction

__all__ = ["Actuator", "Controller", "RobotTimeout"]


class RobotTimeout(RuntimeError):
    """The board did not acknowledge a command in time."""


@runtime_checkable
class Actuator(Protocol):
    """What the control loop is allowed to do to the robot."""

    def stay(self) -> None: ...

    def move(self, distance_mm: int, direction: Direction | str) -> None: ...

    def grab(self, side: ArmSide | str) -> None: ...

    def shoot(self) -> None: ...


class Controller:
    """Implements :class:`Actuator` on top of a :class:`SerialLink`."""

    def __init__(
        self,
        link: SerialLink,
        *,
        ack: str = ACK,
        timeout_s: float = 5.0,
        poll_s: float = 0.01,
        settle_s: float = 0.3,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._link = link
        self._ack = ack
        self._timeout_s = timeout_s
        self._poll_s = poll_s
        self._settle_s = settle_s
        self._clock = clock
        self._sleep = sleep

    # -- Actuator ---------------------------------------------------------
    def stay(self) -> None:
        self._command(protocol.stay(), "stay", settle=False)

    def move(self, distance_mm: int, direction: Direction | str) -> None:
        self._command(protocol.move(distance_mm, direction), f"move {distance_mm}mm {direction}")

    def grab(self, side: ArmSide | str) -> None:
        self._command(protocol.grab(side), f"grab {side}")

    def shoot(self) -> None:
        self._command(protocol.shoot(), "shoot")

    # -- misc -------------------------------------------------------------
    def hello(self) -> str:
        """Handshake.  The board answers with a banner line, not ``OK``."""
        self._link.write_line(protocol.hello())
        return self._link.read_line()

    def close(self) -> None:
        self._link.close()

    def __enter__(self) -> Controller:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # -- internals --------------------------------------------------------
    def _command(self, frame: str, label: str, *, settle: bool = True) -> None:
        self._link.write_line(frame)
        self._await_ack(label)
        if settle and self._settle_s:
            self._sleep(self._settle_s)

    def _await_ack(self, label: str) -> None:
        deadline = self._clock() + self._timeout_s
        while self._clock() < deadline:
            line = self._link.read_line()
            if line == self._ack:
                return
            # Sleep unconditionally: a board that keeps replying with something
            # else must not turn this into a busy loop.
            self._sleep(self._poll_s)
        raise RobotTimeout(f"no {self._ack!r} after {label!r} within {self._timeout_s}s")
