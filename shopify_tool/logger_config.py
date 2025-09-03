import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging():
    """Configures the logging for the entire application.

    This function sets up a logger named "ShopifyToolLogger" which is used
    across the application. It configures two handlers:
    1. A RotatingFileHandler to save log messages to 'logs/app_history.log'.
       The log file rotates when it reaches 1MB and keeps 5 backup files.
    2. A StreamHandler to print log messages to the console, which is useful
       for debugging or running the application in a non-GUI context.

    The logger is configured to capture messages at the INFO level and above.
    If the logger already has handlers, they are cleared to prevent
    duplicate logging.

    Returns:
        logging.Logger: The configured logger instance.
    """
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, "app_history.log")

    # Get the root logger used by the application
    logger = logging.getLogger("ShopifyToolLogger")
    logger.setLevel(logging.INFO)  # Set the lowest level to capture all messages

    # Prevent adding handlers multiple times
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create a handler for writing to a file
    file_handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024, backupCount=5, encoding="utf-8")
    file_handler.setLevel(logging.INFO)  # Log everything to the file
    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # The UI handler will be added separately in the GUI code
    # We add a basic StreamHandler for non-GUI execution or debugging
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_formatter = logging.Formatter("%(levelname)s: %(message)s")
    stream_handler.setFormatter(stream_formatter)
    logger.addHandler(stream_handler)

    return logger
