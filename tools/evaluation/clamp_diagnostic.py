"""PCA unclamped-vs-clamped helpers removed with Stage G mapper deletion."""

from __future__ import annotations

from typing import Any, Optional, Tuple


def clip_bounds_of(model: Any) -> Optional[Tuple[float, float, float, float]]:
    del model
    return None


def unclamped_xy_from_model(model: Any, features: Any) -> Optional[Tuple[float, float]]:
    del model, features
    return None


def make_eval_predict_fns(host: Any) -> Tuple[Any, Any]:
    del host

    def _none(_feat: Any) -> None:
        return None

    return _none, _none
