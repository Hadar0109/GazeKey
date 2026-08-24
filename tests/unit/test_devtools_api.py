"""DevTools host hooks stay compatible with product calibration finish."""

from __future__ import annotations

from unittest.mock import MagicMock

from gazekey.ui.devtools_api import NullDevTools


def test_null_devtools_accepts_calibration_artifact_kwargs():
    """Product finish passes ridge_alpha; NullDevTools must not TypeError."""
    tools = NullDevTools()
    host = MagicMock()
    tools.on_calibration_artifacts(
        host,
        ridge_fit=object(),
        loocv_detail=[],
        quality=MagicMock(),
        ridge_alpha=1.0,
    )
    tools.on_calibration_failed_artifacts(
        host,
        failure_reason="test",
        ridge_alpha=1.0,
        ridge_fit=object(),
        loocv_detail=[],
    )


def test_product_virtual_keyboard_has_no_tools_imports():
    import inspect

    import gazekey.ui.virtual_keyboard as vk_mod

    src = inspect.getsource(vk_mod)
    assert "from tools" not in src
    assert "import tools" not in src
