"""T016 / T009 / T010: GazeFollower lifecycle fail-closed and Qt-safe queue."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from gazekey.backend.lifecycle import GazeFollowerLifecycle, GazeFollowerLifecycleError


class _State:
    def __init__(self, name: str) -> None:
        self.name = name


class FakeCamera:
    def __init__(self) -> None:
        self.camera_running_state = _State("CLOSING")


class FakeConfig:
    def __init__(self) -> None:
        self.cali_mode = 0
        self.screen_physical_size = "unset"


class FakeGazeFollower:
    def __init__(self, config=None) -> None:
        self.config = config
        self.camera = FakeCamera()
        self.screen_size = [1920, 1080]
        self.subscribers = []
        self.preview_calls = 0
        self.calibrate_calls = 0
        self.sampling_calls = 0
        self.release_calls = 0

    def preview(self, win=None) -> None:
        self.preview_calls += 1
        self._win = win

    def calibrate(self, win=None) -> None:
        self.calibrate_calls += 1
        self._win = win

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
        raise AssertionError("Qt thread must not consume camera get_gaze_info()")


def _patch_official(monkeypatch) -> None:
    monkeypatch.setattr(
        "gazekey.backend.lifecycle.require_python_311", lambda: None
    )
    monkeypatch.setattr("gazekey.backend.lifecycle.verify_base_mnn", lambda: "ok")
    monkeypatch.setattr(
        GazeFollowerLifecycle,
        "_load_official",
        staticmethod(lambda: (SimpleNamespace(__version__="1.0.2"), FakeGazeFollower, FakeConfig)),
    )


def test_lifecycle_preview_calibrate_sampling_require_closing(monkeypatch):
    _patch_official(monkeypatch)
    life = GazeFollowerLifecycle(gf_factory=FakeGazeFollower)
    gf = life.construct()
    assert gf.config.cali_mode == 13
    assert gf.config.screen_physical_size is None

    monkeypatch.setattr(life, "_ensure_pygame_window", lambda: "win")
    life.preview()
    life.calibrate()
    life.quit_pygame()
    life.start_sampling()
    assert gf.preview_calls == 1
    assert gf.calibrate_calls == 1
    assert gf.sampling_calls == 1
    assert life._on_camera_sample in gf.subscribers


def test_start_preview_while_sampling_fails_closed(monkeypatch):
    _patch_official(monkeypatch)
    life = GazeFollowerLifecycle(gf_factory=FakeGazeFollower)
    life.construct()
    life._gf.camera.camera_running_state = _State("SAMPLING")
    with pytest.raises(GazeFollowerLifecycleError, match="Failing closed"):
        life.preview()


def test_construct_failure_does_not_start_legacy_estimator(monkeypatch):
    _patch_official(monkeypatch)

    def boom(config=None):
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
    assert life.take_latest_sample() is None
