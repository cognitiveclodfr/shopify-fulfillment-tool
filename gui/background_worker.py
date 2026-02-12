"""Base class for background workers with proper lifecycle management.

This module provides a reusable base class for background I/O operations
that implements the CORRECT cleanup pattern learned from commit #216 failures.

Key Features:
    - Proper QThread lifecycle management
    - Signal disconnection before cleanup
    - Timeout handling for wait()
    - Cancellation support
    - Generic data passing via signals

Critical Pattern (prevents crashes from commit #216):
    1. Check for existing worker before creating new one
    2. Disconnect ALL signals before cleanup
    3. quit() + wait(timeout) + deleteLater() sequence
    4. Handle timeout gracefully (terminate if needed)
"""

from PySide6.QtCore import QThread, Signal
import logging

logger = logging.getLogger(__name__)


class BackgroundWorker(QThread):
    """Reusable base class for background I/O operations.

    Implements correct cleanup pattern to prevent the crashes that occurred
    in commit #216 with QThread workers.

    Signals:
        finished_with_data(object): Emitted when work completes with result
        error_occurred(str): Emitted when error occurs with message
        progress_updated(int, str): Emitted for progress (current, message)

    Example:
        ```python
        class MyWorker(BackgroundWorker):
            def __init__(self, some_data):
                super().__init__()
                self.some_data = some_data

            def run(self):
                try:
                    if self._is_cancelled:
                        return

                    result = expensive_operation(self.some_data)

                    if not self._is_cancelled:
                        self.finished_with_data.emit(result)
                except Exception as e:
                    if not self._is_cancelled:
                        self.error_occurred.emit(str(e))

        # Usage:
        if self.worker is not None:
            self.worker.cleanup()  # CRITICAL: cleanup old worker first
            self.worker = None

        self.worker = MyWorker(data)
        self.worker.finished_with_data.connect(self._on_data_ready)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.start()
        ```
    """

    finished_with_data = Signal(object)  # Generic data result
    error_occurred = Signal(str)  # Error message
    progress_updated = Signal(int, str)  # (current, message)

    def __init__(self, parent=None):
        """Initialize background worker.

        Args:
            parent: Optional parent QObject
        """
        super().__init__(parent)
        self._is_cancelled = False

    def cancel(self):
        """Request cancellation of work.

        Worker should periodically check _is_cancelled flag and exit
        gracefully when it's True.
        """
        self._is_cancelled = True
        logger.debug(f"Cancellation requested for {self.__class__.__name__}")

    def cleanup(self):
        """Proper cleanup sequence to prevent crashes.

        This method MUST be called:
        - Before creating new worker instance
        - In widget's closeEvent()
        - Before parent widget destruction

        Implements the correct pattern from commit #216 post-mortem:
        1. Disconnect all signals (prevents race conditions)
        2. Request thread termination (quit)
        3. Wait with timeout (don't block forever)
        4. Force terminate if timeout exceeded
        5. Schedule for deletion (deleteLater)

        Example:
            ```python
            def create_new_worker(self):
                # CRITICAL: cleanup old worker FIRST
                if self.worker is not None:
                    self.worker.cleanup()
                    self.worker = None

                # Now safe to create new worker
                self.worker = MyWorker(data)
                self.worker.start()
            ```
        """
        if not self.isRunning():
            logger.debug(f"Worker not running, no cleanup needed: {self.__class__.__name__}")
            return

        logger.debug(f"Cleaning up worker: {self.__class__.__name__}")

        # 1. Disconnect ALL signals to prevent race conditions
        # This is CRITICAL - signals can emit after thread marked for deletion
        try:
            self.finished_with_data.disconnect()
        except:
            pass  # OK if not connected
        try:
            self.error_occurred.disconnect()
        except:
            pass
        try:
            self.progress_updated.disconnect()
        except:
            pass

        # 2. Request thread to stop gracefully
        self.quit()

        # 3. Wait with timeout (don't block UI forever)
        if not self.wait(2000):  # 2 second timeout
            logger.warning(
                f"Worker didn't finish in time, forcing termination: "
                f"{self.__class__.__name__}"
            )
            # 4. Force terminate if still running
            self.terminate()
            self.wait(1000)  # Wait after terminate

        # 5. Schedule for deletion
        # This is safe now because signals are disconnected
        self.deleteLater()

        logger.debug(f"Worker cleanup complete: {self.__class__.__name__}")

    def run(self):
        """Override this method in subclass to perform work.

        Must check self._is_cancelled periodically and exit gracefully.
        Emit finished_with_data on success, error_occurred on failure.

        Example:
            ```python
            def run(self):
                try:
                    for i in range(100):
                        if self._is_cancelled:
                            return  # Exit gracefully

                        # Do work...
                        self.progress_updated.emit(i, f"Processing {i}")

                    if not self._is_cancelled:
                        self.finished_with_data.emit(result)
                except Exception as e:
                    if not self._is_cancelled:
                        self.error_occurred.emit(str(e))
            ```
        """
        raise NotImplementedError("Subclass must implement run() method")
