# GazeKey developer tools

This package holds **developer entry points** for preview, evaluation/benchmark,
and debug utilities. These are **not** product modes.

Product launch remains:

```text
python main.py
```

Product code under `gazekey/` must **not** import `tools.*`. Tools attach to a
`VirtualKeyboard` via `tools.devtools_install.install_devtools`.

## Entry points

| Capability | Command | Package |
|------------|---------|---------|
| Read-only gaze preview | `python -m tools.preview` | `tools/preview/` |
| Key-hit benchmark / evaluation | `python -m tools.evaluation` | `tools/evaluation/` |
| Debug overlays / diagnostics | imported by tools entries | `tools/debug/` |
| Offline correction-layer analysis | `python tools/debug/analyze_correction_layers.py` | `tools/debug/` |

`python -m tools.evaluation` **implies** auto-benchmark after calib+preview — no
extra flag required.

## CLI options

Shared (product + tools):

| Option | Effect |
|--------|--------|
| `--verbose` | Detailed console logs |
| `--calib-mode <mode>` | Calibration layout override |
| `--calib-debug` | Verbose fixation UI |
| `--gaze-debug` | Extra mapped-gaze labels |
| `--camera-preview-during-calib` | Camera PiP during fixation |

Tools-only:

| Option | Effect |
|--------|--------|
| `--calib-geom-debug` | Post-fit geometry overlay (independent of `--verbose` / `--calib-debug`) |

Examples:

```text
python -m tools.preview --gaze-debug
python -m tools.evaluation --verbose --calib-geom-debug
```

Config boundary: `gazekey/app_config.py` (no `GAZEKEY_*` env fallback).
Helpers: `tools/flags.py` reads `get_config()`.

## Layout

```text
tools/
  __init__.py
  README.md
  flags.py                 # auto_benchmark + calib_geom_debug from AppConfig
  devtools_install.py      # attach writers / preview / benchmark to product VK
  evaluation/
    __main__.py            # benchmark entry (implies auto-benchmark)
    benchmark_*.py
    run_summary.py
    session_paths.py
    calib_finish_artifacts.py
    ...
  debug/
    calibration_geometry_overlay.py
    mapper_store.py
    layout_csv.py
    analyze_correction_layers.py
    ...
  preview/
    __main__.py            # preview entry
    gaze_preview.py
```

## Related inventory

Reviewed decisions: `specs/002-gaze-typing-os/inventory-review.md`  
Flag / CLI inventory: `specs/002-gaze-typing-os/env-flag-inventory.md`
