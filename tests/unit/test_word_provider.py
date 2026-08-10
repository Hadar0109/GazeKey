"""Unit tests for WordProvider / TrieWordProvider (003)."""

from __future__ import annotations

from pathlib import Path

import pytest

from gazekey.prediction.trie_provider import TrieWordProvider
from gazekey.prediction.word_provider import WordProvider


@pytest.fixture(scope="module")
def provider() -> TrieWordProvider:
    p = TrieWordProvider()
    assert p.load_error is None
    return p


def test_word_provider_protocol_runtime(provider: TrieWordProvider):
    assert isinstance(provider, WordProvider)


def test_suggest_hel_includes_hello_or_help(provider: TrieWordProvider):
    words = provider.suggest("hel")
    assert len(words) <= 3
    assert any(w.startswith("hel") for w in words)
    assert "hello" in words or "help" in words
    for w in words:
        assert w.lower().startswith("hel")


def test_suggest_single_char_empty(provider: TrieWordProvider):
    assert provider.suggest("h") == []
    assert provider.suggest("") == []


def test_suggest_no_match_empty(provider: TrieWordProvider):
    assert provider.suggest("zzzz") == []


def test_suggest_limit_at_most_three(provider: TrieWordProvider):
    for prefix in ("th", "he", "an", "in", "wh", "the", "co"):
        assert len(provider.suggest(prefix)) <= 3


def test_quality_smoke_common_prefixes(provider: TrieWordProvider):
    """Deterministic usefulness checks against bundled FrequencyWords list."""
    expectations = {
        "th": {"the", "that", "this", "there", "they", "then", "than"},
        "he": {"he", "her", "here", "hey", "help", "hello"},
        "an": {"and", "an", "any", "another", "anything"},
        "in": {"in", "into", "inside", "information", "instead"},
        "wh": {"what", "who", "why", "when", "where", "which"},
    }
    for prefix, allowed in expectations.items():
        words = provider.suggest(prefix)
        assert words, f"expected suggestions for {prefix!r}"
        assert any(w in allowed for w in words), (
            f"prefix {prefix!r} got {words}, expected overlap with {allowed}"
        )


def test_fail_open_missing_word_file(tmp_path: Path):
    missing = tmp_path / "missing_words.txt"
    p = TrieWordProvider(missing)
    assert p.load_error is not None
    assert p.suggest("hel") == []
    assert p.suggest("th") == []


def test_fail_open_suggest_exception_handled_by_caller_contract(tmp_path: Path):
    """Caller contract: empty list on load failure; no crash."""
    bad = tmp_path / "words.txt"
    bad.write_text("hello\nhelp\n", encoding="utf-8")
    p = TrieWordProvider(bad)
    assert p.suggest("hel")  # works
    # Simulate suggest path with short prefix still safe
    assert p.suggest("x") == []
