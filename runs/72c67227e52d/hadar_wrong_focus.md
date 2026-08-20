# hadar USER GATE (suggestions unused)

- session_id: 72c67227e52d
- word: hadar
- suggestions_used: no
- condition: head-support — product condition
- role: T020-C live gate session 1 of 2 (correct lid indices)
- typed_output: `uerer`
- keystroke_focus (intended -> focused):
  1. H -> U   (wrong — row 1 mapped up into row 0)
  2. A -> E   (wrong — row 1 mapped up into row 0)
  3. D -> R   (wrong — row 1 mapped up into row 0)
  4. A -> E   (wrong — row 1 mapped up into row 0)
  5. R -> R   (correct)
- wrong_focus_count: **4/5**
- dwell_notes: All five letters registered a dwell activation, so the four
  errors are wrong-**focus** mapping errors rather than missed dwells. The
  four misses are **row** errors into the top row (H/U, A/E, D/R). R, already
  on the top row, was the only hit. This matches the benchmark
  `median_|dy|/h = 1.562` with predictions stuck high.
- compared_to_baseline_a_b: worse than T060 product-condition references
  (3/5 and 2/5). Better than free-head baseline A (5/5) on count only; not
  a keep signal (SC-006; pre-committed rule — `hadar` does not decide).

## Cross-check against the developer evaluation (fidelity)

| Letter | Benchmark result | Live `hadar` | Agrees |
|---|---|---|---|
| H | → Y (`dy=-114.0`, row 0) | → U (row 0) | yes — same upward row error, adjacent column |
| A | → S (`dx=+78.3 dy=-27.6`) | → E | **no** — eval same-row right, live a row up |
| D | → R (`dx=+76.2 dy=-41.0`) | → R | yes — exact same wrong key |
| A | → S | → E | **no** — same as first A |
| R | → R (`inside=0`, `dy=-38.0`) | → R | yes — same key, eval outside tight rect |
