# Contract: Screen geometry

**Feature**: `005-gazefollower-backend`

## Spaces

1. **GazeFollower filtered pixels** — origin top-left of
   `DefaultConfig.screen_size` (screeninfo monitor 0); Y down;
   `convert_to_pixel` after SVR when `screen_physical_size is None`.
2. **Windows desktop / pygame fullscreen** — tested example used
   1920×1080; product must log the actual pygame mode vs screeninfo.
3. **Qt global** — `mapToGlobal` / `QScreen.geometry()`; may be
   logical pixels when `devicePixelRatio` ≠ 1.

## Hard gate (Stage A policy, Stage C live proof)

Stage A (`tasks.md` T011/T012) is schema, helper, and STOP **policy**
infrastructure only (identity / origin / DPR). It MUST NOT be treated
as live keyboard geometry proof.

Before treating Stage C as mapping proof, **record live values**
(T028/T029/T030):

- actual `screeninfo` size
- pygame mode size
- Qt global geometry (`QScreen.geometry()`)
- `devicePixelRatio`
- monitor origin
- keyboard `mapToGlobal(0,0)` origin

Then apply identity, origin offset, and/or DPR scaling only. If those
cannot align official filtered gaze with live key QRects, **STOP and
report**. Do not add a mapper, bias, or affine correction. Do not
change upstream `generate_points` behavior preemptively.

## Allowed conversion

```text
qt_global = origin_offset + gf_filtered_px / dpr_or_1
```

Only origin offset and/or DPR scaling, recorded in the session geometry
audit. Identity if Stage C debug dot already matches live keys.

## Forbidden

Learned affine/Ridge remap, copied `camera_position` cm,
`_gaze_bias_*`, mapper `clip_bounds`, hard-coded key coordinate tables.
