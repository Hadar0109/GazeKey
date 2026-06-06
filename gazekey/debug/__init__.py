"""Debug and analytics tools (CSV logging, overlays)."""

from gazekey.debug.keyboard_accuracy import (
    DEFAULT_SAMPLE_KEYS,
    KeyAccuracyDebugCsv,
    KeyboardAccuracyEvalSession,
    RecordedKeyFrames,
    default_key_accuracy_debug_path,
    evaluate_key_accuracy_from_frames,
    mean_frame_features,
    predict_key_accuracy_screen_xy,
    print_accuracy_summary,
    resolve_sample_keys,
)
from gazekey.debug.keyboard_accuracy_mapper_diag import (
    default_anchor_distance_csv_path,
    default_mapper_stages_csv_path,
    run_keyboard_accuracy_mapper_diagnostics,
)
from gazekey.debug.keyboard_accuracy_compare import (
    compare_mapper_candidates,
    default_compare_csv_path,
    print_compare_leaderboard,
    validate_selected_mapper_matches_debug,
    write_compare_csv,
)
from gazekey.debug.runtime_key_confidence_logger import RuntimeKeyConfidenceLogger

__all__ = [
    "DEFAULT_SAMPLE_KEYS",
    "KeyAccuracyDebugCsv",
    "KeyboardAccuracyEvalSession",
    "RecordedKeyFrames",
    "RuntimeKeyConfidenceLogger",
    "compare_mapper_candidates",
    "default_anchor_distance_csv_path",
    "default_compare_csv_path",
    "default_key_accuracy_debug_path",
    "default_mapper_stages_csv_path",
    "evaluate_key_accuracy_from_frames",
    "mean_frame_features",
    "predict_key_accuracy_screen_xy",
    "print_accuracy_summary",
    "print_compare_leaderboard",
    "resolve_sample_keys",
    "run_keyboard_accuracy_mapper_diagnostics",
    "validate_selected_mapper_matches_debug",
    "write_compare_csv",
]

