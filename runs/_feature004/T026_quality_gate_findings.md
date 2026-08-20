# T026 — Calibration quality / pass-fail gate findings (evidence only)

**Date**: 2026-08-20
**Task**: T026 (research R10). **No product change in this task.** The single
change it authorizes is scoped in T027.
**Code state**: post-T059 (T017 4-D gate reverted; tree matches `bedfb86^`)
**Data**: all 16 sessions with `calibration_debug.csv` under `runs/`
**Product condition**: chin/head support (spec Clarifications 2026-08-20)

---

## 1. What the gate does today

`evaluate_calibration_quality` in `gazekey/calibration/quality.py` collects
`reasons`, then on keyboard layouts filters them through
`_keyboard_blocking_reason`, moving everything else to `warnings`:

```python
def _keyboard_blocking_reason(reason: str) -> bool:
    lower = reason.lower()
    if "predict returned none" in lower:  return True
    if "catastrophic" in lower:           return True
    if "head drift:" in lower and "eye_box" in lower: return True
    return False
```

Blocking is decided by **substring matching on the human-readable message**.
Product thresholds come from `gazekey/mapping/config.py`
(`MIN_CATASTROPHIC_SCREEN_Y_AVG_V_CORR = 0.15`,
`MIN_SCREEN_Y_AVG_V_CORR = 0.55`) and `mapper_runtime.py` does not override
`require_any_vertical_monotonic`, so it stays `True`.

### The inversion, stated as a table

Every vertical-signal check in the file, and whether it can stop a session:

| Check | Reads | Keyboard mode |
|---|---|---|
| `corr(screen_y, avg_v) < 0.15` | `avg_v` (derived) | **BLOCKING** |
| `corr(screen_y, avg_v) < 0.55` | `avg_v` (derived) | warning |
| `require_any_vertical_monotonic` | `pca_v`, `pca_vL`, `pca_vR` | warning |
| `min_avg_v_row_separation` (0.025) | `avg_v` | warning |
| `check_within_row_vertical_spread` | `pca_v` **and** `avg_v` spans | warning |
| `avg_v` / `pca_v` span across targets | both | fullscreen only |

**Exactly one vertical check can block a keyboard session, and it is the one
that reads the derived signal.** Every check that reads the mapper's own
`pca_vL` / `pca_vR` is warning-only — including
`"no pca_v / pca_vL / pca_vR row monotonicity (vertical gaze signal weak)"`,
which is appended to `reasons` and then demoted because its message does not
contain the word `catastrophic`.

Meanwhile `gazekey/mapping/ridge.py` fits Y from `(pca_vL, pca_vR)`. The gate
blocks on a quantity the mapper never consumes.

## 2. What `avg_v` actually is

From `gazekey/features/extractor.py`:

```python
Lv = clamp(0.5 + pca_vL, 0.0, 1.0)
Rv = clamp(0.5 + pca_vR, 0.0, 1.0)
avg_v = mean(Lv, Rv)
```

Reconstructing `avg_v` from the stored per-target `pca_vL` / `pca_vR` with this
formula matches the recorded `mean_avg_v` to a mean absolute residual of
**≤ 0.0003** (max 0.0025) in all 16 sessions, so the derivation is confirmed,
not assumed.

Two mechanisms degrade it, and they compound:

**(a) The clamp saturates the right eye on a target-dependent subset.**
`pca_vR` is frequently below −0.5, so `Rv` pins to exactly 0:

| Session | targets with `pca_vR` ≤ −0.5 |
|---|---|
| `0110e1359bd7` | 14/15 |
| `34fb259ccdfd` (baseline B) | 13/15 |
| `bfb745b0b87e` (support) | 10/15 |
| `0ee046a292cf`, `1b78ad3e50da` | 11/15 |
| `14938da0bdf0` (baseline A) | 9/15 |
| `2879900a17e0` (support) | 9/15 |
| `05e40e22688f`, `0694c1663623` | 9/15 |
| `f2dab57719b6` | 7/15 |
| `42662808ac84`, `702386ab2ea4` | 6/15 |
| `e3488095862f` | 4/15 |
| `14fe126cb238` | 3/15 |
| `3d4be8b6eef7`, `cfdd5f1ea546` | 0/15 |

On a saturated target `avg_v = 0.5 · Lv` exactly; on an unsaturated one
`avg_v = 0.5 · (Lv + Rv)`. So **within a single session the formula silently
changes between targets**, and which targets are affected depends on eye
geometry rather than on screen Y. A correlation against screen Y computed over
that mixture is measuring a piecewise function, not a gaze signal.

