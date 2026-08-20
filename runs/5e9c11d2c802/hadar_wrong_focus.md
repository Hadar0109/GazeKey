# hadar USER GATE (suggestions unused)

- session_id: 5e9c11d2c802
- word: hadar
- suggestions_used: no
- condition: head-support — product condition
- role: T020 live gate (change A — gaze-invariant vertical scale)
- typed_output: `hadaf`
- keystroke_focus (intended -> focused):
  1. H -> H   (correct)
  2. A -> A   (correct)
  3. D -> D   (correct)
  4. A -> A   (correct)
  5. R -> F   (wrong — row 0 mapped down into row 1)
- wrong_focus_count: **1/5**
- dwell_notes: All five letters registered a dwell activation, so the one error
  is a wrong-**focus** mapping error rather than a missed dwell. R→F is a
  **row** error with the correct column neighbourhood (R and F are vertically
  adjacent).
- compared_to_baseline_a_b: better than both free-head baselines (A 5/5, B 4/5)
  and better than both T060 product-condition references (3/5 and 2/5).
- compared_to_t060: **1 letter better than the better reference.** T060 measured
  the product-condition spread at 1 letter, so this sits on the envelope and
  **does not decide T020** (SC-006; pre-committed rule).

## Cross-check against the developer evaluation (fidelity)

| Letter | Benchmark result | Live `hadar` | Agrees |
|---|---|---|---|
| H | inside=1, stab=0.64, `dy=-32.1` | → H | yes |
| A | → S (`dx=+62.2 dy=+11.0`) | → A | **no** — eval missed, live hit |
| D | inside=1, stab=0.73 | → D | yes |
| A | → S | → A | **no** — same as first A |
| R | → F (`dx=+54.7 dy=+39.8`) | → F | yes — **exact same wrong key** |

The single live error is the one the benchmark also called as R→F. The two
disagreements are both on A, where the eval was more pessimistic than live
typing. That is the known EMA-reset caveat in the opposite direction from
session `689c8a8ce90c` (there the benchmark flattered itself on R).
