"""Computer-vision stack for the 24Robo 2024 arena robot.

The package is split into three layers:

``robogame_vision.robot``
    Serial protocol and the command controller that drives the chassis.
``robogame_vision.geometry``
    Camera calibration and pixel -> ground-plane projection, cube top-face
    selection and AprilTag pose estimation.
``robogame_vision.detection``
    Image-space primitives: colour segmentation, cube quads, AprilTag and the
    (abandoned) YOLOv8 segmentation wrapper.

``robogame_vision.app`` wires the layers into the control loop and
``robogame_vision.cli`` exposes them on the command line.
"""

from importlib.metadata import PackageNotFoundError, version

try:  # pragma: no cover - depends on the installation mode
    __version__ = version("robogame-vision")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "1.0.0"

__all__ = ["__version__"]
