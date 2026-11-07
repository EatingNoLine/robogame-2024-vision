"""Wire protocol spoken to the STM32 chassis board over the serial link.

Every frame is six ASCII characters followed by ``\\n``::

    stay    0 0 0 0 0 0
    move    <gear> <direction> <distance in mm, 4 digits>
    grab    6 <l|r> 0 0 0 0
    rotate  7 0 0 0 0 0        (never implemented in the 2024 firmware)
    shoot   8 0 0 0 0 0
    hello   hello              (no fixed-width layout)

The board answers every command with ``OK\\n``.  ``note.txt`` in the 2024 tree
described six speed gears with millisecond timings; the code that actually ran
used the five millimetre ranges reproduced in :func:`gear_for`, which is why
those are authoritative here.  See ``docs/protocol.md``.
"""

from __future__ import annotations

from enum import Enum

__all__ = [
    "ACK",
    "HELLO",
    "MAX_DISTANCE_MM",
    "MIN_DISTANCE_MM",
    "ArmSide",
    "Direction",
    "ProtocolError",
    "gear_for",
    "grab",
    "hello",
    "move",
    "rotate",
    "shoot",
    "stay",
]

ACK = "OK\n"
HELLO = "hello"
STAY_FRAME = "000000"
SHOOT_FRAME = "800000"
MIN_DISTANCE_MM = 1
MAX_DISTANCE_MM = 4000


class ProtocolError(ValueError):
    """Raised when a command cannot be expressed as a valid frame."""


class Direction(str, Enum):
    FORWARD = "f"
    BACKWARD = "b"
    LEFT = "l"
    RIGHT = "r"


class ArmSide(str, Enum):
    LEFT = "l"
    RIGHT = "r"


#: Upper bound (inclusive) of each gear, from slowest to fastest.
_GEAR_LIMITS = ((500, 1), (1200, 2), (2500, 3), (3000, 4), (4000, 5))


def gear_for(distance_mm: int) -> int:
    """Pick the chassis speed gear for a move of ``distance_mm`` millimetres."""
    if not MIN_DISTANCE_MM <= distance_mm <= MAX_DISTANCE_MM:
        raise ProtocolError(
            f"distance must be {MIN_DISTANCE_MM}..{MAX_DISTANCE_MM} mm, got {distance_mm}"
        )
    for limit, gear in _GEAR_LIMITS:
        if distance_mm <= limit:
            return gear
    raise ProtocolError(f"distance {distance_mm} mm has no gear")  # pragma: no cover


def stay() -> str:
    """Stop and hold position."""
    return STAY_FRAME


def shoot() -> str:
    """Fire the launching mechanism."""
    return SHOOT_FRAME


def hello() -> str:
    """Handshake; the board replies with a banner line, not ``OK``."""
    return HELLO


def grab(side: ArmSide | str) -> str:
    """``grab("l")`` / ``grab("r")``; closes the arm on the matching side."""
    return f"6{ArmSide(side).value}0000"


def move(distance_mm: int, direction: Direction | str) -> str:
    """Build a move frame, e.g. ``move(400, "b") -> "1b0400"``.

    ``distance_mm`` is the travel distance in millimetres; the gear is derived
    from it so the board drives at a speed suited to the distance.
    """
    distance = int(distance_mm)
    return f"{gear_for(distance)}{Direction(direction).value}{distance:04d}"


def rotate() -> str:
    """Not implemented by the 2024 firmware; kept so callers get a clear error."""
    raise NotImplementedError("the chassis firmware never implemented rotate")
