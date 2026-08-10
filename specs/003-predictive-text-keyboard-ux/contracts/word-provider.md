# Contract: Word prediction provider

**Version**: 1.0.0  
**Feature**: `003-predictive-text-keyboard-ux`

## Purpose

Modular prefix → suggestion API consumed by keyboard UI. No UI or OS dependencies.

## Interface

```python
class WordProvider(Protocol):
    def suggest(self, prefix: str, *, limit: int = 3) -> list[str]:
        """Return up to `limit` completion words for `prefix`."""
```

## Input rules

- `prefix` is lowercase canonical in-progress word (may be empty)
- Provider returns **full words**, not suffixes
- When `len(prefix) < 2`, return `[]` (caller may skip invoke)
- When no matches, return `[]`

## Output rules

- Maximum **3** strings (spec FR-003)
- Each result must satisfy `word.lower().startswith(prefix.lower())`
- Ordered best-first (frequency rank per research R2)
- No duplicate words

## Default implementation

`TrieWordProvider` in `gazekey/prediction/trie_provider.py` loading
`gazekey/prediction/data/words_en.txt`.

Top-3 frequency retrieval MUST follow research R2 (prefix-node walk alone is
insufficient; use top-k cache or equivalent). Word-list source/license MUST be
documented before bundling (research R1).

## Test contract

- `suggest("hel")` contains `"hello"` or `"help"` (given list content)
- `suggest("h")` → `[]`
- `suggest("zzzz")` → `[]`
- `len(suggest(any)) <= 3`
- **Prediction quality smoke** (deterministic, against the bundled list): for a
  small fixed set of common prefixes (e.g. `th`, `he`, `an`, `in`, `wh`),
  `suggest(prefix)` returns at least one **common/sensible** English completion
  for each (exact expected words asserted in the test fixture once the list is
  chosen). This checks vocabulary usefulness, not only prefix-match mechanics.