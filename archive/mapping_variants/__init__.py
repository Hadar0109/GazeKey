"""Dormant mapper variants archived from gazekey.mapping (T055).

Import example (repo root on PYTHONPATH):

    from archive.mapping_variants.idw_local import IDWFeatureMapper
    from archive.mapping_variants.idw_ratio import IDWRatioMapper
    from archive.mapping_variants.row_aware import RowAwareMapper
"""

from archive.mapping_variants.idw_local import IDWFeatureMapper
from archive.mapping_variants.idw_ratio import IDWRatioMapper
from archive.mapping_variants.row_aware import RowAwareMapper

__all__ = ["IDWFeatureMapper", "IDWRatioMapper", "RowAwareMapper"]
