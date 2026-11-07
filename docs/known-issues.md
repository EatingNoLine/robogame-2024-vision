# Known issues

This repository is a refactor of the code that actually ran at the 2024 competition.
The list below records what was broken in that code, what this version does instead,
and what is still unverified. Parity with the old numeric behaviour is pinned by
`tests/data/golden.json`, produced by running the old modules before the rewrite.

## Bugs fixed

| # | Symptom in the 2024 code | Fix | Covered by |
| --- | --- | --- | --- |
| 1 | `controller.move()` built its frame as `str(gear) + direction + + str(distance).zfill(4)`. The stray unary `+` raises `TypeError` on a `str`, so **no move command could ever be sent**. | `robot.protocol.move()` builds the frame and validates the distance. | `tests/test_protocol.py` |
| 2 | `main.py` called `warnings.warn(...)` in three places without importing `warnings`: a `NameError` on the first frame that was not ready. | Replaced by `logging`; missing frames are skipped. | `tests/test_app.py` |
| 3 | `detect.capture()` returned three values while `main.yolo_process()` unpacked four. | The dead YOLO path is now a self-contained optional module. | `tests/test_yolo_seg.py` |
| 4 | `from detect import *` and `from controller import *` pulled `torch`, `ultralytics`, `matplotlib`, `apriltag` and `pynput` into the start-up path, although the loop only needed `cv2`, `numpy` and `pyserial`. `pynput` also needs a display, which the headless Orange Pi does not have. | Heavy/optional dependencies are imported lazily, only by the feature that needs them. | `tests/test_cli.py`, `tests/test_yolo_seg.py` |
| 5 | `recognition()` drew over the caller's frame and its `if contours == None` branch was unreachable (`findContours` always returns a tuple). | Drawing is an explicit `draw_quads()` call on a copy; the dead branch is gone. | `tests/test_segmentation.py` |
| 6 | `realworld_L.py` and `realworld_R.py` were 113-line copies differing only in the calibration directory. | One `GroundPlaneModel` with a per-side directory. | `tests/test_camera_model.py` |
| 7 | `AtDetect.detect()` returned a 4-tuple when no tag was found and a 5-tuple otherwise; tag ids above 5 raised `IndexError` against a fixed six-entry list; and it re-detected recursively on a de-rotated copy. | `estimate_tag_pose()` returns a `TagPose` dataclass, supports any tag id, and detection is single-pass. | `tests/test_tag_pose.py` |
| 8 | **Yaw was always 0.0°, so `crooked` was never `True`.** The vertical extent was computed as `TL.y - BL.y`, which is negative for an upright tag; it was then used to clamp the edge length, so `acos(1)` always produced 0. | The extent is used as a magnitude and the yaw is `acos(min(edge / extent, 1))`. | `tests/test_tag_pose.py` |
| 9 | `clear_output()` listed `./images/output`, a directory that does not exist, raising `FileNotFoundError` when it was reached. | Removed; the debug renders are opt-in via `--save-vis`. | - |
| 10 | A `CapThread` that could not be stopped wrote every frame of both cameras to `./images/input/*.jpg` (a ~3 ms disk write per frame, per camera), and `MainThread` spun on globals (`condition`, `ctl`, `count`). | `LatestFrames` publishes the newest pair under a lock and can be stopped; the loop has no module-level state. | `tests/test_camera.py`, `tests/test_app.py` |
| 11 | The AprilTag loop read `condition.img_f`, a field `Condition` never had, and was never started - the whole path was dead. | Kept as a documented, separate module (`detect-tag` CLI command) instead of pretending it is wired in. | `tests/test_cli.py` |
| 12 | `serial.cpp`/`stp23.c` decoded the lidar payload with a padded struct (`sizeof == 20` instead of the 15-byte wire layout), so the fields were read at the wrong offsets; `stp23.c` did not even compile (undeclared `data_packet`). | Both probes are packed and `stp23.c` compiles; see `native/lidar/README.md`. | manual |
| 13 | Committed build products and assets: the compiled `serial` ELF (aarch64), `.idea/`, 43 MB of phone photos, `new.pt`, a screen recording. | Removed from the tree **and from history**; `.gitignore` now covers them. | `git count-objects` |

## Behaviour kept on purpose

| Behaviour | Why |
| --- | --- |
| A contour with fewer than five vertices makes the selector return its **first vertex, still in pixels** | It was reachable in the original code and any change would silently alter old logs. Documented in `geometry/cube_center.py` and asserted in `tests/test_cube_center.py`. |
| Only the first five vertices of a contour are considered | Same reason; a six- or seven-vertex approximation is common at the arena's edge. |
| `stay()` is sent twice per iteration when both offsets are inside the dead-band | Matches the original loop, which the motors tolerated. |
| The AprilTag "distance" is not in millimetres | The constant `2.163` is an empirical fit to `distance = tag_size · focal / diagonal_px` and mixes units. The path was never wired into the controller, so there was nothing to calibrate it against. |
| The projection uses a constant `depth_scale` | See `docs/calibration.md`; it is an approximation, not a measurement. |

## Unverified

* **Hardware.** No robot was available while this version was prepared. Camera
  capture (`cv2.VideoCapture` against `/dev/video20`), serial transport against the
  STM32 board and the physical grasp/shoot sequence have **not** been re-tested.
* **AprilTag detection.** The original `apriltag` package would not build in the
  environment used for the refactor, so the wrapper now also accepts
  `pupil-apriltags`. Detection is verified end to end with that backend on
  `examples/arena_tags.jpg` (all six wall tags, ids 0-5), and the overlay in
  `docs/images/tag_detection.jpg` is produced by the refactored code. The
  swatbotics backend is **not** exercised, and the yaw/distance values it produces
  remain heuristic (see the "behaviour kept" table).
* **YOLO path.** Weights are not distributed and the wrapper was tested with a fake
  model only.
* **Race-day tuning.** The HSV window, area window and the 101.08 / 142.93 mm cube
  distances are exactly the 2024 values. They were tuned in that arena, under that
  lighting.

## Intentional differences from the 2024 code

* Depth scale applied in `float64` instead of `float32` (< 6·10⁻⁵ mm on the arena).
* No images are written to disk unless `--save-vis`/`--record` asks for it.
* Serial waits are bounded and raise `RobotTimeout` instead of blocking forever.
* Axis convention is unchanged, but the package now reports millimetres explicitly in
  type names and docstrings.
