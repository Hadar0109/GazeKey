# ExperimentRecord

- hypothesis: (T020 change C, session 1 of 2) Correcting aperture lid indices to ring 1–7 lower / 9–15 upper, keeping `perp(x_hat)`, should equalize left/right `v` scale and let the mapper start using Y.
- logical_area: features (T020 defect 1)
- change: `gazekey/features/extractor.py` — `upper = proj_y[9:16]`, `lower = proj_y[1:8]`. Uncommitted at time of this session.
- condition: head-support — product condition
- eval_before: 14938da0bdf0 (A), 34fb259ccdfd (B); T060 pair 689c8a8ce90c + 4f665467b260. T020-A/B sessions are not `eval_before`.
- eval_after: 72c67227e52d
- decision: **revert** (pair with session 2 `29c07b6b989f`)
- keep_git_sha: n/a
- notes: >
    Corrected 2026-08-20: auto-created from the Phase A baseline template.
    This is the T020-C live gate, not a baseline capture.

    Calibration PASSED, `warning_only`, 14 warnings, LOOCV RMS 84.4 px.

    Evaluation FAILED: mapped-key 2/31 (6%), row 10/31 (32%), median 117.3 px,
    held-out 0%, editing 0%, repeatability 13.3%, focus stability (held-out)
    0.308. `hadar` typed `uerer` = 4/5 wrong focus.

    Locked rule: keep iff **both** sessions have slope `d(dy)/d(target_y)`
    better than **−0.80** and neither misses a listed T060 slice. This
    session slope = **−1.137** (worse than −1; eval `r(Y,predY)=−0.273`).
    Mapped-key 6% is 17 pp below 23% (envelope 6 pp). Held-out 0% is 25 pp
    below 25% (envelope 8.3 pp). Median 117.3 px is 36 px worse than 81.0
    (envelope 2.8 px). Row 32% is inside the 4 pp envelope.

    Mechanism: left/right mean `v` matched (−0.215 / −0.222 vs T060
    −0.337 / −0.542), so the denominator bug was the scale asymmetry.
    `r(X, pca_vR)=−0.955` still the leak. `vL` span 0.038 (shrank, not B's
    explosion). `r(Y, pca_vL)=+0.307` passed 0.15 and did not create a
    mapper that uses Y.

    Full scoring: `runs/_feature004/T020_lid_index_proposal.md`.
