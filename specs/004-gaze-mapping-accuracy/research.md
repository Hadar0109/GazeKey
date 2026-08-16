# Research: Gaze Mapping Accuracy

**Feature**: `004-gaze-mapping-accuracy`  
**Date**: 2026-08-16  
**Spec**: [spec.md](./spec.md)

Resolves planning decisions from the Feature 004 spec. Format: Decision /
Rationale / Alternatives considered. These are **process and measurement**
decisions. Exact calibration-point counts, smoother values, ridge alpha,
correction layers, and mapper replacements remain **experiment outcomes**
after a fresh baseline — not frozen here as the accuracy solution.

Current-code audit (Feature 003 as-built) is treated as a **hypothesis list**,
not a patch backlog.

---

## R1 — Experiment order (baseline before any accuracy code change)

**Decision**: Feature 004 implementation follows a gated sequence. **No
accuracy-related product/mapping code change** until a fresh current-state
baseline is recorded with the evaluation method defined in R2.

Order:

1. **Evaluation fidelity** (developer tools only) so measurement matches
   runtime mapper / geometry / key-hit as closely as possible
2. **Two-session fresh baseline** on unchanged Feature 003 mapping path
   (SC-011) — A and B mandatory; 3-session SC-004 is later, on the kept stack
3. **Collection quality** (fixation vs mapping representation, coherent
   aggregation, left/right semantics, **warning-only quality/pass-fail
   gates**, **spatial row/column metadata** including Space / non-letter
   controls)
4. **Calibration ↔ runtime synchronization** (smoothing, missing-eye policy)
5. **Geometry consistency** after Feature 003 layout, including **clip/clamp**
   when predictions fall outside the prediction domain
6. **Calibration coverage / domain** (spatial layout vs required prediction
   domain) — **one layout candidate per experiment**; further candidates
   allowed after revert/inconclusive; a failed first candidate does **not**
   prove `keyboard15` is optimal
7. **Mapper parameters / extra layers** — only if mapped-key accuracy is still
   insufficient after 3–6; if reached, **auto-alpha selection** is part of
   mapper diagnosis (not an automatic retune)

Each step after the baseline is **one logical area**. Outcome: **keep /
revert / inconclusive**. Unproven changes are not stacked (FR-025, FR-026).
Each **keep** is a Git checkpoint of that proven state.

**Rationale**: The spec forbids combining accuracy changes. The audit found
collection, sync, geometry, and coverage issues that can mimic “bad ridge.”
Tuning alpha first would confound the baseline.

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| Start by retuning PCA4 alpha / smoother | Violates FR-017; confounds data-quality bugs |
| Apply all audit findings in one commit | Violates one-change rule; cannot attribute gain/loss |
| Skip baseline (“we already know it’s wrong”) | No comparison reference (FR-028, SC-011) |

---

## R2 — Developer evaluation: trustworthy, still product-isolated

**Decision**: Keep evaluation in `tools/evaluation/` (and related tests).
`python main.py` product typing MUST NOT import evaluation results for
calibration, fit, clamp, hit-test, dwell, or session enablement (FR-020–022).

Evaluation MUST:

- Call the **same** fitted mapper instance as runtime
- Use the **same** layout snapshot (`inspect_keyboard_layout` /
  `hit_test_layout_keys`) as product typing
- Score **mapped-key (focus)** as primary: intended key from hit-test of
  mapped screen coordinates **before dwell**
- Report dwell activation only as an optional secondary column
- Include **held-out letter keys** (not only calibration-target positions)
- Include **editing/control keys** in the prediction domain (Shift,
  Backspace, Space, Enter, Calibrate; Space may already be a calib target)
- Do **not** score Feature 003 suggestion / prediction-bar keys as 004
  mapped-key accept (preservation / SC-010 only)
- Report error **inside intended key bounds** in addition to pixels-to-center
- Use held-out inside-key + focus stability as the operational reading of
  feature repeatability/distinguishability (FR-007) — no new metrics stack
- Document remaining differences from live typing (FR-029)

**Known as-built gap to close in the evaluation tool (before baseline):**
the current 15-key runner averages predicted `(x,y)` over the collect window,
then hit-tests once, and its sample list **equals** `keyboard15` anchors.
That measures repeatability of a mean point, not live per-frame focus, and
not generalization. Baseline work MUST fix measurement fidelity **or**
explicitly label the old score as supplementary so it cannot be mistaken for
product accuracy.

**Primary mapped-key score (004):**

