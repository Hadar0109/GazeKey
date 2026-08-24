"""T005: packaged base.mnn hash and license-of-record."""

from __future__ import annotations

import sys

from gazekey.backend.provenance import (
    EXPECTED_BASE_MNN_SHA256,
    EXPECTED_PYTHON,
    LICENSE_OF_RECORD,
    UPSTREAM_COMMIT,
    UPSTREAM_VERSION,
    product_interpreter_path,
    provenance_record,
    require_python_311,
    verify_base_mnn,
)


def test_license_of_record_is_cc_by_nc_sa():
    assert LICENSE_OF_RECORD == "CC BY-NC-SA 4.0"
    record = provenance_record()
    assert record["license"] == LICENSE_OF_RECORD
    assert record["upstream_commit"] == UPSTREAM_COMMIT
    assert record["upstream_version"] == UPSTREAM_VERSION


def test_python_is_311():
    require_python_311()
    assert sys.version_info[:2] == EXPECTED_PYTHON
    path = product_interpreter_path()
    assert path
    assert "python" in path.lower()


def test_packaged_base_mnn_sha256():
    digest = verify_base_mnn()
    assert digest == EXPECTED_BASE_MNN_SHA256