**(b) Where `pca_vR` is not saturated, it tracks screen X, not Y.**
`r(screen_x, pca_vR)` is strongly negative in **all 16 sessions**, from −0.779
to −0.974. So the unsaturated contribution injects horizontal structure into a
vertical check. (This is the T020 defect; it is named here only to explain the
gate, and is not fixed by T027.)

## 3. Per-session evidence

`r(Y, ·)` = Pearson correlation of the 15 per-target training means against
target `screen_y`. `mdlY` = the fitted model's `predicted_y`.

| Session | gate | result | warn | LOOCV | r(Y,avg_v) | r(Y,vL) | r(X,vR) | r(Y,mdlY) |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `e3488095862f` | warning_only | PASS | 4 | 45.7 | +0.699 | +0.984 | −0.816 | +0.984 |
| `1b78ad3e50da` | — | PASS | 10 | 56.3 | +0.667 | +0.854 | −0.850 | +0.885 |
| `0ee046a292cf` | — | PASS | 12 | 84.4 | +0.633 | +0.813 | −0.897 | +0.846 |
| `702386ab2ea4` | — | PASS | 5 | 51.7 | +0.548 | +0.852 | −0.889 | +0.869 |
| `f2dab57719b6` | — | PASS | 16 | 90.7 | +0.466 | +0.756 | −0.941 | +0.806 |
| `14fe126cb238` | — | PASS | 8 | 55.6 | +0.405 | +0.651 | −0.915 | +0.813 |
| `0110e1359bd7` | blocking | FAIL | 14 | 88.4 | +0.316 | +0.320 | −0.779 | +0.499 |
| `34fb259ccdfd` **B** | warning_only | PASS | 16 | 95.2 | +0.297 | +0.344 | −0.906 | +0.449 |
| `14938da0bdf0` **A** | warning_only | PASS | 14 | 89.4 | +0.176 | +0.357 | −0.907 | +0.410 |
| `bfb745b0b87e` **support** | blocking | FAIL | 13 | 81.5 | **+0.142** | **+0.625** | −0.939 | **+0.626** |
| `42662808ac84` | blocking | FAIL | 17 | 110.8 | +0.024 | +0.199 | −0.930 | +0.217 |
| `2879900a17e0` **support** | blocking | FAIL | 12 | 86.6 | **+0.019** | **+0.459** | −0.967 | **+0.565** |
| `3d4be8b6eef7` | blocking | FAIL | 17 | 96.8 | −0.080 | +0.075 | −0.974 | +0.405 |
| `05e40e22688f` | blocking | FAIL | 17 | 115.0 | −0.119 | +0.160 | −0.934 | +0.198 |
| `cfdd5f1ea546` | blocking | FAIL | 18 | 96.1 | −0.150 | −0.054 | −0.828 | +0.213 |
| `0694c1663623` | blocking | FAIL | 16 | 97.2 | −0.365 | +0.012 | −0.933 | +0.375 |

Blocking reasons on the eight failures: seven are the `avg_v` Y check; two are
`eye_box_h` head drift (`0110e1359bd7`, and `3d4be8b6eef7` which failed both).

### 3.1 `r(Y, avg_v) < r(Y, pca_vL)` in **16 of 16** sessions

Without exception, the derived signal is a weaker Y correlate than the
left-eye channel the mapper actually fits. The gap ranges from 0.004
(`0110e1359bd7`) to 0.483 (`bfb745b0b87e`).

### 3.2 The gate's decisions invert the mapper's own signal

Four blocked-vs-accepted pairs where the **blocked** session had the stronger
`r(Y, pca_vL)`:

| Blocked | r(Y,vL) | Accepted | r(Y,vL) | avg_v blocked vs accepted |
|---|---:|---|---:|---|
| `2879900a17e0` | +0.459 | `14938da0bdf0` (A) | +0.357 | +0.019 vs +0.176 |
| `2879900a17e0` | +0.459 | `34fb259ccdfd` (B) | +0.344 | +0.019 vs +0.297 |
| `bfb745b0b87e` | +0.625 | `14938da0bdf0` (A) | +0.357 | +0.142 vs +0.176 |
| `bfb745b0b87e` | +0.625 | `34fb259ccdfd` (B) | +0.344 | +0.142 vs +0.297 |

Every inversion involves one of the two confirmed product-condition sessions
being rejected in favour of a free-head baseline with a weaker signal.

### 3.3 The decision boundary is a knife-edge in the wrong direction

The two sessions closest to the 0.15 threshold:

| Session | r(Y,avg_v) | verdict | r(Y,vL) | r(Y,mdlY) |
|---|---:|---|---:|---:|
| `bfb745b0b87e` | +0.142 | **BLOCKED** | +0.625 | +0.626 |
| `14938da0bdf0` (A) | +0.176 | accepted | +0.357 | +0.410 |

