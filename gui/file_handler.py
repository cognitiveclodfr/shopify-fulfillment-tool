import os
import logging
import pandas as pd
from PySide6.QtWidgets import QFileDialog, QMessageBox

from shopify_tool import core


class FileHandler:
    """Handles file selection dialogs, validation, and loading logic.

    This class encapsulates the functionality related to file I/O initiated
    by the user, such as selecting orders and stock files. It interacts with
    the `QFileDialog` to get file paths and then triggers validation on those
    files.

    Attributes:
        mw (MainWindow): A reference to the main window instance.
        log (logging.Logger): A logger for this class.
    """

    def __init__(self, main_window):
        """Initializes the FileHandler.

        Args:
            main_window (MainWindow): The main window instance that this
                handler will manage file operations for.
        """
        self.mw = main_window
        self.log = logging.getLogger(__name__)

    def select_orders_file(self):
        """Opens a file dialog for the user to select the orders CSV file.

        After a file is selected, it updates the corresponding UI labels,
        triggers header validation for the file, and checks if the application
        is ready to run the analysis.
        """
        filepath, _ = QFileDialog.getOpenFileName(self.mw, "Select Orders File", "", "CSV files (*.csv)")
        if filepath:
            self.mw.orders_file_path = filepath
            self.mw.orders_file_path_label.setText(os.path.basename(filepath))
            self.log.info(f"Orders file selected: {filepath}")
            self.validate_file("orders")
            self.check_files_ready()

    def select_stock_file(self):
        """Opens file dialog for stock CSV selection and loads file.

        After a file is selected, it validates the file with the correct
        delimiter from the client configuration.
        """
        filepath, _ = QFileDialog.getOpenFileName(
            self.mw,
            "Select Stock File",
            "",
            "CSV files (*.csv);;All Files (*)"
        )

        if not filepath:
            return

        self.mw.stock_file_path = filepath
        self.mw.stock_file_path_label.setText(os.path.basename(filepath))
        self.log.info(f"Stock file selected: {filepath}")

        # Get delimiter from config
        config = self.mw.active_profile_config
        delimiter = config.get("settings", {}).get("stock_csv_delimiter", ";")

        # Try to load CSV with correct delimiter to verify it's readable
        try:
            stock_df = pd.read_csv(filepath, delimiter=delimiter)
            self.log.info(f"Loaded stock CSV with delimiter '{delimiter}': {len(stock_df)} rows")

        except Exception as e:
            self.log.error(f"Failed to load stock CSV: {e}")
            QMessageBox.critical(
                self.mw,
                "File Load Error",
                f"Failed to load stock file:\n{str(e)}\n\n"
                f"Make sure the delimiter is set correctly in Settings.\n"
                f"Current delimiter: '{delimiter}'"
            )
            return

        # Validate headers
        self.validate_file("stock")
        self.check_files_ready()

    def validate_file(self, file_type):
        """Validates that a selected CSV file contains the required headers.

        It reads the required column names from the client-specific configuration
        and uses `core.validate_csv_headers` to perform the check. The result
        is displayed to the user via a status label (✓ or ✗) with a tooltip
        providing details on failure.

        Args:
            file_type (str): The type of file to validate, either "orders" or
                             "stock".
        """
        # Get client config from main window
        if not self.mw.current_client_id or not self.mw.current_client_config:
            self.log.warning("No client selected or config not loaded")
            return

        client_config = self.mw.current_client_config
        column_mappings = client_config.get("column_mappings", {})

        # Define which internal names are required
        REQUIRED_INTERNAL_ORDERS = ["Order_Number", "SKU", "Quantity", "Shipping_Method"]
        REQUIRED_INTERNAL_STOCK = ["SKU", "Stock"]

        if file_type == "orders":
            path = self.mw.orders_file_path
            label = self.mw.orders_file_status_label
            delimiter = ","

            # Get CSV column names from v2 mappings
            orders_mappings = column_mappings.get("orders", {})

            # Backward compatibility: check for v1 format
            if not orders_mappings and "orders_required" in column_mappings:
                # V1 format - use default Shopify column names
                required_cols = ["Name", "Lineitem sku", "Lineitem quantity", "Shipping Method"]
            else:
                # V2 format - extract CSV column names that map to required internal names
                required_cols = [csv_col for csv_col, internal in orders_mappings.items()
                                if internal in REQUIRED_INTERNAL_ORDERS]

        else:  # stock
            path = self.mw.stock_file_path
            label = self.mw.stock_file_status_label
            delimiter = client_config.get("settings", {}).get("stock_csv_delimiter", ";")

            # Get CSV column names from v2 mappings
            stock_mappings = column_mappings.get("stock", {})

            # Backward compatibility: check for v1 format
            if not stock_mappings and "stock_required" in column_mappings:
                # V1 format - use default Bulgarian column names
                required_cols = ["Артикул", "Наличност"]
            else:
                # V2 format - extract CSV column names that map to required internal names
                required_cols = [csv_col for csv_col, internal in stock_mappings.items()
                                if internal in REQUIRED_INTERNAL_STOCK]

        if not path:
            self.log.warning(f"Validation skipped for '{file_type}': path is missing.")
            return

        self.log.info(f"Validating '{file_type}' file: {path}")
        is_valid, missing_cols = core.validate_csv_headers(path, required_cols, delimiter)

        if is_valid:
            label.setText("✓")
            label.setStyleSheet("color: green; font-weight: bold;")
            label.setToolTip("File is valid.")
            self.log.info(f"'{file_type}' file is valid.")
        else:
            label.setText("✗")
            label.setStyleSheet("color: red; font-weight: bold;")
            tooltip_text = f"Missing columns: {', '.join(missing_cols)}"
            label.setToolTip(tooltip_text)
            self.log.warning(f"'{file_type}' file is invalid. {tooltip_text}")

    def check_files_ready(self):
        """Checks if both orders and stock files are selected and valid.

        If both files have been selected and have passed validation, this
        method enables the main 'Run Analysis' button in the UI. Otherwise,
        the button remains disabled.
        """
        orders_ok = self.mw.orders_file_path and self.mw.orders_file_status_label.text() == "✓"
        stock_ok = self.mw.stock_file_path and self.mw.stock_file_status_label.text() == "✓"
        if orders_ok and stock_ok:
            self.mw.run_analysis_button.setEnabled(True)
            self.log.info("Both files are validated and ready for analysis.")
        else:
            self.mw.run_analysis_button.setEnabled(False)
