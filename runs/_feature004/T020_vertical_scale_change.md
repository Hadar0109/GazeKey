# T020 — Product change: gaze-invariant vertical scale (change A)

- hypothesis: The vertical channel is normalized by measured eyelid aperture, a quantity that moves with vertical gaze and that the extractor reads from the wrong contour indices — asymmetrically, so the two eyes disagree by 1.69x about what one unit of `v` means. Replacing it with a gaze-invariant scale identical for both eyes should let the mapper use the vertical axis instead of ignoring it.
- logical_area: features (research R6 item 3)
- condition: head-support — product condition
- eval_before: 14938da0bdf0 (A), 34fb259ccdfd (B); same-condition reference pair 689c8a8ce90c + 4f665467b260 (T060)
- eval_after: 5e9c11d2c802 (session 1), 9ca533f8c0f0 (session 2)
- decision: **REVERT** (2026-08-20, two-session rule)
- keep_git_sha: n/a
- disposition: **REVERTED 2026-08-20.** Product restored to `861a89c`. Change A tests deleted. Sessions `5e9c11d2c802` and `9ca533f8c0f0` retained as evidence.
- investigation: `runs/_feature004/T020_eye_local_basis_investigation.md`

## Scope of the change

One line of arithmetic in `_eye_uv_one_eye` (`gazekey/features/extractor.py`):

```python
v_n = float(v / aperture)                              # before
v_n = float(v / (_V_SCALE_PER_EYE_WIDTH * eye_w))      # after
```

`_V_SCALE_PER_EYE_WIDTH = 0.152`. Plus comment/docstring corrections and a new
test file.

### Why a *fraction of eye width* rather than the corrected aperture

Two properties were needed. **Gaze-invariance**: eye width is the corner-to-corner
distance, which does not change as the eye rotates, whereas lid aperture does —
the lid follows the eye down, so numerator and denominator moved together and
the normalizer cancelled part of the signal it was scaling. **Per-eye
identity**: one shared constant makes it impossible for the two eyes to disagree
about the unit, which is what the 0.824-vs-0.525 aperture misread was doing.

Fixing the lid indices instead (candidate C) would have corrected the asymmetry
but kept a gaze-dependent denominator, leaving the deeper defect in place.

### Why 0.152, and why nothing else had to be re-tuned

The constant is chosen so `v` keeps the numeric range it had before. Three
places carry scale-sensitive absolute thresholds on `v`:

- `FixationGate.max_std_pca` (0.035) and `jump_threshold_pca` (0.10), applied to
  the binocular mean via `max(std_u, std_v)`
- `outliers.check_target_mean_outlier` — `row_residual_threshold` 0.10 plus an
  additive 0.02
- the legacy `avg_v = mean(clamp(0.5 + pca_v))` clamp

With 0.152 the per-eye scale moves by ×1.218 (left) and ×0.784 (right), and the
**binocular mean scale moves by ×1.001** — so every one of those thresholds
keeps its meaning and none of them had to be touched.

This matters for attribution. `FixationGate` applies a *single* threshold to
both channels, so scaling that shared number would have preserved the vertical
arm only by making the horizontal arm ~1.5x stricter. Preserving the magnitude
instead holds collection constant on both axes without editing any gate, which
is the only version of this experiment that stays a single change. It also
avoids the T017 trap of confounding "better features" with "different frames
collected".

## What the change does to the defect

Leak coefficient (spurious `v` per unit of horizontal iris travel), from the
measured probe geometry:

| eye | before | after |
|---|---:|---:|
| left | 4.87 | 5.94 |
| right | 8.25 | 6.47 |
| **right/left ratio** | **1.69** | **1.09** |

Note what this is and is not. **Per-eye leak is not reduced** — the left eye's
actually rises 22% while the right's falls 22%. What changes is that the leak
becomes *symmetric*, and it is signed: negative on the left, positive on the
right.

That matters in two different ways for two different consumers:

- **For the binocular mean** (`FixationGate`, `outliers.py`): the net leak falls
  from +1.689 to +0.266, an **84% reduction**, because equal-and-opposite terms
  cancel in an average.
- **For the mapper**, which fits `v_left` and `v_right` as two *separate*
  features (`predicted_Y = a·v_left + b·v_right`): the leak cancels when
  `a/b = k_right/k_left`. That required `a/b = 1.69` before and `1.09` now. The
  true vertical signal has the *same* sign in both eyes, so summing it wants
  `a/b ≈ 1`. Previously, cancelling the leak and summing the signal demanded
  conflicting weight ratios and the fit could not satisfy both. Now the two
  demands nearly coincide. **This is the actual mechanism the change is betting
  on** — not automatic cancellation, but making cancellation compatible with
  fitting.

