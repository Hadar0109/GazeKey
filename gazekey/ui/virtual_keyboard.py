"""
Virtual keyboard overlay — thin orchestrator wiring UI controllers (T051).
"""

from typing import Optional, Tuple

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import QTimer
from gazekey.ui.devtools_api import NullDevTools
from gazekey.ui.keyboard_layout import KeyboardLayoutBuilder
from gazekey.runtime.gaze_loop import GazeLoopController
from gazekey.ui.env_flags import EnvFlags
from gazekey.mvp_log import mvp_log
from gazekey.typing.action_dispatcher import ActionDispatcher
from gazekey.typing.dwell_engine import DwellEngine, DwellPhase
from gazekey.typing.gaze_typing_runtime import GazeTypingFrameResult, GazeTypingRuntime
from gazekey.typing.key_semantics import is_os_bound_action, is_pause_resume_action
from gazekey.typing.typing_session import TypingSession
from gazekey.input.pynput_adapter import PynputOsInputAdapter
from gazekey.input.os_input_adapter import OsInjectResult
from gazekey.typing.key_action import KeyAction, KeyActionSource
from gazekey.ui.dwell_progress_overlay import DwellProgressOverlay
from gazekey.prediction.word_provider import WordProvider
from gazekey.prediction.factory import create_default_word_provider
from gazekey.prediction.typing_context import TypingContext
from gazekey.prediction.suggestion_dispatch import dispatch_suggestion_completion
from gazekey.typing.key_semantics import suggestion_slot_index
import time


