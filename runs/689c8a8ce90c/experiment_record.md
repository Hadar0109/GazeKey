# ExperimentRecord

- hypothesis: (T027) The blocking vertical check scores `avg_v`, a clamped binocular mean the mapper never consumes, so it rejects product-condition sessions before they can be measured. Scoring `pca_vL` — the channel the mapper fits Y from — should let such a session reach evaluation without admitting genuinely inverted ones.
- logical_area: collection (research R10 — quality / pass-fail gates)
- change: `gazekey/calibration/quality.py` — catastrophic (0.15) and preferred (0.55) vertical checks now score `r(screen_y, pca_vL)` instead of `r(screen_y, avg_v)`. Thresholds, blocking semantics and the warning band unchanged; `avg_v` still reported as a diagnostic.
- condition: head-support — product condition
- eval_before: 14938da0bdf0 (A), 34fb259ccdfd (B)
- eval_after: 689c8a8ce90c
- decision: **keep**
- keep_git_sha: b07e768 (parent 6156659 = T059 isolation revert)
- notes: >
    Corrected 2026-08-20: this file was auto-created from the Phase A baseline
    template. This session is NOT a current-state baseline; A and B are.

    The change was genuinely exercised. On this session
    `r(Y, avg_v) = -0.152`, so the OLD gate would have BLOCKED it (the value is
    not merely under the 0.15 threshold, it is negative). `r(Y, pca_vL) = +0.222`
    passed the new check. This is the 6th session captured with the chin/head
    support and the FIRST to reach mapping evaluation.

    Calibration PASSED, `warning_only`, 19 warnings, LOOCV RMS 104.3 px.

    Evaluation vs both baselines (31 locations):

    | metric | A | B | this | verdict |
    |---|---|---|---|---|
    | mapped-key | 0% | 10% | **23%** | best |
    | median error | 130 px | 107 px | **81 px** | best |
    | held-out inside-key | 0% | 8% | **25%** | best |
    | editing/control | 0% | 0% | 0% | tie |
    | row accuracy | 45% | 35% | 35% | ties B, **below A** |
    | `hadar` wrong focus | 5/5 | 4/5 | **3/5** | best |

    Decision per the pre-committed rule in
    `runs/_feature004/T027_vertical_gate_representation.md`: the session reached
    evaluation under the product condition, and eval slices plus `hadar` are no
    worse than the worse of A and B (A). KEEP.

    ATTRIBUTION LIMIT — read before citing these numbers. T027 touches only the
    quality gate. It does not change feature extraction, fixation gating,
    aggregation, ridge fitting, or prediction, so it CANNOT have improved mapping
    accuracy. The eval and `hadar` gains over A/B are session-to-session
    variation, not an effect of this change. The keep is earned by the gate
    change doing its one job — making the product condition measurable — plus the
    absence of regression. Do not report 23% / 81 px / 3-of-5 as an accuracy
    result produced by T027.

    Row accuracy (35%) is below baseline A (45%). Not treated as a regression for
    the same reason: the mapping path is byte-identical to A's, so this is noise
    in the same direction as the other metrics' noise. It is recorded so the next
    experiment cannot quietly claim it as an improvement.

    Still not usable typing. The vertical axis is the blocker and is now
    quantified: taught Y spans 128–362 px (234 px) while predicted Y spans only
    177.8–233.2 px (55 px) — the mapper compresses Y by ~4.3x. `pca_vL` spans
    just 0.072 across all 15 targets. `median_|dy|/h = 0.862` vs
    `median_|dx|/w = 0.176`. All three live `hadar` errors were row errors with
    the correct column neighbourhood.

    `r(X, pca_vR) = -0.901` again, consistent with all 16 prior sessions. That is
    the T020 defect and the next experiment.