0.034 apart on the gated metric — well inside session noise — decides pass vs
fail, while the mapper-relevant signal differs by 0.268 the *other* way.
Baseline A went on to be the worst practical result recorded (`hadar` 5/5
wrong focus).

### 3.4 Rank agreement (the honest version)

Spearman rank correlation across the 16 sessions, against `r(Y, pca_vL)`:

- `r(Y, avg_v)` → **+0.924**
- `r(Y, model-Y)` → **+0.953**

So `avg_v` is *broadly* informative; it is **not** noise, and the earlier
working claim that it "does not rank-order sessions consistently" was too
strong. The problem is narrower and worse for a **blocking** gate: the
disagreement is concentrated exactly at the decision boundary, and it is
one-sided — it rejects the product condition. A metric can be 92% rank-correct
and still be unusable as a hard gate if its errors cluster at the threshold.

### 3.5 Counterfactual

Applying the **same 0.15 threshold** to `r(Y, pca_vL)` instead of `avg_v`:

- newly **passes**: `2879900a17e0`, `bfb745b0b87e`, `42662808ac84`,
  `05e40e22688f`
- newly **fails**: none

The change is strictly one-directional on this data: it never admits a session
the current check would have caught. `cfdd5f1ea546` (`r(Y,vL)` = −0.054) still
fails, so the check keeps its ability to reject a genuinely inverted session.

## 3.6 Which representation should T027 score?

Same 0.15 threshold, same 16 sessions, four candidate quantities:

| Session | now | current `avg_v` | A: `pca_vL` | B: unclamped mean(vL,vR) | C: model-Y |
|---|---|---:|---:|---:|---:|
| `e3488095862f` | PASS | +0.699 | +0.984 | +0.694 | +0.984 |
| `1b78ad3e50da` | PASS | +0.667 | +0.854 | +0.618 | +0.885 |
| `0ee046a292cf` | PASS | +0.633 | +0.813 | +0.505 | +0.846 |
| `702386ab2ea4` | PASS | +0.548 | +0.852 | +0.563 | +0.869 |
| `f2dab57719b6` | PASS | +0.466 | +0.756 | +0.453 | +0.806 |
| `14fe126cb238` | PASS | +0.405 | +0.651 | +0.429 | +0.813 |
| `0110e1359bd7` | FAIL (eye_box) | +0.316 | +0.320 | +0.453 | +0.499 |
| `34fb259ccdfd` **B** | PASS | +0.297 | +0.344 | +0.255 | +0.449 |
| `14938da0bdf0` **A** | PASS | +0.176 | +0.357 | +0.277 | +0.410 |
| `bfb745b0b87e` **support** | FAIL Y | +0.142 | +0.625 | +0.214 | +0.626 |
| `42662808ac84` | FAIL Y | +0.024 | +0.199 | +0.091 | +0.217 |
| `2879900a17e0` **support** | FAIL Y | +0.019 | +0.459 | +0.078 | +0.565 |
| `3d4be8b6eef7` | FAIL Y | −0.080 | +0.075 | −0.078 | +0.405 |
| `05e40e22688f` | FAIL Y | −0.119 | +0.160 | −0.028 | +0.198 |
| `cfdd5f1ea546` | FAIL Y | −0.150 | **−0.054** | −0.148 | +0.213 |
| `0694c1663623` | FAIL Y | −0.365 | +0.012 | −0.355 | +0.375 |

Sessions each option would block at 0.15:

| Option | blocks | which |
|---|---:|---|
| current `avg_v` | 7 | `05e40e`, `0694c1`, `287990`, `3d4be8`, `426628`, `bfb745`, `cfdd5f` |
| **A: `pca_vL`** | **3** | `0694c1`, `3d4be8`, `cfdd5f` |
| B: unclamped mean | 6 | as current, minus `bfb745` |
| C: model-Y | **0** | none |

**Option C (fitted model-Y) must be rejected.** It blocks nothing — not even
`cfdd5f1ea546`, whose left-eye Y signal is actually **inverted**
(`r(Y, pca_vL)` = −0.054). This is circularity, not strength: ridge is fitted
to minimise error against the taught Y, so `predicted_y` is positively
correlated with Y by construction, almost regardless of input quality. A gate
scored on the fit cannot reject a bad session. It would also collapse toward
LOOCV as a sole accept/reject, which the constitution forbids.

**Option B is a half-fix.** Removing the clamp recovers `bfb745b0b87e` but
still blocks `2879900a17e0` (+0.078), because it keeps averaging in the
`pca_vR` channel that tracks screen X.

