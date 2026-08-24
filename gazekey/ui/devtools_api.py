"""Optional developer-tooling hooks on the product VirtualKeyboard host.

Product code must not import ``tools.*``. Tools entry points install a real
``DevToolsBundle``; the product default path uses ``NullDevTools``.
"""

from __future__ import annotations

from typing import Any, Optional, Protocol


class DevToolsProtocol(Protocol):
    """Minimal surface used by product UI / gaze loop without importing tools."""

    @property
    def runs_dir(self) -> Any: ...

    def benchmark_active(self) -> bool: ...

    def process_benchmark_eye_data(self, eye_data: Any) -> None: ...

    def process_benchmark_gaze_sample(self, sample: Any) -> None: ...

    def update_benchmark_banner_geometry(self) -> None: ...

    def maybe_start_dev_benchmark(self) -> None: ...

    def start_mvp_benchmark(self) -> None: ...

    def layout_exporter(self) -> Any: ...

    def write_calibration_summary(self, **kwargs: Any) -> None: ...

    def on_calibration_artifacts(
        self,
        host: Any,
        *,
        ridge_fit: Any,
        loocv_detail: Any,
        quality: Any,
        ridge_alpha: Any = None,
        **kwargs: Any,
    ) -> None: ...

    def on_calibration_failed_artifacts(self, host: Any, **kwargs: Any) -> None: ...

    def ensure_gaze_preview(self, host: Any) -> Any: ...

    def hide_gaze_preview(self) -> None: ...

    def clear_gaze_preview(self) -> None: ...

    def update_gaze_preview_dot(self, host: Any, **kwargs: Any) -> None: ...

    def resize_gaze_preview(self) -> None: ...


class NullDevTools:
    """No-op tooling so product launch never depends on tools packages."""

    @property
    def runs_dir(self) -> None:
        return None

    def benchmark_active(self) -> bool:
        return False

    def process_benchmark_eye_data(self, eye_data: Any) -> None:
        return None

    def process_benchmark_gaze_sample(self, sample: Any) -> None:
        return None

    def update_benchmark_banner_geometry(self) -> None:
        return None

    def maybe_start_dev_benchmark(self) -> None:
        return None

    def start_mvp_benchmark(self) -> None:
        return None

    def layout_exporter(self) -> Optional[Any]:
        return None

    def write_calibration_summary(self, **kwargs: Any) -> None:
        return None

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
        return None

    def on_calibration_failed_artifacts(self, host: Any, **kwargs: Any) -> None:
        return None

    def ensure_gaze_preview(self, host: Any) -> None:
        return None

    def hide_gaze_preview(self) -> None:
        return None

    def clear_gaze_preview(self) -> None:
        return None

    def update_gaze_preview_dot(self, host: Any, **kwargs: Any) -> None:
        return None

    def resize_gaze_preview(self) -> None:
        return None
