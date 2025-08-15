import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Configures the logging for the entire application."""
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, 'app_errors.log')

    # Create a logger
    logger = logging.getLogger('ShopifyToolLogger')
    logger.setLevel(logging.ERROR) # We only want to log critical errors

    # Create a handler that writes log records to a file, with rotation
    # 1MB per file, keeping up to 5 backup files.
    handler = RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5, encoding='utf-8')

    # Create a formatter and set it for the handler
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)')
    handler.setFormatter(formatter)

    # Add the handler to the logger
    # Avoid adding handlers multiple times if the function is called more than once
    if not logger.handlers:
        logger.addHandler(handler)

    return logger