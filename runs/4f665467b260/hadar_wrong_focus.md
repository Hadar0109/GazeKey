# hadar USER GATE (suggestions unused)

- session_id: 4f665467b260
- word: hadar
- suggestions_used: no
- condition: head-support — product condition
- role: product-condition reference **2 of 2** (T060)
- typed_output: `ywdar`
- keystroke_focus (intended -> focused):
  1. H -> Y   (wrong — row 1 mapped up into row 0)
  2. A -> W   (wrong — row 1 mapped up into row 0)
  3. D -> D   (correct)
  4. A -> A   (correct)
  5. R -> R   (correct)
- wrong_focus_count: **2/5**
- dwell_notes: All five letters registered a dwell activation, so both errors are
  wrong-**focus** mapping errors rather than missed dwells. Both errors are again
  **row** errors — H→Y and A→W are each one row up — and neither is a horizontal
  jump. Note that A was focused correctly on its second occurrence but not its
  first, on the same tree within one typing run; the vertical estimate is not
  stable even within a single word.
- compared_to_baseline_a_b: **better than both.** Baseline A `14938da0bdf0` = 5/5
  wrong, baseline B `34fb259ccdfd` = 4/5, reference 1 `689c8a8ce90c` = 3/5, this
  session = **2/5**.

## Cross-check against the developer evaluation (fidelity)

| Letter | Benchmark result | Live `hadar` | Agrees |
|---|---|---|---|
| H | → Y (`dy=-114.0`, row 0) | → Y | yes — exact same wrong key |
| A | → S (`dx=+58.8 dy=+37.4`) | → W | **no** — benchmark predicted a same-row right neighbour, live went a row up |
| D | inside=1, stab=1.00 | → D | yes |
| A | → S | → A | **no** — live was correct where the benchmark missed |
| R | inside=1, stab=1.00, err=2.8 px | → R | yes |

Three of the four distinct letters agree. Both disagreements are on **A**, and
they disagree in *opposite* directions within the same run — the benchmark
missed A both times, while live typing missed the first A and hit the second.
That is the clearest single illustration of vertical instability in these two
sessions, and it means neither measurement is reliably conservative on A.

`H → Y` was the benchmark's prediction in **both** reference sessions, and live
typing landed on Y or its neighbour U both times. H mapping up into row 0 is
reproducible; it is not session noise.

## Caution

2/5 wrong focus is still **not usable typing**, and `hadar` remains a
development word (SC-006). The Plan F hold-out words stay unpractised.
