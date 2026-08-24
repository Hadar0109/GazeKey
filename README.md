# GazeKey

Eye-tracking virtual keyboard using a standard webcam and official GazeFollower.

## What it does today

On launch the app runs **official GazeFollower Preview + 13-point Calibration**,
then the existing Qt keyboard. Gaze typing consumes **GazeSample** through
`origin+dpr` live QRect hit-test and **dwell**. Keys inject into the **focused
external application** via OS input (`pynput` behind an adapter).

**Predictive text:** a bundled English word list drives up to **3 fixed
suggestion slots**. Accepting a suggestion injects the remaining letters + Space
through the same KeyAction path.

**Product** launch does **not** start gaze preview or the accuracy benchmark. Those
are **developer tools**.

## Quick start

### Requirements

- Python **3.11** (product runtime; discovery 3.11.9)
- Webcam
- Windows / Linux / macOS
- Chin/head support (Feature 005 product condition)

### Install

```bash
git clone <repository-url>
cd "Virtual Keyboard"
python -m pip install --no-build-isolation -r requirements.txt
```

Use the project `.venv` on Python 3.11. Do not run the product on Python 3.14.

### Run (product)

```bash
python main.py
```

1. Official GazeFollower Preview, then 13-point Calibration (Space=accept, R=retry).
2. The Qt keyboard appears. GREEN ring is filtered gaze (`origin+dpr`).
3. Focus an external editor; dwell or click keys to type there.
4. After 2+ letters of a word, dwell a **suggestion** to complete it + Space.
5. Use **CALIBRATE** for a fresh official recalibration as needed.

### Developer tools (optional)

```bash
python -m tools.preview          # read-only gaze preview
python -m tools.evaluation       # GazeSample key-hit evaluation after official calib
```

Optional launch flags (examples):

```bash
python main.py --verbose
python -m tools.preview --gaze-debug --calib-geom-debug
python -m tools.evaluation --verbose
```

`--calib-mode` is **not** a product flag. Tools may still accept it as a
historical label only.

Details: **`tools/README.md`**. Focus harness: `python tools/focus_validation.py`.

## Project layout

```
Virtual Keyboard/
├── main.py                      # Product entry: official GazeFollower then Qt keyboard
├── docs/                        # Long-term product specification (PDF)
├── runs/<session_id>/           # Per-session artifacts
├── gazekey/                     # Product runtime
│   ├── app_config.py            # CLI → process config boundary
│   ├── backend/                 # GazeFollower lifecycle, GazeSample, geometry
│   ├── ui/                      # VirtualKeyboard + dwell overlay
│   ├── runtime/                 # GazeSample loop
│   ├── layout/                  # Key geometry inspection
│   ├── typing/                  # Dwell, session, KeyAction, dispatcher
│   ├── prediction/              # WordProvider, TypingContext, suggestion dispatch
│   └── input/                   # OsInputAdapter + pynput adapter
├── tools/                       # Developer preview / evaluation / debug
├── tests/                       # Pytest suite
└── specs/                       # Spec Kit feature docs (004 is historical)
```

## Session artifacts

Runtime-generated files go under `runs/<session_id>/` or `runs/_feature005/`
(geometry audit, DPI probe). Feature 004 historical runs stay under
`runs/_feature004/` and must not be rewritten.

## Launch options (CLI)

Normal workflows do **not** require environment variables. Options are parsed at
entry points into `gazekey.app_config.AppConfig`.

### Product (`python main.py`)

| Option | Effect |
|--------|--------|
| `--verbose` | Verbose logs |
| `--calib-debug` | Extra official-calibration logs |
| `--gaze-debug` | Extra gaze debug labels |

Typing has **no** enable flag — it starts after official GazeFollower calibration.

`--calib-mode` and `--camera-preview-during-calib` are **not** product flags.

### Tools

| Option | Preview | Evaluation | Effect |
|--------|:-------:|:----------:|--------|
| Shared product options above | ✓ | ✓ | Same meanings |
| `--calib-mode <mode>` | ✓ | ✓ | Historical label only (not a product mapper) |
| `--calib-geom-debug` | ✓ | ✓ | Tools leftover overlay flag |
| *(entry itself)* | — | auto-benchmark | `python -m tools.evaluation` implies evaluation |

There is **no** `GAZEKEY_*` environment fallback.

## Tests

```bash
python -m pytest tests/ -q
```

Focused typing units:

```bash
python -m pytest tests/unit -k "dwell or key_action or os_input or typing_session"
```

## Technical notes

- **Gaze**: official GazeFollower 1.0.2 → `GazeSample` (no GazeKey PCA/Ridge mapper)
- **Geometry**: production uses `origin+dpr` into live QRect hit-test
- **Filter**: GazeFollower HeuristicFilter only; no extra GazeKey smoothing after it
- **Typing**: Dwell 0.9 s / cooldown 0.20 s / 5-frame re-arm / 0.25 s key-switch confirm
- **Prediction**: Prefix trie + frequency list (`gazekey/prediction/`); UI uses `WordProvider` only
- **OS input**: `pynput` only inside `gazekey/input/pynput_adapter.py`
- **Layout**: Official GazeFollower calib UI; top-half keyboard (`0.62`); letters-only product chrome
