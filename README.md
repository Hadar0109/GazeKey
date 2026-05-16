# GazeKey

Eye-tracking based virtual keyboard for hands-free typing using a standard webcam.

## Overview

GazeKey enables hands-free typing through eye tracking and gaze-based interaction. The system uses MediaPipe for precise eye and iris landmark detection, allowing users to type by looking at keys on a virtual keyboard.

## Features

### ✅ Completed

- **Virtual Keyboard Overlay**
  - Frameless, transparent, always-on-top window
  - Full QWERTY layout with letters and symbols
  - Layout switching (ABC ↔ ?123)
  - Uppercase/lowercase toggle (Shift)
  - Minimize/restore functionality
  - Draggable window positioning

- **Real-Time Eye Tracking**
  - MediaPipe Face Landmarker integration (v0.10.33)
  - 42-point precision tracking (eyes + iris only)
  - 97-100% detection rate at ~30 FPS
  - Background thread processing for smooth UI

- **Camera Preview**
  - Separate floating window with live camera feed
  - 300x225px preview at top-right corner
  - Always-on-top, independent positioning
  - Real-time frame updates

- **Tracking Statistics**
  - Face detection status
  - Eye tracking confirmation
  - Detection rate percentage
  - Live console logging

### ⏳ In Development

- **Keyboard Input Injection** (Next: Phase 1)
  - Mouse-based typing (MVP)
  - pynput integration for cross-application typing
  
- **Calibration System** (Phase 2)
  - 5-point gaze-to-screen mapping
  - Drift detection and correction
  
- **Dwell-Time Selection** (Phase 3)
  - Gaze-based key selection (~1 second dwell)
  - Visual feedback for dwell progress
  
- **Advanced Features** (Future)
  - Word prediction and auto-complete
  - Hebrew/English language switching
  - Configurable dwell-time thresholds

## Setup

### Requirements

- Python 3.8+
- Webcam (built-in or USB)
- Windows/Linux/macOS

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd "Virtual Keyboard"

# Install dependencies
pip install -r requirements.txt

# Download MediaPipe model (automatic on first run)
# Model will be downloaded to: models/face_landmarker.task
```

### Dependencies

```
PySide6>=6.6.0           # Qt GUI framework
opencv-python>=4.8.0     # Computer vision
mediapipe>=0.10.0        # Face and eye tracking
numpy>=1.24.0            # Numerical operations
pynput>=1.7.6            # Keyboard input injection
```

## Usage

### Running the Application

```bash
python main.py
```

### Basic Workflow

1. **Launch Application**
   - Virtual keyboard appears at screen center
   - Drag window to reposition if needed

2. **Start Eye Tracking**
   - Click the orange **"👁 CALIBRATE"** button
   - Camera preview window opens (top-right corner)
   - Status shows: "📷 Connected ✓ | 👁 Eyes Tracked"

3. **Monitor Tracking**
   - Watch live camera feed in preview window
   - Check detection rate in status bar
   - Console shows iris positions every 30 frames

4. **Stop Tracking**
   - Click red **"STOP"** button
   - Camera preview closes
   - Statistics printed to console

5. **Keyboard Features**
   - Click **?123** to switch to symbols/numbers
   - Click **ABC** to return to letters
   - Use **Shift** for uppercase
   - Click **-** to minimize, **⌨** to restore

### Testing Eye Tracking

Run standalone test scripts:

```bash
# Test eye and iris tracking (recommended)
python test_eye_tracking.py

# Test basic camera access
python test_camera_simple.py

# Test face detection with OpenCV
python test_camera_face.py
```

Press **Q** to quit test windows.

## Project Architecture

```
Virtual Keyboard/
├── main.py                          # Application entry point
├── requirements.txt                 # Python dependencies
├── models/
│   └── face_landmarker.task        # MediaPipe model (auto-downloaded)
├── gazekey/
│   ├── ui/
│   │   ├── virtual_keyboard.py     # Main keyboard UI
│   │   └── camera_preview_window.py # Camera preview window
│   └── tracking/
│       ├── video_capture.py        # OpenCV camera wrapper
│       ├── eye_detector.py         # MediaPipe eye/iris detection
│       └── tracking_manager.py     # Background tracking coordinator
└── test_*.py                        # Standalone test scripts
```

### Architecture Overview

**UI Layer:**
- `VirtualKeyboard`: Main keyboard window with controls
- `CameraPreviewWindow`: Separate live camera feed display

**Tracking Layer:**
- `VideoCapture`: Manages webcam access (OpenCV)
- `EyeDetector`: Eye/iris landmark detection (MediaPipe)
- `TrackingManager`: Orchestrates capture and detection in background thread

**Data Flow:**
```
Camera → VideoCapture → TrackingManager → EyeDetector → UI Callback
                              ↓
                        CameraPreview
```

## Development Roadmap

### Phase 1: Mouse-Based Typing (Next)
- [ ] Create `keyboard_injector.py` with pynput
- [ ] Connect mouse clicks to real typing
- [ ] Test across applications (Notepad, browser, etc.)
- [ ] Handle special keys (Space, Backspace, Enter)

### Phase 2: Calibration System
- [ ] Design 5-point calibration UI
- [ ] Collect gaze samples at known positions
- [ ] Calculate transformation matrix
- [ ] Implement drift detection

### Phase 3: Gaze-Based Selection
- [ ] Implement dwell-time detection (~1 second)
- [ ] Add visual feedback (progress indicator)
- [ ] Connect to keyboard input injection
- [ ] Fine-tune thresholds

### Future Enhancements
- [ ] Word prediction engine
- [ ] Hebrew language support
- [ ] Settings panel (dwell-time, sensitivity)
- [ ] Session recording and replay
- [ ] Multi-monitor support

## Technical Details

### Eye Tracking Specifications

- **Model**: MediaPipe Face Landmarker (float16)
- **Landmarks Tracked**: 42 points
  - Left eye: 16 points
  - Right eye: 16 points
  - Left iris: 5 points
  - Right iris: 5 points
- **Detection Confidence**: 0.5 (50%)
- **Tracking Confidence**: 0.5 (50%)
- **Frame Rate**: ~30 FPS
- **Resolution**: 640x480

### Performance Metrics

- **Detection Rate**: 97-100% (face present)
- **Latency**: <50ms per frame
- **CPU Usage**: Moderate (background thread)
- **Memory**: ~200MB

## Troubleshooting

### Camera Issues

**Camera not opening:**
1. Check Windows Settings → Privacy → Camera
2. Enable "Camera access" and "Let desktop apps access your camera"
3. Close other apps using the camera (Zoom, Teams, etc.)

**Low detection rate:**
- Ensure good lighting
- Face the camera directly
- Remove glasses if possible (reflections can interfere)
- Check camera is at eye level

### Window Issues

**Keyboard not visible:**
- Window may be off-screen, check window positioning
- Try dragging from edges
- Restart application

**Preview window covering keyboard:**
- Preview is in separate window at top-right
- Move it manually if needed

## Contributing

This project follows incremental development principles:
1. Each feature is built and tested independently
2. Complex features are broken into small, testable steps
3. Mouse-based testing before gaze-based implementation

## License

[Your License Here]

## Acknowledgments

- **MediaPipe** by Google for face landmark detection
- **OpenCV** for computer vision
- **PySide6** for Qt GUI framework
- **pynput** for keyboard input injection
