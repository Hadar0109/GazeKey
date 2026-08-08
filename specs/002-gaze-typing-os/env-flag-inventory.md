# GAZEKEY_* environment flag inventory (002)

**Feature**: `002-gaze-typing-os`  
**Status**: **Provisional** (T003–T011) — classifications are not final.  
**Date**: 2026-08-08

**Rules**:
- Do **not** delete or relocate any flag until real product-vs-developer role is
  clear and review sign-off is recorded (T019–T021).
- Do **not** KEEP a flag in the product merely because it currently has a consumer.
- Preserve uncertain flags in place for now; re-evaluate after the tools split.

**Locked for now (direction only — not executed)**:
- `GAZEKEY_VERBOSE` → remain **KEEP**
- `GAZEKEY_DEV_BENCHMARK`, `GAZEKEY_CALIB_GEOM_DEBUG` → **MOVE TO TOOLS** (when reviewed)
- Dead selection/gaze-debug flags → remain **DELETE** candidates

**Re-evaluate after tools split (preserve; do not MOVE/DELETE yet)**:
- `GAZEKEY_CALIB_MODE` — if only for calib/mapping experiments → tooling, not a
  normal product flag
- `GAZEKEY_GAZE_DEBUG`, `GAZEKEY_CALIB_DEBUG`, `GAZEKEY_DIAG_EXTRACTOR`,
  `GAZEKEY_CAMERA_PREVIEW_DURING_CALIB` — classify by purpose after preview/
  evaluation leave the product default path

---

## Inventory (provisional)

| Flag | Read sites | Tests / docs dependents | Classification | Notes |
|------|------------|-------------------------|----------------|-------|
| `GAZEKEY_VERBOSE` | `gazekey/ui/env_flags.py` (`verbose`, `EnvFlags.load`); `gazekey/mvp_log.py` (direct `os.environ`); `gazekey/ui/virtual_keyboard.py` (via `EnvFlags`); `gazekey/ui/calibration_overlay.py` (`verbose_fixation_ui`) | Tests: `tests/unit/test_mvp_logging.py`, `tests/integration/test_mvp_pipeline.py`. Docs: README, CURRENT_PIPELINE, PROJECT_STRUCTURE, TYPING_CANDIDATE, `001` quickstart/contracts | **KEEP** | Product quiet-by-default logging |
| `GAZEKEY_DEV_BENCHMARK` | `gazekey/ui/env_flags.py`; tools benchmark host (after T006–T011); was product finish auto-start | Tests: benchmark unit/integration. Docs: README, CURRENT_PIPELINE, `001` | **MOVE TO TOOLS** (provisional) | Must leave product default path; wire via `tools.evaluation` entry |
| `GAZEKEY_CAMERA_PREVIEW_DURING_CALIB` | `gazekey/ui/env_flags.py`; `gazekey/ui/virtual_keyboard.py`; `gazekey/runtime/gaze_loop.py` | Tests: `test_calibration_us1.py`. Docs: `001` quickstart | **RE-EVALUATE** (preserve) | Product calib UX vs developer comfort — decide after tools split |
| `GAZEKEY_CALIB_MODE` | `gazekey/ui/env_flags.py`; `gazekey/ui/calibration_controller.py` | Docs / layout experiment `runs/` | **RE-EVALUATE** (preserve) | Prefer **MOVE TO TOOLS** if only for mapping experiments — not a normal product flag |
| `GAZEKEY_SELECTION_DEBUG` | `gazekey/ui/env_flags.py` → `EnvFlags.selection_debug` only | Docs: CURRENT_PIPELINE | **DELETE** (candidate) | Dead; selection package pending delete |
| `GAZEKEY_GAZE_DEBUG` | `gazekey/ui/env_flags.py` → `rt2_debug`; VK; gaze_loop | Tests: `test_preview_readonly.py`. Docs: README, CURRENT_PIPELINE | **RE-EVALUATE** (preserve) | May become tools/preview-only once product does not require preview |
| `GAZEKEY_GAZE_DEBUG_PRED` | `env_flags` → unused VK field | Docs: CURRENT_PIPELINE | **DELETE** (candidate) | Dead after assignment |
| `GAZEKEY_GAZE_DEBUG_SELECTION` | `env_flags` → unused VK field | Docs: CURRENT_PIPELINE | **DELETE** (candidate) | Dead; selection path |
| `GAZEKEY_CALIB_DEBUG` | `env_flags`; VK; historically coupled to geom overlay | Docs: README, CURRENT_PIPELINE | **RE-EVALUATE** (preserve) | Product fixation verbosity vs tools geom debug coupling |
| `GAZEKEY_CALIB_GEOM_DEBUG` | `env_flags.calib_geom_debug`; tools debug overlay (after T007) | Docs: README, CURRENT_PIPELINE | **MOVE TO TOOLS** (provisional) | Geometry overlay is developer debug |
| `GAZEKEY_DIAG_EXTRACTOR` | `gazekey/features/extractor.py` (not in `env_flags`) | None in tests | **RE-EVALUATE** (preserve) | Feature-path diag; not a product mode — tooling vs keep optional |

