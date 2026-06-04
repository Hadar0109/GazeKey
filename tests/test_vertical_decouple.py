"""Tests for horizontal–vertical feature decoupling."""

from __future__ import annotations

import numpy as np

from gazekey.features.vertical_decouple import apply_v_residualizers_batch, fit_v_residualizers


def test_residualization_reduces_u_correlation():
    # Synthetic: v couples to u; same screen_y for all samples
    u_l = np.linspace(-0.4, 0.4, 9)
    u_r = np.linspace(-0.5, 0.5, 9)
    v_l = -0.3 + 0.8 * u_l + 0.1 * u_r
    v_r = -0.3 + 0.7 * u_r + 0.1 * u_l
    beta_l, beta_r = fit_v_residualizers(u_l, u_r, v_l, v_r)
    vl_r, vr_r = apply_v_residualizers_batch(u_l, u_r, v_l, v_r, beta_l=beta_l, beta_r=beta_r)
    u_mean = 0.5 * (u_l + u_r)
    raw_corr = abs(float(np.corrcoef(0.5 * (v_l + v_r), u_mean)[0, 1]))
    res_corr = abs(float(np.corrcoef(0.5 * (vl_r + vr_r), u_mean)[0, 1]))
    assert raw_corr > 0.9
    assert res_corr < raw_corr * 0.5
