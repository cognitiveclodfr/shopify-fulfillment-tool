"""Tests for background worker classes.

Covers:
- BackgroundWorker base class (gui/background_worker.py)
- Worker/WorkerSignals QRunnable (gui/worker.py)
- SessionLoaderWorker (gui/session_browser_widget.py)
"""

import os
import time
import pytest
from unittest.mock import Mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThreadPool, QCoreApplication

from gui.background_worker import BackgroundWorker
from gui.worker import Worker


def process_events():
    """Process pending Qt events (flushes queued cross-thread signals)."""
    QCoreApplication.processEvents()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class SimpleWorker(BackgroundWorker):
    """Minimal concrete subclass for testing BackgroundWorker."""

    def __init__(self, result=None, raise_exc=None, sleep_sec=0):
        super().__init__()
        self._result = result
        self._raise_exc = raise_exc
        self._sleep_sec = sleep_sec

    def run(self):
        if self._sleep_sec:
            time.sleep(self._sleep_sec)
        if self._is_cancelled:
            return
        if self._raise_exc:
            if not self._is_cancelled:
                self.error_occurred.emit(str(self._raise_exc))
            return
        if not self._is_cancelled:
            self.finished_with_data.emit(self._result)


# ---------------------------------------------------------------------------
# BackgroundWorker tests
# ---------------------------------------------------------------------------

class TestBackgroundWorker:

    def test_emits_finished_with_data(self, qapp):
        received = []
        worker = SimpleWorker(result={"key": "value"})
        worker.finished_with_data.connect(lambda d: received.append(d))
        worker.start()
        assert worker.wait(3000), "Worker did not finish in time"
        process_events()
        assert received == [{"key": "value"}]

    def test_emits_error_on_exception(self, qapp):
        errors = []
        worker = SimpleWorker(raise_exc=RuntimeError("boom"))
        worker.error_occurred.connect(lambda msg: errors.append(msg))
        worker.start()
        assert worker.wait(3000)
        process_events()
        assert len(errors) == 1
        assert "boom" in errors[0]

    def test_cancel_prevents_emission(self, qapp):
        received = []
        worker = SimpleWorker(result="should_not_arrive", sleep_sec=0.05)
        worker.finished_with_data.connect(lambda d: received.append(d))
        worker.cancel()
        worker.start()
        assert worker.wait(3000)
        process_events()
        assert received == [], "Signal should not emit after cancel"

    def test_cancel_sets_flag(self, qapp):
        worker = SimpleWorker()
        assert not worker._is_cancelled
        worker.cancel()
        assert worker._is_cancelled

    def test_cleanup_after_finish(self, qapp):
        worker = SimpleWorker(result=42)
        worker.start()
        assert worker.wait(3000)
        # cleanup() should not raise even after worker already finished
        worker.cleanup()

    def test_cleanup_disconnects_signals(self, qapp):
        called = []
        worker = SimpleWorker(result="x")
        worker.finished_with_data.connect(lambda d: called.append(d))
        worker.cleanup()
        # After cleanup, no signals should fire
        assert called == []

    def test_multiple_workers_sequential(self, qapp):
        """Creating a second worker after cleanup of first should work cleanly."""
        results = []

        w1 = SimpleWorker(result="first")
        w1.finished_with_data.connect(lambda d: results.append(d))
        w1.start()
        w1.wait(3000)
        process_events()
        w1.cleanup()

        w2 = SimpleWorker(result="second")
        w2.finished_with_data.connect(lambda d: results.append(d))
        w2.start()
        w2.wait(3000)
        process_events()
        w2.cleanup()

        assert results == ["first", "second"]


# ---------------------------------------------------------------------------
# Worker (QRunnable) tests
# ---------------------------------------------------------------------------

class TestWorker:

    def test_emits_result(self, qapp):
        received = []
        pool = QThreadPool()
        worker = Worker(lambda: 99)
        worker.signals.result.connect(lambda r: received.append(r))
        pool.start(worker)
        pool.waitForDone(3000)
        process_events()
        assert received == [99]

    def test_emits_error_on_exception(self, qapp):
        errors = []
        pool = QThreadPool()

        def bad_fn():
            raise ValueError("worker error")

        worker = Worker(bad_fn)
        worker.signals.error.connect(lambda t: errors.append(t))
        pool.start(worker)
        pool.waitForDone(3000)
        process_events()
        assert len(errors) == 1
        exc_type, exc_value, _ = errors[0]
        assert exc_type is ValueError
        assert "worker error" in str(exc_value)

    def test_emits_finished_always(self, qapp):
        finished_count = []
        pool = QThreadPool()

        # Success case
        w1 = Worker(lambda: "ok")
        w1.signals.finished.connect(lambda: finished_count.append(1))
        pool.start(w1)
        pool.waitForDone(3000)
        process_events()

        # Error case
        w2 = Worker(lambda: 1 / 0)
        w2.signals.finished.connect(lambda: finished_count.append(2))
        pool.start(w2)
        pool.waitForDone(3000)
        process_events()

        assert len(finished_count) == 2

    def test_passes_args_to_function(self, qapp):
        received = []
        pool = QThreadPool()
        worker = Worker(lambda a, b, c=0: received.append((a, b, c)), 10, 20, c=30)
        pool.start(worker)
        pool.waitForDone(3000)
        process_events()
        assert received == [(10, 20, 30)]


# ---------------------------------------------------------------------------
# SessionLoaderWorker tests
# ---------------------------------------------------------------------------

class TestSessionLoaderWorker:

    def test_emits_sessions_on_success(self, qapp):
        from gui.session_browser_widget import SessionLoaderWorker

        mock_sessions = [{"session_name": "S1", "session_path": "/path/s1"}]
        mock_sm = Mock()
        mock_sm.list_client_sessions.return_value = mock_sessions

        received = []
        worker = SessionLoaderWorker(mock_sm, "CLIENT_A")
        worker.finished_with_data.connect(lambda d: received.append(d))
        worker.start()
        assert worker.wait(3000)
        process_events()
        assert received == [mock_sessions]
        mock_sm.list_client_sessions.assert_called_once_with("CLIENT_A", status_filter=None)

    def test_emits_error_on_exception(self, qapp):
        from gui.session_browser_widget import SessionLoaderWorker

        mock_sm = Mock()
        mock_sm.list_client_sessions.side_effect = OSError("network error")

        errors = []
        worker = SessionLoaderWorker(mock_sm, "CLIENT_B")
        worker.error_occurred.connect(lambda msg: errors.append(msg))
        worker.start()
        assert worker.wait(3000)
        process_events()
        assert len(errors) == 1
        assert "network error" in errors[0]

    def test_passes_status_filter(self, qapp):
        from gui.session_browser_widget import SessionLoaderWorker

        mock_sm = Mock()
        mock_sm.list_client_sessions.return_value = []

        worker = SessionLoaderWorker(mock_sm, "CLIENT_C", status_filter="active")
        worker.start()
        worker.wait(3000)
        process_events()
        mock_sm.list_client_sessions.assert_called_once_with("CLIENT_C", status_filter="active")
