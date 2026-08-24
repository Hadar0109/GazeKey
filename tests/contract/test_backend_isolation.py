"""T013 / T017: gazekey.backend must not import legacy gaze modules or copy features."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_BACKEND = _REPO / "gazekey" / "backend"
_FORBIDDEN_MODULES = (
    "gazekey.features",
    "gazekey.mapping",
    "gazekey.calibration",
    "gazekey.tracking",
)


def _backend_py_files() -> list[Path]:
    return sorted(_BACKEND.rglob("*.py"))


def _imported_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            names.add(mod)
            for alias in node.names:
                if mod:
                    names.add(f"{mod}.{alias.name}")
    return names


def test_backend_ast_does_not_import_forbidden_packages():
    offenders: list[str] = []
    for path in _backend_py_files():
        imported = _imported_names(path)
        rel = path.relative_to(_REPO).as_posix()
        for name in imported:
            for forbidden in _FORBIDDEN_MODULES:
                if name == forbidden or name.startswith(forbidden + "."):
                    offenders.append(f"{rel}: {name}")
    assert offenders == [], "backend imported forbidden modules:\n" + "\n".join(
        offenders
    )


def test_backend_runtime_import_does_not_load_forbidden_packages():
    for name in list(sys.modules):
        if any(name == f or name.startswith(f + ".") for f in _FORBIDDEN_MODULES):
            del sys.modules[name]
    for name in list(sys.modules):
        if name == "gazekey.backend" or name.startswith("gazekey.backend."):
            del sys.modules[name]

    import gazekey.backend  # noqa: F401
    import gazekey.backend.adapter  # noqa: F401
    import gazekey.backend.geometry  # noqa: F401
    import gazekey.backend.gaze_sample  # noqa: F401

    loaded = [
        name
        for name in sys.modules
        if any(name == f or name.startswith(f + ".") for f in _FORBIDDEN_MODULES)
    ]
    assert loaded == []


def test_adapter_never_copies_gazeinfo_features():
    adapter_src = (_BACKEND / "adapter.py").read_text(encoding="utf-8")
    tree = ast.parse(adapter_src)
    attrs = [
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
    ]
    assert "features" not in attrs
    from gazekey.backend.gaze_sample import GazeSample

    assert "features" not in GazeSample.__dataclass_fields__


def test_gaze_sample_type_has_no_features_or_raw_or_event():
    from gazekey.backend.gaze_sample import GazeSample

    fields = set(GazeSample.__dataclass_fields__)
    assert "features" not in fields
    assert "raw_gaze_coordinates" not in fields
    assert "event" not in fields
    assert "confidence" not in fields


def test_backend_does_not_pass_features_to_a_mapper():
    for path in _backend_py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported = _imported_names(path)
        rel = path.relative_to(_REPO).as_posix()
        for name in imported:
            assert not name.startswith("gazekey.runtime.mapper_runtime"), rel
            assert not name.startswith("gazekey.features"), rel
            assert not name.startswith("gazekey.mapping"), rel
        calls = [
            node.func.attr
            if isinstance(node.func, ast.Attribute)
            else getattr(node.func, "id", "")
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
        ]
        assert "key_accuracy_predict_screen_xy" not in calls, rel
        assert "fit_calibration_mapper" not in calls, rel
        assert "FeatureExtractor" not in calls, rel
