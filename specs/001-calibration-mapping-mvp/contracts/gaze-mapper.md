# Contract: Gaze Mapper

**Version**: 1.1.0  
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
- `mapper_id` MUST be `pca4_baseline` unless a **benchmark-approved task**
  adds exactly one documented correction layer

## Constraints

1. **One** fitted `GazeMapper` active after calibration — no fallback chain.
2. Experimental mappers (`poly12`, `decoupled_split`, `idw_*`, `row_aware`, v1)
   MUST NOT be invocable from the normal user flow.
3. Post-fit wrappers (row bias, local Y) MUST NOT ship in the initial MVP active
   path. Add at most **one** layer per approved task when benchmark per-key
   results justify it.
4. Improvement is **result-driven**: benchmark failures guide changes within the
   PCA4 pipeline — not a variant comparison matrix.

## Feature input

- Runtime predict: `PcaFeatureSmoother` → PCA features → `predict()`
- Fit: per-target mean `FrameFeatures` from calibration samples

## Existing implementation mapping

| Piece | Current code |
|-------|--------------|
| PCA4 fit/predict | `gazekey/mapping/ridge.py` |
| Frozen constants | `gazekey/mapping/typing_candidate.py` |
| Inactive (do not wire) | `poly_features.py`, `idw_*.py`, `row_aware.py`, v1 `affine_mapper` |
| Corrections (inactive initially) | `row_bias.py`, `local_y_correction.py` |

## Out of scope

- Loading `calibration_v2.json` on startup (per-session only — CQ-2)
- Mapper variant hunts or LOOCV-based model switching
