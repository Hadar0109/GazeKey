# T020-C — Correct eyelid indices for aperture (**REVERT** 2026-08-20)

Parent tree is `861a89c` (T060 product state, after T020-A and T020-B revert).
The 0.15 `pca_vL` gate is unchanged.

- hypothesis: `_eye_uv_one_eye` computes aperture from the wrong contour
  slices. The variable named `upper` is entirely lower lid; `lower` is a
  mix that differs per eye. That makes the right-eye denominator ~2× too
  small and lets aperture vary with gaze X, which inflates X-in-`v`. Using
  the measured ring split (1–7 lower, 9–15 upper) should give both eyes the
  same true lid opening as the scale, without touching `y_hat = perp(x_hat)`.
- logical_area: features (T020 defect 1 / B-blocked-gate investigation §6)
- change: two slice expressions in `_eye_uv_one_eye` (`gazekey/features/extractor.py`).
  `upper = proj_y[1:5]` → `proj_y[9:16]`; `lower = concat(proj_y[5:8], proj_y[9:13])`
  → `proj_y[1:8]`. Tests: `tests/test_lid_aperture_indices.py`.
- kept unchanged: `perp(x_hat)` vertical axis, `u` normalization, iris pairing,
  FixationGate thresholds, 0.15 quality gate, mapper, collection, EAR/T061.
- condition: head-support — product condition
- eval_before: 14938da0bdf0, 34fb259ccdfd; T060 pair 689c8a8ce90c + 4f665467b260.
  T020-A and T020-B sessions are not `eval_before`.
- eval_after: 72c67227e52d (session 1), 29c07b6b989f (session 2)
- decision: **REVERT** (2026-08-20, two-session rule). Product code is still C pending review; do not stack further accuracy or gate changes.
- investigation: `runs/_feature004/T020_eye_local_basis_investigation.md` §1
- prior: A **REVERT**, B **REVERT** (blocked; leak not removed)

## What is wrong today

`EyeDetector` builds each eye as a 16-point ring, then `_eye_uv_one_eye`
treats ring positions as lids. Measured order (same for both eyes):

| ring pos | role |
|---|---|
| 0 | corner (u-axis end A) |
| **1–7** | **lower lid** |
| 8 | corner (u-axis end B) |
| **9–15** | **upper lid** |

Pre-C code (replaced):

```python
upper = proj_y[1:5]                                   # pos 1,2,3,4
lower = np.concatenate([proj_y[5:8], proj_y[9:13]])   # pos 5,6,7 + 9,10,11,12
```

`upper` is 100% lower lid. `lower` is a mix: left 4 lower + 3 upper (median
lands low); right 3 lower + 4 upper (median lands high). Probe-face apertures
were 0.824× true (left) and 0.525× true (right) for the same physical opening.

### Landmark IDs currently used as “upper” (all wrong)

These are `LEFT_EYE_INDICES` / `RIGHT_EYE_INDICES` positions 1–4:

| ring | MediaPipe left (subject) | MediaPipe right (subject) | actual lid |
|---:|---:|---:|---|
| 1 | **7** | **382** | lower |
| 2 | **163** | **381** | lower |
| 3 | **144** | **380** | lower |
| 4 | **145** | **374** | lower |

### Landmark IDs currently mixed into “lower”

| ring | left | right | actual lid |
|---:|---:|---:|---|
| 5 | 153 | 373 | lower |
| 6 | 154 | 390 | lower |
| 7 | 155 | 249 | lower |
| 9 | 173 | 466 | upper (near corner) |
| 10 | 157 | 388 | upper |
| 11 | 158 | 387 | upper |
| 12 | 159 | 386 | upper |

## Corrected sets (applied)

Exclude corners 0 and 8 (they define `x_hat`, not the lids). Use the full
lid arcs:

**Lower lid (both eyes): ring positions 1–7**

| ring | left | right |
|---:|---:|---:|
| 1 | 7 | 382 |
| 2 | 163 | 381 |
| 3 | 144 | 380 |
| 4 | 145 | 374 |
| 5 | 153 | 373 |
| 6 | 154 | 390 |
| 7 | 155 | 249 |

