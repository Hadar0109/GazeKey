# ExperimentRecord

- hypothesis: (T017) Fixation gating on averaged 2-D PCA mean (u,v) silently accepts frames unstable in the mapper's 4-D vector.
- logical_area: collection
- change: FixationGate jump + stability use per-eye 4-D PCA (T017 tree)
- condition: free-head — NOT the product condition
- eval_before: 14938da0bdf0, 34fb259ccdfd
- eval_after: e3488095862f
- decision: inconclusive (see `runs/_feature004/T017_4d_fixation_gate.md`)
- keep_git_sha: n/a
- notes: >
    Corrected 2026-08-20. This file was auto-created with the Phase A baseline
    template; this session is NOT a current-state baseline. Baseline A is
    `14938da0bdf0` and baseline B is `34fb259ccdfd`, both captured before any
    mapping/collection change. This session ran on the T017 tree as run 3 of the
    controlled support-vs-free-head diagnostic.

    Result: passed the gates (Y r=+0.699, LOOCV 45.7 px) and beat A/B on
    evaluation (held-out inside-key 17% vs 0%/8%; median 65 px vs 130/107;
    LOOCV 46 vs 89/95). The `hadar` USER GATE was never collected.

    Why this is not a KEEP: n=1, no `hadar`, and the session was free-head. The
    product condition is with the chin/head support (spec Clarifications
    2026-08-20), so this result does not measure the product. It also had the
    largest `face_y` span of the four (0.0073), consistent with head pitch
    leaking into `pca_vL` — accuracy that would not survive stabilization.

    Details: `runs/_feature004/T017_controlled_rest_vs_free.md`.
