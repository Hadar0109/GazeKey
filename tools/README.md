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
| Layout CSV export / geometry check | imported by tools entries | `tools/debug/` |
| Offline correction-layer analysis | `python tools/debug/analyze_correction_layers.py` | `tools/debug/` |

`python -m tools.evaluation` **implies** auto-benchmark after official
calibration — no extra flag required.

## CLI options

Shared (product + tools):

| Option | Effect |
|--------|--------|
| `--verbose` | Detailed console logs |
| `--calib-debug` | Extra official-calibration logs |
| `--gaze-debug` | Extra mapped-gaze labels |

Tools-only:

| Option | Effect |
|--------|--------|
| `--calib-mode <mode>` | Historical label only (not a product mapper) |
| `--calib-geom-debug` | Leftover tools flag; no PCA4 overlay remains |
| `--camera-preview-during-calib` | Leftover tools flag; unused on the GazeFollower path |
| *(evaluation entry itself)* | `python -m tools.evaluation` implies auto-benchmark |

Examples:

```text
python -m tools.preview --gaze-debug
python -m tools.evaluation --verbose
```

Config boundary: `gazekey/app_config.py` (no `GAZEKEY_*` env fallback).
Helpers: `tools.flags.py` reads `get_config()`.

## Layout

```text
tools/
  __init__.py
  README.md
  flags.py                 # auto_benchmark + leftover calib_geom_debug from AppConfig
  devtools_install.py      # attach writers / preview / benchmark to product VK
  focus_validation.py      # focus harness
  evaluation/
    __main__.py            # benchmark entry (implies auto-benchmark)
    benchmark_*.py
    gazesample_scoring.py
    run_summary.py
    session_paths.py
    calib_finish_artifacts.py
    ...
  debug/
    layout_csv.py
    layout_geometry_check.py
    analyze_correction_layers.py
  preview/
    __main__.py            # preview entry
    gaze_preview.py
```

## Related inventory

Reviewed decisions: `specs/002-gaze-typing-os/inventory-review.md`  
Flag / CLI inventory: `specs/002-gaze-typing-os/env-flag-inventory.md`
