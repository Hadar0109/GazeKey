"""Install developer tooling onto a product VirtualKeyboard (tools → gazekey only)."""

from __future__ import annotations

from typing import Any, Optional

from tools.debug.layout_csv import KeyboardLayoutCsvExporter
from tools.evaluation.benchmark_controller import BenchmarkController
from tools.evaluation.calib_finish_artifacts import CalibFinishArtifacts
from tools.evaluation.run_summary import RunSummaryWriter
from tools.preview.gaze_preview import GazePreviewController


class DevToolsBundle:
    """Real tooling attached by ``python -m tools.evaluation`` / ``tools.preview``."""

    def __init__(
        self,
        host: Any,
        *,
        enable_preview: bool = True,
        enable_benchmark: bool = True,
        runs_dir: Any = None,
    ) -> None:
        self._host = host
        self._writer = RunSummaryWriter(runs_dir=runs_dir) if runs_dir is not None else RunSummaryWriter()
        self._layout_exporter = KeyboardLayoutCsvExporter(runs_dir=self._writer.runs_dir)
        self._artifacts = CalibFinishArtifacts(host, runs_dir=self._writer.runs_dir)
        self._benchmark = BenchmarkController(host) if enable_benchmark else None
        self._preview: GazePreviewController | None = None
        self._enable_preview = enable_preview
        if enable_preview:
            self._preview = GazePreviewController(host.keyboard_widget)

    @property
    def runs_dir(self) -> Any:
        return self._writer.runs_dir

    def benchmark_active(self) -> bool:
        return bool(self._benchmark is not None and self._benchmark.active())

    def process_benchmark_eye_data(self, eye_data: Any) -> None:
        if self._benchmark is not None:
            self._benchmark.process_eye_data(eye_data)

    def process_benchmark_gaze_sample(self, sample: Any) -> None:
        if self._benchmark is not None:
            self._benchmark.process_gaze_sample(sample)

    def update_benchmark_banner_geometry(self) -> None:
        if self._benchmark is not None:
            self._benchmark.update_banner_geometry()

    def maybe_start_dev_benchmark(self) -> None:
        if self._benchmark is not None:
            self._benchmark.maybe_start_dev_benchmark()

    def start_mvp_benchmark(self) -> None:
        if self._benchmark is not None:
            self._benchmark.start_mvp_benchmark()

    def layout_exporter(self) -> Any:
        return self._layout_exporter

    def write_calibration_summary(self, **kwargs: Any) -> None:
        self._artifacts.write_run_summary(self._writer, **kwargs)

    def on_calibration_artifacts(
        self,
        host: Any,
        *,
        ridge_fit: Any,
        loocv_detail: Any,
        quality: Any,
        ridge_alpha: Any = None,
        **kwargs: Any,
    ) -> None:
        del kwargs
        samples = host._calibration_session.get_training_samples() if host._calibration_session else []
        self._artifacts.on_success(
            self._writer,
            ridge_fit=ridge_fit,
            loocv_detail=loocv_detail,
            quality=quality,
            samples=samples,
            ridge_alpha=ridge_alpha,
        )

    def on_calibration_failed_artifacts(self, host: Any, **kwargs: Any) -> None:
        self._artifacts.on_failure(self._writer, **kwargs)

    def ensure_gaze_preview(self, host: Any) -> Optional[GazePreviewController]:
        if not self._enable_preview:
            return None
        if self._preview is None:
            self._preview = GazePreviewController(host.keyboard_widget)
        return self._preview

    def hide_gaze_preview(self) -> None:
        if self._preview is not None:
            self._preview.hide()

    def clear_gaze_preview(self) -> None:
        if self._preview is not None:
            self._preview.clear_gaze()

    def update_gaze_preview_dot(self, host: Any, **kwargs: Any) -> None:
        preview = self.ensure_gaze_preview(host)
        if preview is None:
            return
        screen_x = kwargs.pop("screen_x")
        screen_y = kwargs.pop("screen_y")
        preview.show_gaze(screen_x, screen_y, **kwargs)

    def resize_gaze_preview(self) -> None:
        if self._preview is not None:
            self._preview.resize_to_keyboard()

    def enable_preview_mode(self) -> None:
        """Tools-only: turn on read-only gaze preview after calibration."""
        h = self._host
        h._preview_mode = True
        if hasattr(h, "preview_btn"):
            h.preview_btn.setProperty("active", "true")
            h.preview_btn.style().unpolish(h.preview_btn)
            h.preview_btn.style().polish(h.preview_btn)
            h.preview_btn.update()
        self.ensure_gaze_preview(h)


def install_devtools(
    host: Any,
    *,
    enable_preview: bool = True,
    enable_benchmark: bool = True,
    auto_preview_after_calib: bool = False,
    runs_dir: Any = None,
) -> DevToolsBundle:
    """Attach tools to a product VirtualKeyboard. Call only from tools entries/tests."""
    bundle = DevToolsBundle(
        host,
        enable_preview=enable_preview,
        enable_benchmark=enable_benchmark,
        runs_dir=runs_dir,
    )
    host._devtools = bundle
    # Compatibility aliases used by older helpers / tests
    host._run_summary_writer = bundle._writer
    host._layout_exporter = bundle._layout_exporter
    host._benchmark_controller = bundle._benchmark
    host._gaze_preview = bundle._preview
    host._tools_auto_preview_after_calib = auto_preview_after_calib
    return bundle
