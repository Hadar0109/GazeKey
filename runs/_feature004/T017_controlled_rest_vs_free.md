# Controlled diagnostic — chin/head support vs free head (T017 tree)

**Date**: 2026-08-20  
**Code state**: T017 4-D fixation gate still in tree; no other product change  
**Protocol**: two WITH support, then two WITHOUT; same camera, seat, height/angle, distance, lighting, `keyboard15`  
**Product code**: not changed in this write-up

## Session IDs (terminal order)

| Order | Condition | Session | Calib | `corr(Y, avg_v)` | LOOCV | Eval |
|---|---|---|---|---:|---:|---|
| 1 | **WITH rest** | `2879900a17e0` | blocking Y | +0.019 | 86.6 | none |
| 2 | **WITH rest** | `bfb745b0b87e` | blocking Y | +0.142 | 81.5 | none |
| 3 | **WITHOUT rest** | `e3488095862f` | warning_only **pass** | **+0.699** | **45.7** | 5/31 (16%) |
| 4 | **WITHOUT rest** | `3d4be8b6eef7` | blocking eye_box_h 0.0068 **and** Y | −0.080 | 96.8 | none |

`face_x` is **not stored** in `calibration_debug.csv` / `calibration_v2.json`. `face_y` and `eye_box_h` are.

`hadar` on `e3488095862f` is still **pending** (template only).

## 1. Does the support materially affect calibration / mapping?

**Yes for calibration usability. Not shown to be the whole mapping problem.**

WITH rest today: **0/2** usable (both Y-gate).  
WITHOUT rest today: **1/2** usable; the other failed head-drift (`eye_box_h` span 0.0068) plus Y.

That matches the earlier T017 evening (0/3 usable, rest suspected) vs the baseline evening without T017 (2/4 usable: A, B pass; `05e40e` Y-fail; `0110` eye_h-fail).

The support did **not** freeze geometry more than a still free-head run:

| | face_y mean | face_y span | eye_box_h span |
|---|---:|---:|---:|
| WITH rest-1 | 0.500 | 0.0029 | 0.0040 |
| WITH rest-2 | 0.500 | 0.0027 | 0.0029 |
| WITHOUT pass `e348` | **0.525** | **0.0073** | **0.0018** |
| WITHOUT fail `3d4b` | 0.533 | 0.0028 | **0.0068** |
| Baseline A | 0.504 | 0.0027 | 0.0030 |
| Baseline B | 0.507 | 0.0015 | 0.0024 |

The **only session with a working vertical map** (`e348`) has the **largest `face_y` span** (nodding along target Y) and a **small** `eye_box_h` span (distance stable). WITH rest, `face_y` span stays in the A/B band and the Y-gate fails.

So the rest is associated with **less pitch-related `face_y` travel**, not with a uniformly “cleaner” recording. Free-head can be either the best session (`e348`) or a head-drift block (`3d4b`).

## 2. Is T017 the cause of the Y-gate blocks?

**No.** All four controlled runs used the same T017 4-D gate. Rest vs free is what changed. Sample counts on the passing session are normal (39–42), same as A/B.

T017 is also **not KEEP**. Only one eval exists (`e348`), `hadar` is unfilled, and 3/4 of today’s calibrations never reached mapping eval.

T017 is **not REVERT**. The one usable session on this tree is the best mapping result so far versus A/B (see §4). Reverting would throw that away without evidence the 4-D gate caused the blocks.

**Decision remains INCONCLUSIVE** (unproven keep; not implicated as the blocker).

## 3. Vertical / mapper-Y vs the `avg_v` gate

| Session | r(Y, avg_v) | r(Y, pca_v) | r(Y, vL) | r(Y, vR) | r(X, vR) | pred_y span (taught 234) |
|---|---:|---:|---:|---:|---:|---:|
| A | +0.176 | +0.277 | +0.357 | +0.176 | −0.907 | 94 |
| B | +0.297 | +0.255 | +0.344 | +0.132 | −0.906 | 97 |
| WITH rest-1 | +0.019 | +0.078 | **+0.459** | −0.011 | −0.967 | 108 |
| WITH rest-2 | +0.142 | +0.214 | **+0.625** | +0.075 | −0.939 | 156 |
| WITHOUT pass | **+0.699** | **+0.694** | **+0.984** | +0.443 | −0.816 | **252** |
| WITHOUT fail | −0.080 | −0.078 | +0.075 | −0.113 | −0.974 | 86 |

`pca_vR` is still an **X** channel on every run (`r(X, vR)` −0.82 to −0.97). `avg_v` averages that with `vL`, so the catastrophic check can fail while **left-eye v still tracks Y**.

WITH rest-2: `r(Y, vL)=+0.625` but `r(Y, avg_v)=+0.142` → **blocked**. The gate is not scoring the mapper’s Y representation (`Y ← (vL, vR)` with `w_y` almost entirely on vL when Y works: `e348` w_y = 67.8, 2.5).

`e348` row means are the first monotonic set in this whole series: avg_v top/mid/bot/space = 0.077 / 0.096 / 0.126 / 0.160. A/B never did that. Within-row avg_v span is still large (~0.06), but between-row separation finally exceeds it.

## 4. Mapping quality when the gate allows eval

