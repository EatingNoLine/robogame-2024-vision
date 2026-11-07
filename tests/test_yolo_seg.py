"""The optional YOLO wrapper, exercised with an injected fake model."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from robogame_vision.detection.yolo_seg import Box, YoloSegmenter, largest_box_centre


class FakeTensor:
    """Mimics the ``.cpu().numpy()`` chain ultralytics returns."""

    def __init__(self, array) -> None:
        self._array = np.asarray(array)

    def cpu(self) -> FakeTensor:
        return self

    def numpy(self) -> np.ndarray:
        return self._array


@dataclass
class FakeBoxes:
    xywh: FakeTensor
    cls: FakeTensor

    def __len__(self) -> int:
        return len(self.xywh.numpy())


@dataclass
class FakeMasks:
    data: FakeTensor


@dataclass
class FakeResult:
    boxes: FakeBoxes | None
    masks: FakeMasks | None


class FakeModel:
    def __init__(self, result: FakeResult) -> None:
        self.result = result
        self.calls: list[dict] = []

    def predict(self, source, **kwargs):
        self.calls.append(kwargs)
        return [self.result]


def _result() -> FakeResult:
    boxes = FakeBoxes(
        xywh=FakeTensor([[10.0, 20.0, 4.0, 6.0], [1.0, 1.0, 2.0, 2.0]]),
        cls=FakeTensor([0, 1]),
    )
    masks = FakeMasks(data=FakeTensor(np.ones((2, 3, 3), dtype=np.float32)))
    return FakeResult(boxes=boxes, masks=masks)


def test_missing_weights_fail_with_a_helpful_message(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="not distributed"):
        YoloSegmenter(tmp_path / "new.pt")


def test_injected_model_parses_boxes_classes_and_masks() -> None:
    model = FakeModel(_result())
    segmenter = YoloSegmenter("ignored.pt", model=model)

    segmentation = segmenter.segment(np.zeros((8, 8, 3), dtype=np.uint8))

    assert [box.x_center for box in segmentation.boxes] == [10.0, 1.0]
    assert segmentation.class_ids == (0, 1)
    assert len(segmentation.masks) == 2
    assert segmentation.masks[0].dtype == np.bool_
    assert model.calls == [{"conf": 0.25, "verbose": False}]


def test_empty_results_are_tolerated() -> None:
    model = FakeModel(FakeResult(boxes=None, masks=None))
    segmenter = YoloSegmenter("ignored.pt", model=model)

    segmentation = segmenter.segment(np.zeros((8, 8, 3), dtype=np.uint8))

    assert segmentation.boxes == ()
    assert segmentation.masks == ()


def test_largest_box_centre_matches_the_legacy_analyze_heuristic() -> None:
    boxes = (
        Box(x_center=1.0, y_center=2.0, width=10.0, height=10.0),
        Box(x_center=9.0, y_center=8.0, width=30.0, height=4.0),
    )

    assert largest_box_centre(boxes) == (9.0, 8.0)


def test_largest_box_centre_rejects_an_empty_result() -> None:
    with pytest.raises(ValueError, match="no boxes"):
        largest_box_centre(())
