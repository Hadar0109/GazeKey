# T065 — Stage G deletion inventory freeze

**Date**: 2026-08-24  
**Status**: **frozen**. No deletions in this task.

**Depends on**: T064 tag `005-pre-cleanup-20260824` at
`4280cc063b36683f3beae85223b044f0d7855e67`.

This freeze is the `plan.md` Stage G list checked against the tree **before**
T066–T078. Production GazeFollower path (`main.py` → `gazekey/backend/` →
`GazeLoopController.on_gaze_sample`) does not *run* these modules. They still
exist on disk and are still imported by leftover VirtualKeyboard / gaze_loop /
tools / tests wiring. T066–T078 strip those references, then delete.

Residual gaze error stays accepted. Do not reopen accuracy work or resize keys.

---

## Gaze runtime / calibration (delete in T066–T073)

| Inventory path | On disk at freeze | Production live path |
|----------------|-------------------|----------------------|
| `gazekey/tracking/tracking_manager.py` | yes | unused (startup isolation) |
| `gazekey/tracking/video_capture.py` | yes | unused |
| `gazekey/tracking/eye_detector.py` | yes | unused |
| `gazekey/tracking/tracking_bridge.py` | yes | constructed on VK init; not started |
| `gazekey/tracking/__init__.py` | yes | import leftover |
| `gazekey/features/extractor.py` | yes | unused on GazeSample path |
| `gazekey/features/feature_types.py` | yes | unused on GazeSample path |
| `gazekey/features/feature_smoother.py` | yes | constructed on VK init; not called on GF path |
| `gazekey/features/__init__.py` | yes | import leftover |
| `gazekey/mapping/ridge.py` | yes | unused on GF path |
| `gazekey/mapping/row_bias.py` | yes | unused |
| `gazekey/mapping/base.py` | yes | unused |
| `gazekey/mapping/config.py` | yes | `CALIBRATION_MODE` / smoother alphas still imported by VK |
| `gazekey/mapping/__init__.py` | yes | import leftover |
| `gazekey/calibration/session.py` | yes | unused on official calib |
| `gazekey/calibration/targets.py` | yes | unused on official calib |
| `gazekey/calibration/fixation_gate.py` | yes | unused on official calib |
| `gazekey/calibration/quality.py` | yes | unused |
| `gazekey/calibration/outliers.py` | yes | unused |
| `gazekey/calibration/region_quality.py` | yes | unused |
| `gazekey/calibration/__init__.py` | yes | import leftover |
| `gazekey/ui/calibration_overlay.py` | yes | leftover; production Calibrate uses official GF UI |
| `gazekey/ui/calibration_controller.py` | yes | leftover |
| `gazekey/ui/calibration_finish.py` | yes | leftover |
| `gazekey/ui/camera_preview_window.py` | yes | leftover |
| `gazekey/runtime/mapper_runtime.py` | yes | constructed; predict path not used for GF typing |
| `gazekey/runtime/tracking_controller.py` | yes | leftover |
| `gazekey/typing/gaze_smoother.py` | yes | constructed on VK init; T031 proved GF path does not call it |
| VK `_gaze_mapper` / `_gaze_bias_*` / `_feature_smoother` / `_init_calibration_on_startup` | yes | leftover fields |

## Dependencies / assets (T074–T075)

| Item | At freeze | Notes |
|------|-----------|--------|
| `models/face_landmarker.task` | **absent** | GazeKey EyeDetector default path; file not in tree |
| `requirements.txt` `mediapipe==0.10.10` | present | GazeKey tracking pin; GF still uses mediapipe internally |
| `gazekey/app_config.py` `--calib-mode` | present on **product** CLI | T075: remove as product flag; tools-only leftover only if still required |

## Tests named for drop/rewrite (T076–T078)

| Task | Path | On disk |
|------|------|---------|
| T076 | `tests/test_ridge_mapper_selection.py` | yes |
| T076 | `tests/test_feature_smoother.py` | yes |
| T076 | `tests/test_row_y_bias_path.py` | yes |
| T077 | `tests/test_fixation_head_gate.py` | yes |
| T078 | `tests/test_calibration2_quality.py` | yes |
| T078 | `tests/test_calibration2_outliers.py` | yes |
| T078 | `tests/unit/test_calibration_us1.py` | yes |
| T078 | `tests/unit/test_calibration_session_collection.py` | yes |
| T078 | `tests/test_region_quality.py` | yes |

Keep typing / prediction / layout tests. Other files that only exist to pin
PCA4 / keyboard15 / overlay will fail after deletions and must be dropped or
rewritten in the same Stage G window; they are not Feature 004 artifacts.

## Preserve-only (do not delete, resume, renumber, or rewrite)

| Artifact | Present |
|----------|---------|
| `specs/004-gaze-mapping-accuracy/` | yes |
| `runs/_feature004/` | yes |
| tag `004-pca4-investigation-closeout-20260820` | yes |
| tag `004-pre-pivot-exact-20260820` | yes |
| eval_before commits `14938da0bdf0`, `34fb259ccdfd`, `689c8a8ce90c`, `4f665467b260` | cited; not rewritten |

## Next

T066–T078 deletions, each depending on T062 PASS, T063 released, T064, and
this freeze. T079 Feature 004 preserve check. T080 one-pipeline verify.
