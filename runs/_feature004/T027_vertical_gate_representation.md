# ExperimentRecord — T027

- hypothesis: The blocking vertical calibration check scores `avg_v`, a clamped binocular mean the mapper never consumes, so it rejects sessions whose mapper-relevant Y signal is better than sessions it accepts. Scoring the mapper's own vertical channel instead should let product-condition sessions reach evaluation without admitting genuinely inverted ones.
- logical_area: collection (research R10 — quality / pass-fail gates)
- change: In `gazekey/calibration/quality.py`, the catastrophic and preferred vertical-orientation checks now score `r(screen_y, pca_vL)` instead of `r(screen_y, avg_v)`. Threshold values, blocking semantics, and message routing are unchanged. `avg_v` is still computed and reported as a diagnostic.
- condition: head-support — product condition
- eval_before: 14938da0bdf0 (A), 34fb259ccdfd (B)
- eval_after: 689c8a8ce90c
- decision: **KEEP** (2026-08-20)
- keep_git_sha: **PENDING COMMIT** — required by FR-026 before T020 starts

## Scope of the change (what was and was not touched)

Changed:

- `_paired_corr_with_screen_y(samples, targets, attr)` added; correlates one
  vertical feature against target `screen_y`, paired **by index**.
- The catastrophic (0.15) and preferred (0.55) vertical checks now read
  `pca_vL`. Reason strings changed from `"avg_v poorly correlated..."` to
  `"pca_vL poorly correlated..."`, keeping the word `catastrophic` so
  `_keyboard_blocking_reason` still routes it as blocking.
- `CalibrationQualityResult.screen_y_pca_vL_corr` added (the gated value).
  `screen_y_avg_v_corr` kept with unchanged meaning (diagnostic).
- `gazekey/ui/calibration_finish.py` reports both correlations, gated first.

Deliberately **not** changed:

- Thresholds (`MIN_CATASTROPHIC_SCREEN_Y_AVG_V_CORR = 0.15`,
  `MIN_SCREEN_Y_AVG_V_CORR = 0.55`) — same numbers, new representation.
- Blocking vs warning policy. Nothing was downgraded to a warning; the
  keyboard soft band between 0.15 and 0.55 still warns exactly as before.
- LOOCV, region, train-pixel, and head-drift gates.
- `pca_vR` itself (that is T020), aggregation (T019), metadata (T024/T025).
- Fixation UI: no on-screen metrics added; pass/fail still reported only after
  the session (FR-004, FR-005, SC-009).

Side effect worth recording: the old code built the feature array with a
`None` filter but the target array without one, then guarded on
`ys.size == vs.size`. A single missing `avg_v` therefore skipped the whole
blocking check silently. The replacement pairs by index, so one missing value
drops only its own pair. This was not a separate experiment — it is how the
new metric had to be computed — and it is pinned by
`test_one_missing_vertical_sample_does_not_skip_the_whole_check`.

## Pre-flight validation (offline, before the live session)

Replaying all 16 recorded sessions' per-target means through the **shipped**
`_paired_corr_with_screen_y` and the product threshold:

| | blocked on the Y check |
|---|---:|
| before (`avg_v`) | **7** |
| after (`pca_vL`) | **3** |

Newly passing: `bfb745b0b87e` (+0.625), `2879900a17e0` (+0.459),
`42662808ac84` (+0.199), `05e40e22688f` (+0.160).
Still blocked: `0694c1663623` (+0.012), `3d4be8b6eef7` (+0.075),
`cfdd5f1ea546` (−0.054).

Both confirmed product-condition sessions now clear the Y check, and the
three sessions with absent or inverted vertical signal still fail — so the
check keeps its protective purpose. No previously passing session is newly
blocked. Matches the T026 §3.6 prediction exactly.

`pytest -q`: **215 passed** (4 new tests).

## What this change does NOT claim

- It is **not** an accuracy improvement. It changes what the gate measures,
  nothing in the mapping path. Mapped-key accuracy should be roughly
  unchanged for a session that previously passed.
- Passing the gate remains **necessary, not sufficient**: baselines A and B
  both passed and were not practically typeable (`hadar` 5/5 and 4/5).
- Success for T027 is only that a product-condition session can now **reach
  evaluation**, plus no regression vs A/B for sessions that already passed.
  The accuracy work itself starts at T020.

## Live gate (completed 2026-08-20) — session `689c8a8ce90c`

Decision rule, agreed **in advance** so the outcome could not be rationalised
after the fact:

