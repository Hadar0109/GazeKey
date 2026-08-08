# Contract: Package Boundaries

**Version**: 1.1.0  
**Feature**: `002-gaze-typing-os`

## Purpose

Enforce `gazekey/` = runtime product vs `tools/` = developer tooling; cleanup
**before** most typing implementation.

## Allowed in `gazekey/`

- tracking, features, calibration, mapping, runtime, layout (mapping/calib
  **behavior unchanged**)
- product UI shell with **existing** fullscreen calib + top-half keyboard geometry
- typing (hit-test, smoother, semantics, dwell, KeyAction, dispatcher, typing session state)
- input (OS adapter; pynput only here)
- minimal **in-process** runtime state needed to run (mapper handle, typing session,
  ids if required) — **not** developer artifact writers

## Must live in `tools/` (separate entry points)

- benchmark runner/session/diagnostics/failure/coverage + **artifact/summary writers**
- debug mapper store, layout CSV, geometry overlays/diagnostics
- read-only preview orchestration
- dedicated preview and benchmark **entry points** (not product modes)

## Import rules

1. Default product path: `gazekey.*` MUST NOT import `tools.*`.
2. Tools MAY import `gazekey.*` for primitives.
3. `gazekey.typing` / UI MUST NOT import `pynput`.

## Early cleanup (before most new typing code)

1. Move evaluation/debug/preview out of `gazekey/`
2. Delete/disconnect `gazekey/future/`, `intent/`, `selection/`, dormant dwell
3. **Post-cleanup behavior gate** (must pass before typing skeleton):
   - product launches
   - fullscreen calibration completes
   - existing PCA4 mapped gaze still fits/produces
   - top-half keyboard geometry preserved
   - relocated developer benchmark runs independently via tools entry
4. **`GAZEKEY_*` inventory before any flag delete/move** — for each flag document
   read sites, tests/docs dependents, and KEEP / MOVE TO TOOLS / DELETE (see
   research R4 starting table; verify completeness with repo search). Do **not**
   use a generic “remove unused flags” task without this inventory.
5. Re-home run-summary / session artifact writers to tools where developer-facing

## Repo-wide cleanup

Separate tasks: obsolete archive leftovers, unjustified scripts, stale
tests/docs, unused flags, dead shims.
