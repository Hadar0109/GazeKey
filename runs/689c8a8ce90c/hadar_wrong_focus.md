# hadar USER GATE (suggestions unused)

- session_id: 689c8a8ce90c
- word: hadar
- suggestions_used: no
- condition: head-support — product condition
- typed_output: `uaraf`
- keystroke_focus (intended -> focused):
  1. H -> U   (wrong — row 1 mapped up into row 0)
  2. A -> A   (correct)
  3. D -> R   (wrong — row 1 mapped up into row 0)
  4. A -> A   (correct)
  5. R -> F   (wrong — row 0 mapped down into row 1)
- wrong_focus_count: **3/5**
- dwell_notes: All five letters registered a dwell activation, so every error is a
  genuine wrong-**focus** mapping error, not a missed dwell. Every one of the three
  errors is a **row** error with the correct column neighbourhood — H/U, D/R and R/F
  are vertically adjacent, and no error was a horizontal jump. This matches the
  benchmark's `median_|dy|/h=0.862` vs `median_|dx|/w=0.176`: horizontal mapping is
  usable, vertical mapping is not.
- compared_to_baseline_a_b: **better than both.** Baseline A `14938da0bdf0` = 5/5
  wrong focus, baseline B `34fb259ccdfd` = 4/5, this session = **3/5**. Per SC-006
  the bar is fewer wrong-focus letters than the worse of the two baselines (A, 5/5);
  this clears both.

## Cross-check against the developer evaluation (fidelity)

The benchmark and live typing agree on 4 of the 5 keystrokes, which supports
FR-029 (evaluation measures the same path the product types with):

| Letter | Benchmark result | Live `hadar` | Agrees |
|---|---|---|---|
| H | → Y (`dy=-62.9`, row 0) | → U (row 0) | yes — same upward row error, adjacent column |
| A | inside=1, stab=1.00 | → A | yes |
| D | → R (`dx=+45.3 dy=-41.3`) | → R | yes — exact same wrong key |
| A | inside=1, stab=1.00 | → A | yes |
| R | inside=1, stab=0.89 (`dy=+15.8`) | → F (row 1) | **no** — held inside R's rect in the benchmark, drifted a row down live |

The single disagreement is on the key whose benchmark `dy` was already positive
and whose stability was the lowest of the four inside-hits (0.89). It is
consistent with the documented `fidelity_notes` difference: the benchmark resets
the feature EMA per key (`on_key_begin`) while live typing carries it across
keys. Not a new defect; it is the known measurement caveat, and it errs on the
side of the benchmark looking *better* than live typing.

## Caution

3/5 wrong focus is an improvement against the baselines and is **not** usable
typing. `hadar` is also a development word (SC-006); it must not be treated as
final acceptance, and the Plan F hold-out words stay unpractised.
