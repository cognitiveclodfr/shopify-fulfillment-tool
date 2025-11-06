import os
import logging
from datetime import datetime
import pandas as pd

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox, QInputDialog

from gui.worker import Worker
from shopify_tool import core
from shopify_tool.analysis import toggle_order_fulfillment
from gui.settings_window_pyside import SettingsWindow
from gui.report_selection_dialog import ReportSelectionDialog
from gui.report_builder_window_pyside import ReportBuilderWindow


class ActionsHandler(QObject):
    """Handles application logic triggered by user actions from the UI.

    This class acts as an intermediary between the `MainWindow` (UI) and the
    backend `shopify_tool` modules. It contains slots that are connected to
    UI widget signals (e.g., button clicks). When a signal is received, the
    handler executes the corresponding application logic, such as running an
    analysis, generating a report, or modifying data.

    It uses a `QThreadPool` to run long-running tasks (like analysis and
    report generation) in the background to keep the UI responsive.

    Signals:
        data_changed: Emitted whenever the main analysis DataFrame is modified,
                      signaling the UI to refresh its views.

    Attributes:
        mw (MainWindow): A reference to the main window instance.
        log (logging.Logger): A logger for this class.
    """

    data_changed = Signal()

    def __init__(self, main_window):
        """Initializes the ActionsHandler.

        Args:
            main_window (MainWindow): The main window instance that this
                handler will manage actions for.
        """
        super().__init__()
        self.mw = main_window
        self.log = logging.getLogger(__name__)

    def create_new_session(self):
        """Creates a new session using SessionManager.

        Uses the SessionManager to create a new session for the current client.
        Upon successful creation, it enables the file loading buttons in the UI.
        """
        if not self.mw.current_client_id:
            QMessageBox.warning(
                self.mw,
                "No Client Selected",
                "Please select a client before creating a session."
            )
            return

        try:
            # Use SessionManager to create session
            session_path = self.mw.session_manager.create_session(self.mw.current_client_id)

            self.mw.session_path = session_path
            session_name = os.path.basename(session_path)
            self.mw.session_path_label.setText(f"Session: {session_name}")

            # Enable file loading buttons
            self.mw.load_orders_btn.setEnabled(True)
            self.mw.load_stock_btn.setEnabled(True)

            # Refresh session browser to show the new session
            self.mw.session_browser.refresh_sessions()

            self.mw.log_activity("Session", f"New session created: {session_name}")
            self.log.info(f"New session created: {session_path}")

            QMessageBox.information(
                self.mw,
                "Session Created",
                f"New session created successfully:\n\n{session_name}"
            )

        except Exception as e:
            self.log.error(f"Failed to create new session: {e}", exc_info=True)
            QMessageBox.critical(
                self.mw,
                "Session Error",
                f"Could not create a new session.\n\nError: {e}"
            )

    def run_analysis(self):
        """Triggers the main fulfillment analysis in a background thread.

        It creates a `Worker` to run the `core.run_full_analysis` function,
        preventing the UI from freezing. It connects the worker's signals
        to the appropriate slots for handling completion or errors.
        """
        if not self.mw.session_path:
            QMessageBox.critical(self.mw, "Session Error", "Please create a new session before running an analysis.")
            return

        if not self.mw.current_client_id:
            QMessageBox.critical(self.mw, "Client Error", "No client selected.")
            return

        self.mw.ui_manager.set_ui_busy(True)
        self.log.info("Starting analysis thread.")
        stock_delimiter = self.mw.active_profile_config.get("settings", {}).get("stock_delimiter", ";")

        worker = Worker(
            core.run_full_analysis,
            self.mw.stock_file_path,
            self.mw.orders_file_path,
            None,  # output_dir_path (not used in session mode)
            stock_delimiter,
            self.mw.active_profile_config,
            client_id=self.mw.current_client_id,
            session_manager=self.mw.session_manager,
            profile_manager=self.mw.profile_manager,
            session_path=self.mw.session_path,
        )
        worker.signals.result.connect(self.on_analysis_complete)
        worker.signals.error.connect(self.on_task_error)
        worker.signals.finished.connect(lambda: self.mw.ui_manager.set_ui_busy(False))
        self.mw.threadpool.start(worker)

    def on_analysis_complete(self, result):
        """Handles the 'result' signal from the analysis worker thread.

        If the analysis was successful, it updates the main DataFrame,
        emits the `data_changed` signal to refresh the UI, and logs the
        activity. If it failed, it displays a critical error message.

        Args:
            result (tuple): The tuple returned by `core.run_full_analysis`.
        """
        self.log.info("Analysis thread finished.")
        success, result_msg, df, stats = result
        if success:
            self.mw.analysis_results_df = df
            self.mw.analysis_stats = stats
            self.data_changed.emit()
            self.mw.log_activity("Analysis", f"Analysis complete. Report saved to: {result_msg}")
        else:
            self.log.error(f"Analysis failed: {result_msg}")
            QMessageBox.critical(self.mw, "Analysis Error", f"An error occurred during analysis:\n{result_msg}")

    def on_task_error(self, error):
        """Handles the 'error' signal from any worker thread.

        Logs the exception and displays a critical error message to the user.

        Args:
            error (tuple): A tuple containing the exception type, value, and
                traceback.
        """
        exctype, value, tb = error
        self.log.error(f"An unexpected error occurred in a background task: {value}\n{tb}", exc_info=True)
        msg = f"An unexpected error occurred in a background task:\n{value}\n\nTraceback:\n{tb}"
        QMessageBox.critical(self.mw, "Task Exception", msg)

    def open_settings_window(self):
        """Opens the settings window for the active client.

        Allows editing client-specific configuration like:
        - Column mappings
        - Filters for packing lists and stock exports
        - Courier mappings
        - Rules and tags
        """
        self.log.info("Opening client settings...")

        # Check if client is selected
        if not self.mw.current_client_id:
            QMessageBox.warning(
                self.mw,
                "No Client Selected",
                "Please select a client before opening settings."
            )
            return

        # Load current client config
        try:
            client_config = self.mw.profile_manager.load_shopify_config(
                self.mw.current_client_id
            )

            if not client_config:
                raise Exception("Failed to load client configuration")

            self.log.info(f"Loaded config for CLIENT_{self.mw.current_client_id}")

        except Exception as e:
            self.log.error(f"Failed to load client config: {e}", exc_info=True)
            QMessageBox.critical(
                self.mw,
                "Error",
                f"Failed to load client configuration:\n\n{str(e)}"
            )
            return

        # Open settings dialog
        try:
            settings_win = SettingsWindow(
                client_id=self.mw.current_client_id,
                client_config=client_config,
                profile_manager=self.mw.profile_manager,
                analysis_df=self.mw.analysis_results_df,
                parent=self.mw
            )

            # Show dialog and wait for result
            if settings_win.exec():
                # Settings were saved, reload config
                self.log.info("Settings dialog accepted, reloading config...")

                try:
                    self.mw.active_profile_config = self.mw.profile_manager.load_shopify_config(
                        self.mw.current_client_id
                    )

                    self.log.info(f"Config reloaded for CLIENT_{self.mw.current_client_id}")

                    self.mw.log_activity(
                        "Settings",
                        f"Settings for CLIENT_{self.mw.current_client_id} updated successfully."
                    )

                    QMessageBox.information(
                        self.mw,
                        "Settings Saved",
                        "Client settings have been saved successfully."
                    )

                except Exception as e:
                    self.log.error(f"Failed to reload config: {e}", exc_info=True)
                    QMessageBox.warning(
                        self.mw,
                        "Warning",
                        f"Settings were saved but failed to reload:\n\n{str(e)}"
                    )
            else:
                self.log.info("Settings dialog cancelled")

        except Exception as e:
            self.log.error(f"Error opening settings window: {e}", exc_info=True)
            QMessageBox.critical(
                self.mw,
                "Error",
                f"Failed to open settings window:\n\n{str(e)}"
            )

    def open_report_selection_dialog(self, report_type):
        """Opens a dialog to select and generate a pre-configured report.

        Args:
            report_type (str): The key for the report configuration list in
                the main config (e.g., "packing_lists", "stock_exports").
        """
        self.log.info(f"Opening report selection dialog: {report_type}")

        # Validate that analysis has been run
        if self.mw.analysis_results_df is None or self.mw.analysis_results_df.empty:
            QMessageBox.warning(
                self.mw,
                "No Analysis Data",
                "Please run analysis first before generating reports."
            )
            return

        # Validate client and session
        if not self.mw.current_client_id:
            QMessageBox.warning(
                self.mw,
                "No Client Selected",
                "Please select a client."
            )
            return

        # Get current session path (use session_path as current_session_path)
        session_path = self.mw.session_path

        if not session_path:
            QMessageBox.warning(
                self.mw,
                "No Active Session",
                "No active session. Please create a new session or open an existing one."
            )
            return

        # Get client config
        client_config = self.mw.active_profile_config

        if not client_config:
            QMessageBox.warning(
                self.mw,
                "Configuration Error",
                "Client configuration not loaded."
            )
            return

        # Get report configs from client config
        report_configs = client_config.get(report_type, [])

        if not report_configs:
            QMessageBox.information(
                self.mw,
                "No Reports Configured",
                f"No {report_type.replace('_', ' ')} are configured for this client.\n"
                f"Please configure them in Client Settings."
            )
            return

        # Open selection dialog
        dialog = ReportSelectionDialog(report_type, report_configs, self.mw)
        dialog.reportSelected.connect(lambda rc: self._generate_single_report(report_type, rc, session_path))
        dialog.exec()

    def _generate_single_report(self, report_type, report_config, session_path):
        """Generates a single report synchronously.

        Args:
            report_type (str): The type of report to generate ("packing_lists" or "stock_exports").
            report_config (dict): The specific configuration for the selected report.
            session_path (str): The path to the current session directory.
        """
        report_name = report_config.get("name", "Unknown")
        self.log.info(f"Generating {report_type}: {report_name}")
        self.mw.log_activity("Report", f"Generating report: {report_name}")

        try:
            # Create output directory based on report type
            if report_type == "packing_lists":
                output_dir = os.path.join(session_path, "packing_lists")
            else:  # stock_exports
                output_dir = os.path.join(session_path, "stock_exports")

            os.makedirs(output_dir, exist_ok=True)

            # Build output filename
            if report_type == "packing_lists":
                base_filename = report_config.get("output_filename", f"{report_name}.xlsx")
                output_file = os.path.join(output_dir, os.path.basename(base_filename))
            else:  # stock_exports
                base_filename = report_config.get("output_filename", f"{report_name}.xls")
                datestamp = datetime.now().strftime("%Y-%m-%d")
                name, ext = os.path.splitext(os.path.basename(base_filename))
                timestamped_filename = f"{name}_{datestamp}{ext}"
                output_file = os.path.join(output_dir, timestamped_filename)

            # Create a copy of config with updated output path
            report_config_copy = report_config.copy()
            report_config_copy["output_filename"] = output_file

            # Generate report
            if report_type == "packing_lists":
                success, message = core.create_packing_list_report(
                    self.mw.analysis_results_df,
                    report_config_copy
                )
            else:  # stock_exports
                success, message = core.create_stock_export_report(
                    self.mw.analysis_results_df,
                    report_config_copy
                )

            if success:
                self.log.info(f"Generated {report_name}: {output_file}")
                self.mw.log_activity("Report", f"Report generated: {output_file}")
                QMessageBox.information(
                    self.mw,
                    "Report Generated",
                    f"Report generated successfully:\n\n{os.path.basename(output_file)}\n\nLocation: {output_dir}"
                )
            else:
                self.log.error(f"Failed to generate {report_name}: {message}")
                QMessageBox.critical(
                    self.mw,
                    "Generation Failed",
                    f"Failed to generate report:\n\n{message}"
                )

        except Exception as e:
            self.log.error(f"Exception generating {report_name}: {e}", exc_info=True)
            QMessageBox.critical(
                self.mw,
                "Error",
                f"An error occurred while generating the report:\n\n{str(e)}"
            )


    def toggle_fulfillment_status_for_order(self, order_number):
        """Toggles the fulfillment status of all items in a given order.

        Calls the `analysis.toggle_order_fulfillment` function and updates
        the UI if the change is successful.

        Args:
            order_number (str): The order number to modify.
        """
        success, result, updated_df = toggle_order_fulfillment(self.mw.analysis_results_df, order_number)
        if success:
            self.mw.analysis_results_df = updated_df
            self.data_changed.emit()
            new_status = updated_df.loc[updated_df["Order_Number"] == order_number, "Order_Fulfillment_Status"].iloc[0]
            self.mw.log_activity("Manual Edit", f"Order {order_number} status changed to '{new_status}'.")
            self.log.info(f"Order {order_number} status changed to '{new_status}'.")
        else:
            self.log.warning(f"Failed to toggle status for order {order_number}: {result}")
            QMessageBox.critical(self.mw, "Error", result)

    def open_report_builder_window(self):
        """Opens the custom report builder dialog window."""
        if self.mw.analysis_results_df.empty:
            QMessageBox.warning(self.mw, "No Data", "Please run an analysis before using the Report Builder.")
            return
        dialog = ReportBuilderWindow(self.mw.analysis_results_df, self.mw)
        dialog.exec()

    def add_tag_manually(self, order_number):
        """Opens a dialog to add a manual tag to an order's 'Status_Note'.

        Args:
            order_number (str): The order number to add the tag to.
        """
        tag_to_add, ok = QInputDialog.getText(self.mw, "Add Manual Tag", "Enter tag to add:")
        if ok and tag_to_add:
            order_rows_indices = self.mw.analysis_results_df[
                self.mw.analysis_results_df["Order_Number"] == order_number
            ].index
            if "Status_Note" not in self.mw.analysis_results_df.columns:
                self.mw.analysis_results_df["Status_Note"] = ""
            for index in order_rows_indices:
                current_notes = self.mw.analysis_results_df.loc[index, "Status_Note"]
                if pd.isna(current_notes) or current_notes == "":
                    new_notes = tag_to_add
                elif tag_to_add not in current_notes.split(","):
                    new_notes = f"{current_notes}, {tag_to_add}"
                else:
                    new_notes = current_notes
                self.mw.analysis_results_df.loc[index, "Status_Note"] = new_notes
            self.data_changed.emit()
            self.mw.log_activity("Manual Tag", f"Added note '{tag_to_add}' to order {order_number}.")

    def remove_item_from_order(self, row_index):
        """Removes a single item (a row) from the analysis DataFrame.

        Args:
            row_index (int): The integer index of the row to remove.
        """
        order_number = self.mw.analysis_results_df.iloc[row_index]["Order_Number"]
        sku = self.mw.analysis_results_df.iloc[row_index]["SKU"]
        reply = QMessageBox.question(
            self.mw,
            "Confirm Delete",
            f"Are you sure you want to remove item {sku} from order {order_number}?\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.mw.analysis_results_df.drop(self.mw.analysis_results_df.index[row_index], inplace=True)
            self.mw.analysis_results_df.reset_index(drop=True, inplace=True)
            self.data_changed.emit()
            self.mw.log_activity("Data Edit", f"Removed item {sku} from order {order_number}.")

    def remove_entire_order(self, order_number):
        """Removes all rows associated with a given order number.

        Args:
            order_number (str): The order number to remove completely.
        """
        reply = QMessageBox.question(
            self.mw,
            "Confirm Delete",
            f"Are you sure you want to remove the entire order {order_number}?\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.mw.analysis_results_df = self.mw.analysis_results_df[
                self.mw.analysis_results_df["Order_Number"] != order_number
            ].reset_index(drop=True)
            self.data_changed.emit()
            self.mw.log_activity("Data Edit", f"Removed order {order_number}.")
