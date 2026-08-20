# T020 — Eye-local `u`/`v` basis semantics (INVESTIGATION, no product change)

Scope: `_eye_uv_one_eye` in `gazekey/features/extractor.py` vs the contour
ordering produced by `gazekey/tracking/eye_detector.py`. Per `tasks.md`, `v` as
well as `u`. **Verdict: implicated, decisively.** No product code was changed.

Method — three independent lines of evidence:

1. **Ground truth on the index convention.** Ran the project's own
   `models/face_landmarker.task` on a synthetic frontal face and read the actual
   coordinates of every index in `LEFT_EYE_INDICES` / `RIGHT_EYE_INDICES`, so
   the ring order is measured rather than assumed.
2. **Controlled synthetic gaze.** Applied an *identical* iris displacement grid
   to both real contours through the real `_eye_uv_one_eye`, isolating code
   asymmetry from physiology.
3. **All 18 recorded sessions.** `calibration_v2.json` stores `train_u_l`,
   `train_u_r`, `train_v_l`, `train_v_r` per target, so every channel can be
   correlated against target X and Y on real data.

---

## 1. What the landmark ring actually is

Measured, both eyes, same structure:

| ring position | contents |
|---|---|
| 0 | a corner |
| **1–7** | **lower lid** |
| 8 | the other corner |
| **9–15** | **upper lid** |

The code does:

```python
upper = proj_y[1:5]                                   # positions 1,2,3,4
lower = np.concatenate([proj_y[5:8], proj_y[9:13]])   # positions 5,6,7 + 9,10,11,12
```

So the variable named `upper` is **entirely lower lid** in both eyes, and
`lower` is a **mixture** of both lids. The mixture composition differs per eye,
which is what makes the error asymmetric:

- left `lower` = positions 5,6,7 (lower) + 9,10,11,12 → **4 lower + 3 upper**, median lands in the *lower* cluster
- right `lower` = positions 5,6,7 (lower) + 9,10,11,12 → **3 lower + 4 upper**, median lands in the *upper* cluster

Resulting `aperture` against the true lid separation:

| eye | code aperture | true aperture | ratio |
|---|---:|---:|---:|
| left | 0.01676 | 0.02034 | **0.824** |
| right | 0.01076 | 0.02049 | **0.525** |

Same physical eye opening (0.0203 vs 0.0205 — the eyes really are symmetric),
but the code reads one as 82% and the other as 53% of it.

**Corner polarity is anatomically mirrored, benignly.** Left: position 0 = lm33
= OUTER, position 8 = lm133 = INNER, so `x_hat` runs outer→inner. Right:
position 0 = lm362 = **INNER**, position 8 = lm263 = **OUTER**, so `x_hat` runs
inner→outer. The docstring's "horizontal axis: outer_corner -> inner_corner" is
therefore true for one eye only. It happens not to matter: both `x_hat` point
image-**right**, so `u` is image-consistent, which is what the mapper needs.
Fix the comment, not the code.

**Iris/contour pairing is correct** — lm468 falls inside the left contour's
bbox and lm473 inside the right's, so the eyes are not swapped.

## 2. The vertical axis inherits the eye's canthal tilt, with opposite sign per eye

`y_hat` is built as `perp(x_hat)` with only its *sign* forced downward. Real eyes
slant, mirror-symmetrically: measured `x_axis` tilt is **+4.7°** (left) and
**−5.1°** (right). So `y_hat` carries a horizontal component:

| eye | `y_hat` | `y_hat_x` |
|---|---|---:|
| left | (−0.0817, +0.9967) | **−0.0817** |
| right | (+0.0888, +0.9961) | **+0.0888** |

Since `v = rel_iris · y_hat`, horizontal iris motion leaks into the vertical
channel **with opposite sign in the two eyes**. Then it is divided by an
aperture that is itself ~2x too small on the right. Net leak per unit of `u`:

```
leak coefficient = |y_hat_x| * eye_w / aperture
                 = 0.441  (left)      0.745  (right)      right = 1.69x left
```

### The synthetic sweep confirms it

Identical iris displacement applied to both real contours:

| eye | dv/d(dx) — spurious | dv/d(dy) — true gain | leak/gain |
|---|---:|---:|---:|
| left | **−4.875** | +59.45 | 0.082 |
| right | **+8.250** | +92.55 | 0.089 |

Opposite signs, and the right eye's spurious sensitivity is 1.69x the left's.
`u` by contrast is clean: `du/d(dx)` = +11.01 / +11.03 (identical, and exactly
`1/eye_w`), with only ~8% cross-talk from vertical motion.

