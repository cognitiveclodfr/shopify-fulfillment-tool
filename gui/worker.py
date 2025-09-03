import sys
import traceback
from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
    """Defines the signals available from a running worker thread.

    Supported signals are:
    - finished: Emitted when the task is done, with no data.
    - error: Emitted when an exception occurs, carrying a tuple of
      (exception_type, value, traceback_string).
    - result: Emitted upon successful completion, carrying the result object.
    """

    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)


class Worker(QRunnable):
    """A generic worker thread that runs a function with given arguments.

    This class inherits from QRunnable to be used with a QThreadPool. It is
    designed to run a specified function in a separate thread to prevent
    blocking the main GUI thread. It uses a `WorkerSignals` object to
    communicate results, errors, or completion status back to the main thread.

    Args:
        fn (function): The function to execute in the worker thread.
        *args: Positional arguments to pass to the function.
        **kwargs: Keyword arguments to pass to the function.
    """

    def __init__(self, fn, *args, **kwargs):
        """Initializes the Worker instance."""
        super(Worker, self).__init__()
        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        """Executes the stored function and emits signals based on the outcome.

        This method is called automatically when the `QThreadPool` starts the
        runnable. It wraps the function call in a try...except block to
        handle exceptions gracefully, emitting an `error` signal if one
        occurs, or a `result` signal on success. The `finished` signal is
        always emitted.
        """
        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done
