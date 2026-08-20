# ExperimentRecord

- hypothesis: (T017 controlled diagnostic, run 2 of 4) Does the chin/head support change calibration or mapping quality?
- logical_area: collection
- change: none in this session (T017 4-D fixation gate was already in the tree and constant across all four controlled runs)
- condition: head-support — product condition
- eval_before: 14938da0bdf0, 34fb259ccdfd
- eval_after: blocked (catastrophic avg_v vs screen-Y, r=+0.142 vs threshold 0.15) — mapping evaluation never ran
- decision: n/a (diagnostic session, not an experiment verdict)
- keep_git_sha: n/a
- notes: >
    Created 2026-08-20 from the controlled-diagnostic analysis; the session
    produced no record at capture time because it never reached evaluation.

    All 15/15 targets collected. This is the strongest vertical signal recorded
    in any session on disk — `r(Y, pca_vL)` = +0.625 vs +0.357 (A) and +0.344
    (B) — with the best LOOCV RMS of the four controlled runs under the support
    (81.5 px) and the fewest quality warnings. It was still rejected, missing
    the 0.15 threshold on clamped binocular `avg_v` by 0.008.

    Mechanism: `avg_v` averages `(0.5 + pca_vL)` and `(0.5 + pca_vR)` after
    clamping to [0,1], and `pca_vR` tracks screen **X** in every session on disk
    (`r(X, vR)` -0.78…-0.97). A clean `vL` Y-signal is diluted by an
    X-contaminated `vR` channel.

    This session is part of the pre-change reference for T027 (the vertical-gate
    change) under the product condition. Aggregate analysis:
    `runs/_feature004/T017_controlled_rest_vs_free.md`,
    `runs/_feature004/T017_y_correlation_investigation.md`.
