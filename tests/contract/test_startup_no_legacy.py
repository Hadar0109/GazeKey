"""T025: production startup path does not import/call the legacy estimator stack."""

from __future__ import annotations

import ast
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_SCAN_PATHS = [
    _REPO / "main.py",
    _REPO / "gazekey" / "backend" / "startup.py",
]
_FORBIDDEN_TOKENS = (
    "FeatureExtractor",
    "Pca4BaselineMapper",
    "pca_vL",
    "pca_vR",
    "keyboard15",
    "TrackingManager",
    "MapperRuntime",
    "CalibrationOverlay",
    "fit_calibration_mapper",
    "key_accuracy_predict_screen_xy",
)


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_startup_sources_do_not_name_legacy_estimators():
    offenders: list[str] = []
    for path in _SCAN_PATHS:
        src = _source(path)
        rel = path.relative_to(_REPO).as_posix()
        for token in _FORBIDDEN_TOKENS:
            if token in src:
                offenders.append(f"{rel}: {token}")
    assert offenders == [], "startup path named legacy estimator:\n" + "\n".join(
        offenders
    )


def test_main_does_not_construct_qt_before_official_startup():
    src = _source(_REPO / "main.py")
    assert "run_official_startup" in src
    assert "QApplication" in src
    qapp_idx = src.index("QApplication")
    startup_idx = src.index("run_official_startup")
    assert startup_idx < qapp_idx
    assert "VirtualKeyboard" in src
    vk_idx = src.index("VirtualKeyboard()")
    assert vk_idx > qapp_idx


def test_backend_startup_ast_has_no_legacy_imports():
    path = _REPO / "gazekey" / "backend" / "startup.py"
    tree = ast.parse(_source(path), filename=str(path))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    for name in imported:
        assert not name.startswith("gazekey.features")
        assert not name.startswith("gazekey.mapping")
        assert not name.startswith("gazekey.calibration")
        assert not name.startswith("gazekey.tracking")
        assert not name.startswith("gazekey.runtime.mapper_runtime")
        assert not name.startswith("gazekey.runtime.tracking_controller")
