import os
import sys
import logging

logger = logging.getLogger('ShopifyToolLogger')

def get_persistent_data_path(filename):
    """
    Generates a path to a file in a persistent application data folder.
    Creates the folder if it doesn't exist.
    """
    # Use APPDATA for Windows, or user's home directory for other platforms
    app_data_path = os.getenv('APPDATA') or os.path.expanduser("~")
    app_dir = os.path.join(app_data_path, "ShopifyFulfillmentTool")

    try:
        os.makedirs(app_dir, exist_ok=True)
    except OSError as e:
        # Fallback to current directory if AppData is not writable
        logger.error(f"Could not create AppData directory: {e}. Falling back to local directory.")
        app_dir = "."

    return os.path.join(app_dir, filename)

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
