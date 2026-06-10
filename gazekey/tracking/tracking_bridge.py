"""Thread-safe bridge from tracking callback to Qt main thread."""

from PySide6.QtCore import QObject, Signal


class TrackingBridge(QObject):
    """Forwards EyeData from worker thread to main thread via queued signal."""

    eye_data_received = Signal(object)

    def forward(self, eye_data) -> None:
        self.eye_data_received.emit(eye_data)
