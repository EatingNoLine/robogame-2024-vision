# Lidar probes (STP-23)

Two throw-away programs from 2024, kept because they are the only documentation of
the lidar frame layout the team reverse-engineered. **They are not part of the vision
pipeline and are not built by CI.**

| File | What it does | Buildable here |
| --- | --- | --- |
| `stp23.c` | Decodes one in-memory frame, no hardware needed | yes - `gcc -std=c11 -o stp23 native/lidar/stp23.c` |
| `serial.cpp` | Reads frames from `/dev/ttyACM0` at 230400 baud using libserial | no - needs libserial 1.x |

## Frame layout

```
offset  size  field
0       4     start of frame, AA AA AA AA
4       1     device address
5       1     command code
6       1     chunk offset
7       1     data length
8       180   12 measurement points, 15 bytes each
188     1     checksum (8-bit sum of bytes 4..187)
```

Each point is `int16 distance, uint16 noise, uint32 peak, uint8 confidence,
uint32 intg, int16 reftof` - 15 bytes, no padding.

## Bug fixed during the refactor

Both programs declared the point as

```c
typedef struct { int16_t distance; ... int16_t reftof; } LidarPointTypedef;
```

which the compiler lays out as **20** bytes (`confidence` is followed by three bytes
of padding so `intg` stays 4-byte aligned). Copying `sizeof(...) * 12` bytes from
offset 8 therefore misaligned every field after `confidence` and read four bytes past
the frame. Both copies now use `__attribute__((packed))` with a `static_assert`, and
`stp23.c` compiles again (the 2024 version referenced an undeclared `data_packet`).

`serial.cpp` additionally reads a *binary* frame with `ReadLine()`, which stops at the
first `0x0A` inside the payload. Left as-is and called out in the file header: the
lidar never made it onto the final robot, so there is nothing to validate a proper
reader against.
