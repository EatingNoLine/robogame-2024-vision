# Architecture

## Layers

```
                    ┌───────────────────────────┐
  /dev/video20 ───► │ camera.Camera             │
  /dev/video22 ───► │ camera.CameraPair         │──► camera.LatestFrames (thread)
                    └───────────────────────────┘              │
                                                               ▼
                    ┌───────────────────────────────────────────────────────┐
                    │ app.CubeDetector                                      │
                    │   detection.cube.find_quads            (pixels)       │
                    │   geometry.camera_model.pixels_to_ground (mm)        │
                    │   geometry.cube_center.top_face_center  (mm)         │
                    └───────────────────────────────────────────────────────┘
                                               │ app.Detection
                                               ▼
                    ┌───────────────────────────┐      ┌────────────────────┐
                    │ app.ControlLoop           │─────►│ robot.Controller   │
                    │  (search / approach /     │      │  protocol frames   │
                    │   grab+shoot decisions)   │      │  ACK, bounded wait │
                    └───────────────────────────┘      └─────────┬──────────┘
                                                                 ▼
                                                        /dev/my_serial0 (STM32)
```

The dependency arrow always points *down*: `detection` and `geometry` know nothing
about the robot, `robot` knows nothing about images, `app` wires the two together and
`cli` wires `app` to the operating system.

## Why the seams exist

| Seam | Protocol | Implementations | What it buys |
| --- | --- | --- | --- |
| Frames | `camera.FrameSource.read() -> (left, right)` | `CameraPair`, `LatestFrames`, `StaticFrames` | The control loop can be driven by still images in tests and by `--replay` |
| Chassis | `robot.Actuator` | `Controller`, `RecordingActuator` (tests) | Decision logic is asserted without a board |
| Serial | `robot.SerialLink` | `PyserialLink`, `FakeLink` | Frame emission and timeouts are unit-testable |
| Projection | `geometry.Projector` | `GroundPlaneModel.pixels_to_ground` | The top-face selector can be tested with a synthetic identity projection |
| Heavy ML | injected `model` | `YoloSegmenter(model=...)` | The YOLO wrapper is testable without `torch` |

## Threading

Two threads at most:

* `LatestFrames` owns one background thread that polls both cameras in a loop and
  publishes the newest `(left, right)` pair under a `threading.Condition`. Consumers
  never see a torn frame from one camera and a stale frame from the other.
* The control loop runs on the main thread. `run(stop_event)` exits when the event is
  set, which is what `Ctrl-C` and the CLI do.

No global mutable state is shared: the loop's only state is its search-jog direction.

## Error handling

* A serial command must be acknowledged within `SerialConfig.ack_timeout_s`
  (`RobotTimeout`); the 2024 code could block forever on `readline()`.
* A distance outside 1..4000 mm raises `ProtocolError` at frame-construction time,
  instead of producing a malformed frame or an unhandled `TypeError`.
* A missing or malformed calibration directory raises `CalibrationError` with the
  offending path, so a mis-mounted camera fails loudly at start-up.
* Optional dependencies (`ultralytics`, `apriltag`, `pynput`) raise `ImportError`
  naming the exact extra to install, and only when the feature is actually used.

## Numeric behaviour

Pixel → ground projection is a homography: a fixed-depth ray (`depth_scale`, ~450 mm)
through the inverse camera matrix, an extrinsic rotation/translation, then a ground
homography. Because every step before the homography is affine in the pixel, the
composition is a single 3×3 homography - which is why the top-face selector can work
purely in millimetres.

`tests/test_camera_model.py` and `tests/test_cube_center.py` compare against values
produced by the pre-refactor modules (`tests/data/golden.json`). The only intentional
difference is that the depth scale is applied in float64 rather than float32, which
moves the result by less than 6·10⁻⁵ mm.

## Extending it

* A different arena: re-run the calibration, drop the arrays into `data/calibration/`,
  then re-tune `ColorThresholds`/`CubeGeometry` in `config.py`. The parity tests will
  fail by design - delete `tests/data/golden.json` test cases you no longer honour, or
  regenerate them from the new arena.
* A different robot: implement `Actuator` and `SerialLink`; nothing else changes.
