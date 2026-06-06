# Typing candidate: `pca4_baseline_v1`

This document freezes the mapper configuration used for **real keyboard typing experiments**.
Calibration quality benchmarking is no longer the primary goal; this stack is "good enough to try."

## What was chosen

| Layer | Choice | Notes |
|-------|--------|-------|
| Mapper | **`pca4_baseline`** | X from `[uL, uR]`; Y from raw `[vL, vR]` |
| Calibration layout | **`keyboard15`** | 15 points on real key centers + row gaps |
| Ridge α | **Auto grid, typically 1.0** | Grid `(1, 10, 50, 100, 200, 400)`; pick largest α within 5 px of best LOOCV |
| Post-fit corrections | **Row Y bias + local Y** | Applied before region gates and at runtime |
| Feature smoother | **EMA α = 0.28** | `PcaFeatureSmoother` on PCA u/v before predict |
| Gaze smoother | **EMA α = 0.35** | Screen-coordinate smoothing after mapper |
| Quality gates | **Region-first (keyboard)** | train region wrong ≤ 1, LOOCV region wrong ≤ 2; pixel thresholds are warnings |
| Candidate ranking | **Disabled (frozen)** | Only `pca4_baseline` is fit; poly12/decoupled paths remain in code but inactive |

All constants live in `gazekey/mapping/typing_candidate.py`.

## Evidence from archived sessions (`runs/`)

Six calibration sessions were collected (passing and failing runs). Summary for **`pca4_baseline`** on the 15-key accuracy benchmark:

| Session | LOOCV RMS | Gates | Key accuracy | Mean error |
|---------|-----------|-------|--------------|------------|
| 01 | 64.3 px | FAILED | 3/15 (20%) | 110.9 px |
| 02 | 58.7 px | PASSED | 5/15 (33%) | 76.9 px |
| 03 | 67.9 px | FAILED | 4/15 (27%) | 114.7 px |
| **04** | **59.9 px** | **PASSED** | **9/15 (60%)** | **46.9 px** |
| 05 | 45.7 px | PASSED | 5/15 (33%) | 79.6 px |
| 06 (freeze) | 66.0 px | PASSED | 4/15 (27%) | 112.1 px |

**Best keyboard hit rate:** session 04 at 9/15 (60%). Session 05 had the lowest LOOCV (45.7 px) but only 5/15 keys correct — LOOCV alone does not predict typing accuracy.

### Why pca4_baseline over poly12 / decoupled

- On the **same gaze replay**, pca4_baseline matched or beat poly12 on key accuracy in most sessions (e.g. session 04: both 9/15).
- Poly12 often wins on LOOCV RMS but adds 12D features and u–v coupling complexity without consistent typing gains.
- `pca4_decoupled_split` failed region gates in 2/6 sessions; baseline pca4 passed in 4/6 and is simpler.
- Correction layers (row bias + local Y) address the main geometric failure mode (row tilt from u–v coupling) without changing the core mapper.

### What we kept from analysis

1. **keyboard15** — denser targets on real keys beat abstract 3×3 grids.
2. **Region gates as primary** — wrong row/column is a harder fail than moderate pixel RMS.
3. **Row Y bias + local Y correction** — layer ablation showed local Y fixes within-row tilt; row bias fixes global row offsets.
4. **Feature smoother α = 0.28** — consistent across eval and runtime paths.
5. **Keyboard corr(screen_y, avg_v) warning-only** below 0.55 — avoids rejecting usable calibrations with moderate vertical coupling.

### What we stopped doing

- Multi-candidate LOOCV ranking (poly12 vs pca4 vs decoupled).
- Automatic post-calibration 15-key accuracy test (opt-in via `GAZEKEY_KEYBOARD_ACCURACY_DEBUG=1`).
- Default preview mode after calibration (preview blocks key activation; typing starts immediately).

## How to test typing

1. Launch: `python main.py`
2. Complete the 15-point calibration (fixate each dot until it advances).
3. When you see `Gaze typing enabled`, look at keys and dwell to type.
4. Optional: click **Preview** to show the gaze dot without key activation.
5. Optional diagnostics:
   - `GAZEKEY_KEYBOARD_ACCURACY_DEBUG=1` — run 15-key accuracy test after calibration
   - `GAZEKEY_CALIB_DEBUG=1` — verbose calibration overlay
   - `GAZEKEY_GAZE_DEBUG=0` — hide per-frame gaze logs

## Expected quality

Calibration will still be imperfect. Typical passing runs show:

- LOOCV RMS: ~45–67 px
- corr(screen_y, avg_v): 0.63–0.82
- Key accuracy benchmark: ~27–60% (high session-to-session variance)

When gates fail (e.g. weak vertical separation, LOOCV region wrong > 2, head drift during collection), typing stays disabled and the app prompts RECALIBRATE. Fix head position and repeat calibration — there is no best-effort typing bypass.

The typing experiment phase evaluates **dwell behavior, row switching, and real text entry** — not calibration LOOCV alone.

## Next phase: real typing evaluation

With `pca4_baseline_v1` frozen, the focus shifts to **live typing sessions**, not calibration model comparison.

### What to observe

- **Typing accuracy** — intended vs activated keys
- **Row transitions** — cross-row switches, stickiness, wrong-row activations
- **Dwell behavior** — time to focus, accidental activations, missed keys
- **Key confusions** — systematic neighbor swaps (e.g. Y/T, adjacent letters)
- **Usability** — fatigue, recalibration need, preview vs typing mode

### Artifacts to collect

| File | Use |
|------|-----|
| `runtime_key_confidence.csv` | Per-frame gaze, focus, dwell, activation (written during typing) |
| Session notes | Subjective usability, phrases attempted, failure patterns |

Optional calibration diagnostics (not run by default):

- `GAZEKEY_KEYBOARD_ACCURACY_DEBUG=1` — 15-key post-calibration benchmark
- `GAZEKEY_KEYBOARD_ACCURACY_COMPARE=1` — multi-mapper replay (legacy; inactive mapper paths)

After several real typing sessions, analyze errors to decide whether the next improvements belong in **mapping**, **dwell/selection**, **correction layers**, or **UI**.

## Changing this configuration

Edit `gazekey/mapping/typing_candidate.py` and update this document.
To re-enable multi-candidate mapper ranking, clear `ACTIVE_MAPPER` freeze logic in `fit_calibration_mapper()` (`gazekey/mapping/ridge.py`).
