# GazeKey developer tools

`tools/` holds **developer** utilities for diagnostics, debugging, validation, experiments, analysis, and troubleshooting.

They are **not** part of normal end-user operation. Product launch remains:

```text
python main.py
```

Product code under `gazekey/` must not import `tools.*`. Tools attach to a `VirtualKeyboard` only from tools entries (via `tools.devtools_install.install_devtools`). The product path uses a no-op `NullDevTools`.

Use the project **Python 3.11** interpreter (`.venv\Scripts\python.exe`). Unlike `main.py`, tools entries do **not** re-exec into `.venv`. Running them with the system Python 3.14 interpreter is not a supported product runtime.

```text
.venv\Scripts\python.exe -m tools.preview --help
.venv\Scripts\python.exe -m tools.evaluation --help
```

---

## Current wiring (read this first)

The **only** code path that starts official GazeFollower Preview → 13-point Calibration → sampling is `python main.py` (`gazekey.backend.startup.run_official_startup`).

`python -m tools.preview` and `python -m tools.evaluation` construct a `VirtualKeyboard`, attach DevTools, and show the overlay. They do **not** construct `GazeFollowerLifecycle`, do **not** run official calibration, and do **not** start sampling. `_official_gaze_ready` stays false unless the product startup path sets it.

`install_devtools(..., auto_preview_after_calib=True)` stores `_tools_auto_preview_after_calib`, but nothing in the current tree reads that flag. `maybe_start_dev_benchmark()` runs only if something calls it, and it still requires usable official calibration plus `_preview_mode`. The evaluation entry never calls it after a GazeFollower session, because it never starts one.

Documented commands below are the real entry points. Live gaze preview and live GazeSample benchmarking through those entries are **not** currently wired to GazeFollower.

---

## Runnable commands

### `python -m tools.preview`

**What it is for.** Developer entry that opens the product keyboard with the read-only gaze-preview overlay controller installed (`GazePreviewController`). Intended historically as a mapped-gaze preview after calibration.

**When to use it.** Inspecting the keyboard chrome without OS typing, or exercising the preview overlay APIs/tests. It is not a substitute for `python main.py`.

**Prerequisites.** Python 3.11 project `.venv`, display. Webcam / GazeFollower are **not** started by this entry.

**Command.**

```text
.venv\Scripts\python.exe -m tools.preview
.venv\Scripts\python.exe -m tools.preview --verbose --gaze-debug
```