- During collect, run the same predict path as product typing
  (`FeatureExtractor` → existing runtime predict helper →
  `hit_test_layout_keys`)
- **Inside-key rate**: fraction of evaluated locations whose **representative
  mapped point** lies in the intended key’s tight rect (no snap required for
  “correct”)
- **Focus stability**: fraction of collect frames whose hit-test is the
  intended key (captures flicker the mean point hides)
- **Key-relative error**: `|dx| / key_width`, `|dy| / key_height`, plus
  inside-rect boolean
- Snap-selected neighbor MAY be logged; it is **not** counted as a mapped-key
  success

**Representative point**: median of collect-window mapped `(x,y)` (robust to
outliers) **and** the per-frame focus-stability rate. Do not use mean-point
hit-test as the only published score.

**Rationale**: Spec FR-029 / FR-033 / FR-034. A developer tool that scores a
different path than typing will keep shipping false passes.

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| Keep 15-key mean-point score as the only gate | Overlaps calibration anchors; hides flicker |
| Put evaluation inside product calibration | Violates FR-021 |
| Score only dwell activations | Wrong focus is already a mapping failure (FR-034) |

---

## R3 — Evaluation set: repeatability vs generalization

**Decision**: Every mapping evaluation reports **three scoring slices**
(SC-005, FR-023):

| Slice | Purpose | Default locations (planning default, not a frozen product layout) |
|-------|---------|-------------------------------------------------------------------|
| **Repeatability** | Can the system reproduce calibration-domain positions? | Current calibration target screen positions (whatever layout is active) |
| **Held-out letters** | Can it identify letter keys whose centers were **not** those targets? | Letter keys **not** coinciding with active calibration positions |
| **Editing / control** | Can it identify prediction-domain non-letter keys? | Shift, Backspace, Space, Enter, Calibrate. If a key’s center **is** a calibration coordinate (e.g. Space on current 15), report it in repeatability and still list it here as covered, not double-counted in the primary rate |

**Held-out letter planning default** (Feature 003 QWERTY):  
`W, R, Y, I, O, S, F, H, K, X, V, N`  
when the active calibration layout is the current key-centered 15
(`Q, E, T, U, P, A, D, G, J, L, Z, C, B, M, Space`). If calibration layout
changes, slices are **recomputed**: any evaluated key whose center was a
calibration coordinate moves to the repeatability slice.

**Suggestion / prediction-bar keys** (Feature 003 prediction line): product
gaze targets, **out of 004 mapped-key acceptance**. Role: SC-010
preservation only. Do not include them in SC-001 percentages or KEEP
decisions.

**Word-relevant subset** for development diagnosis: `H, A, D, R` (`hadar`).
Compare **wrong-focus letters** to the same word on baseline A and B
(SC-006). Final accept adds 2–3 short words **not used during development**.

**Rationale**: The as-built `DEFAULT_SAMPLE_KEYS` list is identical to
`keyboard15` anchors, so it cannot satisfy SC-005. Letters-only held-out
would leave editing/control keys unmeasured while they sit in the
prediction domain. Suggestion-bar scoring would mix prediction-UX into
mapping accept.

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| Keep only the historical 15 keys | Measures calibration recall, not typing generalization |
| Evaluate every key including suggestion slots | Suggestion bar is not the 004 accept surface |
| Freeze held-out list even after layout change | Would accidentally re-test new anchors |
| Letters-only held-out | Leaves Shift/Backspace/Enter/Calibrate (and Space if not an anchor) unmeasured |

---

## R4 — Required prediction domain vs calibration domain

**Decision**:

- **Required prediction domain (004)**: the Feature 003 **letter/editing
  keyboard** — visible letter keys plus Shift, Backspace, Space, Enter, and
  Calibrate. This is where gaze-to-key typing must be accurate (`hadar`
  lives here). **Suggestion / prediction-bar** slots remain product gaze
  targets but are **not** the 004 mapping-acceptance surface (SC-010 only).
- **Calibration domain**: the screen region where fixation targets are
  placed. It is **not** assumed identical to the prediction domain (FR-032).
- **Starting reference (baseline only)**: current product `keyboard15`
  key-center layout inside the keyboard widget. It is a **control**, not
  declared optimal (FR-031).
- **Clip / mapper bounds**: must cover the required prediction domain
  (keyboard widget AABB for letter/editing keys). Do not clip to fullscreen
  unless a later coverage experiment explicitly expands the prediction
  domain.

