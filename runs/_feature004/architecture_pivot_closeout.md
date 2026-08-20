# Feature 004 architecture-pivot closeout (2026-08-20)

Feature 004 remains an auditable historical record. This note does not
delete, renumber, or rewrite prior tasks or run artifacts.

**Product tree:** `gazekey/` and `tests/` are the T060 parent / T027 keep
state (`861a89c`; product code identical to `b07e768`). Candidate A/B/C
product and test changes were **not** restored.

**Exact pre-pivot snapshot** (including Candidate C code as it stood at
pivot time): branch `archive/004-pre-pivot-exact-20260820`, tag
`004-pre-pivot-exact-20260820`.

## T020 investigations (complete)

| Candidate | Decision | Sessions | Record |
|-----------|----------|----------|--------|
| A — gaze-invariant `v` scale (eye width) | **REVERT** | `5e9c11d2c802`, `9ca533f8c0f0` | `T020_vertical_scale_change.md` |
| B — image-vertical `y_hat` | **INCONCLUSIVE / not keepable and reverted** | blocked: `89b4349e848b`, `5e91836cbca2` | `T020_canthal_tilt_proposal.md`, `T020_B_blocked_gate_investigation.md` |
| C — correct aperture lid indices | **REVERT** | `72c67227e52d`, `29c07b6b989f` | `T020_lid_index_proposal.md` |

B's locked live rule was **inconclusive** when a session is blocked before
evaluation (both were). B is **not keepable**: it did not remove X→`v` leak
and lowering the 0.15 `pca_vL` gate would have licensed an unusable Y
feature. Product was restored to `861a89c`.

Investigation (no product change):
`runs/_feature004/T020_eye_local_basis_investigation.md`.
T060 pair: `runs/_feature004/T060_product_condition_reference.md`.

## Remaining A–F sequence: paused, not completed

Completed and kept on this tree: evaluation fidelity + baselines A/B,
T059 isolation, T026 findings, T027 KEEP, T060 product-condition
reference pair, and the T020 A/B/C investigations above.

T019, T021–T025, T028–T054, T057–T058, T061, and the rest of plan phases
A–F after those investigations are **paused**, not done. Unchecked tasks
stay unchecked on purpose.

Reason: repeated product-condition evidence shows the mapper ignores
vertical gaze (`d(dy)/d(target_y)` ≈ −0.9 on T060 and on T020-A/C). True
vertical iris travel is on the order of 1% of eye width; the handcrafted
eye-local `u`/`v` + PCA4 assumption does not yield a usable Y feature.
Continuing the Feature 004 one-change sequence inside that assumption is
not justified.

New architecture work has **not** started in this closeout.