| | A | B | `e348` (T017, no rest) |
|---|---:|---:|---:|
| Held-out inside-key | 0% | 8% | **17%** |
| Overall inside-key | 0% | 10% | **16%** |
| Editing/control | 0% | 0% | **20%** |
| Median err | 130 px | 107 px | **65 px** |
| median \|dx\|/w | 0.93 | 0.51 | **0.24** |
| median \|dy\|/h | 0.73 | 0.99 | 0.77 |
| Train LOOCV | 89 | 95 | **46** |
| Train pred_y span | 94 | 97 | **252** |
| Alpha | 1.0 | 1.0 | 0.3 |

Horizontal offset/compression is much better than A/B (no longer “every point to the right”). Vertical at **eval** is still weak (`dy/h` 0.77; Calibrate 578 px). Train-time Y on calib anchors is good (Space train error 24 px) and **eval** Space is 71 px — a train vs live gap, which is Phase 4 (T028) territory, not a reason to skip collection.

This is still far from Feature 004 accept. It is the first session that is **better than both baselines** on held-out, editing, median error, and LOOCV. n=1. `hadar` unknown.

## 5. Most likely source of weak / unstable Y

Ranked by this diagnostic, not by the original audit list:

1. **Head pitch leaking into eye-local v**, especially `pca_vL`. The usable map had the largest `face_y` span. Rest reduced that travel and the Y-gate died. Iris-only Y over a 234 px keyboard is weak; the pipeline appears to have been accidentally using nod-in-v as Y.
2. **Right-eye v is horizontally contaminated** on every session. That makes `avg_v` a bad Y proxy and poisons binocular Y when `w_y` cannot ignore `vR`.
3. **The blocking gate scores clamped `avg_v`, not mapper Y.** It is a knife-edge (A passed at +0.176) and blocked rest-2 despite `r(Y, vL)=+0.625`.
4. **T017 4-D gating** is not required to explain rest vs free. It may still be a small collection filter; it is not measured as KEEP.
5. Aggregation (T019), layout (Phase 6), and ridge alpha (Phase 7) are not what flipped today’s four runs. Auto-alpha 0.3 on `e348` is a *consequence* of better LOOCV, not a lever we pulled.

`3d4be8b6eef7` (free head, failed) shows the other free-head failure mode: large `eye_box_h` span (distance/lid change) plus v dominated by X (`r(X, vR)=−0.974`, avg_v 0.278 on Q vs 0.085 on P). Free head is not automatically better; it is more variable.

## 6. Feature 004 sequence

Do **not** rewrite plan phases. Do **not** start T019 while T017 is still an unproven product change in the tree.

Adjust how we *use* the existing sequence:

- Mapping evals: **no chin/head support** until a later, explicit pose experiment. Rest is now known to starve the Y-gate.
- Next isolated live work: **one more WITHOUT-rest calib + eval + `hadar`** on this same T017 tree. That is still T017 measurement (eval_after), not a new lever.
  - If held-out / `hadar` beat A/B again → KEEP T017 (Git checkpoint), then T019.
  - If Y-gate fails again or mapping returns to A/B → T017 stays inconclusive; consider revert of the 4-D gate **as isolation**, then T026 write-up.
- T026 is the right place to write that `avg_v` vs Y is the wrong proxy. **T027 is not authorized** by this diagnostic (one-change; T017 still in tree).
- Phase 4 sync is implicated *after* a kept collection state (`e348` train Y good, eval `dy/h` still 0.77). Do not jump there first.
- Phase 5–7: unchanged order. Calibrate’s 578 px is still coverage/geometry later, not this iteration.

## 7. Smallest next experiment

Same T017 code. **No rest.** One calib + developer eval + `hadar` suggestions-off. Cite A/B as `eval_before`. Do not change gates, aggregation, or mapper.

---

## 8. SUPERSEDED — product condition decided 2026-08-20

Sections 6 and 7 above are kept as a decision log but are **no longer the
plan**. They assumed the condition was ours to choose and optimized for
whichever condition passed the existing gate more easily. The product goal is
now fixed: the system is used **with the chin/head support**, to keep the head
stable and reach the highest achievable accuracy under that condition (spec
Clarifications 2026-08-20).

What that changes in this document's conclusions:

- **"No chin/head support until a later pose experiment" is withdrawn.** That
  recommendation optimized for the gate, not the product. Every accuracy run
  from here on uses the support.
- **Finding 1 flips from an explanation to a defect.** Head pitch leaking into
  `pca_vL` is not a mechanism to preserve. If Y only works because the head
  nodded with the target, the product cannot be repeatable and cannot work
  stabilized. The observation stands; the intent inverts.
- **Finding 3 is promoted to the binding constraint.** Under the product
  condition, 0 of 5 sessions reached mapping evaluation. Nothing downstream is
  decidable until the vertical check scores the representation the mapper
  actually fits. Both support sessions beat A and B on `r(Y, pca_vL)`,
  model-Y fidelity, training Y error, LOOCV, and warning count — and were
  rejected.
- **Finding 2 becomes the first accuracy candidate** (T020, widened from `u` to
  `u` and `v`), because a stabilized head removes the head-motion crutch and
  leaves the right eye's rotated basis as the largest identified defect.
- **T017 is reverted for isolation** (T059), not judged. Its one supporting
  eval was free-head, so it never measured the product condition.

Resulting order (see `specs/004-gaze-mapping-accuracy/tasks.md` Phase 3):

```text
T059 isolate → T026 evidence → T027 gate change → T060 reference pair → T020 …
```

Plan phases A–F are unchanged. This reorders work inside Phase B.
