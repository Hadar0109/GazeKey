# Typing candidate: `pca4_baseline_v1`

Frozen configuration for the **active calibration + mapped-gaze path**. This stack
is tuned for a reliable calibration → usable mapper loop. Product gaze typing /
OS injection (`002-gaze-typing-os`) and predictive text (`003-predictive-text-keyboard-ux`)
**consume** mapped gaze downstream and must **not** retune these constants for
typing or suggestion UX.

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
| Runtime interaction | **Mouse + dwell → OS inject** | Auto-starts when usable mapper available |
| Persistence | **Session folder** | `runs/<session_id>/calibration_v2.json` (not loaded on startup) |

All mapping constants live in **`gazekey/mapping/config.py`**.

Dwell selection (downstream, not mapping): **0.9 s** dwell, **0.20 s** post-fire
cooldown, **5-frame** same-key re-arm, **0.25 s** key-switch confirmation; circular
progress ring on existing key geometry.

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
2. Complete the 15-point **fullscreen** calibration (fixate each dot).
3. On pass: usable mapper available; typing auto-starts into the **focused external app**.
4. Gaze-dwell keys (~0.9 s) or optional mouse — same OS path.
5. Use **Pause/Resume** and **RECALIBRATE** as needed.

### Developer tools

```bash
python -m tools.preview
python -m tools.evaluation
```

See `tools/README.md`. Preview/benchmark are **not** product modes.

### Diagnostics (CLI)

| Option | Where | Effect |
|--------|-------|--------|
| `--verbose` | All entries | Detailed calibration/runtime logs |
| `--calib-debug` | All entries | Verbose calibration overlay |
| `--gaze-debug` | All entries | Extra gaze/predict labels |
| `--calib-geom-debug` | Tools | Post-fit geometry overlay |
| `python -m tools.evaluation` | Evaluation entry | Auto 15-key benchmark + `benchmark_summary.txt` |

No product typing enable flag — session activates after usable mapper.
No `GAZEKEY_*` environment fallback.

## Expected quality

Typical **passing** keyboard15 runs:

- LOOCV RMS: ~45–70 px
- corr(screen_y, avg_v): ~0.55–0.85
- Tools benchmark key hit: high session variance (~40–70% on good runs)

When gates fail, the usable mapper stays blocked and the app prompts **RECALIBRATE**.
There is no best-effort mapper bypass. Upstream mapping accuracy issues are
**not** fixed by changing dwell/typing or by retuning gates for typing.

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

- Poly12 / local-Y / decoupled mappers — under `archive/mapping_variants/`
- Deleted selection/intent packages and obsolete debug/typing enable flags
- In-app text buffer as the typing destination (OS is sole destination)
- Preview/benchmark as product modes

## Changing this configuration

Treat `gazekey/mapping/config.py` as frozen for MVP. Any change needs new
evidence via the **tools** benchmark path — not typing-layer tweaks.
