# T017 investigation — Y-gate blocks, head pose, vertical signal

**Date**: 2026-08-20  
**Product code**: unchanged during this write-up  
**Decision**: INCONCLUSIVE (see `T017_4d_fixation_gate.md`)  
**Head-stabilization hypothesis**: plausible but unproven

Sources: `calibration_debug.csv` + `calibration_v2.json` for the sessions below
(gitignored per-session files; summaries are tracked). No per-frame fixation
logs exist, so lock timing and 4-D reset counts cannot be recovered.

## Sessions

| Label | Session | Gate | `corr(Y, avg_v)` | LOOCV RMS | face_y mean | eye_box_h span |
|---|---|---|---:|---:|---:|---:|
| Baseline A | `14938da0bdf0` | warning_only **pass** | +0.176 | 89.4 | 0.504 | 0.0030 |
| Baseline B | `34fb259ccdfd` | warning_only **pass** | +0.297 | 95.2 | 0.507 | 0.0024 |
| Pre-T017 Y-fail | `05e40e22688f` | blocking | −0.119 | 115.0 | 0.504 | 0.0034 |
| Pre-T017 eye_h | `0110e1359bd7` | blocking (eye_box_h) | +0.316 | 88.4 | 0.506 | **0.0041** |
| T017-1 | `0694c1663623` | blocking | −0.365 | 97.2 | **0.545** | 0.0036 |
| T017-2 | `42662808ac84` | blocking | +0.024 | 110.8 | **0.545** | 0.0024 |
| T017-3 | `cfdd5f1ea546` | blocking | −0.150 | 96.1 | 0.497 | 0.0034 |

Catastrophic threshold is **0.15**. Preferred (warning) is **0.55**. A and B
passed by a thin margin and would still be `warning_only`. Same-evening
pre-T017 already had this exact Y-block (`05e40e22688f`).

All listed sessions collected **15/15** targets. Accepted frames per target
are ~40–42 (~30 fps × 1.4 s collect window) on T017 and on A/B. T017 did not
starve collection. `05e40e22688f` is the outlier (two targets at 56 and 60).

## 1. Can small head movement affect eye-relative features?

**Yes, technically, even though u/v are computed in an eye-local basis.**

`FeatureExtractor._eye_uv_one_eye` places the iris in a corner-defined frame
and **normalizes v by eyelid aperture**. Head pitch, camera distance, and lid
opening therefore leak into `pca_vL` / `pca_vR` / `avg_v`. `face_x` / `face_y`
are iris midpoints in the camera frame (not eye-relative). `eye_box_h` is the
contour bbox height.

Observed in **every** session, including the three T017 attempts:

- `corr(screen_y, face_y)` = +0.81 … +0.99 — face still tracks target Y
- `corr(screen_y, eye_box_h)` = −0.81 … −0.96 — lower keys, smaller apparent opening
- `eye_box_h` span is **not** smaller under claimed chin-rest (T017-1 0.0036,
  T017-3 0.0034 vs A 0.0030 / B 0.0024)

The mapper **does not** fit `face_y` or `eye_box_h`. Head motion can help Y
mapping only if it **leaks into v**. That leak is plausible: pitch moves the
iris in the palpebral fissure and changes the aperture used to normalize v.

The session blocked for head drift (`0110e1359bd7`, eye_box_h span 0.0041)
had the **strongest** `corr(Y, avg_v)` of the pre-T017 set (+0.316) and
`corr(Y, pca_v)` +0.453. That is consistent with “more head/lid geometry
change → more apparent vertical signal,” not proof.

## 2. Did previous runs unintentionally benefit from small head motion?

**Plausible.** A/B only just cleared 0.15. Removing a Y-correlated head cue
could drop a later session below the knife-edge without any mapping-code
change. It is **not proven**: the same Y-block happened pre-T017 without the
4-D gate (`05e40e22688f`), and T017-3 failed with baseline-like `face_y`
(0.497), not the 0.545 cluster of T017-1/2.

## 3. Is the true iris-only vertical signal weaker than assumed?

**Supported, independent of chin-rest.** Across passing and failing sessions:

- Within-row `avg_v` span (0.03–0.11) **exceeds** top-vs-bottom row-mean
  separation (0.002–0.024). Horizontal look moves v more than row changes.
- `MIN_AVG_V_ROW_SEPARATION` is 0.025; **no** session here meets it
  (keyboard mode: warning, not blocking).
- Fitted `pred_y` span is 45–105 px vs taught Y span **234 px** (Q→Space).
  Vertical compression is already in the **training** predictions.
- Mapper `w_y` sign is unstable (A/B positive; T017-1 both negative; T017-3 mixed).

