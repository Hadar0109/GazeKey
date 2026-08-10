# GazeKey

Eye-tracking virtual keyboard using a standard webcam and MediaPipe face landmarks.

## What it does today

On launch the app **calibrates every session** (no loading saved mappers from disk),
fits a **PCA4 ridge gaze mapper** on 15 keyboard-aligned targets, then **auto-starts
gaze typing** when a usable mapper is available. Keys activate by **gaze dwell**
(~0.9 s, with progress ring) or optional **mouse click**; both inject into the
**focused external application** via OS input (`pynput` behind an adapter).

**Predictive text (003):** a bundled English word list drives up to **3 fixed
suggestion slots**. Accepting a suggestion injects the remaining letters + Space
through the same KeyAction path. Mapping/calibration constants are **unchanged**.

**Product** launch does **not** start gaze preview or the accuracy benchmark. Those
are **developer tools**.

See **`docs/CURRENT_PIPELINE.md`** for the runtime flow and **`docs/TYPING_CANDIDATE.md`**
for frozen mapper configuration.

## Quick start

### Requirements

- Python 3.10+ (tested on 3.14)
- Webcam
- Windows / Linux / macOS

### Install

```bash
git clone <repository-url>
cd "Virtual Keyboard"
pip install -r requirements.txt
```

MediaPipe model: `models/face_landmarker.task` (downloaded on first run if missing).

### Run (product)

```bash
python main.py
```

1. App opens the virtual keyboard and starts **fullscreen** calibration automatically.
2. Fixate each on-screen dot until the session completes.
3. On success, the keyboard returns to its **top-half** geometry and typing auto-starts.
4. Focus an external editor in the lower half; dwell or click keys to type there.
5. After 2+ letters of a word, dwell a **suggestion** to complete it + Space, or ignore suggestions and keep typing key-by-key.
6. Use **RECALIBRATE** (Calibrate button) as needed.

### Developer tools (optional)

```bash
python -m tools.preview          # read-only gaze preview
python -m tools.evaluation       # 15-key accuracy benchmark after calib+preview
```

Optional launch flags (examples):

```bash
python main.py --verbose
python -m tools.preview --gaze-debug --calib-geom-debug
python -m tools.evaluation --verbose --calib-mode keyboard_full9
```

Details: **`tools/README.md`**. Focus harness: `python tools/focus_validation.py`.

## Project layout

```
Virtual Keyboard/
├── main.py                      # Product entry point
├── docs/                        # Pipeline, structure, typing-candidate notes
├── runs/<session_id>/           # Per-session artifacts
├── gazekey/                     # Product runtime only
│   ├── app_config.py            # CLI → process config boundary
│   ├── ui/                      # VirtualKeyboard + calibration UI + dwell overlay
│   ├── runtime/                 # Gaze loop, mapper fit, session id
│   ├── calibration/             # Target collection, fixation gate, quality
│   ├── mapping/                 # PCA4 ridge (config.py, ridge.py, row_bias.py)
│   ├── features/                # EyeData → FrameFeatures + PCA smoother
│   ├── tracking/                # Webcam + MediaPipe thread
│   ├── layout/                  # Key geometry inspection
│   ├── typing/                  # Dwell, session, KeyAction, dispatcher
│   ├── prediction/              # WordProvider, TypingContext, suggestion dispatch
│   └── input/                   # OsInputAdapter + pynput adapter
├── tools/                       # Developer preview / evaluation / debug
├── archive/                     # Legacy v1 calibration and experiment code
├── tests/                       # Pytest suite
└── specs/                       # Spec Kit feature docs
```

Deeper maps: **`docs/gazekey_code_structure.md`**, **`docs/PROJECT_STRUCTURE.md`**.

## Session artifacts

All runtime-generated files go under **`runs/<session_id>/`** (not the repo root):

| File | Purpose |
|------|---------|
| `calibration_summary.txt` | Console-style pass/fail summary |
| `calibration_v2.json` | Fitted mapper snapshot (inspection only; not loaded on startup) |
| `keyboard_layout.csv` | Key geometry at calibration time |
| `coverage.json` | Calibration anchor vs key coverage |
| `calibration_debug.csv` | Per-target train/LOOCV diagnostics |
| `calibration_ratio_space.csv` | Row-level avg_v stats |
| `benchmark_summary.txt` | 15-key benchmark result (tools) |
| `benchmark_diag.json` | Full benchmark diagnostics (tools) |

## Launch options (CLI)

Normal workflows do **not** require environment variables. Options are parsed at
entry points into `gazekey.app_config.AppConfig`.

### Product (`python main.py`)

| Option | Effect |
|--------|--------|
| `--verbose` | Verbose logs |
| `--calib-mode <mode>` | Override calibration layout |
| `--calib-debug` | Verbose calibration overlay |
| `--gaze-debug` | Extra gaze/predict labels |
| `--camera-preview-during-calib` | Camera PiP during fixation |

Typing has **no** enable flag — it starts after a usable mapper is available.

### Tools

| Option | Preview | Evaluation | Effect |
|--------|:-------:|:----------:|--------|
| Shared product options above | ✓ | ✓ | Same meanings |
| `--calib-geom-debug` | ✓ | ✓ | Post-fit geometry overlay |
| *(entry itself)* | — | auto-benchmark | `python -m tools.evaluation` implies benchmark |

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

- **Eye tracking**: MediaPipe Face Landmarker, ~30 FPS background thread
- **Features**: PCA eye-local `uL/vL/uR/vR` + ratio `avg_h/avg_v`
- **Mapping**: Frozen `pca4_baseline` + optional row-Y bias (see `docs/TYPING_CANDIDATE.md`)
- **Typing**: Dwell 0.9 s / cooldown 0.20 s / 5-frame re-arm / 0.25 s key-switch confirm
- **Prediction**: Prefix trie + frequency list (`gazekey/prediction/`); UI uses `WordProvider` only
- **OS input**: `pynput` only inside `gazekey/input/pynput_adapter.py`
- **Layout**: Fullscreen calib; top-half keyboard (`0.62`); simplified letters-only product chrome (003)
