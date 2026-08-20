# T020-B blocked-gate investigation (no product change)

Two Candidate B calibrations were blocked before evaluation by the T027
vertical gate (`r(screen_y, pca_vL) ≥ 0.15`):

| session | `r(Y, pca_vL)` | LOOCV | warnings | reported blocker |
|---|---:|---:|---:|---|
| `89b4349e848b` | **0.116** | 114.7 px | 19 | pca_vL vs screen Y (not head drift) |
| `5e91836cbca2` | **0.006** | 98.3 px | 14 | pca_vL vs screen Y (not head drift) |

**B was reverted 2026-08-20.** Product tree is the T060 parent (`861a89c`).
The 0.15 gate is unchanged. Candidate C is a proposal only
(`runs/_feature004/T020_lid_index_proposal.md`).

**Replay limitation.** These runs store per-target mean `u`/`v`, not eye
contours or iris points. Identical frames cannot be pushed through pre-B and B
extractors. The counterfactual below is the linear analogue: residualize stored
`v` against target X. Target X and Y are nearly orthogonal (`r(X,Y)=+0.105` on
the keyboard15 grid), so removing X from `v` should **not** collapse `r(Y,v)`
if B were only deleting an X component.

## 1–2. Did B cause the drop, and did it remove X→v leak?

**B is implicated in the drop. It did not remove the leak. It reversed it and,
in session 2, made it stronger.**

| session | `r(X, vL)` | `r(Y, vL)` | `r(Y, vL \| X)` | `r(uL, vL)` | span `vL` |
|---|---:|---:|---:|---:|---:|
| T060-1 (pre-B) | **+0.536** | +0.222 | +0.198 | −0.488 | 0.073 |
| T060-2 (pre-B) | **+0.493** | +0.591 | +0.623 | −0.537 | 0.082 |
| T020-B fail 1 | **−0.385** | +0.116 | +0.171 | **+0.440** | **0.169** |
| T020-B fail 2 | **−0.697** | +0.006 | +0.111 | **+0.726** | **0.266** |

On the right eye, `r(X, vR)` only moved −0.90 → −0.80. The intended
`y_hat_x = 0` term is therefore not the whole X-in-`v` story.

`vL` span **grew** 2–3×. Extra variance is X-aligned. That is the opposite of
“delete a contaminating component.”

Because `r(X,Y)` is only +0.105, a **positive** X-in-`v` leak slightly
*inflated* pre-B `r(Y,vL)` (T060-1: 0.222 observed vs 0.198 after removing X).
A **negative** leak *deflates* it (fail 2: 0.006 observed vs 0.111 after
removing X). The gate is reading the deflated number.

## 3. How much genuine Y remains?

X-residual `r(Y, vL)`:

- T060-1: **0.198** (passed the 0.15 gate)
- T060-2: **0.623**
- B fail 1: **0.171**
- B fail 2: **0.111**

Row means of `vL` under B barely separate the letter rows (fail 1:
top −0.505, home −0.519, bottom −0.510, Space −0.463). Top/home/bottom letters
are indistinguishable. That is not enough for a Y mapper.

The mapper still *fit* (blocked only after). Fail 2 is the warning case:
`r(Y, predicted_Y)=+0.607` but **`r(X, predicted_Y)=+0.456`**, Y compression
only 2.47×. That “Y range” is partly stolen from X. Fail 1 collapsed instead
(Y compression 7.36×, `r(Y, predY)=0.167`).

So: a weak Y residual comparable to the worse T060 session still exists, but
raw `pca_vL` as the mapper consumes it is not a Y channel.

## 4–5. Is the 0.15 `pca_vL` gate still valid? Should it move?

**Yes it is still valid. No, it should not be lowered.**

T027 moved the gate onto `pca_vL` because that is what ridge fits for Y. After
B that is still the fitted channel. The gate is saying “this channel is not
Y,” which matches row means and the fail-2 mapper using X to fake Y.

Lowering 0.15 to let 0.116 / 0.006 through would admit fail 2, whose predicted
Y tracks screen X at 0.456. That is exactly masking an unusable / wrongly
oriented vertical feature.

A partial-correlation gate `r(Y, vL | X)` would pass fail 1 (0.171) and still
fail fail 2 (0.111), but the mapper does **not** residualize on X. Passing a
session whose raw `vL` is 70% X would feed that X into Y. Do not change the
gate to make B look like a keep.

## 6. What else is suppressing Y after B?

Most likely: **aperture, now measured along image Y, with the still-wrong lid
indices (candidate C).**

B changed `y_hat` for both the iris projection **and** the aperture
projection (same vector). Lid indices are still `upper=proj[1:5]` (actually
lower lid) and a mixed `lower`. Projecting that mix onto image Y makes
aperture vary with **column** (yaw): looking left vs right changes which
wrong-lid points sit where in image Y, so the denominator of `v = rel_y /
aperture` becomes an X signal. That explains, together:

- larger `vL` span
- new **negative** `r(X, vL)` (denominator, not canthal `y_hat_x`)
- `r(uL, vL)` flipping from ~−0.5 to +0.44 / +0.73 (axes no longer opposing;
  they share image-Y)

Perspective can add a real `rel_y` vs yaw term (camera below the face), but
that alone would not explode span 3×; a shrinking/varying aperture would.

Clamp is not the story: `avg_v` is not floored on these 15+15 targets (unlike
T020-A session 2). Aggregation is the same per-target mean. Outlier thresholds
were not touched.

## 7. Motion / collection?

Not the blocker, and not a sufficient explanation.

- `face_y` drift 0.00215 / 0.00162 — same band as T060 (0.00155 / 0.00269).
- No head-drift gate in the summary.
- `r(Y, eye_box_h)` is strongly negative on **all** four T060/B sessions
  (−0.84 to −0.95). Looking down changes apparent eye height; that is not new
  and is not what the gate reads.
- Fail 1 sample counts 37–42 (a bit more reset than the usual 41–42). Fail 2
  40–52, including 52 on `key_e` — messy, not empty. Fail 2 is the near-zero
  correlation session and is the better-sampled of the two.

## The two possibilities, separated

**B is wrong / destroys useful Y information — partly, as a feature choice.**
Image-vertical did not isolate gaze elevation. It replaced canthal X-leak
(`r(X,vL)≈+0.5`) with a larger opposite leak (`−0.39` / `−0.70`). Row
separation of `vL` is gone. That is a failed mechanism, not a bookkeeping
change in the gate.

**B correctly removes false X and reveals that the gate must change — no.**
X was not removed. The residual true-Y correlations (0.17 / 0.11) are in the
same weak band as T060-1 (0.20). The gate is failing because raw `pca_vL` is
an X-heavy mix, which is what ridge would fit. Changing the gate would not
recover a Y mapper; it would license the fail-2 behaviour (predicted Y
following X).

Locked T020-B rule: **inconclusive** if a session is blocked before
evaluation. Both were. That is not a keep and not yet an evidence-forced
revert of the *gate*; it is a failed live measurement of B.

## Outcome

1. **0.15 was not lowered.**
2. **B was reverted** (2026-08-20). Tree is the T060 parent (`861a89c`).
3. **C code landed 2026-08-20** (lid indices only; `perp(x_hat)` kept). Live
   sessions pending. Record: `runs/_feature004/T020_lid_index_proposal.md`.