**Layout investigation (after collection + geometry):** candidates to compare
against the baseline layout, without picking a winner in this plan:

| Candidate | Idea |
|-----------|------|
| A. Spatial grid inside the keyboard AABB | Cover the prediction domain as coordinates, not character identities |
| B. Slightly expanded beyond keyboard edges | Keyboard becomes an interpolated interior |
| C. Keep key-centered 15 as control | Isolates whether coverage was the issue |

Test **one candidate per experiment**. Further candidates MAY be run after
`revert` or `inconclusive`. A failed or inconclusive first candidate MUST
NOT be treated as proof that `keyboard15` is optimal (FR-031). Do not change
layout and mapper parameters in the same iteration.

**Rationale**: Typing needs accuracy on the keyboard surface. Teaching the
mapper on key *characters* couples layout to QWERTY identities and made the
benchmark circular. Spatial coverage is a later lever.

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| Lock keyboard15 as optimal | Spec forbids assuming it |
| Immediate fullscreen 9-point | Prediction domain is the keyboard; fullscreen may worsen keyboard interpolation without evidence |
| Calibrate suggestion bar too | Out of 004 acceptance surface; adds targets without helping `hadar` |

---

## R5 — Calibration targets are spatial; fitting ignores key identity

**Decision**: `CalibrationTarget` teaching data is `(gaze_representation →
screen_x, screen_y)`. `key_id` / label / row semantics MAY exist for UI,
logging, or optional quality grouping, but **must not enter ridge fit**
unless a later experiment explicitly justifies it (FR-030).

Quality/outlier grouping, if kept, MUST use spatial `grid_row` / `grid_col`
or screen position — not substring matching on labels such as `key_q`.

**Investigate (do not assume a fix):** whether those spatial indices are
themselves correct for the current target set. As-built, Space may share a
row index with the bottom *letter* row despite sitting on a lower action
row, and a five-column key-center layout may be coarsened to three named
columns for region/quality checks. Non-letter controls (Space, and any
Shift / Calibrate / Enter used as targets) can therefore enter the wrong
row/column peer group, distorting monotonicity, region, and outlier
signals. Confirm with evidence (compare quality conclusions vs actual
`screen_y` / `screen_x` clusters) before retagging metadata or changing
gates.

**Rationale**: As-built outlier peers match `"top"`/`"left"` in labels and
are inert for `key_*` names. Fit already uses coordinates; keep it that way.
Wrong *spatial* tags would still make quality checks lie even after labels
are ignored.

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| Fit per key-id embeddings | Couples mapper to QWERTY; spec says spatial |
| Keep label-based peer checks | Dead on current labels; misleading quality |

---

## R6 — Gaze representation and collection (hypotheses, ordered)

**Decision**: Start from as-built PCA4 features
(`pca_uL, pca_uR, pca_vL, pca_vR`). Do not replace the feature set until
collection, sync, geometry, and coverage are investigated (FR-015–017).

**Baseline configuration (document, do not retune yet):**

- Mapper: `pca4_baseline` ridge; X ← `(uL, uR)`, Y ← `(vL, vR)`
- Row-Y bias: off
- Feature EMA α = 0.28 at **runtime only** today
- Screen-space gaze smoother: **not** on the product typing path
- Clip: keyboard-widget rect from calibration start; out-of-domain
  predictions are clamped to that rect (investigate in R7 — do not remove
  clamp here)

**First collection/sync experiments** (each alone, after baseline), in
suggested order if baseline failure patterns do not contradict:

1. Fixation stability on the **same 4-D representation** the mapper uses
   (not only averaged 2-D `avg_h/avg_v` / mean `u,v`)
2. **Per-frame coherent aggregation** (IQR or keep/reject whole frames), not
   independent per-channel means that invent a vector no frame produced
3. **Left/right `u` axis semantics** (right-eye corner order vs left)
4. Missing-eye policy identical in gate, aggregation, and predict
5. Runtime vs calibration preparation: either apply the same smoother to
   collected frames, stop smoothing at predict, or keep a **documented**
   difference after a measured comparison
6. **Warning-only calibration quality / pass-fail gates** (R10): whether
   mappings that would fail historical pixel/LOOCV/region thresholds still
   become product-usable, and whether that correlates with bad held-out or
   `hadar` results — do not harden or drop gates without that evidence
7. **Spatial row/column metadata** used by those quality checks (R5),
   especially Space and other non-letter controls

