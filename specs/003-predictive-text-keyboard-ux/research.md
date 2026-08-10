# Research: Predictive Text & Keyboard UX

**Feature**: `003-predictive-text-keyboard-ux`  
**Date**: 2026-08-10

Resolves open items from `spec.md` Technical Context and **Open Research /
Planning Decisions**. Format: Decision / Rationale / Alternatives considered.

---

## R1 — Prediction method

**Decision**: **Bundled English word list + in-memory prefix trie** in a new
`gazekey/prediction/` package. No OS IME APIs, no cloud, no on-device ML for
v1.

**Rationale**:

- Offline, deterministic, lightweight (constitution: practical instrumentation)
- No new heavy dependencies beyond existing stack
- Easy to unit-test (`prefix → candidates`) without UI or OS
- English-only scope matches clarified spec

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| OS/autocorrect APIs | Platform-specific, hard to test, couples to external apps |
| Small language model | Dependency/footprint risk; overkill for prefix completion |
| n-gram from corpus | More complex build pipeline; trie + frequency list sufficient for v1 |
| Symspell / third-party lib | Extra dependency for problem solvable in ~100 lines + word file |

**Asset**: `gazekey/prediction/data/words_en.txt` — frequency-ordered common
English words (target ~20k–50k lines; exact size chosen during implement to
balance coverage vs. load time).

**Source & license requirements** (MUST before bundling):

- Prefer a **public-domain / CC0 / MIT / BSD / Apache-2.0** word list (or
  equivalently redistributable under a clear open license) with documented
  provenance.
- Acceptable examples (choose one at implement time after verifying the exact
  file license): SCOWL/wordlist derivatives with clear redistribution terms;
  Project Gutenberg-derived frequency lists with documented license; a curated
  GazeKey-owned list built from public-domain sources.
- Ship a short `gazekey/prediction/data/README.md` (or header comment) naming
  **source URL/name**, **license**, and **any attribution** required.
- **Do not** bundle a vocabulary whose redistribution or license status is
  unclear (e.g. scraped proprietary dictionaries, unmarked “word lists” with no
  license).

---

## R2 — Ranking within max-3 visible set

**Decision**: Return up to **3** candidates that **start with** the current
prefix (case-insensitive match). Order by **frequency rank in the bundled list**
(earlier line / lower rank index = higher priority). Tie-break alphabetically.

**Trie / top-3 efficiency** (design constraint — exact structure is an
implementation detail):

- Locating the prefix node alone does **not** guarantee fast top-3 ranking: a
  naive DFS/BFS over all descendants can visit large subtrees for short prefixes
  (e.g. `"th"`).
- The implementation MUST retrieve the **best ≤3 by frequency** without an
  unbounded full-subtree sort on every query. Acceptable approaches include
  (pick one during implement):
  - store at each node a small **top-k (k≥3) frequency-ranked completion cache**
    maintained at insert/build time; or
  - keep words sorted by frequency and use a structure that yields
    frequency-ordered matches for a prefix in near-linear-in-result time; or
  - equivalent precomputation so `suggest()` work stays proportional to prefix
    length + a small constant (top-3), not to full dictionary size.
- `<1 ms` suggest latency is a **design target** for the tracking-loop budget,
  not a product acceptance gate unless measurement shows it is necessary.

**Rationale**: Spec fixes max visible at 3; frequency ordering maximizes
usefulness without personalization infrastructure; ranking cost must be
explicitly planned, not assumed free after the prefix walk.

**Alternatives considered**: Edit distance (too noisy for short prefixes);
alphabetical only (poor UX); bigram context (out of scope); naive full-subtree
collect-then-sort (rejected as default — too costly for common short prefixes).

---

## R3 — Minimum prefix length

**Decision**: Show suggestions only when prefix length is **≥ 2** characters.

**Rationale**: Single-character prefixes are noisy and widen gaze target
confusion; predictable empty state before 2 chars; typing unaffected.

**Alternatives considered**: ≥1 (too broad); ≥3 (too slow to help on short words).

---

## R4 — Typing-flow context (source + updates)

**Decision**: New **`TypingContext`** in `gazekey/prediction/typing_context.py`
(subscribes to `ActionDispatcher.on_action_delivered`, **`ok=True` only**).

Tracks:

- `prefix: str` — current in-progress word characters (lowercase canonical)
- `shift_armed: bool` — mirrored from `TypingSession` for casing on next char /
  suffix dispatch

Updates:

| Delivered action | Context change |
|------------------|----------------|
| CHAR (letter) | append to `prefix` |
| CHAR (Space) | clear `prefix` |
| BACKSPACE | pop one char from `prefix` (min length 0) |
| ENTER | clear `prefix` (word boundary) |

Suggestion completion does **not** call a separate `clear_prefix()` after the
batch. Suffix letters and the trailing Space are normal `KeyAction` deliveries;
`TypingContext` evolves only through those delivery events (letters append;
Space clears). On partial delivery failure, stop the batch; context already
matches characters that were actually delivered — no extra rollback or clear.