Sanity check that the asymmetry really was an artifact: true aperture as a
fraction of eye width measures 0.2247 (left) and 0.2269 (right). The eyes are
symmetric to within 1%. The entire 1.69x came from the wrong lid indices.

## Tests

`tests/test_eye_local_basis.py`, 8 tests, all new. `pytest -q`: **223 passed**
(was 215; no existing test changed).

Pinned: `v` unchanged when only the lid aperture changes; both eyes report the
same `v` for the same vertical gaze despite mirrored tilt and unequal apertures;
horizontal leak equal-and-opposite so the mean cancels; `u` still normalized by
eye width; `v` uses the fixed fraction; scale invariant to distance from camera;
collapsed contour and short contour still rejected (frame acceptance unchanged).

## Claims NOT being made

- **Not** that per-eye vertical contamination is fixed. It is equalized, not
  removed. Candidate B (removing the canthal tilt from the axis) is the change
  that would attack it directly, and remains available.
- **Not** that the vertical axis is now adequate. Investigation §4 stands: true
  vertical iris travel is ~1.6% of eye width against 16.9% horizontal.
- **Not** that the wrong lid indices are fixed. They are now only used as a
  degeneracy guard, where the error is harmless; candidate C is unnecessary
  rather than done.
- **Nothing** about accuracy until a live session exists.

## Pre-committed decision rule

Judge on whether the mapper starts *using* the vertical axis. Investigation §5
showed ridge shrinks the near-useless Y weights toward zero, so the symptom is
"Y ignored" (slope `d(dy)/d(target_y)` = **−0.961** and **−0.878** on the two
reference sessions) rather than "Y follows X". Tidier correlations alone are not
success.

- **keep** if slope `d(dy)/d(target_y)` moves clearly toward 0 — target better
  than **−0.80**, i.e. outside the reference pair's own range — **and** no eval
  slice regresses beyond the T060 variability envelope (mapped-key 6 pp,
  held-out 8.3 pp, row 4 pp, median error 2.8 px).
- **revert** if the slope does not move, or any slice regresses beyond that
  envelope.
- **inconclusive** if the session is blocked before evaluation, or if results
  land inside the envelope in both directions — at n=1 that is noise, per T060.

`hadar` is reported but does not decide: T060 measured its session-to-session
spread at a full letter, and it is a development word (SC-006).

Reference numbers to beat, from `runs/_feature004/T060_product_condition_reference.md`:
mapped-key 23% / 29%, median error 81.0 / 78.2 px, row 35% / 39%, held-out
25% / 33%, `hadar` 3/5 and 2/5.

## Live gate (completed 2026-08-20) — session `5e9c11d2c802`

Chin/head support. Calibration PASSED `warning_only`, 21 warnings, LOOCV 110.7 px.
`hadar` typed `hadaf` = 1/5 wrong focus (only R→F).

### Primary metric — did the mapper start using Y?

| session | slope `d(dy)/d(target_y)` | Y compression | `r(Y, pca_vL)` |
|---|---:|---:|---:|
| T060 ref 1 `689c8a8ce90c` | **−0.961** | 4.22x | +0.222 |
| T060 ref 2 `4f665467b260` | **−0.878** | 1.47x | +0.591 |
| T020 live `5e9c11d2c802` | **−0.887** | 4.41x | +0.254 |
| keep threshold | better than **−0.80** | — | — |

A slope of −1 means predicted Y is constant. **−0.887 is inside the T060
range**, 0.009 from the better reference, and does not beat −0.80. Predicted Y
spans 53 px against 234 px taught. The hypothesized mechanism did not fire.

### Slices vs the T060 envelope

| metric | ref 1 | ref 2 | envelope | this session | vs envelope |
|---|---:|---:|---|---:|---|
| mapped-key | 23% | 29% | 6 pp | **26%** | inside |
| median error | 81.0 px | 78.2 px | 2.8 px | **70.0 px** | 8.2 px better than best ref (beyond, good) |
| row accuracy | 35% | 39% | 4 pp | **35%** | ties worse ref |
| held-out | 25% | 33% | 8.3 pp | **42%** | 9 pp above best ref (just beyond, good) |
| editing | 0% | 20% | unusable at n=1 | 0% | ties worse ref |
| repeatability | 26.7% | 26.7% | 0 pp (suspicious) | 20% | worse; not a listed keep/revert metric |
| `hadar` wrong | 3/5 | 2/5 | 1 letter | **1/5** | 1 letter better than best ref (on the envelope; does not decide) |

No listed slice regresses beyond the envelope, so revert-for-regression does
not fire. Median and held-out moved the right way by more than session noise;
mapped-key and row did not; the slope did not.

### What the channels still look like

Change A predicted it would **equalize** per-eye leak, not remove it. Confirmed:

