# T061 Baseline Comparison — Two-Run Clean Baseline (T061C)

**Feature**: `001-calibration-mapping-mvp`  
**Date**: 2026-06-10  
**Purpose**: Active tuning reference for Phase 8 (replaces T029 / pre-restart iterations)  
**Flags**: `GAZEKEY_DEV_BENCHMARK=1`, `GAZEKEY_CAMERA_PREVIEW_DURING_CALIB=1`  
**Layout**: `keyboard15` · **Mapper**: `pca4_baseline` · **No code/config changes between runs**

---

## 1. Session identification

| Label | Session ID | Benchmark ID | Artifacts |
|-------|------------|--------------|-----------|
| **T061A (run 1)** | `0ee046a292cf` | `0ee046a292cf-bench1781104684` | `runs/0ee046a292cf/` |
| **T061B (run 2)** | `1b78ad3e50da` | `1b78ad3e50da-bench1781104893` | `runs/1b78ad3e50da/` |

Timestamps: run 1 ~18:17, run 2 ~18:20 (same session, ~3 min apart).

---

## 2. Headline metrics (CQ-1)

| Metric | T061A | T061B | Δ (B−A) | CQ-1 threshold | Status |
|--------|-------|-------|---------|----------------|--------|
| Key-hit | 6/15 (40%) | 6/15 (40%) | 0 pp | ≥ 10/15 (~67%) | **FAIL both** |
| Row accuracy | 9/15 (60%) | 8/15 (53%) | −7 pp | ≥ 80% | **FAIL both** |
| Median error | 58 px | 53 px | −5 px | ≤ 55 px | **FAIL / borderline** |
| Calibration | PASSED | PASSED | — | collection OK | PASS |
| LOOCV RMS (supp.) | 84.4 px | 56.3 px | −28 px | supplementary | varies |
| Ridge α | 1.0 | 1.0 | 0 | frozen | same |
| Quality warnings | 12 | 10 | −2 | supplementary | similar |

**Two-run variance (AR-7)**:

| Metric | Min | Max | Spread |
|--------|-----|-----|--------|
| Key-hit | 40% | 40% | **0 pp** |
| Row accuracy | 53% | 60% | **7 pp** |
| Median error | 53 px | 58 px | **5 px** |

Headline aggregates are **stable** (identical key-hit); **which keys fail swaps** between runs (see §4). SC-004 two-run spread on key-hit is 0 pp; row spread 7 pp.

---

## 3. Per-key benchmark reliability (15-key set)

| Key | T061A | T061B | Hits / 2 | Notes |
|-----|-------|-------|----------|-------|
| Q | ✓ | ✗ | 1/2 | Left top; outside cal hull |
| E | ✗ | ✗ | 0/2 | Top row |
| T | ✗ | ✓ | 1/2 | Top row |
| U | ✓ | ✓ | 2/2 | Reliable |
| P | ✓ | ✗ | 1/2 | Right top; outside cal hull |
| A | ✗ | ✗ | 0/2 | Left home; outside cal hull |
| D | ✗ | ✓ | 1/2 | Home row |
| G | ✗ | ✓ | 1/2 | Home row |
| J | ✗ | ✗ | 0/2 | Home row |
| L | ✗ | ✗ | 0/2 | Right home; outside cal hull |
| Z | ✓ | ✓ | 2/2 | Reliable |
| C | ✓ | ✓ | 2/2 | Reliable |
| B | ✗ | ✗ | 0/2 | Bottom row |
| M | ✗ | ✗ | 0/2 | Right bottom; near hull edge |
| Space | ✓ | ✗ | 1/2 | Outside cal hull |

**Always hit (2/2)**: U, Z, C  
**Never hit (0/2)**: E, A, J, L, B, M  
**Split (1/2)**: Q, T, P, D, G, Space

---

## 4. Per-key dx/dy patterns (failure analysis)

### T061A — `likely_cause: mapping`

| Key | Pred | dx | dy | err |
|-----|------|----|----|-----|
| E | S | +13 | +89 | 89 |
| T | G | +32 | +85 | 91 |
| A | Ctrl | −55 | +111 | 123 |
| D | X | +33 | +44 | 55 |
| G | H | +70 | +11 | 71 |
| J | U | −17 | −37 | 41 |
| L | K | −113 | +18 | 114 |
| B | H | +19 | −37 | 42 |
| M | N | −75 | −12 | 76 |

