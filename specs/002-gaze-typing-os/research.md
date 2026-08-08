# Research: Gaze Typing & OS Integration

**Feature**: `002-gaze-typing-os`  
**Date**: 2026-08-08 (revised)

Decisions resolve Technical Context and deferred spec items. Format: Decision /
Rationale / Alternatives considered.

---

## R1 — Native OS injection library

**Decision**: Use **`pynput.keyboard.Controller`** only inside `OsInputAdapter`
(`gazekey/input/`).

**Rationale**: Already in `requirements.txt`; sufficient for CHAR / Backspace /
Enter / one-shot Shift letter casing; single fake seam for tests.

**Alternatives considered**: ctypes SendInput (defer); Qt events into other apps
(poor fit); in-app buffer only (rejected by spec).

---

## R2 — KeyAction / dispatcher / delivery semantics

**Decision**: Keep **KeyAction → ActionDispatcher → OsInputAdapter**.

Dispatcher exposes two observer signals (names illustrative):

1. **`on_action_requested(KeyAction)`** — selection completed; action accepted
   for delivery attempt (or dropped if paused — then no request).
2. **`on_action_delivered(KeyAction, OsInjectResult)`** — adapter returned;
   observers see success vs failure distinctly from mere selection.

UI/dwell never call `pynput`. Future features may subscribe to either stream.

**Rationale**: Spec FR-001d + plan refinement; requested ≠ delivered.

**Alternatives considered**: Single fire-and-forget callback (cannot distinguish
delivery); event-bus framework (overkill).

---

## R3 — Dwell defaults (reliability-first)

**Decision**:

| Parameter | Value |
|-----------|--------|
| `dwell_sec` | **0.9** |
| `post_activation_cooldown_sec` | **0.20** global after any **successful dwell-based control activation** that changes typing state — including OS-bound typing keys, **Shift**, **Pause**, and **Resume** — unless implementation evidence shows a specific reason to exempt a control |
| Same-key lockout | Until confirmed leave (typing keys) |
| Confirmed leave | **5 consecutive off-key frames** |

Rebuild in `gazekey/typing/dwell_engine.py` only after cleanup gate + injection
skeleton + focus validation.

**Rationale**: Spec band 0.8–1.0; jitter-resistant leave; cooldown as reliability
guard for all dwell state changes, not only character fires.

**Alternatives considered**: Cooldown only after CHAR fires (rejected — apply
consistently unless evidenced); reuse SelectionPolicy (rejected).

---

## R4 — Preview / benchmark entry points and `GAZEKEY_*` inventory

**Decision**: Preview and benchmark are **not** product modes. Prefer **separate
developer entry points** under `tools/`.

**`GAZEKEY_*` flag rule**: Before deleting or relocating any flag, produce an
**explicit inventory** (no generic “remove unused flags” task). For each flag:

| Column | Content |
|--------|---------|
| Flag | e.g. `GAZEKEY_VERBOSE` |
| Read sites | modules/functions |
| Tests/docs dependents | yes/no + paths |
| Classification | **KEEP** / **MOVE TO TOOLS** / **DELETE** |

Starting inventory (must be verified during implementation before action):

| Flag | Read sites (known) | Likely class |
|------|--------------------|--------------|
| `GAZEKEY_VERBOSE` | `env_flags.py`, `mvp_log.py`, VK | KEEP |
| `GAZEKEY_DEV_BENCHMARK` | `env_flags.py`, `benchmark_controller.py` | MOVE TO TOOLS |
| `GAZEKEY_CAMERA_PREVIEW_DURING_CALIB` | `env_flags.py` | KEEP (verify) |
| `GAZEKEY_CALIB_MODE` | `env_flags.py` | KEEP (verify) |
| `GAZEKEY_SELECTION_DEBUG` | `env_flags.py` | DELETE (selection removed) |
| `GAZEKEY_GAZE_DEBUG` | `env_flags.py` | KEEP or MOVE (verify) |
| `GAZEKEY_GAZE_DEBUG_PRED` | `env_flags.py` | KEEP or MOVE (verify) |
| `GAZEKEY_GAZE_DEBUG_SELECTION` | `env_flags.py` | DELETE |
| `GAZEKEY_CALIB_DEBUG` | `env_flags.py` | KEEP or MOVE (verify) |
| `GAZEKEY_CALIB_GEOM_DEBUG` | `env_flags.py` | MOVE TO TOOLS |
| `GAZEKEY_DIAG_EXTRACTOR` | `features/extractor.py` | KEEP or DELETE (verify) |