Keyboard15 Y range is large enough as a **screen** domain. It is not large
relative to vertical **feature** noise once X-contamination is included.

## 4. Can the physical support change camera/eye geometry?

**Plausible for T017-1 and T017-2; not for T017-3 as a single cluster.**

T017-1/2: `face_y` mean 0.545 vs A/B 0.504–0.507 (head ~4% of frame lower in
the image). T017-1 also has larger `eye_box_h` (0.025 vs ~0.021) and higher
mean `avg_v`. That matches closer/more downward pose or a different camera
angle — chin rest, or sitting differently that evening.

T017-3: `face_y` 0.497 (baseline-like / slightly higher in the image), still
blocked on the same Y-gate. A single “chin rest on / off” label cannot
explain all three failures.

Chin rest did **not** freeze pose: Y-correlated `face_y` and `eye_box_h`
remain.

## 5. Horizontal gaze contaminates vertical measurements

This is the dominant structure, **all seven sessions**:

| Session | corr(X, pca_vR) | corr(X, pca_vL) | corr(X, avg_v) | corr(Y, avg_v) |
|---|---:|---:|---:|---:|
| A | −0.907 | +0.415 | −0.328 | +0.176 |
| B | −0.906 | +0.725 | +0.519 | +0.297 |
| 05e40e | −0.934 | +0.013 | −0.674 | −0.119 |
| 0110 | −0.779 | +0.771 | +0.766 | +0.316 |
| T017-1 | −0.933 | +0.814 | −0.438 | −0.365 |
| T017-2 | −0.930 | +0.526 | −0.631 | +0.024 |
| T017-3 | −0.828 | −0.327 | −0.730 | −0.150 |

`pca_vR` tracks **screen X**, not Y. `corr(uR, vR)` is +0.78 … +0.94.
`avg_v` averages left and right, so opposite X-slopes partly cancel and the
leftover vs Y is a coin flip around the 0.15 threshold.

After regressing `pca_v` on screen X, residual vs Y is +0.55 (A) / +0.50 (B)
and still weak or negative on the T017 blocks. Horizontal contamination is
real; it does not hide a strong residual Y signal.

## 6. The blocking gate does not validate the mapper’s Y representation

- Mapper Y uses unclamped `(pca_vL, pca_vR)`.
- The catastrophic check uses `avg_v` = mean of **clamped** `0.5+v` in [0, 1].
- On A/B, right-eye `0.5+pca_vR` is negative on **9/15 and 13/15** targets
  (`Rv` saturates at 0). T017-3 had **0/15** saturations (higher mean v) and
  still failed — clamping is a defect of the proxy, not the only failure mode.
- A/B `corr(Y, pca_v)` is only modestly higher than `corr(Y, avg_v)` (A:
  0.277 vs 0.176). Switching the gate to pca_v would not have saved T017-1
  (−0.355) or T017-3 (−0.148).

LOOCV on the blocked T017 runs (96–111 px) is in the same band as A/B
(89–95). The Y-gate is neither necessary nor sufficient for mapped-key
quality (A/B passed it and still had 0–10% inside-key / 4–5/5 `hadar` wrong
focus). This is input to **T026** (finding only; no policy change in that
task).

## 7. T017 collection behavior

- Sample counts match A/B (~42). No evidence the 4-D gate prevented lock.
- No per-frame dump: cannot see extra `jump_pca` / `unstable` resets.
- Horizontal `u` spans remain healthy (~0.17–0.22); `corr(X, uL/uR)` ≈ −0.99.
  T017 did not destroy the X channel.
- Predicted X span still matches the keyboard; predicted Y does not. Same
  pattern as baseline, sometimes worse (T017-2/3 pred_y span ~45 px).

T017 is **not implicated** as the cause of these three blocks. It is also
**not measured** against held-out / `hadar`, so it cannot be KEEP.

## Smallest diagnostic (no product change)

Four calibrations, **one code state**, same `keyboard15` protocol, verbose
calib if possible so row tables hit the log:

1. Two sessions **without** chin/head support (match A/B conditions).
2. Two sessions **with** the support, same seat/camera distance as (1) aside
   from the rest.

Record for each: session id, rest on/off, `corr(Y, avg_v)`, `corr(Y, pca_v)`,
`corr(X, pca_vR)`, face_y mean/span, eye_box_h span, pass/block reason.

Interpretation:

- Rest-off passes Y-gate, rest-on fails → head-stabilization **supported**.
- Both fail at similar rates → session lottery / weak v; rest **not** the cause.
- Rest-off still fails more than the baseline evening (2/4 usable) → T017
  or another evening confound still in play; then consider revert of the
  4-D gate as isolation, not as a proven harm.

Do not combine this with T019 aggregation, T027 gate-policy, or a mapper lever.