### T061B — `likely_cause: mapping`

| Key | Pred | dx | dy | err |
|-----|------|----|----|-----|
| Q | Shift | +20 | +98 | 100 |
| E | S | −25 | +33 | 41 |
| P | O | −113 | +2 | 113 |
| A | Z | +122 | +99 | 157 |
| J | U | +9 | −85 | 85 |
| L | K | −101 | −35 | 107 |
| B | U | +32 | −108 | 113 |
| M | J | −72 | −83 | 110 |
| Space | V | +5 | −53 | 53 |

### AR-2 — Regional bias

| Region | Pattern | Evidence |
|--------|---------|----------|
| **Left edge** | Q, A chronic failures; large \|dx\| on A, L | A: dx −55/+122; L: dx −113/−101 |
| **Right edge** | P, L, M failures; P large −dx in B | P: −113 px; L/M right-home row |
| **Top row** | E always miss; T split; +dy common in A | Vertical offset above/below row |
| **Bottom** | B always miss; Space split; B large −dy in B | B: dy −108 |
| **Interior** | U, Z, C stable; G, D split | Hull-covered anchors |

**dx summary**: Left-edge and right-edge benchmark keys show largest horizontal errors.  
**dy summary**: Mixed sign across runs — not a single global Y scale bug; row confusion and edge extrapolation both present.

---

## 5. Coverage (calibration hull) — identical both runs

Source: `runs/<session_id>/coverage.json` (same `keyboard15` geometry).

| Scope | Inside hull | Outside hull |
|-------|-------------|----------------|
| All keys | 22/33 (67%) | 11/33 |
| Letters only | 22/26 (85%) | **4**: q, p, a, l |
| Specials | 0/7 | Shift, Space, Ctrl, Alt, ⌫, ↵, CALIBRATE |

**Benchmark keys outside calibration hull** (extrapolation risk):

| Benchmark key | Letter outside hull? | nearest_anchor_px (letters) |
|---------------|----------------------|----------------------------|
| Q | yes (q) | 127 |
| P | yes (p) | 126 |
| A | yes (a) | 71 |
| L | yes (l) | 71 |
| M | inside | 0 |
| Space | yes (special) | 68 |

Six of fifteen benchmark keys are **outside** the calibration anchor hull (Q, P, A, L, M borderline inside but M fails both runs; Space outside). This aligns with chronic edge-key failures.

---

## 6. AR triage (analysis only)

| ID | Check | Finding |
|----|-------|---------|
| **AR-2** | Regional bias | **Yes** — left/right edge and home-row edges (A, L, P, M) dominate failures; interior U/Z/C stable |
| **AR-5** | Calibration dot vs key position | **Not recorded** in artifacts. Synthetic `runs/geometry_check.txt` PASS. **Recommend** brief live check before geometry tuning |
| **AR-6** | Key centers vs visible keyboard | **Not recorded** in artifacts. No user offset note. **Recommend** confirm dots/highlights on-screen before T034 |
| **AR-7** | Natural variance (2 baselines) | Key-hit **0 pp** spread; row **7 pp**; median **5 px**. Same 6/15 but **different key sets** → session noise affects *which* keys, not headline count |
| **AR-8** | SC-004 evaluator before acceptance? | **Recommend yes** — add small `evaluate_session_repeatability()` + unit test before T063; manual spread OK for now |
| **AR-3** | Fixation gate | **Not triggered** — aggregate metrics stable; no erratic cal pass/fail between runs |
| **AR-4** | Mean vs outliers | **Not triggered** — LOOCV differs (84 vs 56) but both cal PASSED; per-target outlier review deferred |
| **AR-1** | Feature sufficiency | **Deferred** — edge/coverage pattern explains much failure; revisit only if layout/geometry fixes leave interior keys (E, J, B) at 0/2 |

---

## 7. Failure-pattern guide (plan.md)

| Signal | Observation | Suggested lever |
|--------|-------------|---------------|
| Coverage gaps on benchmark keys | 6/15 outside or near hull edge | **T032 layout** |
| Edge dx clusters | Q, P, A, L, M | **T032 layout** or T034 geometry |
| Interior chronic (E, J, B) | 0/2 despite hull coverage | **T035 fit** (after layout) |
| Mixed dy, row 53–60% | Mapping Y not sole issue | Do not jump to T035 first |
| Preview/benchmark alignment unknown | AR-5/6 not logged | Quick live check before T034 |

