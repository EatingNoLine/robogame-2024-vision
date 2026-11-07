# Serial protocol and arena geometry

Everything here comes from `note.txt` and the command strings hard-coded in the 2024
`controller.py`; the notes were the only protocol document the team had.

## Frames

Each command is six ASCII characters terminated by `\n`. The board answers `OK\n`;
`hello` is the exception and answers with a banner line.

| Byte | Meaning |
| --- | --- |
| 0 | command: `0` stay, `1`-`5` move, `6` grab, `7` rotate, `8` shoot |
| 1 | move: `f`/`b`/`l`/`r` — grab: `l`/`r` |
| 2-5 | move: distance in millimetres, zero padded; otherwise `0000` |

```
stay    0 0 0 0 0 0
move    1 b 0 4 0 0        gear 1, backwards, 400 mm
grab    6 l 0 0 0 0
rotate  7 0 0 0 0 0        never implemented in the firmware
shoot   8 0 0 0 0 0
hello   hello
```

The acknowledgement is the literal string `OK\n`; anything else that arrives (banner,
echo, partial line) is skipped until the timeout expires.

## Speed gears

`robot/protocol.py` picks the gear from the travel distance:

| Gear | Distance |
| --- | --- |
| 1 | 1 – 500 mm |
| 2 | 501 – 1200 mm |
| 3 | 1201 – 2500 mm |
| 4 | 2501 – 3000 mm |
| 5 | 3001 – 4000 mm |

`note.txt` also lists a *different*, millisecond-based table
(`100 200 300 500 1000 2000 ms` for gears `1 2 3 a b c`). That table describes the
firmware's internal timing steps and was never what the vision code sent, so the
millimetre table above is authoritative. Do not mix them.

## Devices

```bash
# which cameras exist and what they support
v4l2-ctl --list-devices

# stable serial alias for the chassis board (CH340 adapter)
KERNEL=="ttyUSB[0-9]*", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", \
  MODE="0777", SYMLINK+="my_serial0"
```

| Device | Use |
| --- | --- |
| `/dev/video20` | left side camera |
| `/dev/video22` | right side camera |
| `/dev/video11` | front camera (AprilTag work; never wired into the final loop) |
| `/dev/my_serial0` | STM32 chassis board, 115200 baud |

## Arena

* Field: **3 m × 4 m**.
* AprilTags: `tag36h11`, **400 mm × 400 mm**, spaced **240 mm** apart, mounted
  **200 mm** from the wall's horizontal edge and **100 mm** up from its vertical edge.
* Tag ids run **0 … 5 from left to right**; the robot knows which one it faces and
  therefore which part of the wall it is looking at.
* Front camera field of view at the wall: **1552 mm × 1105 mm** - which is where the
  constants `EXACT_FAR_LENGTH`/`EXACT_LEFT_LENGTH` in the old `detect.py` came from.

The side cameras are mounted low and tilted towards the floor: their ground-plane
calibration (`data/calibration/`) is only valid for the cube on the arena floor, not
for arbitrary scenes. A cube photographed on a chair is correctly *rejected* by the
selector - see `examples/cube_sample.jpg`.

## Robot frame

The ground-plane coordinates produced by `geometry.camera_model` are millimetres in
the robot frame: `x` to the right, `y` forward, origin roughly between the front
wheels. The control loop dead-bands ±15 mm and treats a target within 40 mm of the
origin as graspable.
