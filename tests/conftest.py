"""Pytest fixtures for GazeKey tests."""

import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app
