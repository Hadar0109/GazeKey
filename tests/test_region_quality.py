"""Region-based calibration quality checks."""

from gazekey.calibration.region_quality import parse_target_region, _region_match


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


def test_parse_target_region_coarsens_grid_col_2_and_above_to_right():
    """As-built keyboard15 is 5 columns; parse_target_region maps col via min(grid_col, 2)."""
    assert parse_target_region("key_q", grid_row=0, grid_col=0).col == "left"
    assert parse_target_region("key_e", grid_row=0, grid_col=1).col == "center"
    assert parse_target_region("key_t", grid_row=0, grid_col=2).col == "right"
    assert parse_target_region("key_u", grid_row=0, grid_col=3).col == "right"
    assert parse_target_region("key_p", grid_row=0, grid_col=4).col == "right"


def test_parse_target_region_space_and_m_both_coarsen_to_bottom_right():
    space = parse_target_region("key_space", grid_row=2, grid_col=4)
    m = parse_target_region("key_m", grid_row=2, grid_col=3)
    assert space.row == "bottom"
    assert m.row == "bottom"
    assert space.col == "right"
    assert m.col == "right"
