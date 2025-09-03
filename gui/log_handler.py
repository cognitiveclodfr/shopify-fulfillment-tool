import logging
from PySide6.QtCore import QObject, Signal


class QtLogHandler(logging.Handler, QObject):
    """A custom logging handler that emits a Qt signal for each log record.

    This class inherits from both `logging.Handler` to integrate with Python's
    logging framework and `QObject` to leverage Qt's signal/slot mechanism.
    It is used to redirect log messages to a GUI element, like a QTextEdit.

    Attributes:
        log_message_received (Signal): A PySide6 signal that emits a formatted
            log message string whenever a log record is processed.
    """

    # Define a signal that will carry the log message
    log_message_received = Signal(str)

    def __init__(self, parent=None):
        """Initializes the QtLogHandler."""
        # Initialize QObject part first
        QObject.__init__(self)
        # Then initialize the logging.Handler part
        logging.Handler.__init__(self)

    def emit(self, record):
        """Formats a log record and emits it via the `log_message_received` signal.

        This method is called automatically by the Python logging framework
        whenever a new log message needs to be handled.

        Args:
            record (logging.LogRecord): The log record to be processed.
        """
        # Format the log record into a string
        msg = self.format(record)
        # Emit the signal with the formatted message
        self.log_message_received.emit(msg)
