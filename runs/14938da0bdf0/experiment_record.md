# ExperimentRecord

- hypothesis: Current-state baseline after evaluation fidelity (Phase A). No mapping/collection product change.
- logical_area: eval
- change: none (current-state baseline)
- eval_before: n/a (this run is a baseline capture)
- eval_after: 14938da0bdf0
- decision: CurrentStateBaseline A
- keep_git_sha: n/a
- notes: Captured 2026-08-16 19:44:50 local (benchmark id 14938da0bdf0-bench1786898690) on the unchanged Feature 003 mapping path with Feature 004 evaluation fidelity in place. Calibration PASSED, quality_gate_kind=warning_only (14 warnings), LOOCV RMS 89.4 px. Mapped-key inside-tight 0/31 overall — repeatability 0.000 (0/15), held-out letters 0.000 (0/12), editing/control 0.000. Mean held-out focus stability 0.000. Median error 130 px; median |dx|/width 0.934, |dy|/height 0.731. Row accuracy 14/31 (45%). Clamp diagnostic: clamp_hit_rate 0.059, unclamped inside-key 0.000 (clamping is not what makes this fail). Pairs with baseline B 34fb259ccdfd (~5 min later, same code state, no mapping change between). USER GATE (T015) closed: hadar typed with suggestions unused, 5/5 keystrokes wrong focus (H->J, A->D, D->F, A->D, R->G) — see hadar_wrong_focus.md. See runs/_feature004/baseline_A_B_comparison.md.