**Arguments.** Shared tools CLI (see [CLI options](#cli-options)). `auto_benchmark` stays false.

**What to expect.** A GazeKey overlay titled as a tools preview. Console: `GazeKey tools preview started (read-only gaze after calibration).` There is no product Preview button. The Calibrate control has no GazeFollower lifecycle on this path, so it does not start official recalibration. No green product gaze ring and no dwell typing unless some other code wires GazeFollower (the product `main.py` path).

---

### `python -m tools.evaluation`

**What it is for.** Developer entry that enables auto-benchmark (`AppConfig.auto_benchmark=True`) and attaches `BenchmarkController` plus the preview overlay. Intended historically as a GazeSample key-hit evaluation after official calibration.

**When to use it.** Evaluation scoring libraries and the benchmark UI controller live here. A complete live GazeFollower → score session is **not** started by this entry today.

**Prerequisites.** Same as preview. A finished live run would also need official GazeFollower calibration, sampling, and `_official_gaze_ready` — those are set by `main.py`, not by this module.

**Command.**

```text
.venv\Scripts\python.exe -m tools.evaluation
.venv\Scripts\python.exe -m tools.evaluation --verbose
```

**Arguments.** Shared tools CLI. The entry itself implies auto-benchmark; there is no `--no-auto-benchmark`.

**What to expect.** Keyboard overlay. Console: `GazeKey tools evaluation/benchmark started.` and `Auto-benchmark runs after successful calibration + preview.` Auto-start is still gated on `_calibration_usable()` (`_official_gaze_ready`) and `_preview_mode`. If a session did start, it would highlight keys, show a banner (`Benchmark — look at: …`), settle 1200 ms then collect 2500 ms per key, and write under `runs/<session_id>/` (`benchmark_summary.txt`, `experiment_record.md`, `hadar_wrong_focus.md`). Sample labels still include a full-QWERTY-style walk (`Q E T U P …` plus held-out letters and Shift/Backspace/Space/Enter/Calibrate). On the current **paged** keyboard, hidden-page letters are not in the live layout, so resolving those samples can fail with `Benchmark: no key found for sample '…'`.

---

### `python tools/focus_validation.py`

**What it is for.** Manual Qt harness for overlay focus hardening and OS injection: dummy editor in the lower screen, keyboard on top, a fullscreen “calib-like” overlay show/hide cycle, optional mouse click on `a`, then inject `hi` via `ActionDispatcher` + `pynput`.

**When to use it.** Checking that the overlay does not steal the external typing target and that pynput still delivers characters.

**Prerequisites.** Display; Python 3.11 `.venv` with PySide6 and pynput. Does **not** start GazeFollower or a webcam.

**Command.**

```text
.venv\Scripts\python.exe tools/focus_validation.py
```

No CLI flags (no argparse).

**What to expect.** Two windows (dummy editor + keyboard). Console block `FOCUS_VALIDATION_RESULT` with `geometry_ok`, focus flags, injected text, and `PASS=True/False`. Exit code 0 on pass, 1 on fail.

**Known mismatch.** This script still expects keyboard height **0.62** of available screen. Production layout uses **0.70** (`KEYBOARD_HEIGHT_RATIO` in `gazekey/ui/keyboard_layout.py`), so `geometry_ok` can fail on the current keyboard even when focus/injection are fine.

---

### `python tools/debug/analyze_correction_layers.py`

**What it is for.** One-off **offline** analysis of historical PCA/poly12 correction-layer CSVs from an older mapper. It does not talk to GazeFollower.

**When to use it.** Only if you still have those session files and need the printed stage-by-stage accuracy breakdown.

**Prerequisites.** These files at the **repository root** (they are gitignored; they are not produced by the current GazeFollower product path):

- `keyboard_layout.csv`
- `calibration_v2.json`
- `key_accuracy_debug.csv`
- `key_accuracy_compare.csv` (rows with `mapper_type=poly12_ridge_split_decoupled_y`)
- optional: `calibration_debug.csv`, `calibration_summary.csv`

**Command.**

```text
.venv\Scripts\python.exe tools/debug/analyze_correction_layers.py
```

No CLI flags.

**What to expect.** Stdout tables of accuracy / pixel error per correction stage. Missing input files raise a normal Python exception.

---

## CLI options

Parsed in `gazekey/app_config.py`. No `GAZEKEY_*` environment fallback.

Shared (also accepted by `python main.py`):

| Option | Parser help | Verified effect |
|--------|-------------|-----------------|
| `--verbose` | Detailed calibration/runtime console logs | Gates `mvp_log` / extra GazeKey prints |
| `--calib-debug` | Verbose official-calibration logs | Stored on config / `VirtualKeyboard`; no remaining GazeKey call site prints extra GazeFollower logs from this flag |
| `--gaze-debug` | Extra mapped-gaze debug labels on preview | `--gaze-debug` or `--verbose` sets `rt2_debug` so the **tools** preview overlay can show labels if gaze coordinates are fed to it |

Tools-only:

| Option | Parser help | Verified effect |
|--------|-------------|-----------------|
| `--calib-mode MODE` | Historical layout label for tools records (not a product mapper) | Stored on `AppConfig.calib_mode`; not read by current runtime |
| `--camera-preview-during-calib` | Unused on the GazeFollower product path (tools leftover) | Stored; unused |
| `--calib-geom-debug` | Post-fit train/LOOCV geometry overlay (tools only) | Stored; `tools.flags.calib_geom_debug()` exists but is not called by current preview/evaluation UI (no PCA overlay remains) |

Product `python main.py` rejects the tools-only flags.

---

## Supporting modules (not CLI)

These are imported by the entries above or by tests. They have no `if __name__ == "__main__"` command unless noted.

### Package root

| Path | Role |
|------|------|
| `tools/__init__.py` | Package marker |
| `tools/flags.py` | `auto_benchmark_enabled()` / `calib_geom_debug()` over `get_config()` |
| `tools/devtools_install.py` | `install_devtools` / `DevToolsBundle` — attaches preview, benchmark, layout CSV exporter, and no-op calib artifact writer |

### `tools/preview/`

| Path | Role |
|------|------|
| `tools/preview/__main__.py` | Preview entry |
| `tools/preview/gaze_preview.py` | Read-only gaze dot overlay (`GazePreviewController`). Used if something calls `show_gaze`. Does not type. |

### `tools/evaluation/`

| Path | Role |
|------|------|
| `tools/evaluation/__main__.py` | Evaluation entry |
| `tools/evaluation/benchmark_controller.py` | Live 15-key-style banner/highlight session; scores `GazeSample` via `GazeSampleEvalSession` |
| `tools/evaluation/gazesample_scoring.py` | GazeSample + live QRect scoring (no FeatureExtractor / Ridge / PCA4). Optional `write_gaze_replay` JSONL (no webcam frames) |
| `tools/evaluation/benchmark_runner.py` | Sample labels, hit-test scoring, pass thresholds |
| `tools/evaluation/benchmark_session.py` | Older timed session that still takes a `predict_screen_xy` callable (legacy eval shape; GazeFollower path uses `GazeSampleEvalSession`) |
| `tools/evaluation/run_summary.py` | Writes `runs/<id>/benchmark_summary.txt` (and calibration summary helpers that GazeFollower production does not call) |
| `tools/evaluation/session_paths.py` | Paths under `runs/<session_id>/` |
| `tools/evaluation/session.py` | Location-result records / `format_location_results` |
| `tools/evaluation/experiment_record.py` | `experiment_record.md` and `hadar_wrong_focus.md` templates |
| `tools/evaluation/failure_analysis.py` | Per-key miss text for summaries |
| `tools/evaluation/benchmark_diagnostics.py` | JSON diagnostics writer (`benchmark_diag.json`); used by tests; not called from the current controller finish path |
| `tools/evaluation/coverage_diagnostics.py` | Calibration-anchor vs key-center hull report (`coverage.json`); used by tests; not called from the current controller finish path |
| `tools/evaluation/calib_finish_artifacts.py` | No-op stand-in (PCA mapper snapshots removed) |
| `tools/evaluation/clamp_diagnostic.py` | Stub; PCA clamp helpers removed. **Not imported** by other modules |

### `tools/debug/`

| Path | Role |
|------|------|
| `tools/debug/layout_csv.py` | `KeyboardLayoutCsvExporter` — writes `keyboard_layout.csv` when a session id is bound. Product `NullDevTools` does not export. Tools bind an exporter, but `VirtualKeyboard._bind_session_artifact_paths` is never called in the current tree |
| `tools/debug/layout_geometry_check.py` | Compare `layout_inspector` rects to `KeyHitTester`. Used by `tests/unit/test_layout_geometry.py`, not a CLI |
| `tools/debug/analyze_correction_layers.py` | Historical CSV analyzer (see command above) |

---

## Isolation

`tests/contract/test_evaluation_isolation.py` requires that `gazekey/` product modules do not import `tools.evaluation`. Keep new product code on the same side of that boundary.
