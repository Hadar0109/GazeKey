# T029 handoff diagnosis (historical; do not treat as a PASS)

**Date**: 2026-08-24  
**Status**: USER GATE **FAIL**. Stage D / dwell / OS typing **not** started.

Later official `pygame_example.py` + keyboard-screenshot reference supersedes
the “GF is already ~200 px off before Qt” reading of
`pre_qt_validation.json`. See **`T029_parity_audit.md`** for the path
comparison and the next experiment (official-sized GREEN ring, no production
fix yet).

This file keeps the earlier BLUE/GREEN and geometry notes as evidence.

**Transform**: **not changed**. Product `GazeSample` still uses the T028-selected
`origin+dpr` conversion. HeuristicFilter, dwell, mapping, and PCA/Ridge/bias
were not changed.

## BLUE/GREEN session (kept)

BLUE (`calibrated`) and GREEN (`filtered`) generally converged after a 1–2 s
hold; both could still settle far from the intended key. Dominant issue on
the keyboard overlay: **spatial**, not HeuristicFilter latency (~110–130 ms,
secondary).

## Spaces (from T028 audit; unchanged)

| Space | Recorded value |
|-------|----------------|
| GazeFollower `screen_size` / pygame | 1920×1080 |
| Qt `QScreen.geometry()` | 1280×720 at (0,0) |
| `devicePixelRatio` | 1.5 |
| Keyboard origin | (0,0) |
| Transform | `origin+dpr` → `qt = gf_px / 1.5` |

## Explicitly not done

- No Stage D, dwell, or OS typing
- No PCA/Ridge, affine, bias, extra smoothing, or mapper
- No change to the approved DPR/geometry transform, calibration protocol,
  HeuristicFilter, camera lifecycle, or dwell

---

## Closeout pointer (2026-08-24)

This file remains historical FAIL evidence (BLUE/GREEN, pre-Qt protocol).
It is **not** a PASS. The parity ladder was later closed as **USER-ACCEPTED
CONTINUATION** with a known 0–1 adjacent-key residual. See
**`T029_parity_audit.md`** section 8. Do not rewrite this diagnosis into a
PASS.
