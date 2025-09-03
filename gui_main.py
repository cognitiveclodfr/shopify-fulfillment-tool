"""Main entry point for the Shopify Fulfillment Tool application.

This script initializes the QApplication, creates the main window, and starts
the application's event loop. It also handles setting the platform to
'offscreen' for testing or continuous integration environments.
"""

import sys
import os
from PySide6.QtWidgets import QApplication

# Ensure the gui directory is on the path if running this as a script
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from gui.main_window_pyside import MainWindow


def main():
    """Initializes and runs the Qt application.

    Sets up the QApplication, instantiates the MainWindow, and shows it.
    In a testing or CI environment, it sets the platform to 'offscreen'
    to prevent the GUI from actually being displayed.
    """
    # Set platform to offscreen for CI/testing environments
    if "pytest" in sys.modules or os.environ.get("CI"):
        QApplication.setPlatform("offscreen")
        print("Running in offscreen mode.")

    app = QApplication(sys.argv)
    window = MainWindow()

    if QApplication.platformName() != "offscreen":
        window.show()
        sys.exit(app.exec())
    else:
        # In offscreen mode, the window is created but not shown.
        # The app doesn't enter the event loop, allowing tests/CI to exit.
        print("Offscreen application initialized successfully.")


if __name__ == "__main__":
    main()
