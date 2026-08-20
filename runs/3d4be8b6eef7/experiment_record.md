# ExperimentRecord

- hypothesis: (T017 controlled diagnostic, run 4 of 4) Does the chin/head support change calibration or mapping quality?
- logical_area: collection
- change: none in this session (T017 4-D fixation gate was already in the tree and constant across all four controlled runs)
- condition: free-head — NOT the product condition
- eval_before: 14938da0bdf0, 34fb259ccdfd
- eval_after: blocked (eye_box_h span 0.0068 plus catastrophic avg_v vs screen-Y, r=-0.080) — mapping evaluation never ran
- decision: n/a (diagnostic session, not an experiment verdict)
- keep_git_sha: n/a
- notes: >
    Created 2026-08-20 from the controlled-diagnostic analysis; the session
    produced no record at capture time because it never reached evaluation.

    This is the free-head counterpart that also failed, which is why removing
    the support is not a fix: free-head was 1/2 usable, not 2/2. It is the
    reason the support-vs-free comparison cannot carry a verdict on its own.

    Aggregate analysis: `runs/_feature004/T017_controlled_rest_vs_free.md`.
