# Typing candidate: `pca4_baseline_v1`

Frozen configuration for the **active calibration + mapped-gaze path**. This stack
is tuned for a reliable calibration → usable mapper loop. Full gaze typing / OS
injection is specified under `002-gaze-typing-os` and is not enabled on the
default product path yet.

## What is active

| Layer | Choice | Notes |
|-------|--------|-------|
| Mapper | **`pca4_baseline`** | X from `[uL, uR]`; Y from `[vL, vR]` |
| Calibration layout | **`keyboard15`** | 15 points on real key centers + row structure |
| Ridge α | **Auto grid** | `ALPHA_GRID` in config; pick largest α within 5 px of best LOOCV |
| Post-fit correction | **Row Y bias only** | `APPLY_ROW_Y_BIAS=True`; local-Y correction is archived |
| Feature smoother | **EMA α = 0.28** | `PcaFeatureSmoother` before predict |
| Gaze smoother | **EMA α = 0.35** | Screen-coordinate EMA after predict |
| Quality gates | **Region-first (keyboard)** | `evaluate_calibration_quality` + region LOOCV |
| Candidate ranking | **Disabled (frozen)** | Only `pca4_baseline` is fit |
| Runtime interaction | **Mouse typing + usable mapped gaze** | Dwell / OS inject not product-default yet |
| Persistence | **Session folder** | `runs/<session_id>/calibration_v2.json` (not loaded on startup) |

All constants live in **`gazekey/mapping/config.py`**.

## Evidence from archived sessions

Historical benchmarks under `runs/` informed this freeze. On the 15-key accuracy
test, **`pca4_baseline`** with **keyboard15** and correction layers was the most
consistent trade-off between LOOCV and key-hit rate compared to poly12 / decoupled
variants (now removed from the active fit path).

Key takeaways retained:

1. **keyboard15** — targets on real keys beat abstract grids.
2. **Region gates as primary** — wrong row/column fails harder than moderate pixel RMS.
3. **Row Y bias** — fixes global per-row offsets without poly12 complexity.
4. **Feature smoother α = 0.28** — shared across product predict and tools preview/benchmark.
5. **Keyboard corr(screen_y, avg_v)** — catastrophic below 0.15; moderate coupling is a warning, not an automatic hard fail.

## How to run

### Product

1. Launch: `python main.py`
2. Complete the 15-point calibration (fixate each dot).
3. On pass: usable mapper is available; click keys with the mouse to type.
4. Use **RECALIBRATE** to run again.

### Developer tools

```bash
python -m tools.preview
set GAZEKEY_DEV_BENCHMARK=1
python -m tools.evaluation
```

See `tools/README.md`.

### Diagnostics

| Variable | Where | Effect |
|----------|-------|--------|
| `GAZEKEY_VERBOSE=1` | Product | Detailed calibration/runtime logs |
| `GAZEKEY_CALIB_DEBUG=1` | Product (re-evaluate) | Verbose calibration overlay |
| `GAZEKEY_GAZE_DEBUG=1` | Product (re-evaluate) | Extra gaze/predict logs |
| `GAZEKEY_CALIB_GEOM_DEBUG=1` | Tools | Post-fit geometry overlay |
| `GAZEKEY_DEV_BENCHMARK=1` | Tools | Auto 15-key benchmark + `benchmark_summary.txt` |

## Expected quality

Typical **passing** keyboard15 runs:

- LOOCV RMS: ~45–70 px
- corr(screen_y, avg_v): ~0.55–0.85
- Tools benchmark key hit: high session variance (~40–70% on good runs)

When gates fail, the usable mapper stays blocked and the app prompts **RECALIBRATE**.
There is no best-effort mapper bypass.

## Session artifacts

Each run writes under **`runs/<session_id>/`**:

| File | Use |
|------|-----|
| `calibration_summary.txt` | Pass/fail + LOOCV line |
| `calibration_v2.json` | Mapper weights snapshot (inspection) |
| `keyboard_layout.csv` | Key geometry at calibration |
| `coverage.json` | Anchor hull vs interactive keys |
| `calibration_debug.csv` | Per-target train/LOOCV errors |
| `benchmark_summary.txt` | Tools benchmark result |
| `benchmark_diag.json` | Full benchmark JSON |

## Not on this path

- Dwell typing / OS injection (later `002` phases)
- Poly12 / local-Y / decoupled mappers — under `archive/mapping_variants/`
- Deleted selection/intent packages and obsolete debug flags

## Changing this configuration

1. Edit **`gazekey/mapping/config.py`** (thresholds, α grid, smoothers, `CALIBRATION_MODE`).
2. Update this document and run `python -m pytest tests/ -q`.
3. To experiment with alternate mappers, restore code from `archive/mapping_variants/` and change `fit_calibration_mapper` in `ridge.py` — not supported on the frozen path.