## 3. Both predictions confirmed on all 18 recorded sessions

The mechanism predicts `r(X, v_right)` strongly negative and consistent, and
`r(X, v_left)` weakly positive and sign-unstable. Measured:

| quantity | min | max | mean | sign consistency |
|---|---:|---:|---:|---|
| `r(X, u_left)` | −0.997 | −0.959 | −0.985 | **18/18** |
| `r(X, u_right)` | −0.997 | −0.976 | −0.989 | **18/18** |
| `r(X, v_left)` | −0.788 | +0.814 | +0.087 | 10/18 (random) |
| `r(X, v_right)` | −0.974 | −0.779 | **−0.900** | **18/18** |
| `r(Y, v_left)` | −0.054 | +0.984 | +0.457 | 17/18 |
| `r(Y, v_right)` | −0.300 | +0.447 | +0.147 | 13/18 |
| `r(u_left, v_left)` | −0.776 | +0.739 | −0.097 | 9/18 (random) |
| `r(u_right, v_right)` | +0.783 | +0.966 | **+0.896** | **18/18** |

Sign check: `r(X, u_R)` is negative, and `y_hat_x` is **positive** for the right
eye, so the leak must make `r(X, v_R)` negative — it is, 18/18. For the left eye
`y_hat_x` is **negative**, so the leak pushes `r(X, v_L)` positive, where it
fights the genuine Y signal of similar size and the sign becomes a coin flip —
it is, 10/18.

**The right eye's vertical channel is essentially a copy of its own horizontal
channel** (`r(u_R, v_R)` = +0.896, 18/18). It contributes almost no independent
vertical information, while `r(u_L, v_L)` is uncorrelated — the left eye's `v`
is the only real vertical signal in the system.

Dynamic range says the same thing:

| channel | mean span over 15 targets |
|---|---:|
| `u_left` | 0.169 |
| `u_right` | 0.171 |
| `v_left` | **0.087** |
| `v_right` | **0.274** |

The horizontal channels match to 1%. The right eye's `v` swings **3.1x** wider
than the left's — inflated by its halved aperture and filled with horizontal
leakage.

### How much of the vertical range is just leakage

Applying the leak coefficients to each session's own measured `span_u`:

| eye | predicted leak as share of observed vertical range |
|---|---|
| left | **median 89%** (range 51–135%) |
| right | **median 47%** (range 30–84%) |

Several left-eye sessions exceed 100%, i.e. the predicted leak alone is larger
than the entire observed vertical range. The geometry constants come from the
probe face rather than the user's, so treat these as indicative — but the
conclusion does not depend on precision at that level.

## 4. The deeper design defect: `v` is normalized by a gaze-*dependent* scale

`u` is divided by **eye width** (corner distance) — a quantity that does not
change as the eye rotates. Correct.

`v` is divided by **eyelid aperture** — a quantity that *does* change with
vertical gaze, because the lid follows the eye down. Numerator and denominator
therefore move together and partially cancel, so the normalizer removes some of
the very signal it is scaling. Lid aperture is a *cue* for vertical gaze; here
it is being divided out.

This is the root asymmetry between the two axes, and it explains why the
vertical axis is weak even before the leak is counted.

### The vertical signal that survives is tiny

Working back through the gains (left eye, mean over sessions):

- horizontal iris travel across the whole keyboard: **16.9% of eye width**
- vertical iris travel across the whole keyboard: **1.6% of eye width**
- ratio: **10.5x**, and the 1.6% figure still contains the leak, so the true
  vertical travel is smaller again

## 5. What the product actually does with this

Regressing evaluation error on target position for the two T060 reference
sessions:

| | `689c8a8ce90c` | `4f665467b260` |
|---|---:|---:|
| slope `d(dy)/d(target_y)` | **−0.961** | **−0.878** |
| slope `d(dx)/d(target_x)` | −0.015 | −0.138 |
| `r(target_x, dy)` | −0.087 | −0.096 |
| mean \|dy\| | 63.1 px | 64.3 px |
| mean \|dx\| | 31.6 px | 43.7 px |

A slope of −1 means predicted Y is *constant* — the mapper ignores the target's
vertical position entirely. At −0.96 and −0.88, **88–96% of the vertical range
is being ignored on evaluation locations**, against 1.5–14% horizontally.