### Docs-only / already retired (no code reads)

| Flag | Read sites | Tests / docs | Classification | Notes |
|------|------------|--------------|----------------|-------|
| `GAZEKEY_KEYBOARD_ACCURACY_DEBUG` | *(none in `.py`)* | Mentioned in `docs/TYPING_CANDIDATE.md` as replaced by `GAZEKEY_DEV_BENCHMARK` | **DELETE** (docs cleanup only) | Already absent from code; scrub docs in polish if desired |
| `GAZEKEY_KEYBOARD_ACCURACY_COMPARE` | *(none in `.py`)* | Mentioned in `docs/TYPING_CANDIDATE.md` as archived | **DELETE** (docs cleanup only) | Already absent from code |

---

## Classification summary (provisional — not final)

| Classification | Flags |
|----------------|-------|
| **KEEP** | `GAZEKEY_VERBOSE` |
| **MOVE TO TOOLS** (direction; not executed as flag MOVE yet) | `GAZEKEY_DEV_BENCHMARK`, `GAZEKEY_CALIB_GEOM_DEBUG` |
| **DELETE** (candidates) | `GAZEKEY_SELECTION_DEBUG`, `GAZEKEY_GAZE_DEBUG_PRED`, `GAZEKEY_GAZE_DEBUG_SELECTION` (+ docs-only accuracy flags) |
| **RE-EVALUATE** (preserve in place) | `GAZEKEY_CALIB_MODE`, `GAZEKEY_GAZE_DEBUG`, `GAZEKEY_CALIB_DEBUG`, `GAZEKEY_DIAG_EXTRACTOR`, `GAZEKEY_CAMERA_PREVIEW_DURING_CALIB` |

---

## Findings from T006–T011 package moves

What the move revealed (flags still **not** deleted/moved):

1. **`GAZEKEY_DEV_BENCHMARK`** — Confirmed tooling-only. Product `main.py` no longer
   auto-starts benchmark. Flag is still read by `tools.evaluation.benchmark_controller`
   / `env_flags`; use `python -m tools.evaluation` (+ flag) for the old behavior.
2. **`GAZEKEY_CALIB_GEOM_DEBUG`** — Overlay + diagnostics now live under `tools/debug/`
   and run only when DevTools are installed. Still gated via `env_flags.calib_geom_debug`
   when tools artifacts run; product finish path no longer imports the overlay.
3. **`GAZEKEY_CALIB_MODE`** — Still read by product `calibration_controller` for target
   layout override. After the split it looks **experiment/tooling-shaped** (not needed
   for a single default product calib). Prefer eventual **MOVE TO TOOLS**; **preserve**
   until review (do not move yet).
4. **`GAZEKEY_GAZE_DEBUG`** — Still feeds product `EnvFlags.rt2_debug` / gaze_loop labels.
   Preview is no longer a product requirement; this flag may become tools/preview-only.
   **Preserve / re-evaluate**.
5. **`GAZEKEY_CALIB_DEBUG`** — Still used for product fixation verbosity
   (`verbose_fixation_ui`) and historically coupled to geom overlay via
   `calib_debug_cached`. Product no longer shows geom overlay without tools; coupling
   now only matters inside tools artifacts. **Preserve / re-evaluate** (may KEEP thin
   product verbosity vs MOVE geom-related half).
6. **`GAZEKEY_CAMERA_PREVIEW_DURING_CALIB`** — Still product calib UX (camera during
   fixation). Remains a plausible **KEEP** for accessibility/comfort, but confirm it is
   not merely a developer convenience. **Preserve / re-evaluate**.
7. **`GAZEKEY_DIAG_EXTRACTOR`** — Untouched by package moves; still a features-level
   console diag. **Preserve / re-evaluate** (likely tooling).
8. **Import rule achieved** — `gazekey/` has **zero** `tools.*` imports; tools attach via
   `install_devtools`. Session id for product calib lives in `gazekey.runtime.session_id`.

---

## Earlier dependency notes (still relevant)

1. **`GAZEKEY_VERBOSE` dual readers** — `env_flags.verbose()` and `mvp_log.py`.
2. **`GAZEKEY_DIAG_EXTRACTOR` outside `env_flags.py`** — features package reads env itself.
3. **Dead debug fields** — `GAZE_DEBUG_PRED` / `GAZE_DEBUG_SELECTION` / `SELECTION_DEBUG`.
4. **`CALIB_DEBUG` ↔ geom overlay coupling** — now only in tools artifact path.

---

## Review sign-off

| Field | Value |
|-------|-------|
| Inventory complete (T004) | Yes — provisional after T006–T011 |
| Package moves (T006–T011) | Done — flag MOVE/DELETE still blocked |
| Review sign-off | *(pending — do not MOVE/DELETE flags yet)* |
| Sign-off date | |