class VirtualKeyboard(QWidget):
    """Transparent, always-on-top virtual keyboard — wires controllers, owns window lifecycle."""

    def _log_verbose(self, message: str) -> None:
        mvp_log(message)

    def __init__(self):
        super().__init__()
        self.shift_active = False
        self.letter_keys = {}  # Store references to letter buttons for shift toggle
        self.is_expanded = True  # Track zoom state
        self.current_layout = 'letters'  # Product is letters-only (symbols path removed in 003)
        self.letter_page = "left"
        self._gaze_loop = GazeLoopController(self)
        self._typing_session = TypingSession()
        self._dwell_engine = DwellEngine()
        self._os_input_adapter = PynputOsInputAdapter()
        self._action_dispatcher = ActionDispatcher(self._os_input_adapter)
        self._typing_runtime = GazeTypingRuntime(
            self._typing_session,
            self._dwell_engine,
            self._action_dispatcher,
            on_session_ui_sync=self._sync_typing_session_ui,
            on_suggestion_accept=self._on_suggestion_accept,
            on_calibrate=self.on_calibrate_clicked,
            on_page_switch=self.on_page_switch_activated,
        )
        self._action_dispatcher.on_action_delivered(self._on_os_action_delivered)
        # Composition root: construct default WordProvider once via factory.
        self._word_provider: WordProvider = create_default_word_provider()
        if getattr(self._word_provider, "load_error", None) is not None:
            self._log_verbose(
                f"[prediction] word list load failed (fail-open): {self._word_provider.load_error}"
            )
        self._typing_context = TypingContext()
        self._suggestion_epoch: int = -1
        self._dwell_overlay: DwellProgressOverlay | None = None
        self._typing_status_clear_timer: QTimer | None = None
        self._devtools = NullDevTools()
        self._run_summary_writer = None  # set only when tools install DevTools
        self._layout_exporter = None
        self._benchmark_controller = None
        self._is_calibrating = False
        self._gaze_focused_button = None
        self._layout_keys = []
        self._keys_by_id = {}
        env_flags = EnvFlags.load()
        self._layout_version = ""
        self._layout_export_pending = False
        self._verbose = env_flags.verbose
        self._last_runtime_log_ms = 0
        self._preview_mode = False
        self._gaze_preview = None
        self._tools_auto_preview_after_calib = False
        self._rt2_debug = env_flags.rt2_debug
        self._calib_debug = env_flags.calib_debug
        self._row_aware_row_names = [
            "control",
            "suggestions",
            "letters1",
            "letters2",
            "letters3",
            "actions",
        ]
        self._row_aware_row_rects = {}
        self._key_semantic_row = {}
        self._keyboard_layout_builder = KeyboardLayoutBuilder(self)
        self.init_ui()
        self._dwell_overlay = DwellProgressOverlay(self.main_content_widget)
        self._keyboard_layout_builder.schedule_layout_export()
        self._gf_debug_overlay = None
        self._gf_sample_bridge = None
        self._gf_lifecycle = None
        self._official_gaze_ready = False

    def init_ui(self):
        """Initialize the user interface (delegates to KeyboardLayoutBuilder, T046)."""
        self._keyboard_layout_builder.init_ui()

    def _calibration_usable(self) -> bool:
        return bool(getattr(self, "_official_gaze_ready", False))

    def _benchmark_active(self) -> bool:
        return bool(self._devtools.benchmark_active())

    def _set_post_calibration_controls(self, enabled: bool) -> None:
        # Product Pause/Preview removed (003); tools preview remains via python -m tools.preview.
        del enabled

    def _ensure_typing_auto_started(self) -> None:
        """Activate typing when official GazeFollower calibration is usable."""
        runtime = getattr(self, "_typing_runtime", None)
        if runtime is None:
            return
        if self._is_calibrating or not self._calibration_usable():
            return
        if runtime.session.is_inactive:
            runtime.session.activate()
            runtime.set_os_inject_enabled(True)
            self._sync_typing_session_ui()
        elif runtime.session.is_paused:
            # Product pause UI removed — keep session active when mapper available.
            runtime.session.resume()
            runtime.set_os_inject_enabled(True)
            self._sync_typing_session_ui()
        elif runtime.session.is_active and bool(
            getattr(self, "_official_gaze_ready", False)
        ):
            # Recalibrate disables inject but leaves the session active.
            runtime.set_os_inject_enabled(True)

    def _reset_typing_for_recalibration(self) -> None:
        runtime = getattr(self, "_typing_runtime", None)
        if runtime is None:
            return
        runtime.set_os_inject_enabled(False)
        runtime.reset()
        self._sync_typing_session_ui()

    def _sync_typing_session_ui(self) -> None:
        runtime = getattr(self, "_typing_runtime", None)
        if runtime is None:
            return
        if hasattr(self, "shift_btn") and self.shift_btn is not None:
            armed = runtime.session.shift_oneshot_armed
            if self.shift_btn.isChecked() != armed:
                self.shift_btn.blockSignals(True)
                self.shift_btn.setChecked(armed)
                self.shift_btn.blockSignals(False)
            self.shift_active = bool(armed)
        ctx = getattr(self, "_typing_context", None)
        if ctx is not None:
            ctx.set_shift_armed(bool(runtime.session.shift_oneshot_armed))

    def _key_id_for_action(self, action: str) -> Optional[str]:
        for key in getattr(self, "_layout_keys", None) or []:
            if str(getattr(key, "key_action", "")) == action:
                return str(key.key_id)
        return None

    def _maybe_start_dev_benchmark(self) -> None:
        self._devtools.maybe_start_dev_benchmark()

    def on_preview_clicked(self) -> None:
        """Tools-only preview toggle (product Preview button removed — use python -m tools.preview)."""
        if not self._calibration_usable():
            self._log_verbose("[preview] blocked — calibration required before preview (CQ-2)")
            return
        if self._is_calibrating or self._benchmark_active():
            return
        if self._devtools.ensure_gaze_preview(self) is None and not self._preview_mode:
            self._log_verbose("[preview] unavailable on product path — use: python -m tools.preview")
            return
        self._preview_mode = not bool(self._preview_mode)
        if not self._preview_mode:
            self._hide_preview_dot()
            self._clear_v2_focus()

    def _hide_preview_dot(self) -> None:
        self._devtools.hide_gaze_preview()

    def _reset_preview_overlay(self) -> None:
        """Clear benchmark/debug gaze state; single mapped dot on next frame."""
        self._devtools.clear_gaze_preview()

    def _update_gaze_preview_dot(
        self,
        screen_x: float,
        screen_y: float,
        *,
        label: str = "",
        raw_global: Tuple[float, float] | None = None,
        show_raw: bool = False,
    ) -> None:
        """Show mapped gaze on the keyboard (read-only preview overlay via tools)."""
        self._devtools.update_gaze_preview_dot(
            self,
            screen_x=screen_x,
            screen_y=screen_y,
            label=label if self._rt2_debug else "",
            raw_global=raw_global,
            show_raw=show_raw and self._rt2_debug,
        )

    def on_suggestion_clicked(self, suggestion):
        """Mouse parity: accept populated suggestion slot via same dispatch path as dwell."""
        buttons = getattr(self, "suggestion_buttons", None) or []
        slot: Optional[int] = None
        if isinstance(suggestion, int):
            slot = suggestion
        else:
            # Legacy string label path — resolve to slot index.
            for i, btn in enumerate(buttons):
                if btn.text() == str(suggestion):
                    slot = i
                    break
        if slot is None or slot < 0 or slot >= len(buttons):
            return
        btn = buttons[slot]
        if not btn.isEnabled() or not btn.text():
            return
        if self._is_calibrating or self._benchmark_active():
            return
        runtime = getattr(self, "_typing_runtime", None)
        if runtime is None or not runtime.os_inject_enabled or runtime.session.is_inactive:
            return
        key_id = f"suggestion:{slot}"
        runtime.on_mouse_key(key_id=key_id, action=key_id)

    def _on_suggestion_accept(self, key_id: str, source: KeyActionSource) -> None:
        """Dwell/mouse suggestion fire → suffix + Space (epoch guard)."""
        slot = suggestion_slot_index(key_id)
        buttons = getattr(self, "suggestion_buttons", None) or []
        if slot is None or slot < 0 or slot >= len(buttons):
            return
        btn = buttons[slot]
        word = (btn.text() or "").strip().lower()
        if not word or not btn.isEnabled():
            return
        ctx = getattr(self, "_typing_context", None)
        runtime = getattr(self, "_typing_runtime", None)
        if ctx is None or runtime is None:
            return
        accept_epoch = int(getattr(self, "_suggestion_epoch", ctx.get_epoch()))
        dispatch_suggestion_completion(
            word=word,
            prefix=ctx.get_prefix(),
            accept_epoch=accept_epoch,
            current_epoch=ctx.get_epoch(),
            dispatcher=self._action_dispatcher,
            session=runtime.session,
            source=source,
            key_id=key_id,
            clock=time.time,
        )
        self._sync_typing_session_ui()

    def on_key_pressed(self, key):
        """Handle key press from mouse (OS-bound → ActionDispatcher when typing active)."""
        if self._is_calibrating or self._benchmark_active():
            return
        if key == "SHIFT":
            return
        runtime = getattr(self, "_typing_runtime", None)
        if (
            runtime is not None
            and runtime.os_inject_enabled
            and not runtime.session.is_inactive
            and (is_os_bound_action(key) or is_pause_resume_action(key))
        ):
            key_id = self._key_id_for_action(key) or f"mouse:{key}"
            runtime.on_mouse_key(key_id=key_id, action=key)
            self._log_verbose(f"Key pressed (OS path): {key}")
            return
        # OS is the sole typing destination — no in-app text buffer (T046).
        self._log_verbose(f"Key ignored (non-OS or typing inactive): {key}")

    def on_calibrate_clicked(self):
        """Calibrate control → official GazeFollower Preview + Calibration (T042)."""
        self._reset_calibrate_button_style()
        lifecycle = getattr(self, "_gf_lifecycle", None)
        if lifecycle is None:
            self._reset_typing_for_recalibration()
            self._log_verbose(
                "[calib] Calibrate requested without GazeFollower lifecycle; "
                "legacy overlay is not started."
            )
            return
        from gazekey.backend.startup import run_official_recalibrate

        run_official_recalibrate(lifecycle, self)
        self._on_return_from_official_recalibrate()

    def _reset_calibrate_button_style(self) -> None:
        self.calibrate_btn.setText("👁 CALIBRATE")
        if getattr(self, "_calibrate_btn_style_default", None):
            self.calibrate_btn.setStyleSheet(self._calibrate_btn_style_default)

    def _show_recalibrate_prompt(self, status_message: str) -> None:
        """Highlight RECALIBRATE after failed quality gates."""
        self.calibrate_btn.setText("👁 RECALIBRATE")
        self.calibrate_btn.setStyleSheet("""
            QPushButton {
                background-color: #E63946;
                color: white;
                border: 2px solid #FBBF24;
                border-radius: 8px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F04A57;
            }
        """)
        self._log_verbose(f"[calib] recalibrate needed: {status_message}")

    def showEvent(self, event) -> None:
        super().showEvent(event)

    def on_app_started(self) -> None:
        """Called from main() after show(); official Preview/Calibration already ran."""
        return

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._keyboard_layout_builder.update_responsive_sizes()
        self._devtools.resize_gaze_preview()
        self._devtools.update_benchmark_banner_geometry()
        overlay = getattr(self, "_gf_debug_overlay", None)
        if overlay is not None:
            overlay.resize_to_keyboard()
        self._keyboard_layout_builder.schedule_layout_export()

    def _schedule_layout_export(self) -> None:
        self._keyboard_layout_builder.schedule_layout_export()

    def _bind_session_artifact_paths(self, session_id: str) -> None:
        exporter = self._devtools.layout_exporter()
        if exporter is None:
            return
        runs_dir = self._devtools.runs_dir
        if runs_dir is None:
            return
        exporter.set_session(session_id, runs_dir=runs_dir)

    def _export_keyboard_layout(self) -> None:
        self._keyboard_layout_builder.export_keyboard_layout()

    def _clear_v2_focus(self) -> None:
        pass

    def _start_mvp_benchmark(self) -> None:
        self._devtools.start_mvp_benchmark()

    def _on_os_action_delivered(self, action: KeyAction, result: OsInjectResult) -> None:
        """Update TypingContext on success; verbose-only status on delivery failure (R10)."""
        ctx = getattr(self, "_typing_context", None)
        if ctx is not None and result.ok:
            changed = ctx.on_action_delivered(action, ok=True)
            runtime = getattr(self, "_typing_runtime", None)
            if runtime is not None:
                ctx.set_shift_armed(bool(runtime.session.shift_oneshot_armed))
            if changed:
                self._refresh_suggestions()
            return
        if result.ok:
            return
        reason = (result.error or "no usable external typing target").strip()
        self._show_typing_status(f"OS typing unavailable — {reason}", error=True)

    def _refresh_suggestions(self) -> None:
        """Label fixed suggestion slots from WordProvider (delivery-path only; FR-012 fail-open)."""
        buttons = getattr(self, "suggestion_buttons", None) or []
        if len(buttons) < 3:
            return
        ctx = getattr(self, "_typing_context", None)
        provider = getattr(self, "_word_provider", None)
        words: list[str] = []
        epoch = 0
        if ctx is not None and provider is not None:
            epoch = ctx.get_epoch()
            prefix = ctx.get_prefix()
            try:
                words = list(provider.suggest(prefix) or [])
            except Exception as exc:
                self._log_verbose(f"[prediction] suggest failed (fail-open): {exc}")
                words = []
        prev_epoch = getattr(self, "_suggestion_epoch", -1)
        self._suggestion_epoch = epoch
        # Cancel in-progress suggestion dwell when prefix epoch changes (research R6).
        if prev_epoch != -1 and prev_epoch != epoch:
            runtime = getattr(self, "_typing_runtime", None)
            if runtime is not None:
                runtime.cancel_dwell()
        for i, btn in enumerate(buttons[:3]):
            if i < len(words) and words[i]:
                btn.setText(words[i])
                btn.setEnabled(True)
                btn.setToolTip(words[i])
            else:
                btn.setText("")
                btn.setEnabled(False)
                btn.setToolTip("Autocomplete suggestions")
        # Keep hit-test / dwell in sync with enabled state.
        self._schedule_layout_export()

    def _show_typing_status(self, message: str, *, error: bool = False) -> None:
        prefix = "[typing:error]" if error else "[typing]"
        self._log_verbose(f"{prefix} {message}")

    def _clear_typing_status(self) -> None:
        return

    def _update_dwell_visuals(self, result: GazeTypingFrameResult) -> None:
        """Border highlight + circular progress ring on existing key geometry (T047)."""
        button = None
        key_id = result.target_key_id
        if key_id and key_id in getattr(self, "_keys_by_id", {}):
            button = self._keys_by_id[key_id].button

        phase = result.dwell.phase
        progress = float(result.dwell.progress_01)
        show_progress = (
            button is not None
            and phase in (DwellPhase.PROGRESSING, DwellPhase.SWITCH_PENDING)
            and progress > 0.0
            and not result.dwell.in_cooldown
        )
        if phase is DwellPhase.FIRED_LOCK and result.dwell.fired:
            progress = 1.0
            show_progress = button is not None

        if show_progress and button is not None:
            self._on_gaze_focus_key(button, progress)
            if self._dwell_overlay is not None:
                self._dwell_overlay.show_on_button(button, progress)
        else:
            self._on_gaze_focus_key(None, 0.0)
            if self._dwell_overlay is not None:
                self._dwell_overlay.clear()

    def _on_gaze_focus_key(self, button, progress: float) -> None:
        if button is None:
            if self._gaze_focused_button is not None:
                self._set_key_gaze_style(self._gaze_focused_button, False, 0.0)
            self._gaze_focused_button = None
            return
        if self._gaze_focused_button is not None and self._gaze_focused_button is not button:
            self._set_key_gaze_style(self._gaze_focused_button, False, 0.0)
        self._gaze_focused_button = button
        dwelling = progress >= 0.7
        focused = progress > 0.0
        self._set_key_gaze_style(button, focused, progress, dwelling=dwelling)

    def _set_key_gaze_style(
        self,
        button,
        focused: bool,
        progress: float,
        dwelling: bool = False,
    ) -> None:
        button.setProperty("gazeFocused", focused and not dwelling)
        button.setProperty("gazeDwelling", dwelling)
        button.setProperty("dwellProgress", progress)
        style = button.style()
        style.unpolish(button)
        style.polish(button)
        button.update()

    def on_close_clicked(self):
        """Handle close button click - properly exit the application"""
        self._log_verbose("Closing GazeKey application...")
        runtime = getattr(self, "_typing_runtime", None)
        if runtime is not None:
            runtime.session.on_tracking_terminated()
            runtime.dwell.reset()
            runtime.set_os_inject_enabled(False)

        lifecycle = getattr(self, "_gf_lifecycle", None)
        if lifecycle is not None:
            try:
                lifecycle.release()
            except Exception as exc:
                self._log_verbose(f"[shutdown] GazeFollower.release() failed: {exc}")

        QApplication.quit()

    def on_shift_clicked(self, checked):
        """Handle shift — oneshot via typing session when typing is active."""
        del checked
        runtime = getattr(self, "_typing_runtime", None)
        if (
            runtime is not None
            and runtime.os_inject_enabled
            and runtime.session.is_active
        ):
            key_id = self._key_id_for_action("SHIFT") or "mouse:SHIFT"
            runtime.on_mouse_key(key_id=key_id, action="SHIFT")
            self._sync_typing_session_ui()
            self._log_verbose(
                f"Shift oneshot {'ARMED' if runtime.session.shift_oneshot_armed else 'CLEAR'}"
            )
            return
        self.shift_active = self.shift_btn.isChecked() if hasattr(self, "shift_btn") else False
        for char, btn in self.letter_keys.items():
            if self.shift_active:
                btn.setText(char.upper())
            else:
                btn.setText(char.lower())
        self._log_verbose(f"Shift {'ON' if self.shift_active else 'OFF'}")

    def switch_letter_page(self, page: str) -> None:
        """Rebuild the visible letter page and export layout in the same call.

        Must not reset TypingSession (including shift_oneshot_armed) or
        TypingContext prefix/epoch (FR-019).
        """
        if page not in ("left", "right"):
            raise ValueError(f"invalid letter_page: {page!r}")
        self.letter_page = page
        self._keyboard_layout_builder.rebuild_letter_area(page)

    def on_page_switch_activated(self, checked: bool = False) -> None:
        """Dwell/mouse page-switch control: toggle letter page, never OS-type."""
        del checked
        dest = "right" if self.letter_page == "left" else "left"
        self.switch_letter_page(dest)

    def _on_return_from_official_recalibrate(self) -> None:
        """FR-009: reset to left only after official recalibrate returns."""
        if self.letter_page != "left":
            self.switch_letter_page("left")
        else:
            self.letter_page = "left"

    def _restore_shift_visual_from_session(self) -> None:
        """Copy Shift checked-state and letter case from TypingSession after rebuild."""
        runtime = getattr(self, "_typing_runtime", None)
        armed = bool(runtime is not None and runtime.session.shift_oneshot_armed)
        self.shift_active = armed
        shift_btn = getattr(self, "shift_btn", None)
        if shift_btn is not None:
            shift_btn.blockSignals(True)
            shift_btn.setChecked(armed)
            shift_btn.blockSignals(False)
        for char, btn in self.letter_keys.items():
            btn.setText(char.upper() if armed else char.lower())

    def on_minimize_clicked(self):
        """Handle minimize button click - shrink to keyboard icon"""
        self.main_content_widget.hide()
        self.minimized_content_widget.show()
        self._keyboard_layout_builder.apply_minimized_geometry()
        self.is_expanded = False
        self._log_verbose("Keyboard minimized to icon")

    def on_restore_clicked(self):
        """Handle restore button click - expand to full keyboard"""
        self.minimized_content_widget.hide()
        self.main_content_widget.show()
        self._keyboard_layout_builder.apply_full_keyboard_geometry()
        self.is_expanded = True
        self._log_verbose("Keyboard restored to full view")