If 1–7 plus geometry (R7, including clip/clamp) plus coverage experiments
(R4, one candidate at a time) still fail held-out mapped-key and `hadar`
vs baseline, **then** consider ridge alpha (including the **auto-alpha
selection rule**, R11), coupling, or the mapper itself (FR-035) — still one
change per iteration.

**Rationale**: Audit ranked 4-D gate, Frankenstein means, and u-axis mismatch
above alpha. Constitution III: simple pipeline before new layers.

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| New mapper family first | Spec FR-016 |
| Enable row-Y bias immediately | Extra layer; `APPLY_ROW_Y_BIAS` already false; no baseline yet |
| Copy all audit fixes in one PR | Cannot keep/revert per hypothesis |

---

## R7 — Geometry after Feature 003

**Decision**: Before any mapping-parameter change, verify (automated tests +
one USER GATE) that:

- Calibration overlay dots, taught `(screen_x, screen_y)`, visible key
  centers, runtime predict output, and `hit_test_layout_keys` rects share
  one global coordinate system
- Feature 003 bottom-row Calibrate / reduced Space / suggestion bar did not
  leave stale clip rects or hitboxes
- Mapper clip covers the **prediction domain** (keyboard widget), not the
  fullscreen overlay and not a pre-003 layout
- After overlay close, layout export matches taught coordinates (no stale
  snapshot)
- **Resize / reposition / scaling (FR-013/014):** as-built product keyboard
  is a frameless overlay on `availableGeometry`, not a user-resizable mapped
  window. **Close the requirement** during geometry work: if no supported
  user-facing resize/move/scale path exists, record it as **unsupported**
  and do not treat it as an open mapping defect. Overlay `resizeEvent` and
  overlay-close → restored keyboard still MUST be tested. If a supported
  path is found (e.g. restore-from-minimize that changes geometry), then
  refresh-or-disable-stale-mapping MUST be tested.

**Investigate clip/clamp (do not assume remove or expand):** when a
prediction falls **outside** the clip rect, as-built predict **clamps**
`(x,y)` onto the AABB. That can pin overshoot onto **edge keys** (outer
letters, Space, Calibrate) and make mapped-key look like a layout/hit-test
error. Evaluation SHOULD report **unclamped vs clamped** hit-test as a
diagnostic (developer tool; not a product-path change). Confirm with
evidence whether:

- clamp hides extrapolation that would miss the intended key
- clip bounds themselves are wrong (too small, too large, stale vs 003)
- unclamped points would still miss, so clamp is not the cause

Do **not** remove clamp, expand clip to fullscreen, or retune ridge because
edge keys light up — until that comparison exists.

Geometry mismatches are **sync bugs**, not reasons to retune ridge.

**Rationale**: FR-012–014. 003 explicitly did not retune mapping; 004 must
prove coordinates still match.

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| Assume 003 tests already prove mapping geometry | Those tests check UI layout, not calib-dot vs predict vs hit-test on a live session |
| Compensate 003 key sizes inside the mapper | Constitution I / FR-018 |

---

## R8 — Acceptance relative to baseline (67% is not the finish line)

**Decision**: Historical floors (67% mapped-key, 55 px median, 80% row,
3-session spread) are **reference comparisons** against the fresh baseline
(SC-001–004). They are **not** Feature 004 final practical-typing success.

After the two-session baseline + experiments, final acceptance is an
**evidence addendum** (recorded in run notes) using:

1. Held-out **inside-key** and editing/control mapped-key rates vs **both**
   baseline sessions (must improve or a confirmed defect removed without
   harm; report A and B so session noise is visible)
2. Focus stability on held-out keys (flicker) — this plus inside-key is
   FR-007’s operational measure
3. Key-relative error (inside intended rect, not only px)
4. **3-session final repeatability** on the **kept** stack (SC-004): three
   fresh calib+eval sessions; ≥53% mapped-key reference floor each; ≤20 pp
   best–worst spread. Distinct from baseline A/B.
5. USER GATE: `hadar` **wrong-focus letters vs baseline A/B** (suggestions
   unused); then **2–3 additional short words not used during development**,
   different rows/regions
6. Feature 003 product path still works (SC-010), including suggestion /
   prediction-bar **preservation** (not mapping accept)

Do not declare success from repeatability of calibration locations alone.

**Rationale**: Spec session 2026-08-16. Practical typing of `hadar` can fail
while a 10/15 anchor benchmark passes.

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| Treat 10/15 as Feature 004 done | Spec SC-005/SC-006 |
| Invent a new numeric bar before baseline | No evidence; spec defers final bar |

