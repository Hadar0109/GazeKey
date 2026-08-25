# Feature 006 live USER GATEs — deferred by explicit user decision

**Date**: 2026-08-25  
**Status**: **open / deferred**. Not PASS. Not FAIL. No invented scores.

The operator directed that remaining **manual** live USER GATEs and the
SC-006 before/after intended-key comparison **not** be performed in this
implementation pass. Automated production work, isolation checks, and the
full pytest suite continue.

Do **not** treat these as PASS. Do **not** fill
`paged-intended-key.md` from memory. Do **not** retune GazeFollower,
calibration, mapping, origin/DPR, dwell, prediction, or OS input to
compensate for missing live scores.

The recorded full-QWERTY baseline remains the SC-006 `eval_before` and
MUST be preserved:

`specs/006-paged-large-target-keyboard/baseline/full-qwerty-intended-key.md`

## Deferred gates

| Task | Quickstart | What was not run | Status |
|------|------------|------------------|--------|
| T030 | §C mixed-page `hello` (SC-003) and §D suggestion accept after mixed-page prefix | Live chin/head-support typing into Notepad | deferred / not scored |
| T036 | §C2 same 12-letter sequence as T004 on the paged keyboard | Live intended-key/focus table | deferred / not scored |
| T037 | Compare T036 wrong-focus total to the T004 file (SC-006) | Before/after comparison | deferred / not scored — no paged file to compare |

`paged-intended-key.md` does **not** exist because T036 was not run.
Creating that file with invented focus results is forbidden.

## Still recorded (do not overwrite)

- T004 `full-qwerty-intended-key.md` — 12 trials, total wrong-focus **11 / 12**

## Isolation reminder (unchanged)

Independent mapping/GazeFollower benchmarks and Feature 004 records are not
this feature’s acceptance gate. Larger keys are a target-size change only.
