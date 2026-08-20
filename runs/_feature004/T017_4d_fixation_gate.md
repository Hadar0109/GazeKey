# ExperimentRecord

- hypothesis: Fixation gating on averaged 2-D PCA mean (u,v) silently accepts frames that are unstable in the mapper’s 4-D vector (pca_uL, pca_vL, pca_uR, pca_vR).
- logical_area: collection
- change: FixationGate jump + stability use per-eye 4-D PCA. Legacy avg_h/avg_v checks kept.
- condition: mixed — the one usable eval was free-head, i.e. NOT the product condition
- eval_before: 14938da0bdf0, 34fb259ccdfd
- eval_after: e3488095862f (only session of the controlled four that reached mapping eval; free-head). Blocked (no eval): 2879900a17e0, bfb745b0b87e (WITH support); 3d4be8b6eef7 (free-head, eye_box_h + Y). Earlier blocked: 0694c1663623, 42662808ac84, cfdd5f1ea546.
- decision: inconclusive
- disposition: REVERTED FOR ISOLATION — done 2026-08-20 under T059. The revert is not a verdict on the hypothesis.
- change_git_sha: bedfb86 (touched `gazekey/calibration/fixation_gate.py` only; reverted to `bedfb86^`, verified byte-identical)
- keep_git_sha: n/a
- notes: >
    Controlled diagnostic (2 WITH support, 2 free-head) shows the Y-gate block
    tracks the support condition (0/2 usable with support, 1/2 free-head), and
    T017 code was constant across all four, so T017 is not the cause of the
    blocks. The same block also fired pre-T017 (`05e40e22688f`, r=-0.119).

    Not KEEP: n=1 eval, hadar never collected, and that single supporting eval
    was free-head — it says nothing about the product condition (chin/head
    support, spec Clarifications 2026-08-20).

    Not a substantive REVERT either: the hypothesis is still open. The code is
    reverted under T059 purely to restore a clean, proven parent, because the
    next experiment (T027, the vertical-gate change) must be the only change in
    its tree (FR-026). Leaving an unproven change underneath it would make the
    T027 result unattributable.

    Re-test T017 as its own experiment after T060, once a session can pass under
    the product condition and an evaluation is actually reachable.

    Isolation carried out 2026-08-20 (T059). What the reverted tree does, now
    pinned in `tests/test_fixation_head_gate.py`, is the concrete statement of
    this hypothesis: the gate averages the eyes into a 2-D mean, so opposing-eye
    jitter of +/-0.08 per frame locks as a "stable" fixation, and a 0.15
    one-eye jump becomes 0.075 in the mean — under the 0.10 `jump_threshold_pca`
    — and is accepted. The mapper meanwhile fits all four channels
    independently. Those pins are the failing-behavior evidence to re-measure
    against when T017 is retried under the product condition.

    Details: `T017_controlled_rest_vs_free.md`,
    `T017_y_correlation_investigation.md`.
