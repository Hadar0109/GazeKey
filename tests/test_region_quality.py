"""Region-based calibration quality checks."""

from gazekey.calibration2.region_quality import parse_target_region, _region_match


def test_parse_target_region():
    assert parse_target_region("top_left").row == "top"
    assert parse_target_region("top_left").col == "left"
    assert parse_target_region("bottom_right").row == "bottom"
    assert parse_target_region("center").row == "mid"
    assert parse_target_region("center").col == "center"


def test_region_match():
    a = parse_target_region("top")
    b = parse_target_region("top_right")
    assert not _region_match(a, b)
    assert _region_match(parse_target_region("left"), parse_target_region("left"))
