# T020-B — Image-vertical `v` axis (**REVERTED 2026-08-20**)

Parent tree is `861a89c` (T060 product state, after T020-A revert).

- hypothesis: `y_hat = perp(x_hat)` inherits the eye's canthal tilt, so `v`
  contains a horizontal component of opposite sign per eye (`y_hat_x` ≈ −0.082
  left / +0.089 right). Replacing that with image-vertical `(0, 1)` removes the
  leak **per eye**, which Change A could not do (A only equalized it). The
  mapper should then start using Y instead of shrinking the Y weights to zero.
- logical_area: features (research R6 item 3 / T020 defect 2)
- change: one assignment in `_eye_uv_one_eye` (`gazekey/features/extractor.py`).
  `y_hat = perp(x_hat)` → `y_hat = (0, 1)`. `u`, aperture normalization, lid
  indices, and gate thresholds unchanged.
- condition: head-support — product condition
- eval_before: 14938da0bdf0 (A), 34fb259ccdfd (B); T060 pair 689c8a8ce90c +
  4f665467b260. T020-A sessions 5e9c11d2c802 and 9ca533f8c0f0 are **not**
  `eval_before` — they were taken on a reverted tree.
- eval_after: **BLOCKED** — `89b4349e848b` (r=0.116), `5e91836cbca2` (r=0.006). Neither reached evaluation.
- decision: **REVERT** (2026-08-20). Blocked before evaluation (locked rule: inconclusive at n=blocked), then reverted because B did not remove X→v leak and lowering 0.15 would mask an unusable Y feature. Investigation: `runs/_feature004/T020_B_blocked_gate_investigation.md`.
- keep_git_sha: n/a
- disposition: **REVERTED 2026-08-20.** `gazekey/features/extractor.py` restored to `861a89c`. `tests/test_eye_local_basis.py` (B pins) deleted. 0.15 gate untouched.
- investigation: `runs/_feature004/T020_eye_local_basis_investigation.md` §2, §9
- prior experiment: Change A **REVERT** — `runs/_feature004/T020_vertical_scale_change.md`

## Why B, and why not restack A

Change A equalized the leak (right/left ratio 1.69 → 1.09) and bet that the
mapper could then cancel it while summing the true Y signal. Two live sessions
showed it did not: slopes −0.887 and −0.943, both inside the T060 band, Y
compression 4.41× then 6.07×. The leak itself was still there
(`r(X, pca_vR)` −0.938 / −0.960).

B attacks the leak at the source. On the probe face, `dv/d(dx)` was −4.875
(left) and +8.250 (right) solely because `y_hat_x ≠ 0`. Image-vertical sets
`y_hat_x = 0`, so that term is identically zero. True vertical gain changes
only from `y_hat_y` 0.996 → 1.000 (~0.4%), so FixationGate thresholds do not
need a rescale — unlike A, this is not a scale-changing experiment.

Aperture stays the normalizer (A is reverted). Lid-index bug (candidate C) is
not touched. One change.

## Exact product diff (applied, then reverted)

Was (T060 parent):

```python
y_hat = np.array([-x_hat[1], x_hat[0]], dtype=np.float64)
if float(y_hat[1]) < 0.0:
    y_hat = -y_hat
```

Proposed and now applied:

```python
# Image down. Do not inherit canthal tilt from x_hat: perp(x_hat) gives y_hat
# a horizontal component of opposite sign per eye, which leaks gaze-X into v.
y_hat = np.array([0.0, 1.0], dtype=np.float64)
```

`u` still uses `x_hat` (corner axis). `v` and the aperture projection both use
this `y_hat`, so they stay in one basis. `u` and `v` are no longer guaranteed
orthonormal when the eye is rolled; they are just features, and the mapper
already treats them as independent channels.

## What this is and is not claiming

- **Does** remove per-eye X-into-v leak from canthal tilt.
- **Does not** fix the gaze-dependent aperture normalizer (defect 3 / reverted
  A). `v` is still divided by lid opening.
- **Does not** fix the wrong lid indices (candidate C).
- **Does not** increase true vertical iris travel (~1.6% of eye width). If
  landmark noise is comparable, B can still fail the slope test for the same
  reason A did. That is a stop condition, not a reason to skip the experiment.

## Tests (deleted with the revert)

`tests/test_eye_local_basis.py` pinned B's image-vertical `y_hat`. Deleted
with the revert. The T060 parent has no extra T020-B tests.

## Decision rule (locked before any B session exists)

Same primary metric as A, because the claim is the same: the mapper starts
*using* Y. T060 envelope still applies. Because A showed n=1 cannot decide,
**two** product-condition sessions are required from the start.

- **keep** if **both** sessions have slope `d(dy)/d(target_y)` better than
  **−0.80** (outside the T060 range −0.961 / −0.878) **and** neither session
  has a listed slice worse than the T060 envelope (mapped-key 6 pp below 23%,
  held-out 8.3 pp below 25%, row 4 pp below 35%, median 2.8 px worse than
  81.0 px).
- **revert** if **both** sessions have slope at or inside the T060 range, **or**
  if either session regresses a listed slice beyond that envelope.
- **inconclusive** if the two sessions disagree on the slope test, or a session
  is blocked before evaluation.

`hadar` is reported and does not decide.

**Live sessions existed and were blocked.** Both calibrations failed the 0.15
`pca_vL` gate before evaluation. The blocked-gate investigation showed B did
not remove X→v leak; it reversed and strengthened it. Lowering 0.15 would
admit a mapper that uses X as Y. **REVERT.** 0.15 unchanged.

Candidate C is a later standalone proposal on the restored T060 parent
(`runs/_feature004/T020_lid_index_proposal.md`): correct lid indices, keep
`perp(x_hat)`. Not stacked on B. T061 remains separate.
