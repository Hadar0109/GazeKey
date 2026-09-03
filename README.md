# GazeKey

GazeKey is a webcam eye-tracking virtual keyboard for Windows. After official GazeFollower calibration, a Qt overlay sits at the top of the screen. Looking at a key (dwell) or clicking it types into whichever external app currently has focus — not into GazeKey itself.

## How it works

```text
Webcam → official GazeFollower (preview + 13-point calibration + sampling)
      → GazeSample (filtered screen gaze, origin/DPR only)
      → live key hit-test on the visible page
      → dwell → KeyAction → OS input (pynput)
```

There is no GazeKey-owned mapper after GazeFollower. Invalid gaze (including blinks) cancels dwell and does not type.

The keyboard is English QWERTY split into two letter pages so targets stay large:

- **Left** (default): `Q W E R T` / `A S D F G` / Shift `Z X C V` Backspace, plus a tall **→**
- **Right**: `Y U I O P` / `H J K L` / Shift `B N M` Backspace, plus a tall **←**

Suggestions, **CALIBRATE**, Space, and Enter stay on both pages. The arrow switches pages and never types.

## Requirements

- **Windows** desktop (verified product platform)
- **Python 3.11** (project runtime: 3.11.9). Do not install or run on Python 3.14
- A webcam. The product opens OpenCV camera **index 0** at 640×480, 30 fps
- A **chin/head support** for the physical setup used by this project’s accuracy checks
- An external typing target (for example Notepad) visible in the lower part of the screen

Upstream GazeFollower is pinned to v1.0.2 (`553920edcb7998c029828677f50f6d8eb4a16249`) and is licensed **CC BY-NC-SA 4.0** (attribution, non-commercial, share-alike).

## Install

From the repository root, with Python 3.11:

```text
python -m venv .venv
.venv\Scripts\python.exe -m pip install --no-build-isolation -r requirements.txt
```

`--no-build-isolation` is required: GazeFollower’s installer imports the package at build time.

`python main.py` re-executes into the project `.venv` when that interpreter exists. Developer tools and pytest do **not** re-exec; use `.venv\Scripts\python.exe` for those.

## Run

```text
python main.py
```

1. GazeFollower **Preview** (pygame, fullscreen). It continues automatically after about 5 seconds (a real key still works if you press one).
2. GazeFollower **13-point Calibration**. Look at each dot. Guidance and the result screen also continue automatically (about 2 seconds each). If calibration is not accepted, the process exits.
3. The GazeKey overlay appears at the **top** of the available screen, about **70%** of available height. A **green ring** shows filtered gaze.
4. Focus an external editor below the keyboard. Dwell on a key (~0.9 s) or click it to type there. The overlay does not take OS focus.
5. After two or more letters of a word, up to three English suggestions appear. Dwell or click one to inject the remaining letters plus Space.
6. Use **→** / **←** to change letter page. Use **CALIBRATE** for a fresh official Preview + Calibration (keyboard hides, then returns on the **left** page). Minimize/restore keeps the current page.

Close the overlay with **✕**.

## Launch options

Normal use does not need extra flags. There is no `GAZEKEY_*` environment-variable fallback.

| Option | Effect |
|--------|--------|
| `--verbose` | Extra GazeKey console logs |
| `--calib-debug` | Accepted by the parser (intended extra calibration logs; GazeKey does not currently consume this beyond storing the flag) |
| `--gaze-debug` | Accepted by the parser (intended extra labels on the **tools** gaze-preview overlay, not the product green ring) |

Typing starts automatically after a successful official calibration. There is no typing-enable flag.

`--calib-mode`, `--calib-geom-debug`, and `--camera-preview-during-calib` are **not** product flags.

Developer preview / benchmark entries live under [`tools/README.md`](tools/README.md). They are not required for normal use.

## Assumptions and limits

- Single **primary** monitor. The overlay is a top-of-screen tool window, always on top, and does not accept focus.
- Letters-only English keyboard. No symbols layout, no in-app text buffer, no product Pause/Preview button.
- Dwell: 0.9 s select, 0.20 s cooldown, 5-frame leave confirm, 0.25 s key-switch confirm.
- GazeFollower’s HeuristicFilter is the only smoothing. GazeKey does not add a second mapper or extra screen smoothing.
- Recalibration replaces the live model; a previous calibration is not kept as a fallback.
- Accuracy work in this repository assumes chin/head support.

## Repository layout

```text
main.py                 Product launch (GazeFollower, then Qt keyboard)
requirements.txt        Product dependencies
gazekey/                Product runtime (backend, UI, typing, prediction, OS input)
tools/                  Developer utilities (see tools/README.md)
tests/                  Pytest suite
specs/                  Spec Kit feature docs (004 is historical; do not resume it)
runs/                   Session artifacts (geometry audit, optional eval folders)
```

Word-list attribution for suggestions: [`gazekey/prediction/data/README.md`](gazekey/prediction/data/README.md).

## Tests

`pytest` is used by the suite and is present in the project `.venv`, but it is **not** listed in `requirements.txt`.

```text
.venv\Scripts\python.exe -m pytest tests/ -q
```
