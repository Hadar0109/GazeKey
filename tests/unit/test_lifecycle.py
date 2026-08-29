"""T016 / T009 / T010: GazeFollower lifecycle fail-closed and Qt-safe queue."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from gazekey.backend.geometry import GeometryConfig
from gazekey.backend.lifecycle import GazeFollowerLifecycle, GazeFollowerLifecycleError


class _State:
    def __init__(self, name: str) -> None:
        self.name = name


class FakeCalibration:
    def __init__(self, token: str = "orig", has_calibrated: bool = True) -> None:
        self.token = token
        self.has_calibrated = has_calibrated


class FakeCamera:
    def __init__(self) -> None:
        self.camera_running_state = _State("CLOSING")

    def stop_previewing(self) -> None:
        self.camera_running_state = _State("CLOSING")

    def stop_calibrating(self) -> None:
        self.camera_running_state = _State("CLOSING")


class FakeConfig:
    def __init__(self) -> None:
        self.cali_mode = 0
        self.screen_physical_size = "unset"


class FakeGazeFollower:
    def __init__(self, config=None, camera=None, **kwargs) -> None:
        self.config = config
        self.camera = camera if camera is not None else FakeCamera()
        self.screen_size = [1920, 1080]
        self.subscribers = []
        self.preview_calls = 0
        self.calibrate_calls = 0
        self.sampling_calls = 0
        self.release_calls = 0
        self._calibration_controller = SimpleNamespace(cali_available=True)
        self.calibration = FakeCalibration(token="orig", has_calibrated=True)

    def preview(self, win=None) -> None:
        self.preview_calls += 1
        self._win = win

    def calibrate(self, win=None) -> None:
        self.calibrate_calls += 1
        self._win = win
        cal = getattr(self, "calibration", None)
        if cal is not None:
            cal.has_calibrated = bool(self._calibration_controller.cali_available)
            if cal.has_calibrated:
                cal.token = "new"

    def start_sampling(self) -> None:
        self.sampling_calls += 1
        self.camera.camera_running_state = _State("SAMPLING")

    def stop_sampling(self) -> None:
        self.camera.camera_running_state = _State("CLOSING")

    def add_subscriber(self, fn, args=(), kwargs=None) -> None:
        self.subscribers.append(fn)

    def remove_subscriber(self, fn) -> None:
        self.subscribers = [s for s in self.subscribers if s is not fn]

    def release(self) -> None:
        self.release_calls += 1

    def get_gaze_info(self):
        return getattr(self, "_gaze_info", None)


def _patch_official(monkeypatch) -> None:
    import gazekey.backend.lifecycle as life_mod

    monkeypatch.setattr(life_mod, "require_python_311", lambda: None)
    monkeypatch.setattr(life_mod, "verify_base_mnn", lambda: "ok")
    monkeypatch.setattr(
        GazeFollowerLifecycle,
        "_load_official",
        staticmethod(lambda: (SimpleNamespace(__version__="1.0.2"), FakeGazeFollower, FakeConfig)),
    )
    monkeypatch.setattr(
        GazeFollowerLifecycle,
        "_make_web_cam_camera",
        staticmethod(lambda: FakeCamera()),
    )


def test_lifecycle_preview_calibrate_sampling_require_closing(monkeypatch):
    _patch_official(monkeypatch)
    life = GazeFollowerLifecycle(gf_factory=FakeGazeFollower)
    gf = life.construct()
    assert gf.config.cali_mode == 13
    assert gf.config.screen_physical_size is None
    assert isinstance(gf.camera, FakeCamera)

    monkeypatch.setattr(life, "_ensure_pygame_window", lambda: "win")
    life.preview()
    life.calibrate()
    life.quit_pygame()
    life.start_sampling()
    assert gf.preview_calls == 1
    assert gf.calibrate_calls == 1
    assert gf.sampling_calls == 1
    assert life._on_camera_sample in gf.subscribers


def test_construct_passes_provenance_camera(monkeypatch):
    _patch_official(monkeypatch)
    cam = FakeCamera()
    monkeypatch.setattr(
        GazeFollowerLifecycle,
        "_make_web_cam_camera",
        staticmethod(lambda: cam),
    )
    life = GazeFollowerLifecycle(gf_factory=FakeGazeFollower)
    gf = life.construct()
    assert gf.camera is cam


def test_start_preview_while_sampling_fails_closed(monkeypatch):
    _patch_official(monkeypatch)
    life = GazeFollowerLifecycle(gf_factory=FakeGazeFollower)
    life.construct()
    life._gf.camera.camera_running_state = _State("SAMPLING")
    with pytest.raises(GazeFollowerLifecycleError, match="Failing closed"):
        life.preview()


def test_construct_failure_does_not_start_legacy_estimator(monkeypatch):
    _patch_official(monkeypatch)

    def boom(config=None, **kwargs):
        raise RuntimeError("model init failed")

    life = GazeFollowerLifecycle(gf_factory=boom)
    with pytest.raises(GazeFollowerLifecycleError, match="Failing closed") as err:
        life.construct()
    assert "TrackingManager" in str(err.value)
    assert "PCA4" in str(err.value)


def test_camera_thread_queue_not_raw_get_gaze_info(monkeypatch):
    _patch_official(monkeypatch)
    life = GazeFollowerLifecycle(gf_factory=FakeGazeFollower)
    life.construct()
    info = SimpleNamespace(
        timestamp=3,
        status=True,
        tracking_state=SimpleNamespace(name="SUCCESS"),
        filtered_gaze_coordinates=(1.0, 2.0),
        calibrated_gaze_coordinates=(1.0, 2.0),
        left_openness=20.0,
        right_openness=21.0,
    )
    life._on_camera_sample(None, info)
    sample = life.take_latest_sample()
    assert sample is not None
    assert sample.valid is True
    assert (sample.x, sample.y) == (1.0, 2.0)
    assert life.take_latest_sample() is None


def test_debug_filtered_qt_xy_uses_one_get_gaze_info_and_origin_dpr(monkeypatch):
    _patch_official(monkeypatch)
    geom = GeometryConfig(transform="origin+dpr", dpr=1.5, origin_offset=(0.0, 0.0))
    life = GazeFollowerLifecycle(gf_factory=FakeGazeFollower, geometry=geom)
    life.construct()
    calls = []
    orig = life.gf.get_gaze_info

    def counted():
        calls.append(1)
        return orig()

    life.gf.get_gaze_info = counted
    life.gf._gaze_info = SimpleNamespace(
        status=True,
        filtered_gaze_coordinates=(960.0, 540.0),
    )
    geom_before = life.geometry
    xy = life.debug_filtered_qt_xy()
    assert xy == (640.0, 360.0)
    assert len(calls) == 1
    assert life.geometry is geom_before
    assert life.geometry.transform == "origin+dpr"
    life.gf._gaze_info = SimpleNamespace(
        status=False,
        filtered_gaze_coordinates=(960.0, 540.0),
    )
    assert life.debug_filtered_qt_xy() is None
    sample = life.take_latest_sample()
    assert sample is None


def test_unaccepted_calibration_fails_closed(monkeypatch):
    from gazekey.backend.startup import run_official_startup

    class Rejecting(FakeGazeFollower):
        def __init__(self, config=None, **kwargs) -> None:
            super().__init__(config, **kwargs)
            self._calibration_controller.cali_available = False

    _patch_official(monkeypatch)
    life = GazeFollowerLifecycle(gf_factory=Rejecting)
    monkeypatch.setattr(life, "_ensure_pygame_window", lambda: "win")
    with pytest.raises(GazeFollowerLifecycleError, match="Failing closed") as err:
        run_official_startup(life)
    assert "not accepted" in str(err.value)
    assert "PCA4" in str(err.value)
    assert "TrackingManager" in str(err.value)


def test_official_startup_preview_calibrate_then_sampling(monkeypatch):
    from gazekey.backend.startup import run_official_startup

    _patch_official(monkeypatch)
    life = GazeFollowerLifecycle(gf_factory=FakeGazeFollower)
    monkeypatch.setattr(life, "_ensure_pygame_window", lambda: "win")
    run_official_startup(life)
    assert life.gf.preview_calls == 1
    assert life.gf.calibrate_calls == 1
    assert life.gf.sampling_calls == 1
    assert life._on_camera_sample in life.gf.subscribers
