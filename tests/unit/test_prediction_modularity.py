"""Architectural modularity: UI/typing must not import trie internals."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = (
    "gazekey.prediction.trie_provider",
    "from gazekey.prediction.trie_provider",
    "import TrieWordProvider",
)


def _py_files(package: str):
    base = ROOT / "gazekey" / package
    return sorted(base.rglob("*.py"))


def test_ui_and_typing_do_not_import_trie_internals():
    offenders = []
    for package in ("ui", "typing"):
        for path in _py_files(package):
            text = path.read_text(encoding="utf-8")
            for needle in FORBIDDEN:
                if needle in text:
                    offenders.append(f"{path.relative_to(ROOT)}: {needle}")
    assert not offenders, "UI/typing must depend on WordProvider only:\n" + "\n".join(offenders)
