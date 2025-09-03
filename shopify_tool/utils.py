import os
import sys
import logging

logger = logging.getLogger("ShopifyToolLogger")


def get_persistent_data_path(filename):
    """Generates a path to a file in a persistent application data folder.

    This function determines the appropriate user-specific data directory
    based on the operating system (%APPDATA% on Windows, home directory
    on others), creates a folder for the application if it doesn't exist,
    and returns the full path for the given filename within that folder.
    This is used for storing files like the fulfillment history.

    Args:
        filename (str): The name of the file to be stored.

    Returns:
        str: The absolute path to the file in the persistent data folder.
    """
    # Use APPDATA for Windows, or user's home directory for other platforms
    app_data_path = os.getenv("APPDATA") or os.path.expanduser("~")
    app_dir = os.path.join(app_data_path, "ShopifyFulfillmentTool")

    try:
        os.makedirs(app_dir, exist_ok=True)
    except OSError as e:
        # Fallback to current directory if AppData is not writable
        logger.error(f"Could not create AppData directory: {e}. Falling back to local directory.")
        app_dir = "."

    return os.path.join(app_dir, filename)


def resource_path(relative_path):
    """Gets the absolute path to a resource, for both dev and PyInstaller.

    When running from source, this will return the absolute path to the
    resource relative to the project root. When running from a PyInstaller
    bundle, it will return the path to the resource within the temporary
    folder created by PyInstaller.

    Args:
        relative_path (str): The relative path to the resource (e.g.,
            'data/templates/my_template.xls').

    Returns:
        str: The absolute path to the resource.
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
