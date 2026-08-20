# Phase 2 baseline capture (T014–T015) — USER GATE

Live webcam. Evaluation fidelity is in the tree; mapping/collection code must stay unchanged between A and B.

## Commands

1. `python -m tools.evaluation`  
   Same product calib + mapper as `python main.py`, with developer scoring enabled.
2. Complete calibration (dot + progress; pass/fail after the session).
3. Let auto-benchmark walk **repeatability**, **held-out letters**, and **editing/control**.
4. Artifacts land in `runs/<session_id>/` (`calibration_summary.txt`, `benchmark_summary.txt`, `experiment_record.md`).
5. Type `hadar` in an external field **without suggestions**. Fill `hadar_wrong_focus.md` (wrong **focus** on H/A/D/R, even if dwell never fires).
6. Repeat steps 1–5 as **baseline B** (new calibration, same eval method). No mapping code change.

Label the two `experiment_record.md` files `CurrentStateBaseline A` and `CurrentStateBaseline B`. Later accuracy experiments cite both.

Product launch without eval remains `python main.py`.

## Status

**T014 done.** A = `runs/14938da0bdf0/`, B = `runs/34fb259ccdfd/` (2026-08-16, ~5 min apart, one
code state). Results and the observed failure pattern: `baseline_A_B_comparison.md`.

**T015 done.** `hadar` was typed live in both sessions with suggestions unused and read back from
video: **A 5/5 wrong focus**, **B 4/5**. Records in `runs/<session_id>/hadar_wrong_focus.md`.

Each evaluation session writes a blank `hadar_wrong_focus.md` at benchmark finish; an
already-answered file is never overwritten (pass `overwrite=True` to reset one).

The Phase A gate is now satisfied. Every later accuracy experiment must cite **both** run ids as
`eval_before`, change **one** logical area, and re-run this gate before a `keep`.
