import os
import logging
import pandas as pd
from pathlib import Path
from PySide6.QtWidgets import QFileDialog, QMessageBox

from shopify_tool import core
from shopify_tool import batch_loader


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

        if file_type == "orders":
            path = self.mw.orders_file_path
            label = self.mw.orders_file_status_label
            # Get from client-specific config
            required_cols = client_config.get("column_mappings", {}).get("orders_required", [])
            delimiter = ","
        else:  # stock
            path = self.mw.stock_file_path
            label = self.mw.stock_file_status_label
            required_cols = client_config.get("column_mappings", {}).get("stock_required", [])
            delimiter = client_config.get("settings", {}).get("stock_csv_delimiter", ";")

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

    def select_orders_folder(self):
        """Opens a folder dialog for selecting multiple orders CSV files.

        This method allows users to select a folder containing multiple CSV
        files. All CSV files in the folder will be loaded, validated, and
        merged into a single dataset. Duplicates are removed based on Order_Number.
        """
        folder_path = QFileDialog.getExistingDirectory(
            self.mw,
            "Select Folder with Orders CSV Files",
            "",
            QFileDialog.Option.ShowDirsOnly
        )

        if not folder_path:
            return

        self.log.info(f"Orders folder selected: {folder_path}")

        # Get required columns from client config
        if not self.mw.current_client_id or not self.mw.current_client_config:
            QMessageBox.warning(
                self.mw,
                "No Client Selected",
                "Please select a client before loading files."
            )
            return

        client_config = self.mw.current_client_config
        required_cols = client_config.get("column_mappings", {}).get("orders_required", [])

        try:
            # Load and merge all CSV files from folder
            result = batch_loader.load_orders_from_folder(
                Path(folder_path),
                required_columns=required_cols,
                order_number_column="Order_Number",
                delimiter=","
            )

            # Store the result for later use
            self.mw.orders_folder_path = folder_path
            self.mw.orders_batch_result = result

            # Update UI with summary
            summary = (
                f"{result.files_count} files "
                f"({result.total_orders} orders"
            )
            if result.duplicates_removed > 0:
                summary += f", {result.duplicates_removed} duplicates removed"
            summary += ")"

            self.mw.orders_file_path_label.setText(summary)
            self.mw.orders_file_status_label.setText("✓")
            self.mw.orders_file_status_label.setStyleSheet("color: green; font-weight: bold;")
            self.mw.orders_file_status_label.setToolTip(
                f"Files loaded:\n" + "\n".join(result.files_loaded)
            )

            # Set a flag to indicate folder mode
            self.mw.orders_file_path = folder_path  # Store folder path for compatibility

            self.log.info(f"Batch loading successful: {result.get_summary()}")

            if result.duplicates_removed > 0:
                QMessageBox.information(
                    self.mw,
                    "Duplicates Removed",
                    f"Found and removed {result.duplicates_removed} duplicate orders based on Order_Number.\n\n"
                    f"Total orders loaded: {result.total_orders}"
                )

            self.check_files_ready()

        except Exception as e:
            self.log.error(f"Error loading orders from folder: {str(e)}")
            QMessageBox.critical(
                self.mw,
                "Folder Load Error",
                f"Failed to load orders from folder:\n{str(e)}"
            )

    def select_stock_folder(self):
        """Opens a folder dialog for selecting multiple stock CSV files.

        This method allows users to select a folder containing multiple CSV
        files. All CSV files in the folder will be loaded, validated, and
        merged into a single dataset. Duplicates are removed based on SKU.
        """
        folder_path = QFileDialog.getExistingDirectory(
            self.mw,
            "Select Folder with Stock CSV Files",
            "",
            QFileDialog.Option.ShowDirsOnly
        )

        if not folder_path:
            return

        self.log.info(f"Stock folder selected: {folder_path}")

        # Get required columns and delimiter from client config
        if not self.mw.current_client_id or not self.mw.current_client_config:
            QMessageBox.warning(
                self.mw,
                "No Client Selected",
                "Please select a client before loading files."
            )
            return

        client_config = self.mw.current_client_config
        required_cols = client_config.get("column_mappings", {}).get("stock_required", [])
        delimiter = client_config.get("settings", {}).get("stock_csv_delimiter", ";")

        # Determine the deduplication column (usually SKU)
        dedup_column = client_config.get("column_mappings", {}).get("stock_sku_column", "SKU")

        try:
            # Load and merge all CSV files from folder
            result = batch_loader.load_orders_from_folder(
                Path(folder_path),
                required_columns=required_cols,
                order_number_column=dedup_column,  # Use SKU or equivalent for stock
                delimiter=delimiter
            )

            # Store the result for later use
            self.mw.stock_folder_path = folder_path
            self.mw.stock_batch_result = result

            # Update UI with summary
            summary = (
                f"{result.files_count} files "
                f"({result.total_orders} items"
            )
            if result.duplicates_removed > 0:
                summary += f", {result.duplicates_removed} duplicates removed"
            summary += ")"

            self.mw.stock_file_path_label.setText(summary)
            self.mw.stock_file_status_label.setText("✓")
            self.mw.stock_file_status_label.setStyleSheet("color: green; font-weight: bold;")
            self.mw.stock_file_status_label.setToolTip(
                f"Files loaded:\n" + "\n".join(result.files_loaded)
            )

            # Set a flag to indicate folder mode
            self.mw.stock_file_path = folder_path  # Store folder path for compatibility

            self.log.info(f"Batch loading successful: {result.get_summary()}")

            if result.duplicates_removed > 0:
                QMessageBox.information(
                    self.mw,
                    "Duplicates Removed",
                    f"Found and removed {result.duplicates_removed} duplicate items based on {dedup_column}.\n\n"
                    f"Total items loaded: {result.total_orders}"
                )

            self.check_files_ready()

        except Exception as e:
            self.log.error(f"Error loading stock from folder: {str(e)}")
            QMessageBox.critical(
                self.mw,
                "Folder Load Error",
                f"Failed to load stock from folder:\n{str(e)}"
            )
