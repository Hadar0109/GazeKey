# CurrentStateBaseline A + B (T014) — Feature 004 Phase A

**Captured**: 2026-08-16 (A 19:44:50, B 19:49:34 local)
**Code state**: unchanged Feature 003 mapping/collection + Feature 004 evaluation fidelity.
Both sessions ran ~5 minutes apart on the same tree; no mapping code change between them.
**Entry point**: `python -m tools.evaluation` (product calib + mapper, developer scoring enabled).

Later experiments MUST cite **both** run ids as `eval_before`.

## Sessions

| | Baseline A | Baseline B |
|---|---|---|
| Session id | `14938da0bdf0` | `34fb259ccdfd` |
| Benchmark id | `14938da0bdf0-bench1786898690` | `34fb259ccdfd-bench1786898974` |
| Calibration | PASSED | PASSED |
| `quality_gate_kind` | `warning_only` (14 warnings) | `warning_only` (16 warnings) |
| Calibration LOOCV RMS | 89.4 px | 95.2 px |
| Ridge alpha | 1 | 1 |

## Mapped-key results (inside intended tight rect; snap is not success)

| Metric | A | B | Spread |
|---|---|---|---|
| Overall inside-key | 0/31 (0%) | 3/31 (10%) | 10 pp |
| **Held-out letters** (primary) | 0.000 (0/12) | 0.083 (1/12) | 8.3 pp |
| Repeatability (calib anchors) | 0.000 (0/15) | 0.133 (2/15) | 13.3 pp |
| Editing / control | 0.000 | 0.000 | 0 pp |
| Mean focus stability (held-out) | 0.000 | 0.116 | — |
| Median error | 130 px | 107 px | 23 px |
| Median \|dx\|/key width | 0.934 | 0.506 | — |
| Median \|dy\|/key height | 0.731 | 0.987 | — |
| Row accuracy | 14/31 (45%) | 11/31 (35%) | 10 pp |
| `clamp_hit_rate` | 0.059 | 0.036 | — |
| Unclamped inside-key (diagnostic) | 0.000 | 0.097 | — |

The only locations ever inside their key: **T, L** (repeatability, B) and **Y** (held-out, B).

Both sessions are far below the historical reference floors (67% / 55 px / 80% row). Those floors
are reference only; the operative comparison for every later experiment is **against A and B**.

## Observed failure pattern (recorded as evidence — not a patch list)

1. **Every location in both sessions has positive `dx`** (31/31 in A, 31/31 in B): the mapped point
   always lands to the right of the intended key centre.
2. **Horizontal error is larger on the left of the keyboard than on the right.**
   A: Shift +225, A +221, W +212, Q +186 vs L +58, P +63, Backspace +33, Enter +29.
   B: W +140, A +125, S +122, Shift +117 vs Space +8, B +22, U +25, J +29.
   Right-side keys are still positive, so this reads as **horizontal range compression plus a
   rightward offset**, not a pure constant shift.
3. **Vertical error runs from positive at the top rows to strongly negative at the bottom.**
   A: Q +121 → M −118, Space −111, Enter −133, Calibrate −272.
   B: Q +46 → M −147, N −169, Space −244, Enter −171.
   Predicted Y spans a narrower range than the taught Y, collapsing toward the upper rows.
4. **Calibrate is the worst location in both runs** (A err 601 px, dx +536, dy −272; B err 451 px).
   It is the large bottom-row key furthest from the calibration anchors.
5. **Clamping is not what makes this fail.** `clamp_hit_rate` is low (0.059 / 0.036) and the
   unclamped inside-key rate equals the clamped rate (A 0.000 vs 0.000; B 0.097 vs 0.097).
6. **Session-to-session noise is large relative to the signal**: repeatability moved 0% → 13.3%
   with no code change, so a single-session movement of this size is not by itself evidence.
7. **Both usable sessions were `warning_only`** and still practically untypeable. Two further
   calibration attempts the same evening were **blocked**:
   `05e40e22688f` (avg_v vs screen-Y correlation r = −0.119, catastrophic threshold 0.15) and
   `0110e1359bd7` (head drift: eye_box_h span 0.0041 > 0.0040).

## What this does and does not authorise

These are **hypotheses for the ordered investigation**, not approved changes. The contract order
stays `collection → sync → geometry → coverage → mapper`, one logical area per iteration, each
ending in keep / revert / inconclusive.

- Items 1–3 (compression + offset in both axes) are open to collection (Phase 3: `u` semantics,
  aggregation, fixation gate), sync (Phase 4: train vs live EMA), and geometry (Phase 5) — the
  baseline does **not** say which.
- Item 4 feeds coverage (Phase 6, T036/T037) and geometry (T032), one candidate per experiment.
- Item 5 is input to **T033** (clamp analysis). It points away from the clamp hypothesis; T033 is
  still the task that writes the finding.
- Item 7 is input to **T026** (warning-only gate correlation). No pass/fail policy change here.
- Do **not** jump to ridge alpha. Phase E (T040) is only reachable after 3–6 are investigated.

## USER GATE (T015) — `hadar`, suggestions unused

Typed live during each baseline session and read back from video. Full records in
`runs/14938da0bdf0/hadar_wrong_focus.md` and `runs/34fb259ccdfd/hadar_wrong_focus.md`.

| Keystroke | A focused | B focused |
|---|---|---|
| H | J | **H** (correct) |
| A | D | S |
| D | F | F |
| A | D | S |
| R | G | F |
| **Wrong focus** | **5/5** | **4/5** |

This is the SC-006 reference point: 9 of 10 keystrokes focused the wrong key, and the word was
never typeable without suggestions.

Three things this adds beyond the automated benchmark:

1. **Live typing confirms the rightward shift.** Every wrong focus is a key to the **right** of the
   intended one (H→J, A→D, A→S, D→F) — the same direction as the 31/31 positive `dx` in both
   automated runs.
2. **The error is stable, not jittery.** The repeated `A` focused the *same* wrong key both times in
   both sessions (D,D in A; S,S in B). Combined with focus stability of 1.00 on some benchmark
   locations, this says the mapper is confidently wrong, so a fix has to move the mapping, not
   reduce noise.
3. **Live and offline agree on the home row but not the top row.** A→D, D→F and H→J in session A,
   and A→S, D→F in session B, reproduce the automated per-key misses exactly. But `R` (top row)
   focused a **home-row** key live (G in A, F in B) where the benchmark had `R`→`T` on the same row,
   and `H` focused correctly in B where the benchmark had `H`→`U`.

Item 3 is a **fidelity observation to carry into Phase 4 (sync)**, not a verdict: live typing runs a
continuous feature EMA across keystrokes while the evaluation resets it per key (already listed in
`fidelity_notes`). That is one candidate explanation for the larger live vertical error on top-row
keys, and it is exactly the kind of live-vs-eval difference T028–T031 exist to test. Do not treat
the offline benchmark as invalid on the strength of two top-row keystrokes.
