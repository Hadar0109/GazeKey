"""Pinned GazeFollower provenance for Feature 005 (plan.md / FR-022 / FR-041)."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

UPSTREAM_REPO = "https://github.com/GanchengZhu/GazeFollower"
UPSTREAM_COMMIT = "553920edcb7998c029828677f50f6d8eb4a16249"
UPSTREAM_VERSION = "1.0.2"
MODEL_NAME = "base.mnn"
EXPECTED_BASE_MNN_SHA256 = (
    "2f96b95275fe6d7b79e98df3237ebb96e15ef5522c96968f08167da7e1954a96"
)
# License of record: repository LICENSE-CC-BY-NC-SA + README.
# version.py "CC BY 4.0" is upstream metadata inconsistency only.
LICENSE_OF_RECORD = "CC BY-NC-SA 4.0"
LICENSE_NOTES = (
    "Attribution + non-commercial / share-alike. Commercial use is outside "
    "Feature 005. gazefollower.version.__license__ CC BY 4.0 is upstream "
    "inconsistency only — do not reinterpret as CC BY 4.0."
)
CALI_MODE = 13
# OpenCV index: 0 = laptop Integrated Camera, 1 = USB Full HD webcam.
CAMERA = {"webcam_id": 0, "width": 640, "height": 480, "fps": 30}
FILTER = "HeuristicFilter(look_ahead=3)"
PHYSICAL_SCREEN_SIZE = None
EXPECTED_PYTHON = (3, 11)

# Product interpreter is the 3.11 venv at repo `.venv` (T001). Runtime path:
# sys.executable when launched from that environment.
PRODUCT_VENV_PYTHON = str(
    Path(__file__).resolve().parents[2] / ".venv" / "Scripts" / "python.exe"
)


class ProvenanceError(RuntimeError):
    """Model hash or runtime provenance does not match the Feature 005 pin."""


def product_interpreter_path() -> str:
    """Interpreter the product actually runs on (T001)."""
    return sys.executable


def require_python_311() -> None:
    if sys.version_info[:2] != EXPECTED_PYTHON:
        raise ProvenanceError(
            f"GazeKey product runtime must be Python 3.11.x; got {sys.version}"
        )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def packaged_base_mnn_path() -> Path:
    import gazefollower

    pkg = Path(gazefollower.__file__).resolve().parent
    return pkg / "res" / "model_weights" / MODEL_NAME


def verify_base_mnn(path: Path | None = None) -> str:
    """Return SHA-256 of packaged base.mnn; raise if it does not match the pin."""
    model_path = path if path is not None else packaged_base_mnn_path()
    if not model_path.is_file():
        raise ProvenanceError(f"GazeFollower model missing: {model_path}")
    digest = sha256_file(model_path)
    if digest != EXPECTED_BASE_MNN_SHA256:
        raise ProvenanceError(
            f"base.mnn SHA-256 mismatch: got {digest}, "
            f"expected {EXPECTED_BASE_MNN_SHA256}"
        )
    return digest


def provenance_record() -> dict[str, object]:
    try:
        model_path = str(packaged_base_mnn_path())
    except Exception:
        model_path = f"gazefollower/res/model_weights/{MODEL_NAME}"
    return {
        "upstream_repo": UPSTREAM_REPO,
        "upstream_commit": UPSTREAM_COMMIT,
        "upstream_version": UPSTREAM_VERSION,
        "model_path": model_path,
        "model_sha256": EXPECTED_BASE_MNN_SHA256,
        "cali_mode": CALI_MODE,
        "camera": dict(CAMERA),
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "interpreter": product_interpreter_path(),
        "recorded_venv_python": PRODUCT_VENV_PYTHON,
        "license": LICENSE_OF_RECORD,
        "license_notes": LICENSE_NOTES,
        "filter": FILTER,
        "physical_screen_size": PHYSICAL_SCREEN_SIZE,
    }