**Upper lid (both eyes): ring positions 9–15**

| ring | left | right |
|---:|---:|---:|
| 9 | 173 | 466 |
| 10 | 157 | 388 |
| 11 | 158 | 387 |
| 12 | 159 | 386 |
| 13 | 160 | 385 |
| 14 | 161 | 384 |
| 15 | 246 | 398 |

Positions 9 and 15 sit near the corners, so on a frontal probe one of them can
fall on the y-midline. Median of seven points is robust to that; do not special-
case per eye.

Applied code (only these two slice expressions, plus the ring-order comment):

```python
upper = proj_y[9:16]   # pos 9..15, upper lid
lower = proj_y[1:8]    # pos 1..7,  lower lid
```

`aperture = abs(median(lower) - median(upper))` is unchanged as a formula.
`y_hat` stays `perp(x_hat)` with +v down. Fallback quantile aperture unchanged.

## How aperture changes

On the probe face (true opening ≈ 0.0204 both eyes):

| eye | current aperture | corrected (true lids) | \|v\| scale change |
|---|---:|---:|---:|
| left | 0.01676 | 0.02034 | ×0.824 |
| right | 0.01076 | 0.02049 | ×0.525 |

Both eyes then agree on the unit. Leak coefficient `|y_hat_x| * eye_w /
aperture` goes from 0.441 / 0.745 (ratio 1.69) to about 4.02 / 4.33 in the
raw `|y_hat_x|/ap` units used in the investigation (ratio **~1.08**). Canthal
tilt remains (that was B); C only stops the denominator from being eye- and
X-dependent via the wrong mix.

**Scale coupling, not a second change:** `|v|` shrinks, more on the right.
FixationGate `max_std_pca` / `jump_threshold_pca` stay at their T060 values
(user constraint). That makes the vertical arm of the shared `max(std_u,std_v)`
gate slightly more permissive, the opposite of A's "hold collection constant"
trick. Record it; do not retune thresholds in this experiment.

## What this is not

- Not B (image-vertical `y_hat`).
- Not A (normalize `v` by eye width).
- Not T061 (EAR still uses `_EAR_CONTOUR_OFFSETS = (0,4,3,8,5,11)`).
- Not a 0.15 gate change.

## Decision rule (locked before any C session exists)

Same primary metric as A/B: the mapper must start *using* Y. Two product-
condition sessions from the start. **0.15 gate stays.**

- **keep** if **both** sessions reach evaluation, both have slope
  `d(dy)/d(target_y)` better than **−0.80**, and neither misses a listed T060
  slice (mapped-key 6 pp below 23%, held-out 8.3 pp below 25%, row 4 pp below
  35%, median 2.8 px worse than 81.0 px).
- **revert** if **both** sessions have slope at or inside the T060 range, or
  either session regresses a listed slice beyond that envelope.
- **inconclusive** if the two sessions disagree on the slope test, or a session
  is blocked before evaluation (including on `r(Y, pca_vL) < 0.15`).

`hadar` is reported and does not decide.

Mechanism checks, not keep criteria: left/right mean aperture should match;
`r(X, vL)` should not get worse than T060's +0.5 band; `vL` span should not
explode the way it did under B (0.17–0.27). If C equalizes scale but slope
stays near −0.9, that is a revert — same as A. Do not then lower 0.15.

**Live USER GATE complete.** Sessions `72c67227e52d` (`uerer`) and
`29c07b6b989f` (`udfdt`). Verdict **REVERT**. Product code is still C
pending review. No further accuracy or gate changes before that review.
Do not lower 0.15.

## Live gate (completed 2026-08-20)

Both sessions reached evaluation (`warning_only`). Chin/head support.

### Primary metric — did the mapper start using Y?

| session | slope `d(dy)/d(target_y)` | train Y compression | predicted Y span | `r(Y, pca_vL)` |
|---|---:|---:|---:|---:|
| T060 ref 1 `689c8a8ce90c` | **−0.961** | 4.22× | 55 px | +0.222 |
| T060 ref 2 `4f665467b260` | **−0.878** | 1.47× | 159 px | +0.591 |
| T020-C s1 `72c67227e52d` | **−1.137** | 2.97× | 79 px | +0.307 |
| T020-C s2 `29c07b6b989f` | **−0.940** | 2.95× | 79 px | +0.249 |
| keep threshold | better than **−0.80** | — | — | — |

