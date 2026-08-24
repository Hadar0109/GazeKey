"""Read-only pygame.quit → Qt display/DPI probe (T029 parity ladder Step D).

Never re-inits pygame or its display module. Does not change
lifecycle.geometry, origin+dpr, camera order, or the debug overlay.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROBE_PATH = REPO_ROOT / "runs" / "_feature005" / "pygame_qt_dpi_probe.json"

PHASE_AFTER_CALIBRATE = "after_calibrate"
PHASE_AFTER_PYGAME_QUIT = "after_pygame_quit"
PHASE_AFTER_START_SAMPLING = "after_start_sampling"
PHASE_AFTER_QT_KEYBOARD = "after_qt_keyboard"

_DPI_AWARENESS_NAMES = {
    0: "PROCESS_DPI_UNAWARE",
    1: "PROCESS_SYSTEM_DPI_AWARE",
    2: "PROCESS_PER_MONITOR_DPI_AWARE",
}


def snapshot_pygame() -> dict[str, Any]:
    """Read pygame state only if already initialized. Do not init."""
    result: dict[str, Any] = {
        "pygame_init": None,
        "display_init": None,
        "display_info": None,
    }
    try:
        import pygame
    except Exception:
        return result
    try:
        result["pygame_init"] = bool(pygame.get_init())
    except Exception:
        result["pygame_init"] = None
    try:
        result["display_init"] = bool(pygame.display.get_init())
    except Exception:
        result["display_init"] = None
    if result["display_init"]:
        try:
            info = pygame.display.Info()
            result["display_info"] = {
                "current_w": int(info.current_w),
                "current_h": int(info.current_h),
            }
        except Exception:
            result["display_info"] = None
    return result


def snapshot_screeninfo() -> dict[str, Any] | None:
    try:
        from screeninfo import get_monitors

        monitors = get_monitors()
        if not monitors:
            return None
        monitor = monitors[0]
        return {
            "width": int(monitor.width),
            "height": int(monitor.height),
            "x": int(getattr(monitor, "x", 0) or 0),
            "y": int(getattr(monitor, "y", 0) or 0),
        }
    except Exception:
        return None


def snapshot_win32() -> dict[str, Any]:
    out: dict[str, Any] = {
        "SM_CXSCREEN": None,
        "SM_CYSCREEN": None,
        "dpi_awareness": None,
        "dpi_awareness_name": None,
        "dpi_for_system": None,
        "monitor_effective_dpi": None,
    }
    try:
        import ctypes

        user32 = ctypes.windll.user32
        out["SM_CXSCREEN"] = int(user32.GetSystemMetrics(0))
        out["SM_CYSCREEN"] = int(user32.GetSystemMetrics(1))
    except Exception:
        pass
    try:
        import ctypes

        awareness = ctypes.c_int()
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        ctypes.windll.shcore.GetProcessDpiAwareness(handle, ctypes.byref(awareness))
        value = int(awareness.value)
        out["dpi_awareness"] = value
        out["dpi_awareness_name"] = _DPI_AWARENESS_NAMES.get(value, str(value))
    except Exception:
        pass
    try:
        import ctypes

        out["dpi_for_system"] = int(ctypes.windll.user32.GetDpiForSystem())
    except Exception:
        pass
    try:
        import ctypes

        class _Point(ctypes.Structure):
            _fields_ = (("x", ctypes.c_long), ("y", ctypes.c_long))

        dpi_x = ctypes.c_uint()
        dpi_y = ctypes.c_uint()
        monitor = ctypes.windll.user32.MonitorFromPoint(_Point(0, 0), 1)
        ctypes.windll.shcore.GetDpiForMonitor(
            monitor, 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y)
        )
        out["monitor_effective_dpi"] = {
            "x": int(dpi_x.value),
            "y": int(dpi_y.value),
        }
    except Exception:
        pass
    return out


def snapshot_qt() -> dict[str, Any] | None:
    try:
        from PySide6.QtGui import QGuiApplication
    except Exception:
        return None
    app = QGuiApplication.instance()
    if app is None:
        return None
    screen = app.primaryScreen()
    if screen is None:
        return None
    geom = screen.geometry()
    available = screen.availableGeometry()
    return {
        "geometry": (
            int(geom.x()),
            int(geom.y()),
            int(geom.width()),
            int(geom.height()),
        ),
        "available_geometry": (
            int(available.x()),
            int(available.y()),
            int(available.width()),
            int(available.height()),
        ),
        "device_pixel_ratio": float(screen.devicePixelRatio()),
        "logical_dpi": float(screen.logicalDotsPerInch()),
        "physical_dpi": float(screen.physicalDotsPerInch()),
    }


def snapshot_gf_sizes(lifecycle: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "lifecycle_gf_screen_size": None,
        "lifecycle_pygame_mode": None,
        "gf_screen_size": None,
        "config_screen_size": None,
        "geometry_transform": None,
        "geometry_dpr": None,
    }
    size = getattr(lifecycle, "gf_screen_size", None)
    if size is not None:
        try:
            result["lifecycle_gf_screen_size"] = [int(size[0]), int(size[1])]
        except Exception:
            pass
    mode = getattr(lifecycle, "pygame_mode", None)
    if mode is not None:
        try:
            result["lifecycle_pygame_mode"] = [int(mode[0]), int(mode[1])]
        except Exception:
            pass
    gf = getattr(lifecycle, "gf", None)
    if gf is None:
        gf = getattr(lifecycle, "_gf", None)
    if gf is not None:
        gf_size = getattr(gf, "screen_size", None)
        if gf_size is not None:
            try:
                result["gf_screen_size"] = [int(gf_size[0]), int(gf_size[1])]
            except Exception:
                pass
        config = getattr(gf, "config", None)
        cfg_size = getattr(config, "screen_size", None) if config is not None else None
        if cfg_size is not None:
            try:
                result["config_screen_size"] = [int(cfg_size[0]), int(cfg_size[1])]
            except Exception:
                pass
    geometry = getattr(lifecycle, "geometry", None)
    if geometry is not None:
        result["geometry_transform"] = getattr(geometry, "transform", None)
        result["geometry_dpr"] = getattr(geometry, "dpr", None)
    return result


def take_snapshot(
    phase: str,
    lifecycle: Any,
    *,
    include_qt: bool = False,
) -> dict[str, Any]:
    snapshot = {
        "phase": phase,
        "pygame": snapshot_pygame(),
        "screeninfo": snapshot_screeninfo(),
        "win32": snapshot_win32(),
        "qt": snapshot_qt() if include_qt else None,
    }
    snapshot.update(snapshot_gf_sizes(lifecycle))
    return snapshot


class DisplayProbe:
    """Accumulate four lifecycle snapshots and write one JSON file."""

    def __init__(self) -> None:
        self.phases: list[dict[str, Any]] = []

    def capture(
        self,
        phase: str,
        lifecycle: Any,
        *,
        include_qt: bool = False,
    ) -> dict[str, Any]:
        snapshot = take_snapshot(phase, lifecycle, include_qt=include_qt)
        self.phases.append(snapshot)
        return snapshot

    def write(self, path: Path | None = None) -> Path:
        dest = path if path is not None else DEFAULT_PROBE_PATH
        dest.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "notes": (
                "Read-only display/DPI probe. Never re-inits pygame. "
                "Does not change origin+dpr, camera order, or overlay. "
                "Compare screeninfo / Win32 / gf.screen_size / DPI awareness "
                "across after_calibrate, after_pygame_quit, after_start_sampling, "
                "and after_qt_keyboard."
            ),
            "phases": self.phases,
        }
        dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return dest
