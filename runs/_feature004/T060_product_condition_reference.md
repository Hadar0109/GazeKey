# T060 — Product-condition reference pair (CLOSED 2026-08-20)

Two calibration + evaluation + `hadar` sessions captured **with the chin/head
support**, on the unchanged kept tree, to establish how much the product
condition varies session to session. Purpose: give T020 and every later
accuracy experiment a spread to beat instead of a single point.

- Reference 1: `689c8a8ce90c` — tree `b07e768` (T027 keep)
- Reference 2: `4f665467b260` — tree `861a89c` (docs only; product code identical to `b07e768`)
- Condition: head-support (product condition), same rig, same layout `keyboard15`, `ridge_alpha=1`, 15/15 targets, 41–43 samples per target
- These **add to** baselines A `14938da0bdf0` and B `34fb259ccdfd`. Per FR-026 the free-head A+B pair is still cited as `eval_before` on every experiment; the T060 pair is the same-condition comparison alongside it.

## 1. The pair

| metric | ref 1 `689c8a8ce90c` | ref 2 `4f665467b260` | spread |
|---|---:|---:|---:|
| calibration | PASSED `warning_only` | PASSED `warning_only` | — |
| quality warnings | 19 | 13 | 6 |
| LOOCV RMS | 104.3 px | 82.3 px | **22.0 px** |
| mapped-key (focus) | 23% (7/31) | 29% (9/31) | **6 pp** |
| median error | 81.0 px | 78.2 px | **2.8 px** |
| row accuracy | 35% (11/31) | 39% (12/31) | 4 pp |
| repeatability slice | 26.7% | 26.7% | **0 pp** |
| held-out inside-key | 25.0% | 33.3% | **8.3 pp** |
| editing/control | 0% | 20% | **20 pp** (= 1 of 5 keys) |
| focus stability (held-out) | 0.304 | 0.344 | 0.040 |
| clamp hit rate | 0.035 | 0.062 | 0.027 |
| `median_\|dx\|/w` | 0.176 | 0.344 | **0.168** |
| `median_\|dy\|/h` | 0.862 | 0.714 | 0.148 |
| `hadar` wrong focus | 3/5 (`uaraf`) | 2/5 (`ywdar`) | 1 letter |

## 2. The variability envelope T020 must beat

This is the operative output of T060. On an **unchanged** tree in the **same**
condition, these metrics moved by:

- **mapped-key: 6 pp.** A change must clear ~29% + 6 pp ≈ **35%** before one
  session is worth believing.
- **held-out inside-key: 8.3 pp.** The noisiest headline slice. Needs ~42%.
- **median error: 2.8 px.** The *most* stable headline metric of the set — a
  median-error improvement is the cheapest credible signal available.
- **row accuracy: 4 pp.** Needs ~43%.
- **`hadar`: 1 letter.** A single-letter improvement means nothing. Only 0/5 or
  1/5 would be informative, and `hadar` is a development word (SC-006) that
  cannot serve as acceptance regardless.
- **editing/control: 20 pp** — but that slice has only 5 keys, so one key is
  20 pp. Treat it as unusable for deciding anything at n=1.
- **repeatability: 0 pp.** Identical at 26.7% (4/15) in both. Suspiciously
  stable; do not read it as precision until a third session confirms.
- **LOOCV RMS: 22 px**, and it moved *opposite* to eval quality relative to
  what one might expect — ref 1 had the worse LOOCV (104.3) and also the worse
  eval, so LOOCV directionally tracked here, but it remains supplementary and
  must not become an accept/reject criterion (T027 scope note).

Consequence for experiment design: **a single post-change session cannot
resolve a small effect.** Any T020 result inside these bands needs a second
session before keep/revert, and `inconclusive` is the honest verdict at n=1.

## 3. What is stable, and what is not — the localisation

The two references disagree about the *vertical* axis and agree about the
*horizontal* one:

