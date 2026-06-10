"""Camera / eye-tracking startup for the keyboard window."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gazekey.ui.virtual_keyboard import VirtualKeyboard


class TrackingController:
    """Owns TrackingManager lifecycle and calibration frame-size lock."""

    def __init__(self, host: VirtualKeyboard) -> None:
        self._host = host

    def ensure_started(self) -> bool:
        h = self._host
        if not h.tracking_manager:
            from gazekey.tracking.tracking_manager import TrackingManager

            h.tracking_manager = TrackingManager(camera_id=0)

        if h.tracking_manager.is_tracking:
            return True

        success = h.tracking_manager.start_tracking(callback=h._tracking_bridge.forward)
        if success:
            h.camera_status_label.setText("📷 Camera: Connected ✓")
            h.camera_status_label.setStyleSheet(
                "QLabel { color: #10B981; padding: 5px; font-weight: bold; }"
            )
            h._log_verbose("Eye tracking started")
        else:
            h.camera_status_label.setText("📷 Camera: ERROR ✗")
            h.camera_status_label.setStyleSheet(
                "QLabel { color: #E63946; padding: 5px; font-weight: bold; }"
            )
            print(
                "Failed to start eye tracking - check camera permissions "
                "or if another app is using the camera"
            )
        return success

    def get_frame_size(self) -> tuple[int, int]:
        h = self._host
        if h._locked_frame_size is not None:
            return h._locked_frame_size
        if h.tracking_manager:
            frame = h.tracking_manager.get_latest_frame()
            if frame is not None:
                fh, fw = frame.shape[:2]
                return fw, fh
        return 640, 480

    def lock_frame_size_for_calibration(self) -> tuple[int, int]:
        w, h = self.get_frame_size()
        self._host._locked_frame_size = (w, h)
        return w, h
