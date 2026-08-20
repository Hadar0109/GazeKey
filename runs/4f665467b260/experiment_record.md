# ExperimentRecord

- hypothesis: none — reference capture, not an experiment. (T060) Establish the session-to-session spread of the product condition on the kept T027 tree, so a later change can be told apart from noise.
- logical_area: eval
- change: **none** — unchanged tree at `861a89c` (product code identical to `b07e768`)
- condition: head-support — product condition
- eval_before: 14938da0bdf0 (A), 34fb259ccdfd (B)
- eval_after: 4f665467b260
- decision: n/a (reference capture — nothing to keep or revert)
- keep_git_sha: n/a
- notes: >
    Corrected 2026-08-20: auto-created from the Phase A baseline template, which
    mislabels every new session as a current-state baseline. This is
    **product-condition reference 2 of 2** (T060). Baselines A and B remain the
    free-head `eval_before` pair required by FR-026.

    Calibration PASSED, `warning_only`, 13 warnings, LOOCV RMS 82.3 px.
    Evaluation FAILED (expected): mapped-key 9/31 (29%), row 12/31 (39%),
    median 78.2 px, held-out 33%, editing 20%, repeatability 26.7%,
    focus stability (held-out) 0.344. `hadar` typed `ywdar` = 2/5 wrong focus.

    This session's vertical signal was much healthier than reference 1's:
    `r(Y, pca_vL) = +0.591` vs `+0.222`, and Y compression 1.47x vs 4.22x. It is
    the first session on record to clear the *preferred* 0.55 vertical
    threshold, which is why it carries 13 warnings instead of 19.

    `r(Y, avg_v) = +0.179`, i.e. **above** the old 0.15 threshold, so the old
    gate would have passed this session too. Only reference 1 actually needed
    T027. That does not weaken T027 — it sharpens the T026 finding, because two
    sessions in the same condition on the same tree land on opposite sides of the
    old threshold with a margin of 0.029.

    Horizontal is stable and vertical is not, across both references:
    `r(X, avg_h)` is −0.988/−0.994 and X compression 0.94x/0.96x, while
    `r(Y, pca_vL)` moves 0.222→0.591 and Y compression 4.22x→1.47x. Curiously
    `median_|dx|/w` was *worse* here (0.344 vs 0.176) while `median_|dy|/h` was
    better (0.714 vs 0.862) — the two axes moved in opposite directions between
    sessions, so neither can be read from a single run.

    `r(X, pca_vR) = −0.899` (vs −0.901 in reference 1), holding to −0.78…−0.97
    across all 18 sessions now on disk. This is the T020 defect and is the one
    quantity that does **not** vary session to session.

    Pair analysis and the variability envelope T020 must beat:
    `runs/_feature004/T060_product_condition_reference.md`.
