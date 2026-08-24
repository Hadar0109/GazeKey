"""T027 / T028: debug gaze dot and live geometry audit on the existing keyboard."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from gazekey.backend.debug_gaze_dot import DebugGazeOverlay
from gazekey.backend.gaze_sample import GazeSample
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


def test_invalid_sample_hides_debug_dot_no_hold_last(qapp):
    vk = VirtualKeyboard()
    vk.show()
    qapp.processEvents()
    overlay = DebugGazeOverlay(vk.keyboard_widget)
    overlay.update_sample(_valid_sample(80.0, 90.0))
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
    life = SimpleNamespace(
        attach_qt_bridge=lambda parent: SimpleNamespace(
            sample_ready=SimpleNamespace(connect=lambda fn: None),
            start=lambda: None,
            stop=lambda: None,
        )
    )
    wire_debug_gaze_dot(life, vk)
    assert created == []
    assert vk._gf_debug_overlay is not None
