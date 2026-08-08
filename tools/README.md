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

Benchmark auto-start (tools entry only):

```text
set GAZEKEY_DEV_BENCHMARK=1
python -m tools.evaluation
```

## Tools-only flags (`tools/flags.py`)

| Flag | Effect |
|------|--------|
| `GAZEKEY_DEV_BENCHMARK=1` | Auto-start 15-key benchmark after tools calib+preview |
| `GAZEKEY_CALIB_GEOM_DEBUG=1` | Post-fit geometry overlay |

Product flags remain in `gazekey/ui/env_flags.py` (see env-flag inventory).

## Layout

```text
tools/
  __init__.py
  README.md
  flags.py                 # DEV_BENCHMARK, CALIB_GEOM_DEBUG
  devtools_install.py      # attach writers / preview / benchmark to product VK
  evaluation/
    __main__.py            # benchmark entry
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
Flag inventory: `specs/002-gaze-typing-os/env-flag-inventory.md`
