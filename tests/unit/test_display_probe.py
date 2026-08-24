"""T029 Step D: read-only pygame.quit → Qt display/DPI probe."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from gazekey.backend.display_probe import (
    PHASE_AFTER_CALIBRATE,
    PHASE_AFTER_PYGAME_QUIT,
    PHASE_AFTER_QT_KEYBOARD,
    PHASE_AFTER_START_SAMPLING,
    DisplayProbe,
    snapshot_pygame,
    take_snapshot,
)
from gazekey.backend.geometry import GeometryConfig
from gazekey.backend.lifecycle import GazeFollowerLifecycle
from gazekey.backend.startup import record_dpi_probe, run_official_startup, wire_debug_gaze_dot

from tests.unit.test_lifecycle import FakeGazeFollower, _patch_official


def _lifecycle_stub() -> SimpleNamespace:
    return SimpleNamespace(
        pygame_mode=(1920, 1080),
        gf_screen_size=(1920, 1080),
        gf=SimpleNamespace(
            screen_size=[1920, 1080],
            config=SimpleNamespace(screen_size=[1920, 1080]),
        ),
        geometry=GeometryConfig(transform="origin+dpr", dpr=1.5),
    )


def test_snapshot_pygame_does_not_call_init(monkeypatch):
    import pygame

    calls: list[str] = []

    monkeypatch.setattr(pygame, "get_init", lambda: False)
    monkeypatch.setattr(pygame, "init", lambda *a, **k: calls.append("pygame.init"))
    monkeypatch.setattr(pygame.display, "get_init", lambda: False)
    monkeypatch.setattr(
        pygame.display, "init", lambda *a, **k: calls.append("display.init")
    )
    monkeypatch.setattr(
        pygame.display,
        "Info",
        lambda: calls.append("Info") or (_ for _ in ()).throw(AssertionError("Info")),
    )

    result = snapshot_pygame()
    assert calls == []
    assert result["pygame_init"] is False
    assert result["display_init"] is False
    assert result["display_info"] is None


def test_display_probe_source_never_inits_pygame_or_chooses_transform():
    root = Path(__file__).resolve().parents[2]
    src = (root / "gazekey/backend/display_probe.py").read_text(encoding="utf-8")
    assert "pygame.init(" not in src
    assert "pygame.display.init(" not in src
    assert "choose_allowed_transform" not in src


def test_display_probe_four_phase_json_qt_only_in_phase_4(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "gazekey.backend.display_probe.snapshot_pygame",
        lambda: {
            "pygame_init": True,
            "display_init": True,
            "display_info": {"current_w": 1920, "current_h": 1080},
        },
    )
    monkeypatch.setattr(
        "gazekey.backend.display_probe.snapshot_screeninfo",
        lambda: {"width": 1920, "height": 1080, "x": 0, "y": 0},
    )
    monkeypatch.setattr(
        "gazekey.backend.display_probe.snapshot_win32",
        lambda: {
            "SM_CXSCREEN": 1920,
            "SM_CYSCREEN": 1080,
            "dpi_awareness": 2,
            "dpi_awareness_name": "PROCESS_PER_MONITOR_DPI_AWARE",
            "dpi_for_system": 144,
            "monitor_effective_dpi": {"x": 144, "y": 144},
        },
    )
    monkeypatch.setattr(
        "gazekey.backend.display_probe.snapshot_qt",
        lambda: {
            "geometry": (0, 0, 1280, 720),
            "available_geometry": (0, 0, 1280, 680),
            "device_pixel_ratio": 1.5,
            "logical_dpi": 144.0,
            "physical_dpi": 144.0,
        },
    )

    life = _lifecycle_stub()
    geom_before = life.geometry
    probe = DisplayProbe()
    probe.capture(PHASE_AFTER_CALIBRATE, life)
    probe.capture(PHASE_AFTER_PYGAME_QUIT, life)
    probe.capture(PHASE_AFTER_START_SAMPLING, life)
    probe.capture(PHASE_AFTER_QT_KEYBOARD, life, include_qt=True)

    dest = probe.write(tmp_path / "pygame_qt_dpi_probe.json")
    data = json.loads(dest.read_text(encoding="utf-8"))
    names = [phase["phase"] for phase in data["phases"]]
    assert names == [
        PHASE_AFTER_CALIBRATE,
        PHASE_AFTER_PYGAME_QUIT,
        PHASE_AFTER_START_SAMPLING,
        PHASE_AFTER_QT_KEYBOARD,
    ]
    for phase in data["phases"][:3]:
        assert phase["qt"] is None
        assert phase["win32"]["SM_CXSCREEN"] == 1920
        assert phase["screeninfo"]["width"] == 1920
        assert phase["gf_screen_size"] == [1920, 1080]
    qt = data["phases"][3]["qt"]
    assert qt is not None
    assert qt["device_pixel_ratio"] == 1.5
    assert list(qt["geometry"]) == [0, 0, 1280, 720]
    assert life.geometry is geom_before
    assert life.geometry.transform == "origin+dpr"


def test_take_snapshot_without_qt_flag_does_not_fill_qt(monkeypatch):
    monkeypatch.setattr(
        "gazekey.backend.display_probe.snapshot_qt",
        lambda: {"device_pixel_ratio": 1.5},
    )
    monkeypatch.setattr("gazekey.backend.display_probe.snapshot_pygame", lambda: {})
    monkeypatch.setattr("gazekey.backend.display_probe.snapshot_screeninfo", lambda: None)
    monkeypatch.setattr("gazekey.backend.display_probe.snapshot_win32", lambda: {})
    snap = take_snapshot("after_calibrate", _lifecycle_stub(), include_qt=False)
    assert snap["qt"] is None


def test_official_startup_quits_pygame_before_sampling_and_probes(monkeypatch):
    _patch_official(monkeypatch)
    order: list[str] = []
    orig_quit = GazeFollowerLifecycle.quit_pygame
    orig_start = GazeFollowerLifecycle.start_sampling

    def quit_pygame(self) -> None:
        order.append("quit")
        orig_quit(self)

    def start_sampling(self) -> None:
        order.append("sample")
        orig_start(self)

    monkeypatch.setattr(GazeFollowerLifecycle, "quit_pygame", quit_pygame)
    monkeypatch.setattr(GazeFollowerLifecycle, "start_sampling", start_sampling)

    life = GazeFollowerLifecycle(gf_factory=FakeGazeFollower)
    monkeypatch.setattr(life, "_ensure_pygame_window", lambda: "win")
    run_official_startup(life)
    assert order == ["quit", "sample"]
    assert life.gf.preview_calls == 1
    assert life.gf.calibrate_calls == 1
    assert life.gf.sampling_calls == 1
    phases = [item["phase"] for item in life._display_probe.phases]
    assert phases == [
        PHASE_AFTER_CALIBRATE,
        PHASE_AFTER_PYGAME_QUIT,
        PHASE_AFTER_START_SAMPLING,
    ]


def test_record_dpi_probe_adds_qt_phase_without_changing_geometry(tmp_path, monkeypatch):
    monkeypatch.setattr("gazekey.backend.display_probe.snapshot_pygame", lambda: {})
    monkeypatch.setattr("gazekey.backend.display_probe.snapshot_screeninfo", lambda: None)
    monkeypatch.setattr("gazekey.backend.display_probe.snapshot_win32", lambda: {})
    monkeypatch.setattr(
        "gazekey.backend.display_probe.snapshot_qt",
        lambda: {"device_pixel_ratio": 1.5, "geometry": (0, 0, 1280, 720)},
    )
    life = _lifecycle_stub()
    geom_before = life.geometry
    path = record_dpi_probe(life, tmp_path / "probe.json")
    assert path is not None
    assert path.is_file()
    assert life.geometry is geom_before
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["phases"][-1]["phase"] == PHASE_AFTER_QT_KEYBOARD
    assert data["phases"][-1]["qt"]["device_pixel_ratio"] == 1.5


def test_startup_source_keeps_quit_then_sample_and_get_gaze_info_overlay():
    root = Path(__file__).resolve().parents[2]
    startup = (root / "gazekey/backend/startup.py").read_text(encoding="utf-8")
    main = (root / "main.py").read_text(encoding="utf-8")
    body = startup.split("def run_official_startup", 1)[1].split(
        "def record_live_geometry", 1
    )[0]
    assert body.index("lifecycle.quit_pygame()") < body.index(
        "lifecycle.start_sampling()"
    )
    assert "attach_debug_get_gaze_info_bridge" in startup
    assert "sample_ready" not in startup
    assert "record_dpi_probe" in main
    assert "QApplication" in main
    assert main.index("run_official_startup") < main.index("QApplication")


def test_wire_debug_dot_still_uses_get_gaze_info_bridge(qapp, monkeypatch):
    from gazekey.ui.virtual_keyboard import VirtualKeyboard

    vk = VirtualKeyboard()
    vk.show()
    qapp.processEvents()
    debug_calls: list[object] = []
    life = SimpleNamespace(
        geometry=GeometryConfig(transform="origin+dpr", dpr=1.5),
        attach_debug_get_gaze_info_bridge=lambda overlay, parent=None: debug_calls.append(
            overlay
        )
        or SimpleNamespace(start=lambda: None, stop=lambda: None),
    )
    wire_debug_gaze_dot(life, vk)
    assert debug_calls == [vk._gf_debug_overlay]