---

## R9 — Product preservation

**Decision**: Do not change dwell duration, suggestion ranking, OS adapter,
or keyboard visual styling except to fix a **confirmed** geometry/hit-test
sync bug that selects the wrong key from a correct mapped point.

Mapping word checks: leave suggestion slots blank/disabled or instruct the
tester not to use them (SC-006).

**Rationale**: FR-018, FR-027.

---

## R10 — Calibration quality / pass-fail gates (warnings vs blocking)

**Decision**: Treat as-built keyboard-mode quality as an **investigation**,
not a predetermined harden-or-drop. Constitution already forbids using
LOOCV as the sole product accept/reject. As-built, several historical
numeric gates (LOOCV px, train-pixel error, region/row checks) are
**warnings** in keyboard mode; product typing can still start. Blocking
reasons are a smaller set (e.g. predict-None, catastrophic Y correlation,
eye-box drift).

**Investigate after baseline, as one collection/quality experiment:**

- Record, per baseline session: blocking fail vs warning-only vs clean
- Compare those labels to **held-out inside-key** and `hadar` focus
- Ask: do warning-only sessions that would have failed historical
  thresholds actually produce unusable mapping? Do sessions that *pass*
  still fail practical typing because gates measure the wrong thing
  (wrong spatial metadata — R5 — or train-set repeatability only)?

Outcomes: keep warnings as-is, make a **justified** subset blocking, or
change what the gates measure — **only** after that correlation exists.
Do not harden LOOCV into a sole product gate. Do not ignore warnings if
evidence shows they predict mapping failure. Any gate-policy change MUST
keep fixation UI as target + optional progress and pass/fail **only after**
the session (FR-004, FR-005, SC-009).

**Rationale**: Soft gates can ship unusable maps; hard LOOCV can reject
usable maps or encourage fitting to the train set. Evidence first.

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| Immediately make all current warnings blocking | Predetermined fix; may reject usable maps; LOOCV is not sole accept |
| Ignore quality.py because “LOOCV isn’t the metric” | Warnings may still be the only signal that a session is bad |
| Fix region/row metadata and gates in one change | Two levers; metadata (R5) and pass/fail policy (R10) are separate experiments |

---

## R11 — Auto-alpha selection (Phase E mapper diagnosis only)

**Decision**: Do **not** retune ridge alpha, the alpha grid, or the
selection rule during evaluation fidelity, collection, sync, geometry, or
coverage (R1). Document the as-built rule as a **Phase E hypothesis**.

**As-built rule to diagnose if Phase E is reached:** among alphas whose
LOOCV score is within a small pixel tolerance of the best score on the
grid, the fitter picks the **largest** alpha (strongest regularization).

Investigate then (one lever, evidence-driven):

- Which alpha was selected vs the full grid / LOOCV curve on kept sessions
- Whether max-alpha-within-tolerance **underfits** held-out interpolation
  (including keys like H/R that are not calibration anchors)
- Whether a different selection among the same grid (min alpha, best
  LOOCV only, or a held-out-informed rule) improves mapped-key — **or**
  whether alpha is not implicated

Do not change the selection rule because the audit listed it. Do not
combine an alpha-rule change with coupling or a new layer.

**Rationale**: Picking the largest near-best alpha can flatten the map.
Collection/geometry bugs produce the same symptom. Phase E exists so
this is diagnosed only after those areas.

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| Retune alpha in Phase A/B to “get a better baseline” | Violates FR-017 / R1; confounds data-quality bugs |
| Assume max-alpha is always wrong and switch to min-alpha | Predetermined patch; LOOCV-near-best may be correct |

---

## Open items deferred to experiments (not blocked)

- Exact calibration point count
- Winner among layout candidates A/B/C (more than one may be tried, one
  per experiment; first failure ≠ `keyboard15` optimal)
- Exact 2–3 final hold-out words (chosen at Plan F; must not have been
  used as development word checks)
- Whether to keep, remove, or match feature EMA
- Whether warning-only quality gates should stay, harden, or change
  what they measure (R10)
- Whether clip/clamp should stay, change bounds, or be reported
  unclamped in diagnostics only (R7)
- Whether spatial row/col tags for Space / non-letter controls are
  wrong enough to change quality grouping (R5)
- Ridge alpha / **auto-alpha selection rule** / coupling / mapper
  replacement (R11, Phase E only)
- Final numeric acceptance replacing the 67% reference floor

These wait for baseline evidence and one-change results.