- **keep** if the session reaches evaluation under the product condition and
  eval slices plus `hadar` are no worse than the worse of A and B.
- **revert** if a session that would have passed the old gate is now blocked,
  or measured accuracy is worse than both baselines.
- **inconclusive** if the session is blocked for an unrelated reason (for
  example `eye_box_h` head drift, which stopped `3d4be8b6eef7`) so the gate
  change is still unmeasured.

### Was the change actually exercised? Yes.

| metric on `689c8a8ce90c` | value | verdict under that gate |
|---|---:|---|
| `r(screen_y, avg_v)` — old gate | **−0.152** | **BLOCK** |
| `r(screen_y, pca_vL)` — new gate | **+0.222** | **PASS** |

The old check would have rejected this session outright — the value is not
marginally under 0.15, it is negative. So the counterfactual is unambiguous:
this session exists as a measurement *because of* the change. It is the **6th**
session captured with the chin/head support and the **first** to reach mapping
evaluation.

Calibration: PASSED, `warning_only`, 19 warnings, LOOCV RMS 104.3 px.

### Result vs both baselines (31 evaluated locations)

| metric | A `14938da0bdf0` | B `34fb259ccdfd` | `689c8a8ce90c` | vs worse-of-A/B |
|---|---:|---:|---:|---|
| mapped-key (focus) | 0% | 10% | **23%** | better |
| median error | 130 px | 107 px | **81 px** | better |
| held-out inside-key | 0% | 8% | **25%** | better |
| editing/control | 0% | 0% | 0% | tie |
| row accuracy | 45% | 35% | 35% | ties B, below A |
| repeatability slice | — | — | 26.7% | — |
| focus stability (held-out) | — | — | 0.304 | — |
| `hadar` wrong focus | 5/5 | 4/5 | **3/5** | better |

`hadar` typed `uaraf`: H→U, A→A, D→R, A→A, R→F.

**Decision: KEEP.** The session reached evaluation under the product
condition, and no slice is worse than the worse baseline (A). Row accuracy
sits below A but ties B, i.e. inside the A–B spread that SC-011 exists to make
visible.

### Attribution limit — the honest reading

T027 changes **only** the quality gate. It does not touch feature extraction,
fixation gating, aggregation, ridge fitting, or prediction. The mapping path in
this session is identical to the one that produced A and B. Therefore:

**The accuracy gains over A/B are NOT an effect of T027.** They are
session-to-session variation. A gate cannot improve a mapper.

The keep is earned by the change doing its single job — making the product
condition measurable — and by nothing regressing. The 23% / 81 px / 3-of-5
figures must never be reported as accuracy produced by this change. By the same
logic the row-accuracy dip vs A is not a regression; it is noise from the same
distribution. Both directions are recorded here so a later experiment cannot
quietly bank either one.

### What this session revealed about the real problem

The vertical axis is the blocker, now quantified on a session we can finally
see:

- Taught Y spans 128–362 px (**234 px**); predicted Y spans 177.8–233.2 px
  (**55 px**). The mapper compresses Y by roughly **4.3x** — it barely moves
  vertically.
- `pca_vL` spans only **0.072** across all 15 targets. There is very little
  vertical dynamic range to fit, which is exactly what a stabilized head
  exposes.
- `median_|dy|/h = 0.862` vs `median_|dx|/w = 0.176`: vertical error is ~5x
  horizontal error relative to key size. Horizontal mapping is roughly usable.
- All three live `hadar` errors were **row** errors with the correct column
  neighbourhood (H↔U, D↔R, R↔F are vertically adjacent).
- `r(X, pca_vR) = −0.901`, consistent with all 16 earlier sessions.

This is a direct, independent confirmation of the T020 hypothesis and of the
Phase 3 ordering: the next lever is the eye-local vertical basis, not
aggregation, layout, or ridge alpha.

### Follow-ups created, not done here

- `keep_git_sha` must be filled in from the commit of this kept state before
  T020 begins (FR-026).
- `Calibrate` mis-hit at 458 px (`dx=+395.7`) remains the largest single error
  and is a coverage/geometry item for Phase 5–6, not this iteration.
- `Space` at 189.8 px (`dy/h = 2.23`) is the worst vertical case and overlaps
  the T023/T024 metadata question.
- Both new run artifacts (`experiment_record.md`, `hadar_wrong_focus.md`) were
  again auto-created from the **Phase A baseline template** and had to be
  corrected by hand. The template default mislabels every new session as a
  baseline capture; worth fixing in `tools/evaluation` as a small separate
  chore so it stops producing wrong records.
