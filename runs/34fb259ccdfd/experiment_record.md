# ExperimentRecord

- hypothesis: Current-state baseline after evaluation fidelity (Phase A). No mapping/collection product change.
- logical_area: eval
- change: none (current-state baseline)
- eval_before: n/a (this run is a baseline capture)
- eval_after: 34fb259ccdfd
- decision: CurrentStateBaseline B
- keep_git_sha: n/a
- notes: Captured 2026-08-16 19:49:34 local (benchmark id 34fb259ccdfd-bench1786898974) on the unchanged Feature 003 mapping path with Feature 004 evaluation fidelity in place. Calibration PASSED, quality_gate_kind=warning_only (16 warnings), LOOCV RMS 95.2 px. Mapped-key inside-tight 3/31 overall — repeatability 0.133 (2/15: T, L), held-out letters 0.083 (1/12: Y), editing/control 0.000. Mean held-out focus stability 0.116. Median error 107 px; median |dx|/width 0.506, |dy|/height 0.987. Row accuracy 11/31 (35%). Clamp diagnostic: clamp_hit_rate 0.036, unclamped inside-key 0.097 vs clamped 0.097 (clamping is not what makes this fail). Pairs with baseline A 14938da0bdf0 (~5 min earlier, same code state, no mapping change between). USER GATE (T015) closed: hadar typed with suggestions unused, 4/5 keystrokes wrong focus (H ok, A->S, D->F, A->S, R->F) — see hadar_wrong_focus.md. See runs/_feature004/baseline_A_B_comparison.md.
