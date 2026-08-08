# GazeKey developer tools

This package holds **developer entry points** for preview, evaluation/benchmark,
and debug utilities. These are **not** product modes.

Product launch remains:

```text
python main.py
```

Product code under `gazekey/` must **not** import `tools.*`. Tools attach to a
`VirtualKeyboard` via `tools.devtools_install.install_devtools`.

## Entry points (T010–T011)

| Capability | Command | Package |
|------------|---------|---------|
| Read-only gaze preview | `python -m tools.preview` | `tools/preview/` |
| Key-hit benchmark / evaluation | `python -m tools.evaluation` | `tools/evaluation/` |
| Debug overlays / diagnostics | imported by tools entries | `tools/debug/` |

Benchmark auto-start (tools entry only):

```text
set GAZEKEY_DEV_BENCHMARK=1
python -m tools.evaluation
```

## Layout

```text
tools/
  __init__.py
  README.md
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
    ...
  preview/
    __main__.py            # preview entry
    gaze_preview.py
```

## Related inventory

Flag MOVE/DELETE decisions: `specs/002-gaze-typing-os/env-flag-inventory.md`
(provisional — do not apply until review).
