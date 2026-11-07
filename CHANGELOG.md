# Changelog

All notable changes to this project. The project is archived after `1.0.0`.

## [1.0.0] - 2026-11-07

First published release: the 2024 competition code, refactored and tested.

Behaviour is pinned by golden values produced from the pre-refactor modules
(`tests/data/golden.json`), so the numeric pipeline is unchanged except where a bug
made the old behaviour meaningless - see `docs/known-issues.md`.

### Added

- `src/robogame_vision/` package: `config`, `camera`, `detection/*`, `geometry/*`,
  `robot/*`, `app`, `cli`.
- CLI: `run`, `replay`, `detect-tag`, `teleop`, `preview`, `--version`.
- 114 tests, none of which need a camera, a chassis board or `torch`; parity tests
  against the 2024 code for projection, segmentation and top-face selection.
- GitHub Actions CI: `ruff check`, `ruff format --check` and `pytest` on
  Ubuntu/Windows × Python 3.10/3.12.
- `pyproject.toml` with optional extras `apriltag`, `yolo`, `teleop`, `dev`.
- Documentation: `docs/architecture.md`, `docs/protocol.md`, `docs/calibration.md`,
  `docs/known-issues.md`, and a bilingual README.
- `native/lidar/`: the STP-23 probes, with the point struct now packed to the 15-byte
  wire layout and `stp23.c` compiling again.
- MIT licence.

### Fixed

- `robot.protocol` builds move frames correctly (the 2024 `Controller.move()` raised
  `TypeError` on every call, so the robot could never drive).
- `warnings` was used without being imported in the old main loop.
- Serial acknowledgement waits are bounded (`RobotTimeout`) instead of looping forever.
- AprilTag yaw was always `0.0°`; tag ids above 5 no longer raise `IndexError`.
- Heavy/optional dependencies (`torch`, `ultralytics`, `matplotlib`, `apriltag`,
  `pynput`) are no longer imported by the main start-up path.
- The camera thread no longer writes every frame to disk, and can be stopped.

### Removed

- Compiled `serial` ELF binary, `.idea/` project files, a screen recording, 43 MB of
  phone photos, and the 6.4 MB `new.pt` YOLO checkpoint - removed from the working
  tree and from the whole history.
- `tmp.py` (an older copy of `main.py`), `commandgetimg.py` (fswebcam scratch),
  `imgtmp.py` (three-camera preview scratch), `requirements.txt` (superseded by
  `pyproject.toml`).
- `detect.perspective_trans()` - a one-off calibration experiment with hard-coded
  arena lengths that was never reachable from the control loop.

### Changed

- Two 113-line `realworld_L.py` / `realworld_R.py` modules became one
  `GroundPlaneModel` parameterised by calibration directory.
- Calibration arrays renamed from `H_mtx.npy`-style names to
  `ground_homography.npy`-style names and moved to `data/calibration/{left,right}/`.
- Depth scale applied in `float64` instead of `float32` (differences < 6·10⁻⁵ mm).
- Git history rewritten to drop large binaries; the pre-refactor history is preserved
  as commits up to the 2024 season, but rewritten without those blobs.
