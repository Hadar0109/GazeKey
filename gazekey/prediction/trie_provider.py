"""TrieWordProvider — bundled word-list WordProvider with top-k node caches."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

DEFAULT_WORD_LIST = Path(__file__).resolve().parent / "data" / "words_en.txt"
_MIN_PREFIX_LEN = 2
_TOP_K = 3


class _TrieNode:
    __slots__ = ("children", "top")

    def __init__(self) -> None:
        self.children: Dict[str, _TrieNode] = {}
        # Best completions under this node: (rank, word), rank ascending.
        self.top: List[Tuple[int, str]] = []


def _merge_top(existing: List[Tuple[int, str]], candidate: Tuple[int, str], k: int) -> List[Tuple[int, str]]:
    merged = list(existing)
    word = candidate[1]
    merged = [item for item in merged if item[1] != word]
    merged.append(candidate)
    merged.sort(key=lambda item: (item[0], item[1]))
    return merged[:k]


class TrieWordProvider:
    """
    Frequency-ranked prefix completions via an in-memory trie.

    Each node stores a top-k (k=3) frequency cache maintained at build time so
    ``suggest`` does not sort the full prefix subtree (research R2).
    """

    def __init__(self, words_path: Optional[Path] = None) -> None:
        self._root = _TrieNode()
        self._loaded = False
        self._load_error: Optional[BaseException] = None
        path = Path(words_path) if words_path is not None else DEFAULT_WORD_LIST
        try:
            self._build_from_file(path)
            self._loaded = True
        except BaseException as exc:  # fail-open at product boundary
            self._load_error = exc
            self._root = _TrieNode()

    @property
    def load_error(self) -> Optional[BaseException]:
        return self._load_error

    def _build_from_file(self, path: Path) -> None:
        text = path.read_text(encoding="utf-8")
        rank = 0
        for line in text.splitlines():
            word = line.strip().lower()
            if not word or not word.isalpha():
                continue
            self._insert(word, rank)
            rank += 1

    def _insert(self, word: str, rank: int) -> None:
        node = self._root
        candidate = (rank, word)
        node.top = _merge_top(node.top, candidate, _TOP_K)
        for ch in word:
            child = node.children.get(ch)
            if child is None:
                child = _TrieNode()
                node.children[ch] = child
            node = child
            node.top = _merge_top(node.top, candidate, _TOP_K)

    def suggest(self, prefix: str, *, limit: int = 3) -> List[str]:
        if self._load_error is not None:
            return []
        if not prefix or len(prefix) < _MIN_PREFIX_LEN:
            return []
        node = self._root
        for ch in prefix.lower():
            child = node.children.get(ch)
            if child is None:
                return []
            node = child
        lim = max(0, min(int(limit), _TOP_K))
        return [word for _, word in node.top[:lim]]
