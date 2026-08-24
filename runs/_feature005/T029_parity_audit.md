# T029 parity audit: official pygame_example vs GazeKey integration

**Date**: 2026-08-24  
**Status**: USER GATE **FAIL**. Stage D / dwell / OS typing **not** started.  
**Reference**: official `example/pygame_example.py` at GazeFollower
`553920edcb7998c029828677f50f6d8eb4a16249` (v1.0.2), run by the user with a
GazeKey keyboard screenshot as the pygame background. In that run the GREEN
gaze mark looked much more stable, with only a small visible offset from the
looked-at keys.

This file is the audit. Production behavior was **not** changed. Temporary
dual-dot / pre-Qt diagnostic **code** was removed after this comparison;
recorded JSON/markdown under `runs/_feature005/` is kept.

Official source (pinned commit):

https://github.com/GanchengZhu/GazeFollower/blob/553920edcb7998c029828677f50f6d8eb4a16249/example/pygame_example.py

---

## 1. Exact path differences

### 1.1 Construction

| Step | Official `pygame_example.py` | GazeKey (`lifecycle.construct`) |
|------|------------------------------|----------------------------------|
| Config | `GazeFollower()` → internal `DefaultConfig()` | Explicit `DefaultConfig()` then `cali_mode=13`, `screen_physical_size=None` |
| Estimator | Default `MGazeNetGazeEstimator` | Same default |
| Filter | Default `HeuristicFilter()` (`look_ahead=3`) | Same default (not wrapped) |
| Camera | Default `WebCamCamera(0, 640×480, 30 FPS)` | Same default |
| Screen size | `DefaultConfig.screen_size` from `screeninfo` monitor 0 | Same, recorded **1920×1080** |
| Pygame window | **Hard-coded** `set_mode((1920, 1080), FULLSCREEN)` | `set_mode(gf.screen_size, FULLSCREEN)` (also 1920×1080 here) |

Construction is effectively the same on this machine. The official example
does **not** pass a custom config; our explicit 13-point / `physical_size=None`
are the upstream defaults.

### 1.2 Preview / calibrate / sampling lifecycle

| Step | Official | GazeKey |
|------|----------|---------|
| Preview | `gf.preview(win=win)` on the **same** pygame surface | `gf.preview(win=win)` |
| Calibrate | `gf.calibrate(win=win)` on that **same** surface | `gf.calibrate(win=win)` |
| After accept | **Keep pygame running** | **`pygame.quit()`** then `start_sampling()` |
| Sampling | `gf.start_sampling()` while the 1920×1080 pygame window still owns the screen | `gf.start_sampling()` with **no** pygame window, then `QApplication` + Qt keyboard |
| Live gaze UI | Tight pygame loop on that window | Qt keyboard + debug overlay |

This is the largest lifecycle difference. Official never leaves the pygame
fullscreen that calibration used. GazeKey tears pygame down, then Qt starts
(and Windows DPI awareness can change at that boundary).

`start_sampling()` itself is the same official call: camera thread opens,
`process_frame` SAMPLING runs SVR `predict` → `convert_to_pixel` →
`HeuristicFilter.filter_values`. GazeKey does not add another filter.

### 1.3 GazeInfo consumption

Official live loop:

```text
gaze_info = gf.get_gaze_info()          # reads _gaze_info
if gaze_info and gaze_info.status:
    gx = int(filtered_gaze_coordinates[0])
    gy = int(filtered_gaze_coordinates[1])
pygame.draw.circle(win, (0,255,0), (gx,gy), 50, 5)
```

`get_gaze_info()` is a lock-free read of `_gaze_info` written on the camera
thread by the `_write_sample` subscriber that `start_sampling()` registers.

GazeKey:

```text
camera thread
  process_frame → dispatch subscribers
    _write_sample          # official, sets _gaze_info
    _on_camera_sample      # extra GazeKey subscriber
      gaze_info_to_sample  # validity + origin+dpr
      queue.Queue(maxsize=1)  # latest-only, drops older
Qt thread, QTimer 16 ms
  drain queue → DebugGazeOverlay.update_sample
```

GazeKey **does not** call `gf.get_gaze_info()` on the Qt thread (T010). It
adds a second subscriber and a maxsize-1 queue.

Both display **latest** sample only. Neither keeps a multi-frame display
buffer of the filtered stream. Camera production rate is the same 30 FPS
class; the last BLUE/GREEN session measured **~23 Hz** median (`filter_vs_calibrated.json`).
That rate applies to the official camera thread too, not only to Qt.

### 1.4 Validity / hold-last

| | Official pygame loop | GazeKey overlay |
|--|----------------------|-----------------|
| Draw if | `gaze_info` is truthy **and** `status` | `GazeSample.valid` (status, `tracking_state==SUCCESS`, finite filtered xy, both openness `> 10`) |
| If not | **Hold last** `(gx, gy)` and keep drawing the circle | **Hide** the dot (no hold-last) |

Official can keep a large ring parked on the last good point through blinks
and failed frames. GazeKey blinks the small dot off. That is a large
**perceived** stability difference even with identical samples.

### 1.5 Coordinates before render / hit-test

Official: **no transform**. `filtered_gaze_coordinates` are
`convert_to_pixel` output in `config.screen_size` pixels (here 1920×1080).
They are passed straight to `pygame.draw.circle` on a 1920×1080 surface.

GazeKey: **`origin+dpr`** after T028 audit:

- GF / pygame / screeninfo: 1920×1080
- Qt `QScreen.geometry()`: 1280×720, origin (0,0)
- `devicePixelRatio`: **1.5**
- keyboard origin (0,0)
- `qt_global = gf_px / 1.5`

Then `QWidget.mapFromGlobal` into overlay-local logical pixels. Paint does
not divide by DPR again.

