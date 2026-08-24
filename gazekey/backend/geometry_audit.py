"""Live geometry audit writer (T011 helper + T028 live fill)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from gazekey.backend.geometry import (
    GeometryAudit,
    GeometryConfig,
    TransformKind,
    choose_allowed_transform,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AUDIT_PATH = REPO_ROOT / "runs" / "_feature005" / "geometry_audit.json"


def _rect_tuple(rect: Any) -> tuple[int, int, int, int]:
    return (int(rect.x()), int(rect.y()), int(rect.width()), int(rect.height()))


def collect_pygame_mode() -> tuple[int, int] | None:
    try:
        import pygame

        if not pygame.get_init():
            pygame.init()
        if not pygame.display.get_init():
            pygame.display.init()
        info = pygame.display.Info()
        return (int(info.current_w), int(info.current_h))
    except Exception:
        return None


def collect_screeninfo_size() -> tuple[int, int] | None:
    try:
        from screeninfo import get_monitors

        monitors = get_monitors()
        if not monitors:
            return None
        return (int(monitors[0].width), int(monitors[0].height))
    except Exception:
        return None


def collect_qt_screen_fields() -> dict[str, Any]:
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance()
    if app is None:
        return {
            "qt_geometry": None,
            "device_pixel_ratio": None,
            "monitor_origin": None,
        }
    screen = app.primaryScreen()
    if screen is None:
        return {
            "qt_geometry": None,
            "device_pixel_ratio": None,
            "monitor_origin": None,
        }
    geom = screen.geometry()
    return {
        "qt_geometry": (int(geom.x()), int(geom.y()), int(geom.width()), int(geom.height())),
        "device_pixel_ratio": float(screen.devicePixelRatio()),
        "monitor_origin": (int(geom.x()), int(geom.y())),
    }


def collect_keyboard_fields(keyboard: Any) -> dict[str, Any]:
    from PySide6.QtCore import QPoint, QRect

    origin = keyboard.mapToGlobal(QPoint(0, 0))
    keyboard_origin = (int(origin.x()), int(origin.y()))
    key_rects: dict[str, tuple[int, int, int, int]] = {}
    suggestion_rects: dict[str, tuple[int, int, int, int]] = {}

    for key in getattr(keyboard, "_layout_keys", None) or []:
        key_id = str(getattr(key, "key_id", ""))
        rect = getattr(key, "rect", None)
        if key_id and rect is not None:
            key_rects[key_id] = _rect_tuple(rect)
            if key_id.startswith("suggestion:"):
                suggestion_rects[key_id] = _rect_tuple(rect)

    buttons = getattr(keyboard, "suggestion_buttons", None) or []
    for index, btn in enumerate(buttons):
        slot_id = f"suggestion:{index}"
        if slot_id in suggestion_rects:
            continue
        tl = btn.mapToGlobal(QPoint(0, 0))
        suggestion_rects[slot_id] = _rect_tuple(QRect(tl, btn.size()))
        key_rects.setdefault(slot_id, suggestion_rects[slot_id])

    return {
        "keyboard_origin": keyboard_origin,
        "key_rects": key_rects,
        "suggestion_rects": suggestion_rects,
    }


def build_live_audit(
    *,
    keyboard: Any,
    pygame_mode: tuple[int, int] | None,
    gf_screen_size: tuple[int, int] | None = None,
    geometry: GeometryConfig | None = None,
) -> tuple[GeometryAudit, GeometryConfig]:
    """Fill the T011 schema from the live Qt keyboard plus recorded pygame/GF size."""
    qt = collect_qt_screen_fields()
    kb = collect_keyboard_fields(keyboard)
    screeninfo_size = collect_screeninfo_size()
    if pygame_mode is None:
        pygame_mode = collect_pygame_mode()
    origin = qt["monitor_origin"] or (0, 0)
    dpr = float(qt["device_pixel_ratio"] or 1.0)
    if geometry is None:
        transform: TransformKind = choose_allowed_transform(
            origin_offset=(float(origin[0]), float(origin[1])),
            dpr=dpr,
        )
        geometry = GeometryConfig(
            transform=transform,
            origin_offset=(float(origin[0]), float(origin[1])),
            dpr=dpr,
        )
    audit = GeometryAudit(
        gf_screen_size=gf_screen_size or screeninfo_size,
        pygame_mode=pygame_mode,
        qt_geometry=qt["qt_geometry"],
        device_pixel_ratio=qt["device_pixel_ratio"],
        monitor_origin=qt["monitor_origin"],
        keyboard_origin=kb["keyboard_origin"],
        transform=geometry.transform,
        key_rects=kb["key_rects"],
        suggestion_rects=kb["suggestion_rects"],
    )
    return audit, geometry


def audit_to_dict(audit: GeometryAudit) -> dict[str, Any]:
    return {
        "gf_screen_size": list(audit.gf_screen_size) if audit.gf_screen_size else None,
        "pygame_mode": list(audit.pygame_mode) if audit.pygame_mode else None,
        "qt_geometry": list(audit.qt_geometry) if audit.qt_geometry else None,
        "device_pixel_ratio": audit.device_pixel_ratio,
        "monitor_origin": list(audit.monitor_origin) if audit.monitor_origin else None,
        "keyboard_origin": list(audit.keyboard_origin)
        if audit.keyboard_origin
        else None,
        "transform": audit.transform,
        "key_rects": {k: list(v) for k, v in dict(audit.key_rects).items()},
        "suggestion_rects": {
            k: list(v) for k, v in dict(audit.suggestion_rects).items()
        },
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "notes": (
            "Allowed transform is identity | origin | origin+dpr only. "
            "T012 STOP if a later live audit cannot align with these. "
            "T029 USER GATE still confirms official filtered gaze vs these QRects."
        ),
    }


def write_geometry_audit(
    audit: GeometryAudit,
    path: Path | None = None,
    extra: Mapping[str, Any] | None = None,
) -> Path:
    dest = path if path is not None else DEFAULT_AUDIT_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = audit_to_dict(audit)
    if extra:
        payload.update(dict(extra))
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return dest
