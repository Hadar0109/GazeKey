# Feature Specification: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`

**Created**: [DATE]

**Status**: Draft

**Input**: User description: "$ARGUMENTS"

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.

  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - [Brief Title] (Priority: P1)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently - e.g., "Can be fully tested by [specific action] and delivers [specific value]"]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]
2. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 2 - [Brief Title] (Priority: P2)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 3 - [Brief Title] (Priority: P3)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right edge cases.
-->

- What happens when [boundary condition]?
- How does system handle [error scenario]?

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST [specific capability, e.g., "allow users to create accounts"]
- **FR-002**: System MUST [specific capability, e.g., "validate email addresses"]
- **FR-003**: Users MUST be able to [key interaction, e.g., "reset their password"]
- **FR-004**: System MUST [data requirement, e.g., "persist user preferences"]
- **FR-005**: System MUST [behavior, e.g., "log all security events"]

*GazeKey calibration/mapping features — constitution-aligned examples:*

- **FR-00X**: GazeKey-owned calibration fixation UI MUST show only target dot and optional simple progress; no metrics or debug text during fixation. An approved upstream backend MAY use its official Preview/Calibration/result UI unmodified; GazeKey MUST NOT recreate a metric-heavy copy (Principle XI)
- **FR-00X**: Each calibration/benchmark run MUST produce a simple pass/fail summary with primary metrics (Principles VII & X)
- **FR-00X**: Normal runs MUST keep terminal output minimal; optional verbose flag for investigation — no logging framework (Principle X)
- **FR-00X**: First MVP MUST clarify the active path; targeted cleanup only where legacy, experimental, or placeholder code causes confusion (Principle IX)

*Example of marking unclear requirements:*

- **FR-006**: System MUST authenticate users via [NEEDS CLARIFICATION: auth method not specified - email/password, SSO, OAuth?]
- **FR-007**: System MUST retain user data for [NEEDS CLARIFICATION: retention period not specified]

### Key Entities *(include if feature involves data)*

- **[Entity 1]**: [What it represents, key attributes without implementation]
- **[Entity 2]**: [What it represents, relationships to other entities]

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria per GazeKey Constitution
  Principle II (Measurable Progress Only). For calibration/mapping features,
  MUST include: key-hit accuracy (primary), pixel error, row accuracy, and
  repeatability across sessions. Internal model metrics (LOOCV, RMS) may
  supplement but MUST NOT be sole acceptance criteria. Non-mapping features
  MUST define their own measurable outcomes and MUST NOT replace independent
  mapping benchmarks.
-->

### Measurable Outcomes

- **SC-001**: [Key-hit accuracy target, e.g., "≥ X% correct keys on 15-key benchmark"]
- **SC-002**: [Pixel error target, e.g., "median gaze-to-target error ≤ X px"]
- **SC-003**: [Row accuracy target, e.g., "≥ X% correct row on benchmark keys"]
- **SC-004**: [Session repeatability, e.g., "accuracy variance ≤ X% across N sessions"]

## MVP Scope *(mandatory for GazeKey)*

<!--
  ACTION REQUIRED: Confirm scope aligns with Constitution Principle V
  (Feature Scope Control). Explicitly list in-scope and out-of-scope items.
  Mapping foundation stays isolated; post-mapping features (dwell/typing/OS)
  are allowed when this feature's spec defines them — they must consume mapped
  gaze only and must not compensate via mapping changes. Advanced capabilities
  (prediction, language, personalization, multi-monitor, a11y polish) still
  need their own specs when undertaken.
-->

**In scope**: [for this feature — e.g. calibration/mapping, or dwell→KeyAction→OS]

**Out of scope**: [explicit exclusions for this feature; do not treat dwell/OS as
constitutionally forbidden if this feature specifies them — still exclude
unspecified advanced capabilities]

## Assumptions

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right assumptions based on reasonable defaults
  chosen when the feature description did not specify certain details.
-->

- [Assumption about target users, e.g., "Single monitor, fixed keyboard layout"]
- [Assumption about scope boundaries, e.g., "Consumes mapped gaze only; does not add post-backend mapping corrections"]
- [Assumption about data/environment, e.g., "Webcam at 640×480; existing MediaPipe pipeline"]
- [Dependency on existing system/service, e.g., "Reuses gazekey/ tracking and calibration modules"]
