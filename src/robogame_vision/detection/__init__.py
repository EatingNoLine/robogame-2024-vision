"""Image-space detection: colour segmentation, AprilTag and the YOLO wrapper."""

from .apriltag import AprilTagDetector, TagDetection, render_detections
from .color import draw_quads, orange_mask, sort_vertices_by_y
from .cube import find_quads
from .yolo_seg import Box, Segmentation, YoloSegmenter, largest_box_centre

__all__ = [
    "AprilTagDetector",
    "Box",
    "Segmentation",
    "TagDetection",
    "YoloSegmenter",
    "draw_quads",
    "find_quads",
    "largest_box_centre",
    "orange_mask",
    "render_detections",
    "sort_vertices_by_y",
]
