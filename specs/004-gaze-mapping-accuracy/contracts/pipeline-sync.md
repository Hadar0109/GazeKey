# Contract: Calibration / Runtime Pipeline Sync

**Version**: 1.0.0  
**Feature**: `004-gaze-mapping-accuracy`

## Purpose

Guarantee the mapper is taught and queried with a **compatible gaze
representation**, and that keyboard coordinates stay consistent after
Feature 003 layout.

## Representation

The vector used in `TargetSample.gaze_representation` MUST be the same
fields, order, and left/right semantics as `GazeMapping.predict`.

| Concern | Rule |
|---------|------|
| Feature order | Identical at fit and predict |
| Left/right axes | Same geometric meaning; no silent inversion |
| Missing eye | Same accept / reject / degrade policy in gate, aggregation, and predict |
| Smoothing / averaging | Same, **or** difference documented and justified by a measured experiment (FR-010) |
| Normalization | Fit-time `mu`/`sigma` (or equivalent) applied unchanged at predict |

## Collection vs mapper dimensionality

The fixation **stability gate** MUST evaluate stability in the
**same dimensionality** the mapper consumes (as-built: four per-eye u/v
components). A 2-D average of the two eyes MUST NOT be the sole lock
criterion unless an experiment **keep**s that after evidence.

## Aggregation

Combining accepted frames into one `TargetSample` MUST preserve
same-observation relationships (FR-003). Independent per-channel outlier
means that invent a vector no frame produced are a defect unless justified.

## Geometry checklist (must hold on a session)

1. Calibration dot global position = `CalibrationTarget.screen_x/y`
2. Those coordinates = mapper training Y
3. Visible key `rect` / center from `inspect_keyboard_layout` after overlay
4. Runtime `MappedGaze` in the same global space
5. `hit_test_layout_keys` uses those rects
6. Clip bounds cover the required **prediction domain**
7. When a raw prediction falls **outside** those bounds, as-built **clamp**
   onto the AABB is an investigation (research R7): evaluation MAY report
   unclamped vs clamped hit-test as a diagnostic. Product clamp MUST NOT be
   removed, expanded to fullscreen, or treated as a ridge bug until that
   comparison exists.

8. Resize / reposition / scaling: if no supported user-facing path exists,
   record **unsupported** and close FR-014 for that case; overlay-close →
   restored keyboard still MUST hold (research R7).

Failure of 1–6 is a geometry/sync bug, not a reason to retune ridge.
Clamp pinning edge keys is a **hypothesis**, not a required product change.

## Product typing vs evaluation

Product typing: `MappedGaze` → `hit_test_layout_keys` → dwell (002/003).
Evaluation may observe the same `MappedGaze` and hit-test; it MUST NOT
replace them.
