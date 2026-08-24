"""T011 / T012: identity/origin/DPR-only geometry STOP policy."""

from __future__ import annotations

import pytest

from gazekey.backend.geometry import (
    ALLOWED_TRANSFORMS,
    GeometryAudit,
    GeometryConfig,
    GeometryStopError,
    apply_geometry,
    choose_allowed_transform,
)


def test_allowed_transforms_are_only_identity_origin_dpr():
    assert ALLOWED_TRANSFORMS == frozenset({"identity", "origin", "origin+dpr"})


def test_identity_passthrough():
    cfg = GeometryConfig(transform="identity")
    assert apply_geometry(100.0, 200.0, cfg) == (100.0, 200.0)


def test_origin_offset():
    cfg = GeometryConfig(transform="origin", origin_offset=(5.0, -3.0))
    assert apply_geometry(10.0, 20.0, cfg) == (15.0, 17.0)


def test_origin_plus_dpr():
    cfg = GeometryConfig(transform="origin+dpr", origin_offset=(10.0, 20.0), dpr=2.0)
    assert apply_geometry(100.0, 200.0, cfg) == (60.0, 120.0)


def test_forbidden_transform_name_stops():
    with pytest.raises(GeometryStopError, match="STOP"):
        GeometryConfig(transform="affine")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"affine": [[1, 0, 0], [0, 1, 0]]},
        {"bias": (1.0, 2.0)},
        {"_gaze_bias_x": 3.0},
        {"clip_bounds": (0, 0, 1920, 1080)},
        {"camera_position": (17.15, -0.68)},
        {"mapper": object()},
        {"ridge": True},
        {"generate_points": True},
        {"key_table": {"a": (1, 1)}},
    ],
)
def test_forbidden_kwargs_stop_and_report(kwargs):
    cfg = GeometryConfig(transform="identity")
    with pytest.raises(GeometryStopError, match="STOP"):
        apply_geometry(1.0, 2.0, cfg, **kwargs)


def test_audit_schema_fields_exist():
    audit = GeometryAudit()
    assert hasattr(audit, "gf_screen_size")
    assert hasattr(audit, "pygame_mode")
    assert hasattr(audit, "qt_geometry")
    assert hasattr(audit, "device_pixel_ratio")
    assert hasattr(audit, "monitor_origin")
    assert hasattr(audit, "keyboard_origin")
    assert hasattr(audit, "transform")
    assert audit.transform in ALLOWED_TRANSFORMS


def test_choose_allowed_transform_never_invents_affine():
    assert choose_allowed_transform(origin_offset=(0.0, 0.0), dpr=1.0) == "identity"
    assert choose_allowed_transform(origin_offset=(10.0, 0.0), dpr=1.0) == "origin"
    assert choose_allowed_transform(origin_offset=(0.0, 0.0), dpr=1.5) == "origin+dpr"