Note what is *not* there: `r(target_x, dy)` is only about −0.09. The leak does
**not** surface as X-dependent Y error, because ridge regression, seeing a Y
feature that is mostly noise, shrinks the Y weights toward zero — so neither
the signal nor the leak reaches the output. The product symptom is "vertical is
ignored", not "vertical follows horizontal". Any fix must be judged on whether
the mapper starts *using* Y, not on whether an X-into-Y correlation disappears.

Consistent with that, the fitted `w_y` already leans on the left eye in 15 of 18
sessions (left carries 51–100% of `|w_y|`, median ~65%): the regression has
partially discovered on its own that `v_left` is the better channel, while
`v_right` still injects horizontal noise into Y.

## 6. Why this also explains the T060 instability

T060 found `r(Y, pca_vL)` swinging 0.222 → 0.591 and Y compression 4.22x → 1.47x
between two sessions minutes apart, while `r(X, pca_vR)` held at −0.90. That is
exactly the signature of a channel whose content is *mostly* a stable geometric
artifact plus a *small* genuine signal: the artifact reproduces to two decimals,
and whichever fraction of true vertical signal survives depends on incidental
session geometry. The vertical axis was never measuring one thing consistently.

## 7. Coupling that a fix must not ignore

`FixationGate` applies **one** threshold to both channels —
`max_std_pca = 0.035` and `jump_threshold_pca = 0.10` via `max(std_u, std_v)`.
Because `v` is currently divided by aperture (~5.4x smaller than `eye_w`), `v`
is ~5.4x larger than `u` for the same physical motion, so **the collection gate
is currently ~5x stricter vertically than horizontally, by accident.** Any
change to `v`'s scale silently re-tunes that gate.

To keep the experiment honest, a scale-changing fix must rescale those
thresholds in the same commit so collection behavior is held constant, and say
so — otherwise the result confounds "better features" with "looser gate", which
is exactly the T017 trap.

`_eye_uv_one_eye` is the single feature path for both calibration and live
typing (`FeatureExtractor.from_eye_data`), so a fix applies symmetrically to
train and serve; it introduces no new skew (FR-029).

## 8. Separate defect found, out of T020 scope: the blink EAR

`_EAR_CONTOUR_OFFSETS = (0, 4, 3, 8, 5, 11)` picks `p3` = position 3 and
`p5` = position 5 — **both lower-lid points**. So the second of EAR's two
"vertical" terms, `d(p3, p5)`, measures a near-horizontal chord along the lower
lid, not lid separation. On the open eye it happens to read 0.0332 against the
genuine 0.0344, so EAR looks plausible (0.373 / 0.382) — but that term will not
collapse during a blink, so the computed EAR cannot fall as far as a correct one
and the `_EAR_BLINK_THRESHOLD = 0.20` does not mean what it appears to.
Consequence: under-detected blinks, letting partially-occluded frames into
calibration. Not part of T020; should be its own task.

## 9. Candidate single changes (none implemented)

All three are in `_eye_uv_one_eye`. Recommended order:

**A — normalize `v` by eye width instead of eyelid aperture. TRIED and
REVERTED 2026-08-20.** Two product-condition sessions (`5e9c11d2c802`,
`9ca533f8c0f0`) failed the slope keep threshold. Record:
`runs/_feature004/T020_vertical_scale_change.md`.

**B — remove the canthal tilt from the vertical axis.** Image vertical
`(0, 1)` instead of `perp(x_hat)`. **TRIED and REVERTED 2026-08-20.** Both
live sessions blocked (`89b4349e848b` r=0.116, `5e91836cbca2` r=0.006); B
did not remove X→v leak. Product restored to `861a89c`. 0.15 gate unchanged.

**C — fix the aperture lid indices** (§1). **TRIED; live verdict REVERT
2026-08-20.** Sessions `72c67227e52d` (slope −1.137) and `29c07b6b989f`
(slope −0.940). Scale equalized; mapper still ignored Y. Product code still
C pending review. Record:
`runs/_feature004/T020_lid_index_proposal.md`.

## 10. Honest risk on the whole approach

Even a perfect fix leaves the §4 finding standing: true vertical iris travel
across the entire keyboard is on the order of **1% of eye width**. If MediaPipe
landmark noise is comparable, the vertical axis may be under-resolved by this
feature set no matter how cleanly it is computed. A must therefore be judged on
whether `d(dy)/d(target_y)` moves off −0.9, not merely on whether correlations
tidy up. If it does not, the next lever is not another feature tweak but Phase 5
geometry / Phase 6 coverage, or reducing how much vertical resolution the
layout demands.
