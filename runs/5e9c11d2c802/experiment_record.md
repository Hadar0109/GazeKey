# ExperimentRecord

- hypothesis: (T020 change A) Normalizing `v` by a gaze-invariant fraction of eye width, identical for both eyes, should let the mapper start *using* the vertical axis instead of ignoring it.
- logical_area: features (research R6 item 3)
- change: `gazekey/features/extractor.py` — `v_n = v / aperture` → `v_n = v / (_V_SCALE_PER_EYE_WIDTH * eye_w)` with `_V_SCALE_PER_EYE_WIDTH = 0.152`. Uncommitted at time of this session.
- condition: head-support — product condition
- eval_before: 14938da0bdf0 (A), 34fb259ccdfd (B); same-condition T060 pair 689c8a8ce90c + 4f665467b260
- eval_after: 5e9c11d2c802
- decision: **inconclusive** at n=1; pair with session 2 `9ca533f8c0f0` → **revert**
- keep_git_sha: n/a
- notes: >
    Corrected 2026-08-20: auto-created from the Phase A baseline template.
    This is the T020 live gate, not a baseline capture.

    Calibration PASSED, `warning_only`, 21 warnings, LOOCV RMS 110.7 px
    (worse than both T060 refs: 104.3 / 82.3).

    Evaluation FAILED (expected): mapped-key 8/31 (26%), row 11/31 (35%),
    median 70.0 px, held-out 42%, editing 0%, repeatability 20%,
    focus stability (held-out) 0.321. `hadar` typed `hadaf` = 1/5 wrong focus.

    Pre-committed rule: keep iff slope `d(dy)/d(target_y)` beats **−0.80**
    (outside the T060 range −0.961 / −0.878) AND no slice regresses beyond
    the T060 envelope. Measured slope = **−0.887**. That is inside the
    reference pair, 0.009 from the better ref, and does not beat −0.80.
    The hypothesized mechanism — mapper starts using Y — did not fire.

    Slices vs T060 envelope (mapped-key 6 pp, held-out 8.3 pp, row 4 pp,
    median 2.8 px): mapped-key 26% is inside 23–29; row 35% ties the worse
    ref; median 70 px is **8.2 px better** than the better ref (beyond the
    2.8 px envelope in the good direction); held-out 42% is **9 pp** above
    the better ref (just beyond 8.3 pp, good direction). No listed slice
    regresses beyond the envelope, so revert-for-regression does not fire.

    Y compression 4.41x (taught 234 → predicted 53), vs T060 4.22x / 1.47x.
    `r(Y, pca_vL) = +0.254` (vs +0.222 / +0.591). `r(u_right, v_right) = +0.945`
    and `r(X, pca_vR) = −0.938` — the right-eye leak is unchanged, as change A
    predicted (equalize, do not remove). Fitted `w_y` left share 97%: the
    mapper dropped the right eye rather than using both at a compatible ratio.

    Full scoring: `runs/_feature004/T020_vertical_scale_change.md`.
