# ExperimentRecord

- hypothesis: (T020 change A, session 2 of 2) Normalizing `v` by a gaze-invariant fraction of eye width should let the mapper start using the vertical axis. Session 1 (`5e9c11d2c802`) was inconclusive at n=1 (slope −0.887, inside the T060 band). This session exists to close the two-session rule locked before it was run.
- logical_area: features (research R6 item 3)
- change: same uncommitted Change A as session 1 — `v_n = v / (_V_SCALE_PER_EYE_WIDTH * eye_w)` in `gazekey/features/extractor.py`. No other product change.
- condition: head-support — product condition
- eval_before: 14938da0bdf0 (A), 34fb259ccdfd (B); T060 pair 689c8a8ce90c + 4f665467b260; T020-A session 1 5e9c11d2c802
- eval_after: 9ca533f8c0f0
- decision: **revert** (pair verdict with session 1; see `runs/_feature004/T020_vertical_scale_change.md`)
- keep_git_sha: n/a
- notes: >
    Corrected 2026-08-20: auto-created from the Phase A baseline template.
    This is T020-A session 2, not a baseline capture.

    Calibration PASSED, `warning_only`, 23 warnings, LOOCV RMS 105.9 px.
    Evaluation FAILED: mapped-key 7/31 (23%), row 9/31 (29%), median 77.2 px,
    held-out 25%, editing 0%, repeatability 26.7%, focus_stab_held_out 0.208.
    `hadar` typed `gsfs` = 4/4 registered wrong + R missing.

    Slope `d(dy)/d(target_y)` = **−0.943**. Keep threshold is better than
    −0.80. T060 range is −0.961 / −0.878. This is inside the T060 range and
    worse than session 1 (−0.887). Y compression **6.07x** (taught 234 px →
    predicted 38.6 px), worse than session 1 (4.41x) and both T060 refs.

    Two-session rule, locked before this run: revert if **both** slopes stay
    at or inside the T060 range. Session 1 −0.887 and session 2 −0.943 both
    fail. Independently, row accuracy 29% is 6 pp below the worse T060 ref
    (35%), beyond the 4 pp envelope.

    The "stable offset" impression is Y-compression, not a translation and
    not lower jitter. Predicted Y barely moves, so the cursor feels steady
    and always a bit off; within-row dy is tightly clustered (top +73.5±13.6,
    bottom −70.5±4.9) while held-out focus_stability is the **worst** of the
    four product-condition sessions (0.208 vs 0.304 / 0.344 / 0.321).
