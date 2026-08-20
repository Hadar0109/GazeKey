# hadar USER GATE (suggestions unused)

- session_id: 29c07b6b989f
- word: hadar
- suggestions_used: no
- condition: head-support — product condition
- role: T020-C live gate session 2 of 2 (correct lid indices)
- typed_output: `udfdt`
- keystroke_focus (intended -> focused):
  1. H -> U   (wrong — row 1 mapped up into row 0)
  2. A -> D   (wrong — same row, two keys right)
  3. D -> F   (wrong — same row, two keys right)
  4. A -> D   (wrong — same row, two keys right)
  5. R -> T   (wrong — same row, two keys left)
- wrong_focus_count: **5/5**
- dwell_notes: All five letters registered a dwell activation, so every
  error is a wrong-**focus** mapping error. Unlike session 1, four of five
  live misses are **horizontal** (A/D, D/F, A/D, R/T); only H→U is a row
  error. That does not contradict the slope result: the mapper still is
  not using Y (`d(dy)/d(target_y)=−0.940`), and `median_|dx|/w=0.452` is
  the worst of the T060/C four.
- compared_to_baseline_a_b: ties free-head baseline A at 5/5; worse than
  T060 (3/5, 2/5). Does not decide T020-C.

## Cross-check against the developer evaluation (fidelity)

| Letter | Benchmark result | Live `hadar` | Agrees |
|---|---|---|---|
| H | inside=1, stab=0.91, `dy=-31.6` | → U | **no** — eval held H, live a row up |
| A | → S (`dx=+91.0 dy=+28.5`) | → D | **no** — both wrong, different neighbours |
| D | → F (`dx=+79.6 dy=+6.4`) | → F | yes — exact same wrong key |
| A | → S | → D | **no** — same as first A |
| R | → F (`dx=+81.4 dy=+41.7`) | → T | **no** — eval a row down, live same-row left |
