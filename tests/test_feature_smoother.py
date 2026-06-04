from gazekey.features.feature_smoother import PcaFeatureSmoother
from gazekey.features.feature_types import FrameFeatures


def _feat(u_l: float, v_l: float, u_r: float, v_r: float) -> FrameFeatures:
    return FrameFeatures(
        0,
        True,
        False,
        1.0,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        pca_uL=u_l,
        pca_vL=v_l,
        pca_uR=u_r,
        pca_vR=v_r,
    )


def test_pca_feature_smoother_ema():
    s = PcaFeatureSmoother(alpha=0.5)
    a = s.smooth(_feat(0.0, 0.0, 0.0, 0.0))
    b = s.smooth(_feat(1.0, 1.0, 1.0, 1.0))
    assert b.pca_uL == 0.5
    assert b.pca_vR == 0.5
