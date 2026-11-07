"""Transport layer between the controller and the chassis board.

``SerialLink`` is the whole surface the controller needs: write one frame, read
one reply.  Keeping it this small means the control logic can be exercised in
tests (and on a laptop) with :class:`FakeLink`, without any hardware.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator
from typing import Protocol, runtime_checkable

from .protocol import ACK

__all__ = ["FakeLink", "PyserialLink", "SerialLink"]

log = logging.getLogger(__name__)


@runtime_checkable
class SerialLink(Protocol):
    """Minimal line-oriented serial link."""

    def write_line(self, text: str) -> None:
        """Send ``text`` as one newline-terminated frame."""

    def read_line(self) -> str:
        """Return one line, or ``""`` when nothing arrived before the timeout."""

    def close(self) -> None:
        """Release the underlying device."""


class PyserialLink:
    """Real link over ``/dev/ttyUSB*`` (a udev alias in the arena image)."""

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 10.0) -> None:
        import serial  # imported lazily so `import robogame_vision` stays cheap

        self.port = port
        self._serial = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
        log.info("serial link open on %s @ %d baud", port, baudrate)

    def write_line(self, text: str) -> None:
        frame = text if text.endswith("\n") else text + "\n"
        self._serial.write(frame.encode("ascii"))
        self._serial.flush()
        log.debug("-> %s", text.rstrip("\n"))

    def read_line(self) -> str:
        line = self._serial.readline().decode("utf-8", errors="replace")
        if line:
            log.debug("<- %s", line.rstrip("\n"))
        return line

    def close(self) -> None:
        self._serial.close()
        log.info("serial link closed")

    def __enter__(self) -> PyserialLink:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class FakeLink:
    """In-memory link: records what was written and replays canned replies.

    ``replies`` is consumed in order; once it is exhausted ``default`` is
    returned forever.  ``default=""`` models a silent board and is how the
    acknowledgement timeout is tested.
    """

    def __init__(
        self,
        replies: Iterable[str] | None = None,
        *,
        default: str = ACK,
        writer: object | None = None,
    ) -> None:
        self._replies: list[str] = list(replies or ())
        self.default = default
        self.written: list[str] = []
        self.closed = False
        self._writer = writer

    def write_line(self, text: str) -> None:
        self.written.append(text)
        if callable(self._writer):
            self._writer(text)

    def read_line(self) -> str:
        if self._replies:
            return self._replies.pop(0)
        return self.default

    def close(self) -> None:
        self.closed = True

    def __iter__(self) -> Iterator[str]:
        return iter(self.written)
