"""US2 / SC-007: read-only gaze preview does not activate keys or text fields."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from tools.preview.gaze_preview import GazePreviewController
from gazekey.ui.virtual_keyboard import VirtualKeyboard


def test_gaze_preview_controller_updates_dot_only(qapp):
    root = QWidget()
    root.setGeometry(0, 0, 400, 200)
    root.show()
    qapp.processEvents()

    preview = GazePreviewController(root)
    preview.show_gaze(50.0, 60.0)
    qapp.processEvents()

    dot = preview.ensure_dot()
    assert dot.isVisible()
    assert dot._pos is not None


def test_mvp_product_exposes_typing_and_tools_preview_is_readonly(qapp):
    """Product has typing path; tools preview mode must not claim OS typing active."""
    vk = VirtualKeyboard()
    vk._official_gaze_ready = True
    vk._is_calibrating = False
    vk.is_expanded = True

    assert hasattr(vk._gaze_loop, "on_gaze_sample")
    assert hasattr(vk._gaze_loop, "gaze_typing_active")
    assert not hasattr(vk, "_text_buffer")

    assert vk._preview_mode is False
    vk._preview_mode = True
    vk._typing_runtime.set_os_inject_enabled(False)
    assert vk._gaze_loop.gaze_typing_active() is False


def test_gaze_preview_clear_removes_benchmark_label(qapp):
    root = QWidget()
    root.setGeometry(0, 0, 400, 200)
    root.show()
    qapp.processEvents()

    preview = GazePreviewController(root)
    preview.show_gaze(50.0, 60.0, label="benchmark: Q", raw_global=(48.0, 58.0), show_raw=True)
    preview.clear_gaze()
    qapp.processEvents()

    dot = preview.ensure_dot()
    assert dot._pos is None
    assert dot._raw_pos is None
    assert dot._label == ""


def test_delivery_failure_logs_verbose_status(qapp, monkeypatch):
    vk = VirtualKeyboard()
    vk._typing_runtime.session.activate()
    from gazekey.input.os_input_adapter import OsInjectResult
    from gazekey.typing.key_action import KeyAction, KeyActionKind, KeyActionSource

    action = KeyAction(
        kind=KeyActionKind.CHAR,
        text="z",
        source=KeyActionSource.MOUSE,
        key_id="k",
        timestamp=1.0,
    )
    ready_before = vk._official_gaze_ready
    logs: list[str] = []
    monkeypatch.setattr(vk, "_log_verbose", lambda msg: logs.append(msg))
    vk._on_os_action_delivered(action, OsInjectResult(ok=False, error="no_target"))
    assert any("OS typing unavailable" in m for m in logs)
    assert vk._typing_runtime.session.is_active
    assert vk._official_gaze_ready is ready_before


def test_os_keys_still_work_when_suggestions_empty(qapp):
    """US2: ignore/empty suggestions must not block letter KeyAction path."""
    from gazekey.input.os_input_adapter import FakeOsInputAdapter
    from gazekey.typing.action_dispatcher import ActionDispatcher

    vk = VirtualKeyboard()
    fake = FakeOsInputAdapter()
    vk._action_dispatcher = ActionDispatcher(fake)
    vk._typing_runtime.dispatcher = vk._action_dispatcher
    vk._action_dispatcher.on_action_delivered(vk._on_os_action_delivered)
    vk._typing_runtime.session.activate()
    vk._typing_runtime.set_os_inject_enabled(True)

    for btn in vk.suggestion_buttons:
        btn.setText("")
        btn.setEnabled(False)

    published = vk._typing_runtime.on_mouse_key(key_id="key_t", action="t")
    assert published is not None
    assert fake.injected[-1].text == "t"
    assert vk._typing_context.get_prefix() == "t"


def test_provider_suggest_failure_fail_open(qapp, monkeypatch):
    """US2 / FR-012: suggest exception clears slots; typing continues."""
    from gazekey.input.os_input_adapter import FakeOsInputAdapter
    from gazekey.typing.action_dispatcher import ActionDispatcher

    class BoomProvider:
        def suggest(self, prefix: str, *, limit: int = 3):
            raise RuntimeError("boom")

    vk = VirtualKeyboard()
    vk._word_provider = BoomProvider()
    fake = FakeOsInputAdapter()
    vk._action_dispatcher = ActionDispatcher(fake)
    vk._typing_runtime.dispatcher = vk._action_dispatcher
    vk._action_dispatcher.on_action_delivered(vk._on_os_action_delivered)
    vk._typing_runtime.session.activate()
    vk._typing_runtime.set_os_inject_enabled(True)

    vk._typing_runtime.on_mouse_key(key_id="key_h", action="h")
    vk._typing_runtime.on_mouse_key(key_id="key_e", action="e")
    assert all(not b.isEnabled() and b.text() == "" for b in vk.suggestion_buttons)
    assert [a.text for a in fake.injected] == ["h", "e"]
    assert vk._typing_context.get_prefix() == "he"