**Rationale**: Clarification FR-006a requires internal tracking from
**successfully dispatched** actions; delivery hook avoids divergence on inject
failure; a post-batch `clear_prefix()` would duplicate Space-driven clear and
risk double-clear / epoch skew.

**Alternatives considered**: `on_action_requested` (updates before delivery —
rejected); external-app readback (rejected in clarify); state inside
`TypingSession` (rejected — mixes pause/shift with prediction domain);
post-batch `clear_prefix()` (rejected — redundant with Space delivery).

---

## R5 — Suggestion selection & completion dispatch

**Decision**:

1. Suggestion bar buttons are real gaze targets (`objectName="gazeTarget"`,
   stable `key_id` like `suggestion:0` … `suggestion:2`).
2. Dwell/mouse on a populated suggestion publishes a **`SuggestionAccept`**
   intent (not a raw OS shortcut).
3. Completion path computes `suffix = word[len(prefix):]` and dispatches
   **sequential `KeyAction` CHAR** for each suffix character, then **CHAR Space**,
   through existing `ActionDispatcher` — same adapter path as manual typing.
4. **No redundant context clear**: `TypingContext` updates only via normal
   successful deliveries of those CHARs (and Space). On first failure: stop
   batch; context remains consistent with delivered characters only.

**Suggestion casing / Shift** (MUST):

- Suggestion labels and dictionary words are treated as **lowercase full words**.
- If `shift_oneshot_armed` is **false** at accept: dispatch the suffix as
  lowercase (e.g. prefix `hel` + `hello` → `lo` then Space → external `hello `).
- If `shift_oneshot_armed` is **true** at accept: the intended word is a
  **title-cased** completion of the whole word (`Hello`), not “Shift only the
  first suffix character.” Because the already-delivered prefix was lowercase,
  a one-shot Shift applied only to the first suffix letter would produce
  incorrect mixed casing (e.g. `helLo`). Therefore:
  - **Preferred v1 rule**: if Shift is armed and `prefix` is non-empty,
    **clear Shift without applying it** to the suggestion suffix (treat accept
    as lowercase completion), then dispatch lowercase suffix + Space; OR
  - **Equivalent safe rule**: refuse/ignore Shift for suggestion accept when
    prefix is non-empty (same external outcome: lowercase full word).
  - If Shift is armed and `prefix` is **empty** (accepting a full word with no
    typed stem — uncommon with min prefix ≥2, but if ever enabled): apply
    one-shot Shift to the **first letter of the full word**, then lowercase
    remainder + Space, and clear Shift (same semantics as typing Shift then
    letters).
- Add a **regression test** covering Shift-armed + non-empty lowercase prefix
  (must not produce mixed casing like `helLo`).

**Rationale**: FR-005 mandates existing KeyAction path; sequential CHARs reuse
`OsInputAdapter` and delivery semantics without new inject types; Shift must
not corrupt already-typed lowercase prefixes.

**Alternatives considered**: Single clipboard/paste inject (new OS mechanism);
one composite KeyAction (breaks adapter contract); request-time context update
(rejected per R4); apply Shift only to first suffix char (rejected — mixed
casing).

---

## R6 — Stale-suggestion / race rules

**Decision**:

- Recompute suggestion list on every **`TypingContext` change** (sync on UI
  thread after delivery).
- Each suggestion set carries a monotonic **`prefix_epoch`**; dwell completion
  accepts only if `epoch` still matches active prefix.
- While dwell is in progress on a suggestion, prefix change **cancels** pending
  suggestion dwell (same family as key-switch rules).
- UI hides labels on empty slots but **keeps three fixed-geometry slots**
  blank/disabled (no resize/reflow by count; FR-003).

**Rationale**: SC-003 one-cycle refresh; prevents selecting a candidate for an
obsolete prefix.

---

## R7 — Product keyboard layout redistribution

**Decision**: **Letters-only product layout** with simplified chrome — this is
the **acceptance layout** for implementation (FR-008c):

```text
[ Calibrate ] [ minimize | close ]          ← slim control bar (no status text)
[ suggestion_0 | suggestion_1 | suggestion_2 ]  ← fixed geometry, fully visible
[ qwertyuiop row — taller keys ]
[ asdfghjkl row ]
[ Shift | zxcvbnm | Backspace ]
[ Space (wide) | Enter ]
```

**Removed from product UI**: Pause, Preview, lang, symbols toggle, symbols
layout, Ctrl, Alt, gaze-status label, typed-text bar.

**Space reclaimed**: remove text-display row + pruned control bar + bottom-row
Ctrl/Alt → redistribute appropriately to key heights and suggestion bar height;
**no empty spacer/dead rows**. Key enlargement is a gaze-usability layout goal,
**not** a mapping-accuracy requirement.

**Suggestion slots**: Always three fixed positions; unused slots blank/disabled
(not dwellable); no bar reflow by suggestion count.

