"""Contract: product typing / UI enablement must not import tools.evaluation."""

from __future__ import annotations

import ast
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_PRODUCT_ROOTS = (
    _REPO / "gazekey" / "ui",
    _REPO / "gazekey" / "typing",
    _REPO / "gazekey" / "runtime",
    _REPO / "gazekey" / "calibration",
    _REPO / "gazekey" / "mapping",
    _REPO / "gazekey" / "backend",
)
_PRODUCT_FILES = [_REPO / "main.py"]


def _iter_product_py() -> list[Path]:
    files: list[Path] = []
    for root in _PRODUCT_ROOTS:
        if root.is_dir():
            files.extend(sorted(root.rglob("*.py")))
    for extra in _PRODUCT_FILES:
        if extra.is_file():
            files.append(extra)
    return files


def _imports_tools_evaluation(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "tools.evaluation" or alias.name.startswith("tools.evaluation."):
                    hits.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod == "tools.evaluation" or mod.startswith("tools.evaluation."):
                hits.append(mod)
            if mod == "tools" and any(a.name == "evaluation" for a in node.names):
                hits.append("tools.evaluation")
    return hits


def test_product_modules_do_not_import_tools_evaluation():
    offenders: list[str] = []
    for path in _iter_product_py():
        rel = path.relative_to(_REPO).as_posix()
        for name in _imports_tools_evaluation(path):
            offenders.append(f"{rel}: {name}")
    assert offenders == [], "product path imported tools.evaluation:\n" + "\n".join(offenders)


def test_typing_enablement_source_does_not_consult_evaluation():
    vk = (_REPO / "gazekey" / "ui" / "virtual_keyboard.py").read_text(encoding="utf-8")
    loop = (_REPO / "gazekey" / "runtime" / "gaze_loop.py").read_text(encoding="utf-8")
    for src in (vk, loop):
        assert "tools.evaluation" not in src
        assert "tools/evaluation" not in src


def test_gazekey_ui_package_import_does_not_load_evaluation():
    import sys

    banned = [
        name
        for name in list(sys.modules)
        if name == "tools.evaluation" or name.startswith("tools.evaluation.")
    ]
    for name in banned:
        del sys.modules[name]
    import gazekey.ui  # noqa: F401
    import gazekey.ui.devtools_api as devtools_api

    loaded = [
        name
        for name in sys.modules
        if name == "tools.evaluation" or name.startswith("tools.evaluation.")
    ]
    assert loaded == []
    assert hasattr(devtools_api, "NullDevTools")