- `r(X, pca_vR) = −0.938` (T060: −0.901 / −0.899) — still the defect
- `r(u_right, v_right) = +0.945` (T060: +0.936 / +0.917) — right-eye `v` is
  still a copy of `u`
- `r(X, pca_vL) = −0.111` (was +0.536 / +0.493) — left-eye X-contamination
  flipped sign; not a keep signal
- fitted `w_y` left share **97%** (T060: 62% / 69%): the mapper dropped the
  right eye rather than using both at a compatible ratio. That is the opposite
  of the bet (compatible `a/b ≈ 1.09` so both eyes can contribute)

### Decision: INCONCLUSIVE

Keep fails: slope −0.887 does not beat −0.80.

Revert-for-regression fails: no listed slice is worse than the T060 envelope.

Revert-because-slope-did-not-move is the closest revert reading, but T060's
own rule was that a result inside these bands at n=1 is **inconclusive** until
a second session confirms. The slope is inside the pair's range. The secondary
improvements (median, held-out, `hadar`) are the wrong thing to bank as a keep
because they are not the pre-committed mechanism, and they are also the wrong
thing to throw away as a revert because they sit outside the noise band in the
good direction.

`hadar` 1/5 is the best product-condition result so far and the live R→F error
matches the benchmark's R→F exactly, which is a fidelity point, not an accuracy
one. It does not decide.

**Resolution path chosen 2026-08-20: a second product-condition session on
this same uncommitted tree.** Change A stays as-is; candidate B is not
implemented. The n=1 options to revert now or keep on missing slope evidence
are closed.

### Two-session rule (locked before session 2 exists)

Apply to session 2 (`9ca533f8c0f0`) together with session 1 (`5e9c11d2c802`).
Neither session is allowed to decide alone.

- **keep** if **both** sessions have slope `d(dy)/d(target_y)` better than
  **−0.80**, **and** neither session has a listed slice worse than the T060
  envelope relative to the T060 pair (mapped-key 6 pp below the worse of 23/29,
  held-out 8.3 pp below the worse of 25/33, row 4 pp below the worse of 35/39,
  median 2.8 px worse than the worse of 81.0/78.2).
- **revert** if **both** sessions have slope at or inside the T060 range
  (not better than −0.80), **or** if either session regresses a listed slice
  beyond that envelope.
- **inconclusive** if the two sessions disagree on the slope test (one beats
  −0.80, the other does not), **or** if session 2 is blocked before
  evaluation.

`hadar` is still reported and still does not decide. Median / held-out
movement in session 1 does not become a keep if session 2's slope also fails.

Candidate B stays unused until this verdict is KEEP, REVERT, or a new
explicit decision to abandon A.

## Live gate session 2 (completed 2026-08-20) — `9ca533f8c0f0`

Chin/head support, unchanged uncommitted Change A tree. Calibration PASSED
`warning_only`, 23 warnings, LOOCV 105.9 px. `hadar` typed `gsfs`.

### Primary metric across both T020-A sessions

| session | slope `d(dy)/d(target_y)` | Y compression | predicted Y span | `r(Y, pca_vL)` |
|---|---:|---:|---:|---:|
| T060 ref 1 | −0.961 | 4.22x | 55 px | +0.222 |
| T060 ref 2 | −0.878 | 1.47x | 159 px | +0.591 |
| T020-A s1 `5e9c11d2c802` | **−0.887** | 4.41x | 53 px | +0.254 |
| T020-A s2 `9ca533f8c0f0` | **−0.943** | **6.07x** | **39 px** | +0.155 |
| keep threshold | better than **−0.80** | — | — | — |

Neither T020-A session beats −0.80. Both sit inside the T060 range. Session 2
is *worse* than session 1 on the metric the change was supposed to move.
Predicted Y collapsed further (39 px against 234 px taught). The hypothesized
mechanism — mapper starts using Y — did not fire in either session, and it
did not repeat as an improvement.

### Slices vs T060 and vs session 1

| metric | T060-1 | T060-2 | T020-A s1 | T020-A s2 | pair reading |
|---|---:|---:|---:|---:|---|
| mapped-key | 23% | 29% | 26% | **23%** | inside envelope; not a repeatable gain |
| median error | 81.0 | 78.2 | 70.0 | **77.2** | s1's 8 px gain did **not** repeat (back inside 2.8 px of T060-2) |
| row accuracy | 35% | 39% | 35% | **29%** | **6 pp below worse T060 ref, beyond the 4 pp envelope** |
| held-out | 25% | 33% | 42% | **25%** | s1's held-out gain did **not** repeat |
| editing | 0% | 20% | 0% | 0% | unusable at n=1 |
| repeatability | 26.7% | 26.7% | 20% | 26.7% | not a listed metric |
| `median_\|dx\|/w` | 0.176 | 0.344 | 0.299 | **0.406** | worst of the four |
| `median_\|dy\|/h` | 0.862 | 0.714 | 0.774 | **0.916** | worst of the four |
| focus_stab held-out | 0.304 | 0.344 | 0.321 | **0.208** | **worst** of the four |
| `hadar` | 3/5 | 2/5 | 1/5 (`hadaf`) | **4/4 + miss (`gsfs`)** | not repeatable; s2 worse than both refs |

