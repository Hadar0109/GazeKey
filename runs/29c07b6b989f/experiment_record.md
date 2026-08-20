# ExperimentRecord

- hypothesis: (T020 change C, session 2 of 2) Same lid-index correction as session 1 `72c67227e52d`. Two-session rule already locked.
- logical_area: features (T020 defect 1)
- change: same uncommitted C tree (`upper = proj_y[9:16]`, `lower = proj_y[1:8]`, `perp(x_hat)` unchanged)
- condition: head-support — product condition
- eval_before: 14938da0bdf0 (A), 34fb259ccdfd (B); T060 pair 689c8a8ce90c + 4f665467b260
- eval_after: 29c07b6b989f
- decision: **revert** (pair with session 1 `72c67227e52d`)
- keep_git_sha: n/a
- notes: >
    Corrected 2026-08-20: auto-created from the Phase A baseline template.
    This is T020-C live gate session 2 of 2, not a baseline capture.

    Calibration PASSED, `warning_only`, 20 warnings, LOOCV RMS 99.8 px.

    Evaluation FAILED: mapped-key 8/31 (26%), row 14/31 (45%), median 98.4 px,
    held-out 42%, editing 0%, repeatability 20%, focus stability (held-out)
    0.333. `hadar` typed `udfdt` = 5/5 wrong focus.

    Slope `d(dy)/d(target_y)` = **−0.940**. Keep threshold is better than
    −0.80. This is inside the T060 range (−0.961 / −0.878). Median 98.4 px
    is 17.4 px worse than 81.0 (beyond the 2.8 px envelope). Mapped-key 26%
    and held-out 42% and row 45% do not save the pair: session 1 already
    missed mapped-key, held-out, and median, and neither slope beat −0.80.

    `r(X, pca_vL)=+0.753` is worse than T060's +0.5 band. `r(X, pca_vR)=−0.982`.
    Mean `vL`/`vR` −0.231 / −0.261 (scale closer than T060, still not a Y
    mapper).

    Two-session rule: **REVERT**. Product code still C pending review.
    Full scoring: `runs/_feature004/T020_lid_index_proposal.md`.
