# Contract: Gaze Mapper

**Version**: 1.2.0  
**Feature**: `001-calibration-mapping-mvp`

## Interface (logical)

```text
GazeMapper
  mapper_id: str          # e.g. "pca4_baseline"
  predict(features: FrameFeatures) -> (screen_x: float, screen_y: float)
  fit_metrics: dict       # supplementary only

MapperFit
  fit(samples: list[CalibrationSample], targets: list[CalibrationTarget]) -> GazeMapper
```

## MVP mapping direction (fixed)

The active path uses **`pca4_baseline`** only:

- Ridge regression on PCA u/v features (`gazekey/mapping/ridge.py`)
- Single fit entry point — no multi-candidate ranking at runtime
- Frozen constants in `gazekey/mapping/config.py`
- Optional **row Y bias** post-fit (`APPLY_ROW_Y_BIAS=True`, `row_bias.py`)

## Constraints

1. **One** fitted `GazeMapper` active after calibration — no fallback chain.
2. Experimental mappers (`poly12`, `decoupled_split`, `idw_*`, `row_aware`, v1)
   MUST NOT be invocable from the normal user flow (archived under `archive/mapping_variants/`).
3. Add at most **one** new correction layer per approved benchmark task.
4. Improvement is **result-driven**: benchmark failures guide changes within the
   PCA4 pipeline — not a variant comparison matrix.

## Tuning levers (Phase 8 — one per iteration)

| Lever | Module |
|-------|--------|
| Ridge α, feature smoothing | `ridge.py`, `config.py` (`ALPHA_GRID`, `FEATURE_SMOOTHER_ALPHA`) |
| Row Y bias on/off or parameters | `config.py`, `row_bias.py` |
| Gaze smoother | `config.py` (`GAZE_SMOOTHER_ALPHA`) |

**Not on active path**: `local_y_correction`, poly12, decoupled, IDW (archived).

## Feature input

- Runtime predict: `PcaFeatureSmoother` → PCA features → `predict()`
- Fit: per-target mean `FrameFeatures` from calibration samples

## Existing implementation mapping

| Piece | Current code |
|-------|--------------|
| PCA4 fit/predict | `gazekey/mapping/ridge.py` |
| Frozen constants | `gazekey/mapping/config.py` |
| Row bias | `gazekey/mapping/row_bias.py` |
| Runtime orchestration | `gazekey/runtime/mapper_runtime.py` |
| Inspection snapshot | `gazekey/debug/mapper_store.py` → `runs/<id>/calibration_v2.json` |

## Out of scope

- Loading `calibration_v2.json` on startup (per-session only — CQ-2)
- Mapper variant hunts or LOOCV-based model switching