| quantity | ref 1 | ref 2 | stable? |
|---|---:|---:|---|
| `r(X, avg_h)` | −0.988 | −0.994 | **yes** |
| X compression (taught/predicted span) | 0.94x | 0.96x | **yes** |
| `r(X, pca_vR)` | −0.901 | −0.899 | **yes — and it is the defect** |
| `r(Y, pca_vL)` | +0.222 | +0.591 | **no — 2.7x apart** |
| `r(Y, pca_vR)` | +0.108 | +0.231 | no |
| `r(Y, avg_v)` | −0.152 | +0.179 | no — opposite signs |
| Y compression | **4.22x** | **1.47x** | **no — 2.9x apart** |
| `pca_vL` span over 15 targets | 0.073 | 0.082 | yes (both tiny) |
| `face_y` drift | 0.0016 | 0.0027 | yes (both small) |
| `eye_box_h` drift | 0.0020 | 0.0029 | yes (both small) |

Three things follow.

**(a) Horizontal mapping is essentially solved and essentially stable.** X
correlation is ≈ −0.99 in both, and predicted X spans 94–96% of the taught
range — no meaningful compression. Nothing in Phase 3 should spend effort on
the horizontal axis.

**(b) Vertical mapping is both weak and unstable.** `r(Y, pca_vL)` nearly
tripled between two sessions taken minutes apart in the same condition, and Y
compression ranged from 1.5x to 4.2x. The available vertical range is tiny in
both (`pca_vL` spans ~0.08 across the full 234 px of taught Y), so small
absolute changes in that signal swing the fit dramatically. This is a
*signal-to-noise* problem in the vertical feature, not a fitting problem.

**(c) The head really was stable, so head motion is not the explanation.**
`face_y` and `eye_box_h` drift are small in both, and comparable. The vertical
weakness is a property of the eye-local vertical feature under a stabilized
head, which is exactly what the T017 controlled runs suggested and what T020
targets.

The one quantity that does **not** vary is `r(X, pca_vR)` ≈ −0.90 — the right
eye's "vertical" channel tracking screen **X**. Across all 18 sessions on disk
it sits in −0.78…−0.97. A defect that reproduces to two decimal places while
everything around it swings is the most promising thing to fix.

## 4. Product condition vs the free-head baselines (observational only)

| | A (free) | B (free) | ref 1 (support) | ref 2 (support) |
|---|---:|---:|---:|---:|
| mapped-key | 0% | 10% | 23% | 29% |
| median error | 130 px | 107 px | 81 px | 78 px |
| held-out | 0% | 8% | 25% | 33% |
| `hadar` wrong | 5/5 | 4/5 | 3/5 | 2/5 |

Both support sessions beat both free-head sessions on every one of these, and
the two groups do not overlap. That is **suggestive but not a controlled
result** and must not be quoted as one: the pairs differ in condition *and* in
calendar time *and* in gate version, n is 2 per group, and the earlier T017
controlled runs found the opposite direction of pass-rate (0/2 usable with
support vs 1/2 without). It is recorded because the product condition is now
the shipping assumption and the numbers should be on the record — not as
evidence that the chin rest improves accuracy.

## 5. Note on T027 in hindsight

Reference 2's `r(Y, avg_v) = +0.179` clears the old 0.15 threshold, so the old
gate would have admitted it. Only reference 1 (`−0.152`) actually needed T027.

This strengthens the T026 diagnosis rather than weakening it: two sessions in
the same condition, on the same tree, minutes apart, land on **opposite sides**
of the old threshold with a margin of 0.029 — while their mapper-relevant
signals (`r(Y, pca_vL)` = 0.222 and 0.591) are both comfortably positive and
agree in sign. The old gate's verdict was being decided by noise in a quantity
the mapper never reads. T027 stays KEEP.

## 6. Follow-ups created, not done here

- The `tools/evaluation` record template mislabels every new session as
  "CurrentStateBaseline A or B" and forces a hand correction each run. It has
  now produced three wrong records (`e3488095862f`, `689c8a8ce90c`,
  `4f665467b260`). Small separate chore.
- `Space` is the worst location in both references (189.8 px / 202.7 px,
  `dy/h` 2.23 / 2.33). Overlaps T023/T024 metadata work.
- `Calibrate` was the worst error in ref 1 (458 px) and 119 px in ref 2 — a
  large swing on a control key; Phase 5–6 coverage/geometry.
- Repeatability being *exactly* 26.7% twice deserves a look at whether that
  slice is actually varying or is structurally pinned.
