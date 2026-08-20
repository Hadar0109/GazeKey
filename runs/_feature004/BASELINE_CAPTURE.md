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