Search the repo for any additional `GAZEKEY_*` before closing the inventory.

**Alternatives considered**: Ad-hoc “delete unused flags” without inventory
(rejected).

---

## R5 — Layout preserved; focus is OS/window-only

**Decision**:

- **Do not redesign or reposition** the keyboard. Keep **fullscreen calibration**
  as today, then keyboard in its **current top-half** geometry with the external
  app usable in the **lower half**.
- Treat focus as an **OS/window-behavior** issue only.
- **Early focus validation** runs **after** a minimal KeyAction → dispatcher →
  adapter path exists (cannot precede injection skeleton). After calib →
  top-half keyboard, confirm inject reaches the external app without restoring
  focus between characters.

**Rationale**: Layout constraint; focus proof needs a real inject path.

**Alternatives considered**: Focus check before adapter exists (impossible);
layout change to “fix” focus (rejected).

---

## R6 — Pause / Resume

**Decision**: `TypingSession` `ACTIVE | PAUSED`. Dwellable Pause/Resume (mouse
optional) toggles state; **never** emits OS `KeyAction`.

**Rationale**: Spec FR-001b.

---

## R7 — Active OS key set and Shift one-shot (+ clear rules)

**Decision**:

| Control | OS `KeyAction`? | Behavior |
|---------|-----------------|----------|
| a–z | Yes (`CHAR`) | Lowercase by default |
| Shift then letter | Yes | Shift **one-shot**: arms next letter only, then clears |
| Space / Backspace / Enter | Yes | As named |
| Ctrl / Alt | **No** | Visible OK; ignored for OS |
| Pause/Resume | **No** | System control |

**Clear pending Shift (`shift_oneshot_armed = false`) on**:

- successful consumption by the next letter
- **Pause**
- **recalibration** start/completion paths that reset typing
- **mapping/session reset** (mapper cleared, failed quality, new session)
- **tracking/mapping session termination** / app teardown of the gaze session
- any other transition where leaving Shift armed could cause an unexpected later
  uppercase character

Ctrl/Alt shortcuts and multi-key combinations remain **out of scope** for 002.

**Rationale**: Prevents stale Shift across session boundaries.

**Alternatives considered**: Sticky Shift; clear only on letter consume (rejected —
unsafe across Pause/recalib).

---

## R8 — Package boundaries and `gazekey/session/`

**Decision**:

- Move evaluation/debug/preview to `tools/`.
- **Do not** park developer artifact writers / run-summary CSV/JSON dumps inside
  a new fat `gazekey/session/`.
- Keep in `gazekey/` only **runtime session/calibration state** truly needed to
  run the product (in-memory ids, mapper handle, typing session state). Persist
  developer artifacts via **tools** (or existing writers relocated there).
- Calibration/mapping **behavior and fit path unchanged**.

**Rationale**: FR-011 / FR-013a; avoid smuggling tooling into product under a
“session” name.

**Alternatives considered**: `gazekey/session/` owning all `runs/` I/O (rejected
as tooling-in-product).

---

## R9 — Implementation order

**Decision** (binding sequence):

1. Cleanup / package boundaries (+ flag inventory before any flag delete)
2. **Post-cleanup behavior gate**: product launch, fullscreen calib, PCA4 mapped
   gaze, top-half keyboard preserved, tools benchmark still runs independently
3. Minimal KeyAction + ActionDispatcher + OsInputAdapter skeleton
4. Early Windows focus validation (needs step 3)
5. Full dwell/typing integration
6. Dev entry polish / tests / quickstart

**Rationale**: Focus proof cannot precede inject path; cleanup must not silently
break sealed calibration/mapping.

**Alternatives considered**: Focus before skeleton (rejected); typing before
cleanup gate (rejected).

---

## R10 — In-app text buffer

**Decision**: Not the product destination; KeyAction → OS only (gaze primary,
mouse optional convenience).

**Rationale**: Spec assumptions.

---

## R11 — Constitution relationship

**Decision**: Keep justified violations in plan Complexity Tracking; optional later
`/speckit.constitution` for post-MVP typing/OS stage wording.

**Rationale**: Constitution VIII.