Official never needs `/ 1.5` because pygame and `convert_to_pixel` share the
same 1920 space. GazeKey **must** reconcile GF physical pixels with Qt
logical pixels if those two spaces really differ. Whether `/ 1.5` is the
correct reconciliation is still the T029/T030 question; this audit does not
change it.

### 1.6 Rendering: pygame vs Qt, and dot size

Official (physical pygame pixels):

```text
pygame.draw.circle(win, (0, 255, 0), (gx, gy), 50, 5)
```

- Green **ring**, radius **50**, stroke **5** (not filled)
- Diameter **100** physical pixels
- Repaint: busy loop + `display.flip()` (typically vsync ~60 Hz), **full
  scene** redraw each frame (background image + circle)

GazeKey Stage C debug dot (Qt logical pixels):

```text
radius = 10
filled ellipse, white 2 px outline, green fill
```

- Diameter **20** logical px ≈ **30** physical px at DPR 1.5
- Official ring is about **3.3×** the radius and **~11×** the area
- Repaint: `QWidget.update()` on the overlay only; Qt 16 ms timer

A 30–50 px jitter or residual miss sits **inside** the official ring and
still looks “on the key.” The same miss sits **outside** our 10 px disk and
looks “far.”

### 1.7 Prior diagnostics (kept as evidence, not as current UI)

`runs/_feature005/pre_qt_validation.json` (after `pygame.quit()` + sampling,
**before** Qt) recorded median filtered hold error **~226 px** vs 9 grid
targets. That protocol is **not** the official example: it re-opened pygame
after `pygame.quit()`, used small live dots, and auto-advanced. The user's
later official `pygame_example.py` + keyboard screenshot is the reference
for “GF-only can look close.” Treat the 226 px file as a contaminated /
different protocol, not as proof that official sampling is ~200 px off.

`runs/_feature005/filter_vs_calibrated.json`: BLUE and GREEN converge after a
1–2 s hold; best lag **k=3 (~130 ms)**; spatial miss remains. Filter lag is
secondary. Official uses the same HeuristicFilter.

---

## 2. What can affect true gaze accuracy / stability

These can move the **sample** or the **mapped point**, not just how it looks:

1. **`origin+dpr` (`gf / 1.5`)** — systematic scale vs official identity draw.
   If Qt logical already matches GF numbers, this shrinks gaze toward the
   top-left. If GF is 1920 and Qt is 1280, omitting it would expand gaze
   toward the bottom-right. This is the only allowed geometry difference
   that can create a large settled miss.
2. **`pygame.quit()` then Qt** — DPI awareness / which pixel space
   `screeninfo` vs `QScreen` report. Official never crosses this boundary
   during live gaze.
3. **Stricter `valid` gate** — extra frames dropped vs official `status`
   only. Affects flicker and missing samples, not a static offset after a
   hold of good frames.
4. **maxsize-1 queue + 16 ms timer** — can drop intermediate frames (same
   “latest only” as `get_gaze_info()`). Does not create a large static
   offset. Can add up to one UI interval of display delay (~16 ms), tiny
   next to HeuristicFilter ~100 ms.

Unlikely to explain the settled key miss:

- Extra subscriber vs `get_gaze_info()` (same `GazeInfo`, copied on the
  camera thread)
- HeuristicFilter (identical official default)
- Calibration protocol (same 13-point defaults)
- Camera 30 FPS / ~23 Hz measured stream

---

## 3. What mainly affects visual perception (especially dot size)

1. **Dot size / shape** — official 50 px **ring** vs our 10 px **filled**
   disk. This can account for a large part of “looked more stable / only a
   small offset” without any sample change.
2. **Hold-last vs hide** — official keeps the big ring still during invalid
   frames; we hide. Looks jumpy even when the filter is fine.
3. **Full-scene pygame blit** vs small Qt overlay — persistence and vsync.
4. **Busy pygame loop** vs 16 ms Qt timer — both faster than 30 Hz camera;
   not a primary accuracy issue.

Dot size alone cannot hide a **hundreds-of-pixels** miss. It **can** hide a
one-key (~80–120 logical px, ~120–180 GF px) residual that the official ring
still covers.

---

## 4. Step A live result — PARTIAL PASS

Official-sized GREEN ring + hold-last produced a significant visible
improvement in stability and perceived accuracy. Visualization was part of
the gap.

A noticeable **settled spatial miss** vs the official pygame_example +
keyboard-screenshot reference **remains**. T029 stays FAIL.

- GREEN unfilled ring `(0, 255, 0)`, radius `50 / dpr`, stroke `5 / dpr`
- Hold-last on this overlay only
- `GazeSample.valid` rules unchanged (future dwell still cancels on invalid)
- Stream / `origin+dpr` / HeuristicFilter / calibration unchanged

**B is the next isolation step.** C / D are not started.

## 5. Step B implemented — live verdict pending

Debug ring polls official `gf.get_gaze_info()` like pygame_example (unlocked
`_gaze_info` read). Updates when `status` is True and filtered xy is finite,
then applies the **current** `origin+dpr` transform. Otherwise hold-last.

The T010 subscriber + maxsize-1 queue remains for the future product stream
and is **not** connected to the debug ring.

**Live gate:** chin/head support vs the official screenshot reference.

- Match → stop; cause was subscriber/queue consumption.
- Settled miss remains → B FAIL; then C (identity vs origin+dpr A/B) only.

---

## Explicitly not done

- No Stage D, dwell, or OS typing
- No change to DPR transform, calibration, HeuristicFilter, or camera
  lifecycle
- No PCA/Ridge/affine/bias/extra smoothing
- No Step C identity A/B overlay, no Step D pygame.quit DPI probe
