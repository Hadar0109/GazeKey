# ExperimentRecord

- hypothesis: (T017 controlled diagnostic, run 1 of 4) Does the chin/head support change calibration or mapping quality?
- logical_area: collection
- change: none in this session (T017 4-D fixation gate was already in the tree and constant across all four controlled runs)
- condition: head-support — product condition
- eval_before: 14938da0bdf0, 34fb259ccdfd
- eval_after: blocked (catastrophic avg_v vs screen-Y, r=+0.019 vs threshold 0.15) — mapping evaluation never ran
- decision: n/a (diagnostic session, not an experiment verdict)
- keep_git_sha: n/a
- notes: >
    Created 2026-08-20 from the controlled-diagnostic analysis; the session
    produced no record at capture time because it never reached evaluation.

    All 15/15 targets collected. Blocked by the vertical sanity gate on clamped
    binocular `avg_v`, yet the mapper-relevant vertical signal was *better* than
    both accepted baselines: `r(Y, pca_vL)` = +0.459 (A +0.357, B +0.344) and
    LOOCV RMS 86.6 px (A 89.4, B 95.2). The gate scored a proxy the mapper does
    not fit.

    This session is part of the pre-change reference for T027 (the vertical-gate
    change) under the product condition. Aggregate analysis:
    `runs/_feature004/T017_controlled_rest_vs_free.md`,
    `runs/_feature004/T017_y_correlation_investigation.md`.
