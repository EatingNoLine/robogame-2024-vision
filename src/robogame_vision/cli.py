"""Command line entry point: ``python -m robogame_vision`` / ``robogame-vision``.

Sub-commands
------------
``run``         drive the robot (or ``--dry-run`` to print frames instead)
``replay``      run the cube pipeline over a still image - no hardware needed
``detect-tag``  detect AprilTags in a still image and print their pose
``teleop``      keyboard tele-operation over the serial link
``preview``     live preview of the configured cameras
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import threading
from dataclasses import replace
from pathlib import Path
from typing import Any

from . import __version__
from .app import ControlLoop, CubeDetector
from .camera import Camera, CameraPair, LatestFrames
from .config import (
    AppConfig,
    CameraConfig,
    SerialConfig,
    default_calibration_dir,
)
from .geometry.camera_model import CalibrationError
from .robot.controller import Controller
from .robot.link import FakeLink, PyserialLink

__all__ = ["build_parser", "main"]

log = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _read_image(path: str) -> Any:
    import cv2

    image = cv2.imread(path)
    if image is None:
        raise SystemExit(f"cannot read image: {path}")
    return image


def _write_image(path: str, image: Any) -> None:
    import cv2

    destination = Path(path)
    if destination.parent != Path(""):
        destination.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(destination), image):
        raise SystemExit(f"cannot write image: {path}")


def _add_calibration_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--calibration",
        type=Path,
        default=default_calibration_dir(),
        help="directory holding the left/ and right/ calibration arrays",
    )


def _config_from_args(args: argparse.Namespace) -> AppConfig:
    config = AppConfig()
    if getattr(args, "calibration", None) is not None:
        config = replace(config, calibration_dir=Path(args.calibration))
    if getattr(args, "left_camera", None) is not None:
        config = replace(config, left_camera=CameraConfig(args.left_camera))
    if getattr(args, "right_camera", None) is not None:
        config = replace(config, right_camera=CameraConfig(args.right_camera))
    if getattr(args, "port", None) is not None:
        config = replace(config, serial=replace(config.serial, port=args.port))
    return config


# --------------------------------------------------------------------------
# sub-commands
# --------------------------------------------------------------------------
def cmd_replay(args: argparse.Namespace) -> int:
    from .detection.color import draw_quads
    from .detection.cube import find_quads

    image = _read_image(args.image)
    detector = CubeDetector.from_calibration(args.calibration)
    quads = find_quads(image, detector.thresholds)

    report: dict[str, Any] = {
        "image": str(args.image),
        "width": int(image.shape[1]),
        "height": int(image.shape[0]),
        "quad_count": len(quads),
    }
    for side, model in (("left", detector.left_model), ("right", detector.right_model)):
        estimate = detector.estimate(image, model)
        report[side] = {
            "found": estimate.found,
            "overlapping": estimate.overlapping,
            "center": None if estimate.center is None else [round(v, 3) for v in estimate.center],
        }

    if args.save_vis:
        _write_image(args.save_vis, draw_quads(image, quads))
        report["saved_visualisation"] = str(args.save_vis)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"{report['image']} ({report['width']}x{report['height']})")
        print(f"  cube candidates: {report['quad_count']}")
        for side in ("left", "right"):
            entry = report[side]
            centre = (
                "none"
                if entry["center"] is None
                else f"({entry['center'][0]:.0f}, {entry['center'][1]:.0f}) mm"
            )
            print(f"  {side:5} camera: found={entry['found']} centre={centre}")
    return 0


def cmd_detect_tag(args: argparse.Namespace) -> int:
    from .detection.apriltag import AprilTagDetector, render_detections
    from .geometry.tag_pose import estimate_tag_pose

    image = _read_image(args.image)
    try:
        detector = AprilTagDetector()
    except ImportError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    detections = detector.detect(image)
    poses = [
        estimate_tag_pose(
            detection.corners,
            image_size=image.shape[:2],
            tag_id=detection.tag_id,
            tag_count=len(detections),
        )
        for detection in detections
    ]

    if args.save_vis:
        _write_image(args.save_vis, render_detections(image, detections))

    if args.json:
        print(
            json.dumps(
                {
                    "image": str(args.image),
                    "tags": [
                        {
                            "id": pose.tag_id,
                            "distance": round(pose.distance, 4),
                            "yaw_deg": round(pose.yaw_deg, 3),
                            "crooked": pose.crooked,
                        }
                        for pose in poses
                    ],
                },
                indent=2,
            )
        )
    elif not poses:
        print("no tags found")
    else:
        for pose in poses:
            print(
                f"tag {pose.tag_id}: distance={pose.distance:.3f} "
                f"yaw={pose.yaw_deg:+.2f}deg crooked={pose.crooked}"
            )
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    config = _config_from_args(args)
    try:
        detector = CubeDetector.from_calibration(config.calibration_dir)
    except CalibrationError as exc:
        print(f"calibration error: {exc}", file=sys.stderr)
        return 1

    link: Any
    if args.dry_run:
        link = FakeLink(writer=lambda frame: print(f"[dry-run] -> {frame}"))
    else:
        link = PyserialLink(config.serial.port, config.serial.baudrate)
    controller = Controller(
        link,
        timeout_s=config.serial.ack_timeout_s,
        settle_s=config.serial.settle_s,
    )

    left = Camera(config.left_camera)
    right = Camera(config.right_camera)
    if not (left.is_open() and right.is_open()):
        print(
            f"cannot open cameras {config.left_camera.path} / {config.right_camera.path}",
            file=sys.stderr,
        )
        left.close()
        right.close()
        controller.close()
        return 1

    frames = LatestFrames(CameraPair(left, right)).start()
    stop = threading.Event()
    try:
        banner = controller.hello()
        log.info("board: %s", banner.strip() or "<no banner>")
        steps = ControlLoop(frames, controller, detector, config).run(stop)
    except KeyboardInterrupt:
        stop.set()
        log.info("interrupted")
        steps = 0
    finally:
        frames.stop()
        controller.stay()
        controller.close()
        log.info("commands sent: %d", steps)
    return 0


def cmd_teleop(args: argparse.Namespace) -> int:
    try:
        from pynput import keyboard
    except ImportError:
        print(
            "teleop needs pynput: pip install 'robogame-vision[teleop]'",
            file=sys.stderr,
        )
        return 2

    link = PyserialLink(args.port, args.baudrate)
    controller = Controller(link, timeout_s=args.timeout)
    controller.hello()

    bindings = {
        "w": lambda: controller.move(1000, "f"),
        "s": lambda: controller.move(1000, "b"),
        "a": lambda: controller.move(1000, "l"),
        "d": lambda: controller.move(1000, "r"),
        "j": lambda: controller.grab("l"),
        "k": lambda: controller.grab("r"),
        "c": controller.shoot,
        " ": controller.stay,
    }

    def on_press(key: Any) -> bool | None:
        name = getattr(key, "char", None)
        if key == keyboard.Key.esc:
            return False
        action = bindings.get(name or "")
        if action is None:
            print(f"{name!r}: no binding (w/a/s/d, j/k, c, space, esc)")
            return None
        print(f"{name}: {action.__name__ if hasattr(action, '__name__') else 'action'}")
        action()
        return None

    print("teleop started - w/a/s/d move, j/k grab, c shoot, space stop, esc quit")
    try:
        with keyboard.Listener(on_press=on_press) as listener:
            listener.join()
    finally:
        controller.stay()
        controller.close()
    return 0


def cmd_preview(args: argparse.Namespace) -> int:
    import cv2

    windows = {}
    for device in args.devices:
        config = CameraConfig(device)
        camera = Camera(config)
        if not camera.is_open():
            print(f"cannot open camera {config.path}", file=sys.stderr)
            camera.close()
            continue
        windows[config.path] = camera

    if not windows:
        return 1
    print("press q to quit")
    try:
        while True:
            for name, camera in windows.items():
                frame = camera.read()
                if frame is not None:
                    cv2.imshow(name, frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        for camera in windows.values():
            camera.close()
        cv2.destroyAllWindows()
    return 0


# --------------------------------------------------------------------------
# parser
# --------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="robogame-vision",
        description="Vision stack for the 24Robo 2024 arena robot.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="logging verbosity",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    replay = subparsers.add_parser("replay", help="run the cube pipeline on a still image")
    replay.add_argument("image", help="BGR image captured by one of the side cameras")
    _add_calibration_argument(replay)
    replay.add_argument("--json", action="store_true", help="print a JSON report")
    replay.add_argument("--save-vis", metavar="PATH", help="write the segmentation overlay")
    replay.set_defaults(func=cmd_replay)

    tag = subparsers.add_parser("detect-tag", help="detect AprilTags in a still image")
    tag.add_argument("image", help="image containing tag36h11 markers")
    tag.add_argument("--json", action="store_true", help="print a JSON report")
    tag.add_argument("--save-vis", metavar="PATH", help="write an annotated copy")
    tag.set_defaults(func=cmd_detect_tag)

    run = subparsers.add_parser("run", help="drive the robot")
    run.add_argument("--left-camera", default="20", help="left V4L2 device")
    run.add_argument("--right-camera", default="22", help="right V4L2 device")
    run.add_argument("--port", default=SerialConfig.port, help="serial device of the chassis")
    _add_calibration_argument(run)
    run.add_argument(
        "--dry-run",
        action="store_true",
        help="print the frames instead of talking to the chassis",
    )
    run.set_defaults(func=cmd_run)

    teleop = subparsers.add_parser("teleop", help="keyboard tele-operation")
    teleop.add_argument("--port", default=SerialConfig.port, help="serial device of the chassis")
    teleop.add_argument("--baudrate", type=int, default=SerialConfig.baudrate)
    teleop.add_argument("--timeout", type=float, default=SerialConfig.ack_timeout_s)
    teleop.set_defaults(func=cmd_teleop)

    preview = subparsers.add_parser("preview", help="live preview of the cameras")
    preview.add_argument("--devices", nargs="+", default=["20", "22"], help="V4L2 devices")
    preview.set_defaults(func=cmd_preview)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    try:
        return int(args.func(args))
    except CalibrationError as exc:
        print(f"calibration error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
