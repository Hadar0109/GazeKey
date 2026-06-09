"""Verify layout_inspector geometry against key_hit_tester tight rects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from PySide6.QtWidgets import QWidget

from gazekey.layout.layout_inspector import KeyGeometryRow, inspect_keyboard_layout
from gazekey.typing.key_hit_tester import KeyHitTester


@dataclass(frozen=True)
class GeometryMismatch:
    key_id: str
    field: str
    layout_value: str
    tester_value: str


def verify_keyboard_geometry(
    root: QWidget,
    *,
    hitbox_margin_px: int = 6,
) -> tuple[List[KeyGeometryRow], List[GeometryMismatch]]:
    """
    Compare layout_inspector snapshot to KeyHitTester regions on the same widget tree.
    """
    layout_keys = inspect_keyboard_layout(root, hitbox_margin_px=hitbox_margin_px)
    tester = KeyHitTester(root)
    tester.refresh()
    regions = tester.regions

    by_button = {id(r.button): r for r in layout_keys}
    mismatches: List[GeometryMismatch] = []

    for region in regions:
        row = by_button.get(id(region.button))
        if row is None:
            mismatches.append(
                GeometryMismatch(
                    key_id="?",
                    field="missing_layout_row",
                    layout_value="absent",
                    tester_value=str(region.tight_rect),
                )
            )
            continue
        if row.rect != region.tight_rect:
            mismatches.append(
                GeometryMismatch(
                    key_id=row.key_id,
                    field="tight_rect",
                    layout_value=str(row.rect),
                    tester_value=str(region.tight_rect),
                )
            )
        expected_hitbox = row.rect.adjusted(
            -hitbox_margin_px,
            -hitbox_margin_px,
            hitbox_margin_px,
            hitbox_margin_px,
        )
        if row.hitbox != expected_hitbox:
            mismatches.append(
                GeometryMismatch(
                    key_id=row.key_id,
                    field="hitbox_margin",
                    layout_value=str(row.hitbox),
                    tester_value=str(expected_hitbox),
                )
            )

    return layout_keys, mismatches


def format_geometry_report(
    layout_keys: Sequence[KeyGeometryRow],
    mismatches: Sequence[GeometryMismatch],
) -> str:
    lines = [
        "geometry_check",
        f"keys_inspected: {len(layout_keys)}",
        f"mismatches: {len(mismatches)}",
    ]
    if mismatches:
        lines.append("details:")
        for m in mismatches:
            lines.append(f"  {m.key_id} {m.field}: layout={m.layout_value} tester={m.tester_value}")
    else:
        lines.append("status: layout_inspector tight rects align with KeyHitTester")
        lines.append(
            "note: benchmark hit-test uses KeyHitTester tight/snap (margin=4px); "
            "layout_inspector hitbox (margin=6px) is for intent scoring only"
        )
        lines.append(
            "manual: before T029 baseline, verify live VirtualKeyboard key alignment on-screen"
        )
    return "\n".join(lines) + "\n"
