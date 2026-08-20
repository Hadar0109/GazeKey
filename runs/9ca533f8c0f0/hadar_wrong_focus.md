# hadar USER GATE (suggestions unused)

- session_id: 9ca533f8c0f0
- word: hadar
- suggestions_used: no
- condition: head-support — product condition
- role: T020-A live gate **session 2 of 2**
- typed_output: `gsfs`
- keystroke_focus (intended -> focused):
  1. H -> G   (wrong — same row, left)
  2. A -> S   (wrong — same row, right)
  3. D -> F   (wrong — same row, right)
  4. A -> S   (wrong — same row, right)
  5. R -> (no character registered)
- wrong_focus_count: **4/4 registered, R produced no character** (treat as 5/5
  failed keystrokes: 4 wrong-focus + 1 missed dwell)
- dwell_notes: The four registered letters are all **same-row horizontal**
  errors, not row errors. That is the opposite of T020-A session 1 (`hadaf`,
  only R→F, a row error). `hadar` is not a repeatable effect under Change A.
  R producing no character is consistent with a dwell that never stayed inside
  a typeable key; the benchmark independently called R→F (`dx=+50.1 dy=+54.7`).
- compared_to_baseline_a_b: ties A (5/5 wrong/failed), worse than B (4/5).
- compared_to_t060: worse than both references (3/5 and 2/5).
- compared_to_t020_session_1: much worse (session 1 was 1/5).

## Cross-check against the developer evaluation (fidelity)

| Letter | Benchmark result | Live `hadar` | Agrees |
|---|---|---|---|
| H | inside=1, `dx=-53.0 dy=-7.9` (pulls left toward G) | → G | yes — same-row left |
| A | → S (`dx=+71.8 dy=+24.2`) | → S | yes — exact same wrong key |
| D | inside=1, `dx=+55.2 dy=-2.5` (pulls right toward F) | → F | yes — same-row right |
| A | → S | → S | yes |
| R | → F (`dx=+50.1 dy=+54.7`) | no character | partial — eval predicted a miss, live never activated |

Four of four registered live errors match the benchmark's direction. This is a
fidelity point: evaluation and typing agree that the miss is mapping, not
dwell. It is not an accuracy improvement.
