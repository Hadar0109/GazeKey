"""CLI → AppConfig boundary (no GAZEKEY_* env)."""

from __future__ import annotations

import pytest

from gazekey.app_config import (
    AppConfig,
    apply_config,
    get_config,
    parse_evaluation_args,
    parse_preview_args,
    parse_product_args,
)


def test_product_cli_defaults():
    cfg = parse_product_args([])
    assert cfg == AppConfig()
    assert cfg.auto_benchmark is False
    assert cfg.calib_geom_debug is False


def test_product_cli_options():
    cfg = parse_product_args(
        [
            "--verbose",
            "--calib-debug",
            "--gaze-debug",
        ]
    )
    assert cfg.verbose is True
    assert cfg.calib_debug is True
    assert cfg.gaze_debug is True
    assert cfg.auto_benchmark is False


def test_product_rejects_tools_only_flags():
    with pytest.raises(SystemExit):
        parse_product_args(["--calib-geom-debug"])
    with pytest.raises(SystemExit):
        parse_product_args(["--calib-mode", "keyboard_full9"])
    with pytest.raises(SystemExit):
        parse_product_args(["--camera-preview-during-calib"])


def test_preview_allows_geom_debug_without_auto_benchmark():
    cfg = parse_preview_args(["--calib-geom-debug", "--verbose", "--calib-mode", "keyboard_full9"])
    assert cfg.calib_geom_debug is True
    assert cfg.verbose is True
    assert cfg.auto_benchmark is False
    assert cfg.calib_mode == "keyboard_full9"


def test_evaluation_implies_auto_benchmark():
    cfg = parse_evaluation_args([])
    assert cfg.auto_benchmark is True


def test_apply_config_is_process_wide():
    apply_config(AppConfig(verbose=True, auto_benchmark=True))
    assert get_config().verbose is True
    assert get_config().auto_benchmark is True