Neither session beats −0.80. Session 2 is inside the T060 range. Session 1
is *worse than −1*: on eval locations predicted Y moved opposite target Y
(`r(Y, predY) = −0.273`). A slope of −1 means predicted Y is constant; C
did not make the mapper start using Y.

### Slices vs the T060 envelope

Floors from the locked rule (worse T060 ref minus envelope): mapped-key
17% (23% − 6 pp), held-out 16.7% (25% − 8.3 pp), row 31% (35% − 4 pp),
median ceiling 83.8 px (81.0 + 2.8).

| metric | T060-1 | T060-2 | C s1 | C s2 | vs envelope |
|---|---:|---:|---:|---:|---|
| mapped-key | 23% | 29% | **6%** | 26% | **s1: 17 pp below 23%, beyond 6 pp** |
| median error | 81.0 | 78.2 | **117.3 px** | **98.4 px** | **both worse than 83.8 px** |
| row accuracy | 35% | 39% | 32% | 45% | s1 3 pp below 35% (inside 4 pp); s2 better |
| held-out | 25% | 33% | **0%** | 42% | **s1: 25 pp below 25%, beyond 8.3 pp** |
| editing | 0% | 20% | 0% | 0% | unusable at n=1 |
| repeatability | 26.7% | 26.7% | 13.3% | 20% | not a listed metric |
| `median_\|dx\|/w` | 0.176 | 0.344 | 0.251 | 0.452 | s2 worst of the four |
| `median_\|dy\|/h` | 0.862 | 0.714 | **1.562** | 0.706 | s1 worst of the four |
| `hadar` | 3/5 `uaraf` | 2/5 `ywdar` | **4/5 `uerer`** | **5/5 `udfdt`** | reported, does not decide |

Session 1 misses mapped-key, held-out, and median. Session 2 misses median.
Either-session envelope miss is enough for revert on its own.

### Mechanism checks (not keep criteria)

C's scale claim did fire. T060 mean `vL`/`vR` was −0.337 / −0.542; C s1 is
−0.215 / −0.222 and s2 is −0.231 / −0.261. Left and right now share a unit.

It did not create a Y signal:

| | T060-1 | T060-2 | C s1 | C s2 |
|---|---:|---:|---:|---:|
| `r(X, pca_vL)` | +0.536 | +0.493 | +0.517 | **+0.753** |
| `r(X, pca_vR)` | −0.901 | −0.899 | −0.955 | **−0.982** |
| `r(Y, vL \| X)` | +0.198 | +0.623 | +0.297 | +0.259 |
| `r(uR, vR)` | +0.936 | +0.917 | +0.953 | +0.956 |
| span `vL` | 0.073 | 0.082 | **0.038** | 0.078 |
| `w_y` left share | 62% | 69% | 89% | 70% |

`r(X, vL)` on session 2 is worse than T060's +0.5 band. `vL` span did not
explode the way it did under B (0.17–0.27); session 1's span *shrank*,
which is the larger-aperture denominator. Row means of `vL` still do not
separate letter rows. Canthal leak remains (`r(X, vR)` ≈ −0.96). Equalizing
scale without usable Y is the same class of outcome as A.

Head was stable: `face_y` drift 0.00137 / 0.00123 (T060 0.00155 / 0.00269).
Not a head-motion session.

### Decision: REVERT

- Keep fails: neither slope beats −0.80.
- Inconclusive does not apply: both sessions reached evaluation, and they
  agree on the slope test (both fail).
- Revert fires twice: both slopes fail to leave the T060 "Y ignored" band
  (session 1 is worse than the band), **and** listed slices miss the
  envelope (session 1 mapped-key / held-out / median; session 2 median).

`hadar` 4/5 and 5/5 does not decide. Do not lower 0.15. Product code is
still C until review; restoring the T060 parent is the revert, not a new
experiment.

T020 feature-semantics candidates A, B, and C have all failed their locked
rules. T061 remains a separate collection-quality task, not stacked here.
