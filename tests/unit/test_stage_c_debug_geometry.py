"""T027 / T028: debug gaze dot and live geometry audit on the existing keyboard."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from gazekey.backend.debug_gaze_dot import DebugGazeOverlay, overlay_ring_metrics
from gazekey.backend.gaze_sample import GazeSample
from gazekey.backend.geometry import GeometryConfig
from gazekey.backend.geometry_audit import build_live_audit, write_geometry_audit
from gazekey.backend.lifecycle import GazeFollowerLifecycle
from gazekey.backend.startup import record_live_geometry, wire_debug_gaze_dot
from gazekey.ui.virtual_keyboard import VirtualKeyboard


def _valid_sample(x: float, y: float) -> GazeSample:
    return GazeSample(
        timestamp_ns=1,
        valid=True,
        x=x,
        y=y,
        calibrated_x=x,
        calibrated_y=y,
        tracking_state="SUCCESS",
        left_openness=20.0,
        right_openness=21.0,
    )


def test_debug_dot_uses_gazesample_only_not_dwell(qapp, monkeypatch):
    vk = VirtualKeyboard()
    vk.show()
    qapp.processEvents()
    runtime = vk._typing_runtime
    monkeypatch.setattr(runtime, "on_mapped_gaze", MagicMock())
    overlay = DebugGazeOverlay(vk.keyboard_widget)
    overlay.update_sample(_valid_sample(50.0, 60.0))
    qapp.processEvents()
    runtime.on_mapped_gaze.assert_not_called()
    assert overlay._dot.isVisible()
    assert overlay._dot._pos is not None


def test_invalid_sample_holds_last_debug_only(qapp):
    vk = VirtualKeyboard()
    vk.show()
    qapp.processEvents()
    overlay = DebugGazeOverlay(vk.keyboard_widget)
    overlay.update_sample(_valid_sample(80.0, 90.0))
    qapp.processEvents()
    held = overlay._dot._pos
    assert held is not None
    invalid = GazeSample(
        timestamp_ns=2,
        valid=False,
        x=0.0,
        y=0.0,
        calibrated_x=None,
        calibrated_y=None,
        tracking_state="FACE_MISSING",
        left_openness=0.0,
        right_openness=0.0,
    )
    overlay.update_sample(invalid)
    qapp.processEvents()
    assert overlay._dot._pos == held


def test_overlay_ring_metrics_scale_official_pygame_size_by_dpr():
    radius, stroke = overlay_ring_metrics(1.5)
    assert radius == 50.0 / 1.5
    assert stroke == 5.0 / 1.5


def test_first_invalid_sample_does_not_draw(qapp):
    vk = VirtualKeyboard()
    vk.show()
    qapp.processEvents()
    overlay = DebugGazeOverlay(vk.keyboard_widget, dpr=1.5)
    invalid = GazeSample(
        timestamp_ns=2,
        valid=False,
        x=0.0,
        y=0.0,
        calibrated_x=None,
        calibrated_y=None,
        tracking_state="FACE_MISSING",
        left_openness=0.0,
        right_openness=0.0,
    )
    overlay.update_sample(invalid)
    qapp.processEvents()
    assert overlay._dot._pos is None


def test_live_geometry_audit_records_keyboard_qrects(qapp, tmp_path):
    vk = VirtualKeyboard()
    vk.show()
    qapp.processEvents()
    vk._keyboard_layout_builder.export_keyboard_layout()
    qapp.processEvents()

    lifecycle = GazeFollowerLifecycle.__new__(GazeFollowerLifecycle)
    lifecycle.pygame_mode = (1920, 1080)
    lifecycle.gf_screen_size = (1920, 1080)
    lifecycle.geometry = None

    path = record_live_geometry(lifecycle, vk)
    assert path.is_file()
    audit, geometry = build_live_audit(
        keyboard=vk,
        pygame_mode=(1920, 1080),
        gf_screen_size=(1920, 1080),
    )
    assert audit.qt_geometry is not None
    assert audit.device_pixel_ratio is not None
    assert audit.keyboard_origin is not None
    assert audit.transform in {"identity", "origin", "origin+dpr"}
    assert geometry.transform == audit.transform
    assert len(audit.suggestion_rects) == 3
    assert any(not kid.startswith("suggestion:") for kid in audit.key_rects)

    dest = write_geometry_audit(audit, path=tmp_path / "geometry_audit.json")
    text = dest.read_text(encoding="utf-8")
    assert '"transform"' in text
    assert "suggestion:0" in text


def test_wire_debug_dot_does_not_construct_second_keyboard(qapp, monkeypatch):
    vk = VirtualKeyboard()
    vk.show()
    qapp.processEvents()
    created = []
    real_init = VirtualKeyboard.__init__

    def wrapped(self, *args, **kwargs):
        created.append(self)
        return real_init(self, *args, **kwargs)

    monkeypatch.setattr(VirtualKeyboard, "__init__", wrapped)
    qt_calls: list[Any] = []
    debug_calls: list[Any] = []
    life = SimpleNamespace(
        gf_screen_size=(1920, 1080),
        pygame_mode=(1920, 1080),
        geometry=GeometryConfig(transform="origin+dpr", dpr=1.5),
        attach_qt_bridge=lambda parent: qt_calls.append(parent)
        or SimpleNamespace(
            sample_ready=SimpleNamespace(connect=lambda fn: None),
            start=lambda: None,
            stop=lambda: None,
        ),
        attach_debug_get_gaze_info_bridge=lambda overlay, parent=None: debug_calls.append(
            overlay
        )
        or SimpleNamespace(start=lambda: None, stop=lambda: None),
    )
    wire_debug_gaze_dot(life, vk)
    assert created == []
    assert qt_calls == []
    assert debug_calls == [vk._gf_debug_overlay]
    assert vk._gf_debug_overlay is not None
    assert isinstance(vk._gf_debug_overlay, DebugGazeOverlay)
    assert abs(vk._gf_debug_overlay._dot._radius - (50.0 / 1.5)) < 1e-6
    assert abs(vk._gf_debug_overlay._dot._stroke - (5.0 / 1.5)) < 1e-6


def test_wired_debug_dot_covers_full_keyboard_not_dwell(qapp, monkeypatch):
    vk = VirtualKeyboard()
    vk.show()
    qapp.processEvents()
    monkeypatch.setattr(vk._typing_runtime, "on_mapped_gaze", MagicMock())
    overlay = DebugGazeOverlay(vk)
    overlay.update_xy(640.0, 360.0)
    qapp.processEvents()
    vk._typing_runtime.on_mapped_gaze.assert_not_called()
    assert overlay._dot._pos is not None


def test_debug_dot_paint_does_not_apply_dpr_again():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    debug = (root / "gazekey/backend/debug_gaze_dot.py").read_text(encoding="utf-8")
    debug_dot = debug.split("class DebugGazeDot", 1)[1].split("class DebugGazeOverlay", 1)[0]
    assert "devicePixelRatio" not in debug_dot
    assert "apply_geometry" not in debug_dot
    assert "/ dpr" not in debug_dot
