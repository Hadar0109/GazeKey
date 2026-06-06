"""Frozen typing-candidate configuration (pca4_baseline).

Single source of truth for the mapper stack used after calibration v2.
Evidence and rationale: TYPING_CANDIDATE.md at repo root.
"""

from __future__ import annotations

# Human-readable label printed at calibration finish.
TYPING_CANDIDATE_ID = "pca4_baseline_v1"

# Core ridge mapper (frozen — LOOCV multi-candidate ranking disabled).
ACTIVE_MAPPER = "pca4_baseline"

# Calibration target layout (15 key-aligned points on letter region).
CALIBRATION_MODE = "keyboard15"

# Ridge regularization: alpha=1.0 selected in all 6 archived sessions within 5 px LOOCV band.
ALPHA_GRID: tuple[float, ...] = (1.0, 10.0, 50.0, 100.0, 200.0, 400.0)
ALPHA_SELECT_LOOCV_TOL_PX = 5.0
MIN_ALPHA = 1.0

# Post-fit correction layers (row Y bias + X-interpolated local Y; both kept at runtime).
APPLY_ROW_Y_BIAS = True
APPLY_LOCAL_Y_CORRECTION = True

# Runtime smoothing (matches keyboard-accuracy eval pipeline).
FEATURE_SMOOTHER_ALPHA = 0.28
GAZE_SMOOTHER_ALPHA = 0.35

# Mapper candidate quality gates (keyboard15).
MAX_LOOCV_RMS_PX = 95.0
MAX_TARGET_LOOCV_PX = 110.0
MAX_TRAIN_ERROR_PX = 60.0
HALF_KEY_HEIGHT_PX = 34.0

# Final calibration acceptance before typing is enabled.
MAX_VALIDATION_ERROR_PX = 80.0
MAX_OFF_SCREEN_LOOCV = 0
MIN_SCREEN_Y_AVG_V_CORR = 0.55  # warning only for keyboard mode
MIN_CATASTROPHIC_SCREEN_Y_AVG_V_CORR = 0.15  # hard fail
MAX_SINGLE_TARGET_TRAIN_PX = 55.0

# When False, failed calibration gates block typing (no mapper bypass).
ENABLE_TYPING_ON_BEST_EFFORT = False

# Per-sample head geometry limits during fixation collection (stricter than post-hoc QA).
CALIB_HEAD_DRIFT_FACE_XY = 0.008
CALIB_HEAD_DRIFT_EYE_H = 0.003

# Hard fail at calibration finish if eye-box span exceeds this (distance/posture drift).
MAX_HEAD_DRIFT_EYE_H = 0.0045

# Minimum avg_v separation between top and bottom calibration rows.
MIN_AVG_V_ROW_SEPARATION = 0.025

# Cross-row selection stability (runtime intent path).
SELECTION_SWITCH_MARGIN = 0.10
SELECTION_CROSS_ROW_SWITCH_MARGIN = 0.20
SELECTION_MIN_SWITCH_MS = 160.0
SELECTION_CROSS_ROW_MIN_SWITCH_MS = 320.0

# Intent scoring (anisotropic Gaussian + row stickiness).
INTENT_SIGMA_PX = 48.0
INTENT_SIGMA_Y_PX = 62.0
INTENT_ROW_STICKINESS = 1.5
INTENT_CROSS_ROW_PENALTY = 0.5
