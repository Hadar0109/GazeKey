# Contract: Accuracy Experiment Discipline

**Version**: 1.0.0  
**Feature**: `004-gaze-mapping-accuracy`

## Purpose

Make mapping changes attributable. One logical area per iteration; unproven
work is not stacked.

## Baseline gate

```text
accuracy_code_change_allowed =
  CurrentStateBaseline A recorded
  AND CurrentStateBaseline B recorded
  AND evaluation fidelity notes written
  AND comparison method == method used for baseline A and B
```

No collection, mapper, smoother, layout, or clip change before that gate
except **evaluation-tool** changes required for R2 fidelity.

## Iteration record

```text
ExperimentRecord
  hypothesis: str
  logical_area: eval | collection | sync | geometry | coverage | mapper
  # collection includes warning-only quality gates and spatial row/col
  # metadata (Space / non-letter controls). geometry includes clip/clamp.
  # mapper includes auto-alpha selection (Phase E only).
  change: one focused modification
  eval_before: run ids (baseline A+B or last keep)
  eval_after: run id
  decision: keep | revert | inconclusive
  keep_git_sha: str  # required when decision == keep
```

## Decision meanings

| Decision | Meaning | Tree state |
|----------|---------|------------|
| `keep` | Held-out mapped-key (and supporting metrics) improved vs the two-session baseline, or a confirmed defect was removed without harm; `hadar` wrong-focus is not worse than both A and B | Becomes parent for the next experiment; **Git commit** of this state is required |
| `revert` | Harm or no benefit | Restore last keep **commit** before continuing |
| `inconclusive` | Cannot tell (noise, protocol error, mixed levers) | Do **not** stack; revert or isolate before the next change |

## Forbidden

- Two mapping levers in one iteration (e.g. aggregation **and** alpha)
- Layout count change **and** mapper change together
- Leaving an unproven change in the tree while starting the next experiment
- Using suggestion / prediction-bar accept to judge mapping word checks
- Using repeatability-only scores to `keep` a change that hurts held-out
  letters or editing/control keys
- Treating a failed first layout candidate as proof `keyboard15` is optimal
- Leaving a `keep` without a Git checkpoint

## Suggested area order (research R1)

`eval` (fidelity + baseline) → `collection` (incl. quality gates + spatial
metadata) → `sync` → `geometry` (incl. clip/clamp) → `coverage` → `mapper`
(incl. auto-alpha selection if Phase E is reached)

Skip forward only if evidence shows that area is not implicated; do not skip
**baseline**. Do not treat audit items as required patches.

## If the first hypothesis list is exhausted

Continue: coverage (further layout candidates, one per experiment), mapping
assumptions, feature sufficiency, current mapper (FR-035). Same iteration
contract. Do not stop while `hadar` wrong-focus is worse than both baselines
and held-out inside-key has not improved vs A and B.

## Final repeatability (SC-004)

On the kept stack only: three fresh calibration + evaluation sessions.
Reference floors: every session ≥ 53% mapped-key; best–worst spread ≤ 20 pp.
This is not the two-session current-state baseline.

## Usage notes — persist `ExperimentRecord` under `runs/<session_id>/`

Write one markdown file per iteration (and per baseline session) as
`runs/<session_id>/experiment_record.md`. Do not add a separate diagnostics
platform. Use `tools.evaluation.experiment_record.write_experiment_record`.

Copy this template (fill every field; `keep_git_sha` is required on `keep`):

```markdown
# ExperimentRecord

- hypothesis:
- logical_area: eval | collection | sync | geometry | coverage | mapper
- change:
- eval_before:  # baseline A+B session ids, or last keep
- eval_after:
- decision: keep | revert | inconclusive
- keep_git_sha:  # required when decision == keep; else omit or "n/a"
- notes:
```

**Phase A baseline:** two records with `logical_area: eval`, `change: none
(current-state baseline)`, `decision` left as the capture label
`CurrentStateBaseline A` / `CurrentStateBaseline B`. Later product/mapping
experiments MUST cite both `eval_before` ids (or the last keep). Missing A or
B blocks accuracy code changes.

**Hadar USER GATE (suggestions unused):** record wrong-focus letters
(H/A/D/R vs dwell) in `runs/<session_id>/hadar_wrong_focus.md` on both
baseline sessions (and after every later keep candidate).