### R7 follow-up — large bottom-row recalibration target (2026-08-10)

**Decision**: Move the orange Calibrate/Recalibrate control from the top chrome
row to the **bottom keyboard row**, immediately **left of Space**, as a
**noticeably larger** gaze recovery target than a normal letter key.

Updated acceptance sketch:

```text
[ minimize | close ]                     ← slim window chrome only (no Calibrate)
[ suggestion_0 | suggestion_1 | suggestion_2 ]
[ qwertyuiop ]
[ asdfghjkl ]
[ Shift | zxcvbnm | Backspace ]
[ Calibrate (large) | Space (reduced, centered) | Enter (slightly smaller) ]
```

Rules:

- Recalibrate remains `objectName="gazeTarget"` with stable `system:calibrate`
- Larger target improves **recovery tolerance** when mapping feels inaccurate —
  **not** mapper accuracy and MUST NOT justify mapping retune
- Slim the top chrome after Calibrate leaves; reclaim vertical space into letter
  rows when available; keep QWERTY balanced
- Functional geometry only: export / hit-test / dwell stay synchronized (FR-011)

**Geometry rules** (FR-011):

- `inspect_keyboard_layout` / `KeyHitTester` / `hit_test_layout_keys` remain
  single source of truth after export
- Re-run `tests/unit/test_layout_geometry.py` and
  `tests/test_keyboard_geometry_targets.py` after layout change
- Layout/export/semantic alignment updates only as required by the new surface
- **Do not** change calibration strategy, targets, PCA4, or mapping config for
  typing UX

**Rationale**: Matches clarify session removals + FR-008c; maximizes gaze target
size within existing top-half window without mapping compensation.

**Alternatives considered**: Keep symbols layout hidden (still dead code);
shrink-only without redistributing space (wastes clarify intent); dynamic
slot count / reflow (rejected — unstable gaze targets).

---

## R8 — Preview preservation

**Decision**: Remove **product** `preview_btn` and product wiring only. Keep:

- `python -m tools.preview` entry (`tools/preview/__main__.py`)
- `GazeLoopController.process_gaze_preview`
- `_preview_mode` toggling via devtools API / tools launch flags

**Rationale**: Verified in codebase — preview is a developer entry point, not
product mode (002 research R4).

---

## R9 — Pause removal impact

**Decision**: Remove **product** Pause/Resume control and product pause dwell
path. Product typing session stays **`active`** whenever mapper is available
(no user-facing pause). Internal `TypingSessionState.PAUSED` may remain for test
harness compatibility but is unreachable from product UI.

**Rationale**: Clarify session explicitly removed Pause button; simplifies
chrome. Shift-clear-on-pause rule from 002 becomes N/A for product (Shift still
clears on recalib/session reset).

---

## R10 — Delivery failure UX without text_display

**Decision**: Replace `text_display` status with **minimal non-blocking feedback**:

- `mvp_log` verbose line on delivery failure (existing pattern)
- Optional short-lived overlay/toast on keyboard chrome (if trivial); otherwise
  verbose-only for v1

**Rationale**: Typed-text bar removed per spec; must not silently fail — align
with existing delivery observer pattern.

---

## R11 — Module boundaries

**Decision**:

| Module | Responsibility |
|--------|----------------|
| `gazekey/prediction/word_provider.py` | `Protocol`: `suggest(prefix) → list[str]` (≤3) |
| `gazekey/prediction/trie_provider.py` | Default `TrieWordProvider` implementation |
| `gazekey/prediction/typing_context.py` | Prefix tracking from deliveries |
| `gazekey/prediction/suggestion_dispatch.py` | suffix+Space → KeyAction sequence |
| `gazekey/typing/gaze_typing_runtime.py` | Hit-test + dwell for `suggestion:*` ids |
| `gazekey/ui/keyboard_layout.py` | Layout + suggestion bar labels |
| `gazekey/ui/virtual_keyboard.py` | Composition root: construct `TrieWordProvider` once as `WordProvider`; wire context → provider → bar; epoch guard |

**Rules**:

- UI / typing MUST depend on **`WordProvider` only** (not `TrieWordProvider` /
  trie internals) — FR-009; preserves a future personalized provider / user
  frequency store (e.g. SQLite) without implementing it in 003.
- Word-list load or `suggest()` failure → fail open (empty/disabled slots;
  typing continues; no crash) — FR-012.

**Rationale**: FR-009 modularity; UI and OS inject never import trie internals.

---

## R12 — Performance constraints

**Decision**:

- Trie build: once at startup (&lt; 200 ms **design target** on a typical
  developer machine)
- `suggest(prefix)`: design target &lt; 1 ms with top-3 retrieval per R2
  (not a product acceptance gate unless measurement shows it is necessary)
- Suggestion refresh: on delivery only (not per gaze frame)

**Rationale**: Tracking loop stays ~30 FPS; prediction must not run on gaze path.
