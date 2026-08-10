# Quickstart gate log — 003-predictive-text-keyboard-ux

**Feature**: Predictive Text & Keyboard UX  
**Started**: 2026-08-10

## Automated geometry gate (T014)

**Command**:

```bash
python -m pytest tests/unit/test_layout_geometry.py tests/test_keyboard_geometry_targets.py -q
```

**Result**: **PASS** (2026-08-10) — geometry + related UI tests green (18 passed including focus/preview regressions).

Automated tests do **not** claim live webcam/OS typing passed.

## USER GATE T015 — tools preview + visual keyboard

**Ask user to confirm**:

1. Run `python -m tools.preview` (preview without product Preview button)
2. Visual check of redesigned keyboard (quickstart §A / FR-008b):
   - Calibrate + window chrome only (no Pause, Preview, lang, status text, typed-text bar)
   - Suggestion bar with 3 slots, fully visible
   - No Ctrl/Alt; no symbols layout; no empty dead rows

**Result**: **PASS** (2026-08-10) — user confirmed tools preview + visual keyboard check.

## USER GATE T030 — suggestion MVP live

**Ask user to confirm** (quickstart §C):

1. `python main.py`, calibrate, focus Notepad
2. Type `hel` by gaze → suggestions appear
3. Dwell a suggestion (e.g. `hello`) → Notepad shows `hello ` (suffix + Space)
4. Optional: Shift armed + prefix `hel` + accept → still lowercase `hello `; Shift cleared

**Result**: **PASS** (2026-08-10) — user confirmed live suggestion MVP (quickstart §C).

## Automated Feature 003 sweep (T041) + full regression (T045)

```bash
python -m pytest tests/unit/test_typing_context.py tests/unit/test_word_provider.py tests/unit/test_suggestion_dispatch.py tests/unit/test_layout_geometry.py tests/unit/test_prediction_modularity.py tests/contract/test_typing_dispatch_path.py tests/contract/test_suggestion_typing_path.py -q
python -m pytest -q
```

**Result**: **PASS** (2026-08-10) — Feature 003 sweep green; full suite **174 passed**.  
`gazekey/mapping/config.py` unmodified for this feature (T043).

## Remaining USER GATES (live)

| Task | Gate | Result |
|------|------|--------|
| T034 | Typing ignoring suggestions / empty slots (quickstart §D) | pending |
| T038 | Consistency sequence vs TypingContext (quickstart §B/§E) | pending |
| T042 | Remaining live quickstart A–G as needed | pending |
| T051 | Bottom-row large Calibrate recovery target (quickstart §H) | pending — dwell→recalib wiring fixed 2026-08-10; await manual confirm |
| T056 | Live gaze reachability of suggestion row after typing_region_rect update | pending |

## Calibrate dwell wiring fix (pre-T051)

**Root cause**: `GazeTypingRuntime` ignored `system:calibrate` / `CALIBRATE` as non-OS;
legacy `_on_gaze_activate_key` was never called from the gaze loop.

**Fix**: wire `on_calibrate=self.on_calibrate_clicked` (existing entry point); remove dead
`_on_gaze_activate_key`. Layout/geometry unchanged. Mapping/config untouched.

**Automated**: `tests/contract/test_calibrate_dwell_path.py` + full `pytest -q` → **179 passed**.

## Phase 8 — Recalibration layout follow-up (T050)

**Automated**: `pytest tests/unit/test_layout_geometry.py tests/test_keyboard_geometry_targets.py -q` then `pytest -q` → **PASS** (2026-08-10); full suite **175 passed**.  
`gazekey/mapping/config.py` unmodified (T052).

**USER GATE T051** — ask user to confirm quickstart §H:

1. Recalibrate clearly larger and easier to target  
2. Bottom row layout correct (Calibrate | Space | Enter)  
3. Keyboard still works with gaze  
4. No important UI clipped or misaligned  

Automated suites MUST NOT claim webcam gaze for these gates.

## Phase 9 — Typing-region geometry consistency (T053–T055)

**Change**: Layout-export `typing_region_rect` is now the union of exported product
gaze-target rects (fixed `suggestion:0..2` even when blank/disabled + letter/editing
keys + Recalibrate/Space/Enter). Calibration continues to use `letter_keys_region_rect`
(keyboard widget only). No stretch/compensation; no PCA4/calib-target/config changes.

**Audit**: `map_gaze_to_typing_ui` has **no product callers** (dead for live typing;
product uses PCA4 screen xy → `hit_test_layout_keys`). Kept with NOTE; not removed.

**Automated**:
```bash
python -m pytest tests/unit/test_layout_geometry.py tests/test_keyboard_geometry_targets.py -q
python -m pytest -q
```
**Result**: **PASS** (2026-08-10) — geometry **9 passed**; full suite **180 passed**.  
`gazekey/mapping/config.py` unmodified (T055).

**USER GATE T056** — ask user to confirm live:

1. `python main.py`, calibrate, type a prefix so suggestions appear  
2. Can gaze physically reach / dwell the suggestion row?  
3. Does accept still insert the word correctly if reachable?

Automated suites MUST NOT claim this fixed live mapping.