Session 1's median and held-out movement was session noise, which is why T060
forbade banking it at n=1.

### Channels — leak unchanged, still not a Y signal

| | T060-1 | T060-2 | T020-A s1 | T020-A s2 |
|---|---:|---:|---:|---:|
| `r(X, pca_vR)` | −0.901 | −0.899 | −0.938 | **−0.960** |
| `r(uR, vR)` | +0.936 | +0.917 | +0.945 | **+0.924** |
| `w_y` left share | 62% | 69% | 97% | 80% |
| X compression | 0.94x | 0.96x | 0.93x | 1.00x |

Horizontal mapping remains healthy. The right-eye vertical channel is still a
copy of its horizontal channel in both T020-A sessions. Change A equalized
scale; it did not create a usable Y feature. Diagnostic `avg_v` is **0.0 on
all 15 targets** in session 2 (clamp floor): `pca_v` sits entirely below −0.5.
That is a representation side-effect, not a keep signal.

### The "stable offset" impression — supported as compression, not as accuracy

The live report was: the gaze point felt more stable than before, but sat at a
fairly consistent positional offset rather than on the correct keys.

**What the data supports**

1. **Predicted Y barely moves.** Session 2 taught Y spans 234 px; predicted Y
   spans **39 px** (187–226). Looking from Q-row to Space, the mapper's Y
   output almost does not change. A cursor that does not travel vertically
   *feels* stable.
2. **Within-row vertical error is unusually tight**, which is the signature of
   a near-constant predicted Y, not of a global translation:
   - top row mean `dy` = **+73.5 ± 13.6 px** (every top key too low; 10/10)
   - home row mean `dy` = **+4.7 ± 10.1 px**
   - bottom row mean `dy` = **−70.5 ± 4.9 px** (every bottom key too high; 7/7)
   T060 top-row `dy` std was 27–32 px; T020-A s1 was 15.6; s2 is 13.6. Bottom
   row std 4.9 px is the tightest of the four sessions.
3. **The offset is not one offset.** Direction reverses by row. A true
   positional bias would be a similar `(dx, dy)` everywhere. Overall mean
   `(dx, dy) = (+21.4, +3.0)` looks small only because top and bottom cancel.
   That cancellation *is* slope ≈ −1.

**What the data contradicts**

- **Not lower tracking jitter.** Held-out `focus_stability` is **0.208**, the
  worst of the four product-condition sessions (T060 0.304 / 0.344, s1 0.321).
  Mean per-key stability 0.237 vs ~0.29. The overlay can look calm because the
  *model output* does not move in Y, even when the features are not calmer.
- **Not better mapping.** Mapped-key 23%, row 29%, `hadar` failed. Relative
  error `median_|dy|/h = 0.916` and `median_|dx|/w = 0.406` are the worst of
  the four.
- **Not a repeatable hadar path.** s1 was H/A/D/A correct and R→F (row miss).
  s2 was H→G, A→S, D→F, A→S, R missing (same-row X misses + a miss). The only
  shared live letter is not even shared: s1 hit H, s2 sent H to G.

So: **more consistent wrong Y per row**, caused by the mapper ignoring Y, which
can feel like a stable offset. That is the defect Change A was supposed to
fix, expressed more cleanly, not a benefit of the change.

### Decision: REVERT

Keep fails: neither session beats −0.80.

Revert fires twice, independently:

1. **Both** slopes are at or inside the T060 range (−0.887, −0.943).
2. Session 2 row accuracy 29% is beyond the 4 pp envelope vs the worse T060
   ref (35%).

Inconclusive does not apply: the sessions agree on the slope test (both fail),
and session 2 reached evaluation.

Session 1's median 70 px / held-out 42% / `hadar` 1/5 do not survive as
effects. They did not repeat.

Change A has been reverted. Product `gazekey/features/extractor.py` restored to
`861a89c` (T060 parent / T027 keep). The Change A unit file
`tests/test_eye_local_basis.py` was deleted. Session artifacts and this record
are kept as evidence.

Candidate B is **not** implemented here. Proposal:
`runs/_feature004/T020_canthal_tilt_proposal.md`.

X compression staying ~1.0 in both T020-A sessions confirms the remaining
blocker is still the vertical basis (canthal-tilt leak / tiny true iris
travel), which is candidate B's target, not a reason to keep A.
