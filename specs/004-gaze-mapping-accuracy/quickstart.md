# Quickstart: Gaze Mapping Accuracy

**Feature**: `004-gaze-mapping-accuracy`  
**Date**: 2026-08-16

Manual and developer-tool procedure. **Do not change mapping/collection code
until section 3 (two-session baseline) is done.**

## Prerequisites

- Webcam; face visible; single primary monitor
- Product keyboard: Feature 003 letters + editing/control keys
- Sit consistently; move eyes, not head, during calibration
- Suggestions unused during mapping word checks
- Development word check is `hadar` only until Plan F

## 1. Product path (unchanged)

```text
python main.py
```

Calibrate (dot + progress only; pass/fail after the session). After pass,
gaze typing into an external field uses mapped gaze → hit-test → dwell.
Evaluation must not be required.

## 2. Evaluation fidelity (tools only)

Use the developer evaluation entry (existing `python -m tools.evaluation`
or documented flag). Confirm in the run summary:

- Same mapper and `hit_test_layout_keys` as typing
- Slices present: **repeatability**, **held-out letters**, **editing/control**
  (Shift, Backspace, Space, Enter, Calibrate)
- Suggestion / prediction-bar keys **not** in mapped-key accept
- Primary score is **inside intended tight rect** + **focus stability**
- `fidelity_notes` lists any remaining diffs vs live typing (e.g. EMA reset
  per key)

If the tool still only mean-point-scores the historical 15 anchors, **fix
the tool first**. That is not a mapping experiment.

## 3. Two-session current-state baseline (SC-011)

On **unchanged** mapping/collection code:

1. Calibrate
2. Run developer evaluation (all three slices)
3. Save `runs/<session_id>/` as **baseline A**
4. Repeat (new calibration, same eval method) as **baseline B** — mandatory,
   still no mapping code change
5. USER GATE: type `hadar` in an external field **without using suggestions**.
   Record which letters had wrong **focus** (H/A/D/R; focus vs dwell) on
   **both** sessions

Later experiments compare to **both** A and B. Historical 67% / 55 px are
reference only. The **3-session** protocol in section 8 is a later final
check on the kept stack — not a substitute for A and B.

## 4. One experiment

1. Write hypothesis + logical area (`collection` / `sync` / `geometry` /
   `coverage` / `mapper`)
2. Make **one** focused change
3. Recalibrate; rerun the **same** evaluation
4. Record **keep / revert / inconclusive** vs A and B (`hadar` wrong-focus
   vs those sessions)
5. If **keep**: Git commit this proven state; store the SHA on the
   experiment record
6. If revert or inconclusive, restore the last keep commit; do not stack

Suggested first product/mapping experiments after baseline (only if the
baseline pattern agrees): 4-D fixation gate; coherent frame aggregation;
left/right `u` semantics — **one** of these, not all.

Also investigate (still one at a time, evidence-driven — not predetermined
fixes): warning-only calib quality gates vs held-out/`hadar`; spatial
row/col tags for Space and non-letter controls; unclamped vs clamped
hit-test when predictions leave the prediction domain.

Layout coverage: one candidate per experiment. If the first candidate is
revert/inconclusive, another candidate MAY be tried. That does **not**
prove `keyboard15` is optimal.

## 5. Practical word check (every keep candidate)

After a `keep` during development:

- Suggestions off
- Type `hadar` by gaze (H, A, D, A, R)
- Record wrong-focus letters; compare to baseline A and B (SC-006)
- Wrong **focus** is a mapping fail even if dwell never fires
- Do not use word completion to “fix” the string
- Do **not** practice the Plan F hold-out words here

## 6. Geometry spot-check (once per layout change)

After calibration overlay closes, confirm taught target coordinates still
match visible key geometry used for hit-test (especially Space vs Calibrate
after Feature 003). If they diverge, treat as geometry/sync — not ridge
alpha.

If evaluation shows many raw predictions **outside** the keyboard AABB,
compare unclamped vs clamped mapped-key before changing clamp or clip
bounds.

User-driven resize/reposition/scaling: if the product has no supported
path, record **unsupported** and close that FR-014 case. Overlay vs
restored keyboard still must match.

## 7. When to touch the mapper

Only after collection, sync, geometry, and coverage investigation (one or
more layout candidates, one per experiment), if held-out inside-key,
editing/control slice, and `hadar` wrong-focus vs A/B are still
insufficient. Still one lever (e.g. alpha **or** coupling, not both). If
this stage is reached, include diagnosis of the existing **auto-alpha**
rule (largest alpha among near-best LOOCV) — do not retune it earlier, and
do not assume the rule is wrong.

## 8. Final accept (kept stack)

1. Compare eval slices to baseline A and B
2. Run **3** fresh calib+eval sessions (SC-004 reference floors)
3. USER GATE: `hadar` vs baseline wrong-focus, then **2–3 additional short
   words not used during development**, different rows/regions, suggestions
   unused
4. Confirm suggestions still work when used (not a mapping score)
5. `pytest -q`

## USER GATEs

| Gate | What |
|------|------|
| Baseline A+B `hadar` | Suggestions off; record wrong-focus letters |
| Post-keep `hadar` | Same word; compare to A and B |
| Final hold-out words | 2–3 short words unused in development |
| Overlay vs keyboard | Dots land on intended screen positions; restored keyboard hitboxes match |
| Resize | Test if supported; else document unsupported |

Live webcam checks cannot be fully automated; pytest covers scoring, gate
dimensionality, aggregation coherence, spatial fit (no key-id / label / row
as regression inputs), and evaluation isolation from product modules.
