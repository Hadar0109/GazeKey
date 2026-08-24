# Feature 005 integrated acceptance (Stage F)

**Date**: 2026-08-24  
**Verdict**: **PASS**. Cleanup hold **released** (T063). Stage G may begin at
T064 after this record is on the pre-cleanup checkpoint commit. Do not
start deletions in T064.

This is not a Feature 004 T060 comparison and does not use those formulas as
a cleanup trigger.

**Production path (preserved)**: GazeFollower 1.0.2 → GazeSample →
`origin+dpr` → live QRect hit-test → dwell → ActionDispatcher / OS.
No post-GF mapper, key resize, or extra smoothing.

---

## Sessions (SC-001)

| Session | Id | Status |
|---------|-----|--------|
| 1 | `005-t054-20260824` | USER-REPORTED PASS (integrated keyboard; residual error accepted) |
| 2 | `005-t055-20260824` | USER-REPORTED PASS (functional sweep + extra gates below) |
| 3 | `005-t056-20260824` | USER-REPORTED PASS (letters, editing, suggestions, dwell, OS typing) |

Three distinct chin/head-support sessions. One run does not decide cleanup;
three recorded sessions do.

## Functional USER GATEs

| Gate | Result | Record |
|------|--------|--------|
| T045 recalibration | PASS | `runs/005-t045-recalibrate-20260824/summary.md` |
| T054 session 1 | PASS | `runs/005-t054-20260824/summary.md` |
| T055 session 2 | PASS | `runs/005-t055-20260824/summary.md` |
| T056 session 3 | PASS | `runs/005-t056-20260824/summary.md` |
| T057 `hadar` | **deferred / not scored** | `runs/_feature005/T057_hadar_deferred.md` |
| T058 blink / invalid gaze | PASS (session 2) | dwell does not complete; no OS type |
| T059 OS typing | PASS (session 2; reconfirmed session 3) | external application via ActionDispatcher |
| T060 suggestion accept | PASS (session 2) | Feature 005; suffix + Space. Not Feature 004 T060 |
| T061 second user | explicit skip | `runs/_feature005/T061_second_user_skip.md` |

## Success criteria

| ID | Result | Notes |
|----|--------|-------|
| SC-001 | **PASS** | three distinct sessions: T054, T055, T056 |
| SC-002 | PASS | letters, editing, suggestions (sessions 2 and 3) |
| SC-003 | PASS | letter rows reachable |
| SC-004 | PASS | editing keys reachable |
| SC-005 | PASS | suggestion slots reachable / visible |
| SC-006 | not scored as mapping metric | residual error accepted; accuracy work not reopened |
| SC-007 | PASS | dwell-usable pointing on integrated path |
| SC-008 | qualitative PASS | live dwell interaction; no numeric latency log |
| SC-009 | PASS | T059 / T056 OS typing |
| SC-010 | **not scored** | `hadar` deferred; must not override other SCs; not a cleanup gate |
| SC-011 | PASS | T060 suggestion gaze-select + suffix/Space |
| SC-012 | PASS | Stage E T042–T047 **and** T045 live second-calibration resume |
| SC-013 | evidence only | no numeric mapped-key table; Feature 004 A/B + Feature 004 T060 are `eval_before` only |
| SC-014 | PASS | official GF Preview/Calibration; no GazeKey overlay on production path |
| SC-015 | PASS | pytest isolation (T013/T017/T025/T040/T051) |
| SC-016 | PASS | HeuristicFilter only; T031/T039; T058 no hold-last |
| SC-017 | PASS | `origin+dpr`; T012/T028–T030; STOP not invoked |
| SC-018 | PASS | sequential pygame then Qt; T045 reconfirmed recalibrate |
| SC-019 | skip recorded | T061 explicit skip |
| SC-020 | PASS | GazeSample contract as implemented |
| SC-024 | this file | quiet summary below |
| SC-021 / SC-022 | n/a | after Stage G only |

## Replay (T053)

Full GazeSample replay JSONL was **not** written for T045, T054, T055, or
T056. Live sessions remain valid. Optional helper:
`tools.evaluation.gazesample_scoring.write_gaze_replay` (gitignored; not on
the product keyboard).

## Provenance (FR-022 / FR-041 / FR-037)

- GazeFollower `1.0.2` commit `553920edcb7998c029828677f50f6d8eb4a16249`
- `base.mnn` SHA-256 `2f96b95275fe6d7b79e98df3237ebb96e15ef5522c96968f08167da7e1954a96`
- cali_mode=13; camera 0 / 640×480 / 30; HeuristicFilter look-ahead 3
- license CC BY-NC-SA 4.0
- geometry `origin+dpr` (`runs/_feature005/geometry_audit.json`)
- eval_before: Feature 004 A/B `14938da0bdf0`, `34fb259ccdfd`; Feature 004 T060 `689c8a8ce90c`, `4f665467b260`

## Quiet summary (FR-037)

Integrated GazeFollower typing is accepted on three distinct chin-support
sessions. Recalibration resume (T045) passed. Residual pointing error is
accepted. `hadar` is not scored and does not block cleanup. Accuracy work
and key resize were not reopened.

## Next

T064: Git pre-cleanup checkpoint/tag `005-pre-cleanup-20260824` after these
Stage F records are committed. Do not start deletions in T064.
