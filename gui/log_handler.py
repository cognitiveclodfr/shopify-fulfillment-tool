import logging
from PySide6.QtCore import QObject, Signal

class QtLogHandler(logging.Handler, QObject):
    """
    A custom logging handler that emits a Qt signal for each log record.
    """
    # Define a signal that will carry the log message
    log_message_received = Signal(str)

    def __init__(self, parent=None):
        # Initialize QObject part first
        QObject.__init__(self)
        # Then initialize the logging.Handler part
        logging.Handler.__init__(self)

    def emit(self, record):
        """
        This method is called by the logging framework for each log record.
        """
        # Format the log record into a string
        msg = self.format(record)
        # Emit the signal with the formatted message
        self.log_message_received.emit(msg)
