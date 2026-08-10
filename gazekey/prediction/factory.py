"""Composition helpers for prediction providers (setup-site only)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from gazekey.prediction.trie_provider import TrieWordProvider
from gazekey.prediction.word_provider import WordProvider


def create_default_word_provider(words_path: Optional[Path] = None) -> WordProvider:
    """Construct the default WordProvider once at the composition root."""
    return TrieWordProvider(words_path)
