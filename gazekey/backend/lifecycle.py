"""Thin lifecycle wrapper around official GazeFollower + DefaultConfig.

Never starts TrackingManager, MapperRuntime, PCA4, Ridge, or another estimator.
Never starts Preview/Calibration/sampling unless camera state is CLOSING.
"""

from __future__ import annotations

import queue
import sys
from typing import Any, Callable

from gazekey.backend.adapter import gaze_info_to_sample
from gazekey.backend.gaze_sample import GazeSample
from gazekey.backend.geometry import GeometryConfig
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
        self._sample_queue: queue.Queue[GazeSample] = queue.Queue(maxsize=1)
        self._qt_bridge: Any = None
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

    def preview(self) -> None:
        self._require_closing("preview()")
        try:
            win = self._ensure_pygame_window()
            self._gf.preview(win=win)
        except GazeFollowerLifecycleError:
            self._cleanup_after_failure()
            raise
        except Exception as exc:
            self._cleanup_after_failure()
            self._fail_closed("preview()", exc)

    def calibrate(self) -> None:
        """Official 13-point Calibration + result UI (Space accept / R retry)."""
        self._require_closing("calibrate()")
        try:
            win = self._ensure_pygame_window()
            self._gf.calibrate(win=win)
        except GazeFollowerLifecycleError:
            self._cleanup_after_failure()
            raise
        except Exception as exc:
            self._cleanup_after_failure()
            self._fail_closed("calibrate()", exc)

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

    def attach_qt_bridge(self, parent: Any = None) -> Any:
        """Qt-thread-safe consumer: timer on the Qt thread drains the camera queue.

        Camera-thread ``get_gaze_info()`` is not read on the Qt thread.
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

        self._qt_bridge = GazeSampleBridge()
        return self._qt_bridge

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

    def stop_qt_bridge(self) -> None:
        bridge = self._qt_bridge
        if bridge is not None:
            try:
                bridge.stop()
            except Exception:
                pass
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
