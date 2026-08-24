"""Thin lifecycle wrapper around official GazeFollower + DefaultConfig.

Never starts TrackingManager, MapperRuntime, PCA4, Ridge, or another estimator.
Never starts Preview/Calibration/sampling unless camera state is CLOSING.
"""

from __future__ import annotations

import math
import queue
import sys
from typing import Any, Callable

from gazekey.backend.adapter import gaze_info_to_sample
from gazekey.backend.gaze_sample import GazeSample
from gazekey.backend.geometry import GeometryConfig, apply_geometry
from gazekey.backend.provenance import (
    CALI_MODE,
    PHYSICAL_SCREEN_SIZE,
    ProvenanceError,
    require_python_311,
    verify_base_mnn,
)

CLOSING_NAME = "CLOSING"


class GazeFollowerLifecycleError(RuntimeError):
    """Fail-closed GazeFollower failure. Do not recover via PCA4/Ridge."""


class GazeFollowerLifecycle:
    """Official preview → calibrate → start_sampling → get_gaze_info wrapper."""

    def __init__(
        self,
        *,
        geometry: GeometryConfig | None = None,
        gf_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.geometry = geometry if geometry is not None else GeometryConfig()
        self._gf_factory = gf_factory
        self._gf: Any = None
        self._pygame_win: Any = None
        self.pygame_mode: tuple[int, int] | None = None
        self.gf_screen_size: tuple[int, int] | None = None
        self._sample_queue: queue.Queue[Any] = queue.Queue(maxsize=1)
        self._qt_bridge: Any = None
        self._qt_consumers: list[Any] = []
        self._released = False

    @property
    def gf(self) -> Any:
        return self._gf

    @staticmethod
    def _load_official() -> tuple[Any, Any, Any]:
        import gazefollower
        from gazefollower import GazeFollower
        from gazefollower.misc import DefaultConfig

        reported = getattr(gazefollower, "__version__", None)
        if reported is None:
            try:
                from gazefollower import version as gf_version

                reported = gf_version.__version__
            except Exception:
                reported = None
        if reported is not None and str(reported) != "1.0.2":
            raise ProvenanceError(f"expected gazefollower 1.0.2, got {reported}")
        return gazefollower, GazeFollower, DefaultConfig

    def construct(self) -> Any:
        """Import/construct official GazeFollower. Fail closed on model/import errors."""
        require_python_311()
        try:
            _pkg, GazeFollower, DefaultConfig = self._load_official()
        except GazeFollowerLifecycleError:
            raise
        except Exception as exc:
            self._fail_closed("import gazefollower", exc)

        try:
            verify_base_mnn()
        except Exception as exc:
            self._fail_closed("base.mnn provenance", exc)

        try:
            config = DefaultConfig()
            config.cali_mode = CALI_MODE
            config.screen_physical_size = PHYSICAL_SCREEN_SIZE
            factory = self._gf_factory if self._gf_factory is not None else GazeFollower
            self._gf = factory(config=config)
        except GazeFollowerLifecycleError:
            raise
        except Exception as exc:
            self._fail_closed("GazeFollower construction/model initialization", exc)

        size = getattr(self._gf, "screen_size", None)
        if size is not None:
            try:
                self.gf_screen_size = (int(size[0]), int(size[1]))
            except Exception:
                self.gf_screen_size = None
        return self._gf

    def camera_state_name(self) -> str:
        camera = getattr(self._gf, "camera", None) if self._gf is not None else None
        state = getattr(camera, "camera_running_state", None)
        name = getattr(state, "name", None)
        if isinstance(name, str):
            return name
        return CLOSING_NAME if self._gf is None else str(state)

    def _require_closing(self, action: str) -> None:
        if self._gf is None:
            self._fail_closed(action, RuntimeError("GazeFollower is not constructed"))
        name = self.camera_state_name()
        if name != CLOSING_NAME:
            self._fail_closed(
                action,
                RuntimeError(
                    f"camera state is {name}, expected {CLOSING_NAME} before {action}"
                ),
            )

    def preview(self, *, cleanup_on_failure: bool = True) -> None:
        self._require_closing("preview()")
        try:
            win = self._ensure_pygame_window()
            self._gf.preview(win=win)
        except GazeFollowerLifecycleError:
            if cleanup_on_failure:
                self._cleanup_after_failure()
            raise
        except Exception as exc:
            if cleanup_on_failure:
                self._cleanup_after_failure()
            self._fail_closed("preview()", exc)

    def calibrate(self, *, cleanup_on_failure: bool = True) -> None:
        """Official 13-point Calibration + result UI (Space accept / R retry)."""
        self._require_closing("calibrate()")
        try:
            win = self._ensure_pygame_window()
            self._gf.calibrate(win=win)
        except GazeFollowerLifecycleError:
            if cleanup_on_failure:
                self._cleanup_after_failure()
            raise
        except Exception as exc:
            if cleanup_on_failure:
                self._cleanup_after_failure()
            self._fail_closed("calibrate()", exc)

    def calibration_accepted(self) -> bool:
        """True when official ``cali_available`` is set after Space accept.

        First-run startup still uses this flag. Recalibrate uses
        ``calibration_model_usable()`` (``has_calibrated``) and does not
        fall back to a previous SVR.
        """
        gf = self._gf
        if gf is None:
            return False
        controller = getattr(gf, "_calibration_controller", None)
        if controller is None:
            return False
        return bool(getattr(controller, "cali_available", False))

    def calibration_model_usable(self) -> bool:
        """True when the live GazeFollower SVR (or test double) is trained."""
        gf = self._gf
        if gf is None:
            return False
        cal = getattr(gf, "calibration", None)
        if cal is None:
            return False
        return bool(getattr(cal, "has_calibrated", False))

    def invalidate_live_calibration(self) -> None:
        """Mark the live model unusable. Does not keep or restore a prior SVR."""
        if self._gf is None:
            return
        cal = getattr(self._gf, "calibration", None)
        if cal is not None and hasattr(cal, "has_calibrated"):
            cal.has_calibrated = False
        controller = getattr(self._gf, "_calibration_controller", None)
        if controller is not None:
            controller.cali_available = False

    def _return_camera_to_closing(self) -> None:
        if self._gf is None:
            return
        name = self.camera_state_name()
        if name == CLOSING_NAME:
            return
        cam = getattr(self._gf, "camera", None)
        try:
            if name == "SAMPLING":
                self.stop_sampling()
            elif name == "PREVIEWING" and cam is not None:
                cam.stop_previewing()
            elif name == "CALIBRATING" and cam is not None:
                cam.stop_calibrating()
        except Exception as exc:
            print(
                f"GazeFollower camera close after recalibrate failed: {exc}",
                file=sys.stderr,
            )

    def resume_sampling_after_pygame(self) -> None:
        """CLOSING → SAMPLING after pygame. No-op if already sampling."""
        if self.camera_state_name() == "SAMPLING":
            return
        self._return_camera_to_closing()
        if self.camera_state_name() == CLOSING_NAME:
            self.start_sampling()

    def quit_pygame(self) -> None:
        self._pygame_win = None
        try:
            import pygame

            pygame.quit()
        except Exception:
            pass

    def start_sampling(self) -> None:
        self._require_closing("start_sampling()")
        try:
            self._gf.add_subscriber(self._on_camera_sample)
            self._gf.start_sampling()
        except GazeFollowerLifecycleError:
            raise
        except Exception as exc:
            try:
                self._gf.remove_subscriber(self._on_camera_sample)
            except Exception:
                pass
            self._fail_closed("start_sampling() / camera opening", exc)

    def stop_sampling(self) -> None:
        if self._gf is None:
            return
        try:
            if self.camera_state_name() == "SAMPLING":
                self._gf.stop_sampling()
        except Exception as exc:
            print(f"GazeFollower stop_sampling failed: {exc}", file=sys.stderr)
        try:
            self._gf.remove_subscriber(self._on_camera_sample)
        except Exception:
            pass

    def get_gaze_info(self) -> GazeSample | None:
        """Latest GazeSample already converted on the camera thread (queue)."""
        return self.take_latest_sample()

    def take_latest_sample(self) -> GazeSample | None:
        sample: GazeSample | None = None
        while True:
            try:
                sample = self._sample_queue.get_nowait()
            except queue.Empty:
                break
        return sample

    def debug_filtered_qt_xy(self) -> tuple[float, float] | None:
        """One gf.get_gaze_info() sample mapped with lifecycle.geometry (origin+dpr).

        Does not change lifecycle.geometry. Does not apply identity/no-DPR.
        """
        gf = self._gf
        if gf is None:
            return None
        gaze_info = gf.get_gaze_info()
        if gaze_info is None or not bool(getattr(gaze_info, "status", False)):
            return None
        coords = getattr(gaze_info, "filtered_gaze_coordinates", None)
        try:
            if coords is None or len(coords) != 2:
                return None
            x = float(coords[0])
            y = float(coords[1])
        except (TypeError, ValueError):
            return None
        if not math.isfinite(x) or not math.isfinite(y):
            return None
        return apply_geometry(x, y, self.geometry)

    def attach_qt_bridge(self, parent: Any = None) -> Any:
        """Qt-thread-safe consumer: timer on the Qt thread drains the camera queue.

        Camera-thread ``get_gaze_info()`` is not read on the Qt thread.
        Product path (unused by the Step B debug ring).
        """
        from PySide6.QtCore import QObject, QTimer, Signal

        lifecycle = self

        class GazeSampleBridge(QObject):
            sample_ready = Signal(object)

            def __init__(self) -> None:
                super().__init__(parent)
                self._timer = QTimer(self)
                self._timer.setInterval(16)
                self._timer.timeout.connect(self._drain)

            def start(self) -> None:
                self._timer.start()

            def stop(self) -> None:
                self._timer.stop()

            def _drain(self) -> None:
                sample = lifecycle.take_latest_sample()
                if sample is not None:
                    self.sample_ready.emit(sample)

        return self._register_qt_consumer(GazeSampleBridge())

    def attach_debug_get_gaze_info_bridge(self, overlay: Any, parent: Any = None) -> Any:
        """Poll official ``gf.get_gaze_info()`` once per tick for the GREEN overlay.

        Does not drain the T010 subscriber queue. Stopped by ``stop_qt_bridge``.
        """
        from PySide6.QtCore import QObject, QTimer

        lifecycle = self

        class DebugGetGazeInfoBridge(QObject):
            def __init__(self) -> None:
                super().__init__(parent)
                self._timer = QTimer(self)
                self._timer.setInterval(16)
                self._timer.timeout.connect(self._poll)

            def start(self) -> None:
                self._timer.start()

            def stop(self) -> None:
                self._timer.stop()

            def _poll(self) -> None:
                xy = lifecycle.debug_filtered_qt_xy()
                if xy is not None:
                    overlay.update_xy(xy[0], xy[1])

        return self._register_qt_consumer(DebugGetGazeInfoBridge())

    def release(self) -> None:
        self.stop_qt_bridge()
        self.stop_sampling()
        self.quit_pygame()
        if self._gf is not None and not self._released:
            try:
                self._gf.release()
            except Exception as exc:
                print(f"GazeFollower.release() failed: {exc}", file=sys.stderr)
        self._released = True
        self._gf = None

    def _register_qt_consumer(self, bridge: Any) -> Any:
        consumers = getattr(self, "_qt_consumers", None)
        if consumers is None:
            consumers = []
            self._qt_consumers = consumers
        consumers.append(bridge)
        self._qt_bridge = bridge
        return bridge

    def stop_qt_bridge(self) -> None:
        for bridge in list(getattr(self, "_qt_consumers", None) or []):
            try:
                bridge.stop()
            except Exception:
                pass
        self._qt_consumers = []
        self._qt_bridge = None

    def _on_camera_sample(self, face_info: Any, gaze_info: Any, *args: Any, **kwargs: Any) -> None:
        _ = face_info, args, kwargs
        sample = gaze_info_to_sample(gaze_info, self.geometry)
        try:
            self._sample_queue.get_nowait()
        except queue.Empty:
            pass
        try:
            self._sample_queue.put_nowait(sample)
        except queue.Full:
            pass

    def _ensure_pygame_window(self) -> Any:
        import pygame

        if self._pygame_win is not None:
            return self._pygame_win
        pygame.init()
        size = self.gf_screen_size
        if size is None:
            cfg_size = getattr(self._gf, "screen_size", None)
            if cfg_size is not None:
                size = (int(cfg_size[0]), int(cfg_size[1]))
            else:
                size = (1920, 1080)
        self._pygame_win = pygame.display.set_mode(size, pygame.FULLSCREEN)
        pygame.display.set_caption("GazeFollower")
        self.pygame_mode = tuple(self._pygame_win.get_size())
        return self._pygame_win

    def _cleanup_after_failure(self) -> None:
        try:
            if self._gf is not None:
                self._gf.release()
        except Exception as exc:
            print(
                f"GazeFollower.release() after failure: {exc}",
                file=sys.stderr,
            )
        self.quit_pygame()

    def _fail_closed(self, action: str, exc: BaseException) -> None:
        message = (
            f"GazeFollower failed during {action}: {exc}. "
            "Failing closed — not starting TrackingManager, MapperRuntime, "
            "PCA4, Ridge, or another estimator."
        )
        print(message, file=sys.stderr)
        raise GazeFollowerLifecycleError(message) from exc
