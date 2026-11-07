"""Command line: replay/detect-tag paths that need no hardware."""

from __future__ import annotations

import importlib.util
import json

import pytest

from robogame_vision.cli import build_parser, main

cv2 = pytest.importorskip("cv2")

HAS_APRILTAG = importlib.util.find_spec("apriltag") is not None


def test_parser_requires_a_subcommand() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


def test_version_exits_zero() -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])

    assert exit_info.value.code == 0


def test_replay_json_report(capsys, examples_dir) -> None:
    code = main(["replay", str(examples_dir / "cube_sample.jpg"), "--json"])

    assert code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["image"].endswith("cube_sample.jpg")
    assert report["quad_count"] >= 1
    assert set(report) >= {"left", "right", "width", "height"}
    assert (report["width"], report["height"]) == (1280, 960)
    assert report["left"]["found"] is False


def test_replay_human_report(capsys, examples_dir) -> None:
    code = main(["replay", str(examples_dir / "cube_sample.jpg")])

    out = capsys.readouterr().out
    assert code == 0
    assert "cube candidates" in out
    assert "left" in out and "right" in out


def test_replay_writes_the_overlay(tmp_path, examples_dir) -> None:
    destination = tmp_path / "overlay.png"

    code = main(
        ["replay", str(examples_dir / "cube_sample.jpg"), "--json", "--save-vis", str(destination)]
    )

    assert code == 0
    assert destination.is_file()
    assert cv2.imread(str(destination)) is not None


def test_replay_rejects_a_missing_image(tmp_path) -> None:
    with pytest.raises(SystemExit):
        main(["replay", str(tmp_path / "nope.jpg")])


def test_replay_rejects_a_bad_calibration_dir(tmp_path, examples_dir) -> None:
    code = main(
        ["replay", str(examples_dir / "cube_sample.jpg"), "--calibration", str(tmp_path / "nope")]
    )

    assert code == 1


@pytest.mark.skipif(
    HAS_APRILTAG, reason="apriltag installed; the missing-extra path is unreachable"
)
def test_detect_tag_reports_the_missing_extra(examples_dir, capsys) -> None:
    code = main(["detect-tag", str(examples_dir / "arena_tags.jpg")])

    assert code == 2
    assert "apriltag" in capsys.readouterr().err
