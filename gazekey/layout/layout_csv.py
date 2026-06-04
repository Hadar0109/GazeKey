"""CSV export for keyboard layout geometry."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

from PySide6.QtCore import QRect

from gazekey.layout.layout_inspector import KeyGeometryRow


def _repo_root() -> Path:
    # gazekey/layout/layout_csv.py -> gazekey -> repo root
    return Path(__file__).resolve().parents[2]


def default_layout_csv_path() -> Path:
    return _repo_root() / "keyboard_layout.csv"


def _rect_fields(prefix: str, r: QRect) -> dict:
    return {
        f"{prefix}_x": int(r.x()),
        f"{prefix}_y": int(r.y()),
        f"{prefix}_w": int(r.width()),
        f"{prefix}_h": int(r.height()),
    }


def _layout_version(
    *,
    window_rect: QRect,
    typing_region_rect: QRect,
    keys: List[KeyGeometryRow],
) -> str:
    h = hashlib.sha256()
    h.update(
        f"w={window_rect.x()},{window_rect.y()},{window_rect.width()},{window_rect.height()}".encode(
            "utf-8"
        )
    )
    h.update(
        f"t={typing_region_rect.x()},{typing_region_rect.y()},{typing_region_rect.width()},{typing_region_rect.height()}".encode(
            "utf-8"
        )
    )
    for k in keys:
        h.update(
            f"{k.key_id}|{k.key_action}|{k.key_label}|{k.rect.x()},{k.rect.y()},{k.rect.width()},{k.rect.height()}".encode(
                "utf-8"
            )
        )
    return h.hexdigest()[:16]


class KeyboardLayoutCsvExporter:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or default_layout_csv_path()

    def export(
        self,
        *,
        window_rect: QRect,
        typing_region_rect: QRect,
        keys: List[KeyGeometryRow],
    ) -> str:
        """
        Write `keyboard_layout.csv` (overwrite) and return `layout_version`.
        """
        layout_version = _layout_version(
            window_rect=window_rect,
            typing_region_rect=typing_region_rect,
            keys=keys,
        )
        generated_at = datetime.now(timezone.utc).isoformat()

        self.path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "layout_version",
            "generated_at_iso",
            "window_global_x",
            "window_global_y",
            "window_w",
            "window_h",
            "typing_region_x",
            "typing_region_y",
            "typing_region_w",
            "typing_region_h",
            "key_id",
            "key_label",
            "key_action",
            "row_index",
            "col_index",
            "rect_x",
            "rect_y",
            "rect_w",
            "rect_h",
            "center_x",
            "center_y",
            "hitbox_x0",
            "hitbox_y0",
            "hitbox_x1",
            "hitbox_y1",
            "is_special_key",
            "weight",
        ]

        with open(self.path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for key in keys:
                row = {
                    "layout_version": layout_version,
                    "generated_at_iso": generated_at,
                    "window_global_x": int(window_rect.x()),
                    "window_global_y": int(window_rect.y()),
                    "window_w": int(window_rect.width()),
                    "window_h": int(window_rect.height()),
                    "typing_region_x": int(typing_region_rect.x()),
                    "typing_region_y": int(typing_region_rect.y()),
                    "typing_region_w": int(typing_region_rect.width()),
                    "typing_region_h": int(typing_region_rect.height()),
                    "key_id": key.key_id,
                    "key_label": key.key_label,
                    "key_action": key.key_action,
                    "row_index": int(key.row_index),
                    "col_index": int(key.col_index),
                    "rect_x": int(key.rect.x()),
                    "rect_y": int(key.rect.y()),
                    "rect_w": int(key.rect.width()),
                    "rect_h": int(key.rect.height()),
                    "center_x": float(key.center[0]),
                    "center_y": float(key.center[1]),
                    "hitbox_x0": int(key.hitbox.left()),
                    "hitbox_y0": int(key.hitbox.top()),
                    "hitbox_x1": int(key.hitbox.right()),
                    "hitbox_y1": int(key.hitbox.bottom()),
                    "is_special_key": bool(key.is_special_key),
                    "weight": float(key.weight),
                }
                w.writerow(row)

        return layout_version

