# Contract: Mapping Evaluation (developer-only)

**Version**: 1.0.0  
**Feature**: `004-gaze-mapping-accuracy`

## Purpose

Measure whether **mapped gaze identifies the intended key** (focus), including
locations that were not calibration coordinates. Used only during development.

## Isolation (MUST)

Evaluation MUST NOT participate in:

- calibration accept/reject or target advance
- mapper fitting or clip-bound selection
- runtime predict / clamp / bias
- key hit-test used for dwell
- dwell timing or fire
- enabling/disabling typing
- `python main.py` normal product execution

Product MUST run with evaluation unused (SC-008). Implementation stays under
`tools/evaluation/` (and tests of that package).

## Runtime fidelity (MUST)

The evaluation predict + hit-test path SHOULD match product typing:

| Step | Product | Evaluation |
|------|---------|------------|
| Features | `FeatureExtractor.from_eye_data` | same |
| Predict | `MapperRuntime.key_accuracy_predict_screen_xy` (or the helper typing actually calls) | same helper |
| Geometry | `_layout_keys` from `inspect_keyboard_layout` | same snapshot as typing |
| Hit-test | `hit_test_layout_keys` | same function |

Any remaining difference (e.g. collect-window statistics vs continuous typing
EMA state) MUST be written in `fidelity_notes` on the run summary.

**Clip/clamp diagnostic (research R7):** evaluation SHOULD also record
unclamped vs clamped `(x,y)` hit-test for the same frames when a raw
prediction would fall outside clip bounds. That column is **diagnostic
only** — it MUST NOT change product clamp, clip-bound selection, or dwell.
Use it to confirm or reject the hypothesis that clamp pins edge keys.

## Slices

1. **Repeatability** — look at current calibration target positions
2. **Held-out letters** — letter keys whose centers are **not** those
   positions (default set: research R3; recompute if layout changes)
3. **Editing / control** — Shift, Backspace, Space, Enter, Calibrate
   (research R3; do not double-count a key that is already a calib target
   in the primary rate)

**Out of 004 mapped-key accept:** Feature 003 suggestion / prediction-bar
keys (preservation / SC-010 only).

Do not treat a run as mapping success from slice 1 alone (SC-005). Held-out
inside-key + focus stability are the operational FR-007 measures; do not
add a separate feature-space metrics framework.

## Per-location procedure

## Per-location procedure

1. Highlight the intended **key** (not a calibration-style quality overlay
   on the product keyboard during normal typing; evaluation UI is tools-only).
2. Settle, then collect frames (existing settle/collect timing MAY be reused).
3. Each frame: extract → predict → `hit_test_layout_keys`.
4. Record:
   - `inside_tight`: representative point (median x/y of collect window)
     inside intended tight rect (**primary correctness**; snap does not count)
   - `focus_stability`: fraction of collect frames whose hit-test key is
     intended
   - `dx`, `dy`, `error_px` to intended center
   - `dx_over_width`, `dy_over_height`
   - `row_correct`
   - optional dwell activation id (secondary)

## Aggregates

| Metric | Role |
|--------|------|
| Held-out inside-key rate | Primary 004 comparison vs baseline A and B |
| Editing/control inside-key rate | Required prediction-domain coverage (FR-023) |
| Repeatability inside-key rate | Secondary (calibration recall) |
| Mean focus stability (held-out) | Flicker / live-typing relevance |
| Median error_px | Reference floor SC-002 only |
| Median \|dx\|/width, \|dy\|/height | Key-relative (FR-033) |
| Row accuracy | Reference floor SC-003 |

Historical 67% / 55 px / 80% row are **reference floors**, not automatic
Feature 004 final accept.

## Baseline

`CurrentStateBaseline` is **two** runs (A and B) after evaluation-fidelity
work, with **no** mapping/collection code changes. Later experiments MUST
cite **both** (or the last **keep** run). Missing either session blocks
accuracy code changes (FR-028).

The **3-session** SC-004 protocol is a **final** check on the kept stack.
It is not a substitute for A and B.

## Pass/fail output

## Pass/fail output

One short summary: slices, primary rates, median errors, vs-baseline delta,
`fidelity_notes`. Verbose logs optional (`--verbose`).
