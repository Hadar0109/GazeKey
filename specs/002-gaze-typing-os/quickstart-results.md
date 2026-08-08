# Quickstart checklist results (T061)

**Feature**: `002-gaze-typing-os`  
**Date**: 2026-08-08  
**Branch**: `002-gaze-typing-os`  
**Checklist**: `specs/002-gaze-typing-os/quickstart.md`

## Summary

| Section | Result | Notes |
|---------|--------|-------|
| §A Post-cleanup gate | **PASS** | Prior `quickstart-gate-log.md` (T023–T028) |
| §B Early focus validation | **PASS** | `tools/focus_validation.py` — 3/3 after harness settle harden |
| §C Full product typing (live gaze) | **PENDING** | Same gap as T050 — needs operator; upstream mapping accuracy may cause unintended keys (not dwell regression) |
| Automated unit checks | **PASS** | See T062 / T063 |

Overall for automated + prior gates: **PASS with §C/T050 still open**.

---

## §A — Post-cleanup

Recorded in `quickstart-gate-log.md`. Product launch, fullscreen calib presentation,
PCA4 usable mapper, top-half geometry, independent `tools.evaluation` benchmark entry.

## §B — Focus validation (post typing integration)

Command:

```text
PYTHONPATH=. python tools/focus_validation.py
```

Evidence (representative):

```text
geometry_ok=True geo=(0,0 1280x416)
focus_hardening_ok=True
mouse_click_keeps_external_focus=True
target_had_focus_before_inject=True
inject_all_ok=True delivered=[True, True]
target_text='hi'
PASS=True
```

Also covered in `focus-validation-log.md` (T054). Harness always performs **one**
OS restore of the external target after the optional mouse click before inject
(allowed by §B); inject still needs no per-character restore.

Deviation noted during T061: one earlier run saw `inject ok` with empty
`target_text` when restore after mouse was conditional on Qt `focusWidget` only —
Windows foreground can diverge. Harness updated; 3 consecutive reruns **PASS**.

## §C — Live short-word gaze

| Step | Status |
|------|--------|
| ≥4-char word by dwell + ring / 0.25 s switch | **PENDING operator** (T050) |
| Pause/Resume / Shift / Ctrl-Alt | **PENDING operator** |
| Optional mouse same OS path | **PASS** (harness + unit/contract) |
| No usable target → non-blocking feedback | **PASS** (`test_delivery_failure_shows_nonblocking_status`) |

## Automated checks (quickstart)

```text
pytest tests/unit -k "dwell or key_action or os_input or typing_session"
```

**Result**: `26 passed, 71 deselected` (T062).

Full suite (T063): `140 passed`.
