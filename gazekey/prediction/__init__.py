"""Prefix-based word prediction (feature 003)."""

from __future__ import annotations

from gazekey.prediction.word_provider import WordProvider
from gazekey.prediction.trie_provider import TrieWordProvider
from gazekey.prediction.typing_context import TypingContext

__all__ = [
    "WordProvider",
    "TrieWordProvider",
    "TypingContext",
]