**Option A is the choice on this data.** It admits both product-condition
sessions while still rejecting all three sessions with genuinely absent or
inverted vertical signal (`0694c1663623` +0.012, `3d4be8b6eef7` +0.075,
`cfdd5f1ea546` −0.054). It keeps the check's protective purpose and stops it
from terminating the product condition.

Caveat to record with the change: option A is right *because* `pca_vR` is
currently defective. If T020 repairs the right-eye basis, a binocular check
becomes preferable and this gate should be revisited — as its own later task,
not folded into T020.

## 4. Gate label vs measured outcome

Only three sessions have both a gate label and a developer evaluation, so this
is reported as insufficient rather than dressed up as a correlation:

| Session | gate | held-out inside-key | median err | `hadar` wrong focus |
|---|---|---:|---:|---|
| `14938da0bdf0` (A) | warning_only PASS | 0% | 130 px | 5/5 |
| `34fb259ccdfd` (B) | warning_only PASS | 8% | 107 px | 4/5 |
| `e3488095862f` | warning_only PASS | 17% | 65 px | not collected |

**n = 3, all with the same label.** The requested correlation between
`quality_gate_kind` and held-out / `hadar` outcomes therefore **cannot be
computed** — not because the analysis was skipped, but because the gate has
never let a `blocking` session through to be evaluated. That is itself the
finding: the label has no measured discriminative power because it terminates
the measurement.

What the three do establish: **passing is not sufficient.** A and B both passed
and were not practically typeable. Any future report must not present a gate
pass as mapping success.

## 5. Secondary observations (not part of T027)

- **String-dispatch fragility**: blocking depends on the word `catastrophic`
  appearing in a message. In fullscreen mode the same condition produces
  `"... need >=0.15"` with no such word. Rewording a message changes product
  gating. Worth a follow-up, but changing the dispatch mechanism is a separate
  concern from what the check measures — do not bundle it into T027.
- **Silent skip**: the Y check is guarded by `ys.size == vs.size`, and `vs` is
  built by filtering out `None` `avg_v` while `ys` is not filtered. A single
  target with a missing `avg_v` makes the sizes disagree and the entire
  vertical check is skipped with no warning. Not observed in these 16 sessions
  (all 15/15), but it is a latent hole in a blocking gate.
- **Warning counts do not separate outcomes**: 4–18 warnings across the set,
  with the best session at 4 and a passing session at 16. Warning count is not
  a usable proxy.
- `min_avg_v_row_separation` (0.025) and the within-row `avg_v` span check
  inherit exactly the same clamp/contamination defect described in §2, and are
  warning-only. If T027 changes the representation, these should be revisited
  **later** and separately.

## 6. Conclusion (evidence only)

1. The only vertical check that can block a keyboard session reads `avg_v`,
   which the mapper does not consume; every check reading `pca_vL`/`pca_vR` is
   warning-only. The gate is inverted relative to the pipeline.
2. `avg_v = mean(clamp(0.5+pca_vL), clamp(0.5+pca_vR))` is confirmed
   numerically. The right-eye term saturates at the clamp floor on 0–14 of 15
   targets depending on session, so the effective formula changes between
   targets; where it does not saturate, `pca_vR` tracks screen X in 16/16
   sessions.
3. `r(Y, avg_v) < r(Y, pca_vL)` in **16/16** sessions.
4. The gate's decisions invert the mapper's own Y signal in 4 blocked-vs-
   accepted pairs, all rejecting a product-condition session in favour of a
   weaker free-head baseline, and the boundary case turns on 0.034.
5. Under the product condition the gate has blocked every session before
   evaluation, so no collection experiment is currently decidable.
6. Passing the gate is necessary, not sufficient (A and B passed, `hadar` 5/5
   and 4/5).

7. Of the candidate replacements, **`r(screen_y, pca_vL)` is the only one that
   both admits the product condition and still rejects genuinely bad
   sessions**. Fitted model-Y is circular and blocks nothing (0/16, including
   an inverted session); the unclamped binocular mean is a half-fix that still
   blocks one of the two support sessions.

This implicates **what the vertical check measures**, not whether gates should
block. T027 is therefore scoped to the representation only: keep blocking
semantics, keep the 0.15 threshold, and score `r(screen_y, pca_vL)`. It must
not be combined with T020 (the `pca_vR` basis defect) or T025, and it must not
use fitted model-Y.

**Reproduce**: `runs/_feature004/T017_y_correlation_investigation.md` and
`T017_controlled_rest_vs_free.md` hold the earlier per-session detail; the
tables here were generated from each session's `calibration_debug.csv` and
`calibration_summary.txt`.
