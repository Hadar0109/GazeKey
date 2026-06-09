"""MVP console logging gate (FR-015, FR-016)."""

from __future__ import annotations

from gazekey.mvp_log import mvp_log, mvp_verbose


def test_mvp_log_quiet_by_default(capsys, monkeypatch):
    monkeypatch.delenv("GAZEKEY_VERBOSE", raising=False)
    assert mvp_verbose() is False
    mvp_log("diag-only")
    mvp_log("essential", always=True)
    out = capsys.readouterr().out
    assert "diag-only" not in out
    assert "essential" in out


def test_mvp_log_verbose_enabled(capsys, monkeypatch):
    monkeypatch.setenv("GAZEKEY_VERBOSE", "1")
    mvp_log("verbose-detail")
    out = capsys.readouterr().out
    assert "verbose-detail" in out
