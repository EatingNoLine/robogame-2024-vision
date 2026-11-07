"""The abandoned YOLOv8-segmentation path, kept for the record.

In the 2024 tree ``detect.py`` wrapped ``ultralytics.YOLO`` and was imported by
the main script, so ``torch``/``matplotlib`` were loaded on every start even
though the final control loop never called it.  The wrapper is preserved here as
an *optional* module: nothing imports it unless you ask for it, and the trained
weights (``new.pt``, 6.4 MB) are not distributed with this repository.

A YOLO model is injectable, which is how the tests avoid downloading torch.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

__all__ = ["Box", "Segmentation", "YoloSegmenter", "largest_box_centre"]


@dataclass(frozen=True)
class Box:
    """A detection box in pixels, ``xywh`` centred, as ultralytics reports it."""

    x_center: float
    y_center: float
    width: float
    height: float

    @property
    def area(self) -> float:
        return self.width * self.height


@dataclass(frozen=True)
class Segmentation:
    """Per-frame segmentation output."""

    boxes: tuple[Box, ...]
    class_ids: tuple[int, ...]
    masks: tuple[np.ndarray, ...]


class YoloSegmenter:
    """Thin, side-effect-free wrapper around an ultralytics segmentation model."""

    def __init__(
        self,
        weights: str | Path,
        *,
        conf: float = 0.25,
        imgsz: int | None = None,
        device: str | None = None,
        model: Any | None = None,
    ) -> None:
        self.weights = Path(weights)
        self.conf = conf
        self.imgsz = imgsz
        self.device = device
        if model is not None:
            self._model = model
            return
        if not self.weights.is_file():
            raise FileNotFoundError(
                f"YOLO weights not found: {self.weights}. They are not distributed with "
                "this repository; point --weights at a yolov8-seg checkpoint you trained."
            )
        try:
            from ultralytics import YOLO
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "YOLO support needs ultralytics and torch: pip install 'robogame-vision[yolo]'"
            ) from exc
        self._model = YOLO(str(self.weights))

    def segment(self, bgr: np.ndarray) -> Segmentation:
        """Run the model on one BGR frame (no images are written to disk)."""
        kwargs: dict[str, Any] = {"conf": self.conf, "verbose": False}
        if self.imgsz is not None:
            kwargs["imgsz"] = self.imgsz
        if self.device is not None:
            kwargs["device"] = self.device

        results = self._model.predict(source=np.asarray(bgr), **kwargs)
        if not results:
            return Segmentation(boxes=(), class_ids=(), masks=())

        result = results[0]
        boxes: tuple[Box, ...] = ()
        class_ids: tuple[int, ...] = ()
        if getattr(result, "boxes", None) is not None and len(result.boxes) > 0:
            xywh = np.asarray(result.boxes.xywh.cpu().numpy(), dtype=np.float64)
            boxes = tuple(
                Box(float(x), float(y), float(w), float(h)) for x, y, w, h in xywh.reshape(-1, 4)
            )
            class_ids = tuple(int(c) for c in np.asarray(result.boxes.cls.cpu().numpy()).ravel())

        masks: tuple[np.ndarray, ...] = ()
        if getattr(result, "masks", None) is not None:
            masks = tuple(
                np.asarray(mask, dtype=bool) for mask in np.asarray(result.masks.data.cpu().numpy())
            )
        return Segmentation(boxes=boxes, class_ids=class_ids, masks=masks)


def largest_box_centre(boxes: tuple[Box, ...]) -> tuple[float, float]:
    """Centre of the largest box, in pixels - the 2024 ``analyze()`` heuristic."""
    if not boxes:
        raise ValueError("no boxes to analyse")
    biggest = max(boxes, key=lambda box: box.area)
    return biggest.x_center, biggest.y_center
