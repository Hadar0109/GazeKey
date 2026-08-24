# T057 — `hadar` USER GATE deferred

**Date**: 2026-08-24  
**Status**: **open / deferred**. Not PASS. Not FAIL.

The operator directed that `hadar` must **not** be recorded or evaluated as
an accuracy metric during current product integration.

Typing accuracy will be evaluated later, after integration, and after a
decision whether to:

- evaluate the 32M-image GazeFollower model, or
- adjust key size / hit areas.

Until then: do not reopen accuracy work, do not resize keys, do not change
the GazeFollower production path. Feature 004 T060 formulas are not a
cleanup trigger. SC-010 remains **not scored**.