---

## 8. Phase 8 testing order (confirmed)

1. **Layout / coverage** (T032) — structural hull gap on benchmark edges  
2. **Geometry / hitboxes** (T034) — if live AR-5/6 show misalignment  
3. **Collection** (T033) — if post-layout runs remain erratic on same keys  
4. **PCA4 fit / smoothing / row bias** (T035) — if interior keys still fail after layout+geometry  

---

## 9. T061D — First lever (approved)

**Approved: T032 — layout iteration**

**Selected layout for iteration_01**: `keyboard_full9` (Candidate A in `gazekey/calibration/targets.py`)

**Type**: Existing candidate, **adjusted** — `_band_candidate_rows()` now skips lone utility rows (e.g. CALIBRATE) so all nine anchors land on typing keys instead of three duplicate CALIBRATE fixations.

**Rationale**:

- `coverage.json` shows benchmark keys **Q, P, A, L** (and **Space**) lie **outside** the `keyboard15` calibration hull — same keys that are chronic or split failures.
- Interior anchors (U, Z, C) hit 2/2; failures concentrate on hull-exterior and edge letters.
- Two-run dx/dy shows strong left/right edge error magnitude, consistent with extrapolation beyond anchors — not fixed by a single α/smoothing tweak.
- Headline metrics identical 6/15 — first lever should address **structural coverage**, not fit params.

**Why `keyboard_full9` over `keyboard_wide9` or `keyboard15` tweak**:

| Layout | Letters outside hull | Anchor alignment | Notes |
|--------|---------------------|------------------|-------|
| `keyboard15` | q, p, a, l (4/26) | On key centers | Baseline; hull x 196–1083 misses edges |
| `keyboard_wide9` | none (simulated) | **Off-keyboard** grid | Fixes hull by extrapolation, not fixation on keys (AR-5 risk) |
| `keyboard_full9` | **none** (simulated) | On key centers | q, p, a, g, l, Ctrl, Space, Enter anchors; full width |

**`keyboard_full9` anchor map** (T061B layout snapshot):

| Band | Left | Center | Right | Benchmark keys helped |
|------|------|--------|-------|------------------------|
| Top | q (69,169) | y (702,169) | p (1209,169) | Q, P |
| Mid | a (176,237) | g (639,237) | l (1102,237) | A, L |
| Bottom | Ctrl (77,373) | Space (641,373) | Enter (1132,373) | Space |

**Iteration_01 command** (layout override only; default `keyboard15` unchanged):

```powershell
$env:GAZEKEY_CALIB_MODE = "keyboard_full9"
$env:GAZEKEY_DEV_BENCHMARK = "1"
$env:GAZEKEY_CAMERA_PREVIEW_DURING_CALIB = "1"
python main.py
```

Document results in `runs/iteration_01_layout_keyboard_full9.txt` vs **this T061 baseline set** (§1–§5).

**Not recommended first**:

- **T035** (fit/smoothing/row bias) — edge pattern is coverage-driven; interior-only failures remain for a second cycle.
- **T033** (collection) — session variance low on headline metrics.
- **T034** (geometry) — no artifact evidence of misalignment; quick live AR-5/6 check advised before choosing T034 over T032.

---

## 10. Baseline capability summary

| | Value |
|---|--------|
| **Active comparison reference** | This document + `runs/0ee046a292cf/` + `runs/1b78ad3e50da/` |
| **Typical session** | 6/15 key-hit (40%), 53–60% row, 53–58 px median |
| **CQ-1 pass** | Not met on either run |
| **Stable keys** | U, Z, C |
| **Chronic misses** | E, A, J, L, B, M |

**Historical only (do not compare)**: T029 `baseline_pca4_summary.txt`, `iteration_01–04_*`.

---

## 11. Task status

| Task | Status |
|------|--------|
| T061A | Complete — `0ee046a292cf` |
| T061B | Complete — `1b78ad3e50da` |
| T061C | **Complete** — this document |
| T061D | **Complete** — T032 layout; `keyboard_full9` selected (§9) |
| T062 | Ready — run iteration_01 with `GAZEKEY_CALIB_MODE=keyboard_full9` |
