import os
import json
import logging
from datetime import datetime
import pandas as pd

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox, QInputDialog

from gui.worker import Worker
from shopify_tool import core
from shopify_tool.analysis import toggle_order_fulfillment
from shopify_tool.utils import resource_path
from gui.settings_window_pyside import SettingsWindow
from gui.report_selection_dialog import ReportSelectionDialog
from gui.report_builder_window_pyside import ReportBuilderWindow


class ActionsHandler(QObject):
    """Handles application logic triggered by user actions from the main window.

    This class connects user interface events (like button clicks) to the
    backend business logic in the `shopify_tool` module. It orchestrates
    running tasks in background threads, handling results, and updating the UI.

    Attributes:
        data_changed (Signal): A PySide6 signal that is emitted whenever the
            main analysis DataFrame is modified, allowing the UI to refresh.
        mw (MainWindow): A reference to the main application window instance.
        log (logging.Logger): A logger instance for this class.
    """

    data_changed = Signal()

    def __init__(self, main_window):
        """Initializes the ActionsHandler.

        Args:
            main_window (MainWindow): The main application window instance.
        """
        super().__init__()
        self.mw = main_window
        self.log = logging.getLogger(__name__)

    def create_new_session(self):
        """Creates a new, uniquely named session folder for output files.

        The folder is created in the base output directory specified in the
        config. The name is based on the current date and an incrementing
        session number (e.g., '2023-10-27_session_1'). This ensures that
        reports from different runs are kept separate.
        """
        try:
            base_output_dir = self.mw.config["paths"].get("output_dir_stock", "data/output")
            os.makedirs(base_output_dir, exist_ok=True)
            date_str = datetime.now().strftime("%Y-%m-%d")
            session_id = 1
            while True:
                session_path = os.path.join(base_output_dir, f"{date_str}_session_{session_id}")
                if not os.path.exists(session_path):
                    break
                session_id += 1
            os.makedirs(session_path, exist_ok=True)
            self.mw.session_path = session_path
            self.mw.session_path_label.setText(f"Current Session: {os.path.basename(self.mw.session_path)}")
            self.mw.load_orders_btn.setEnabled(True)
            self.mw.load_stock_btn.setEnabled(True)
            self.mw.log_activity("Session", f"New session started. Output: {self.mw.session_path}")
        except Exception as e:
            self.log.error(f"Failed to create new session: {e}", exc_info=True)
            QMessageBox.critical(self.mw, "Session Error", f"Could not create a new session folder.\nError: {e}")

    def run_analysis(self):
        """Runs the main analysis in a background thread.

        This method validates that a session has been created, then creates a
        `Worker` thread to execute the `core.run_full_analysis` function.
        Running the analysis in a separate thread prevents the GUI from
        freezing during the potentially long-running operation. The worker's
        signals are connected to the appropriate completion and error handlers.
        """
        if not self.mw.session_path:
            QMessageBox.critical(self.mw, "Session Error", "Please create a new session before running an analysis.")
            return
        self.mw.ui_manager.set_ui_busy(True)
        self.log.info("Starting analysis thread.")
        stock_delimiter = self.mw.config["settings"]["stock_csv_delimiter"]
        worker = Worker(
            core.run_full_analysis,
            self.mw.stock_file_path,
            self.mw.orders_file_path,
            self.mw.session_path,
            stock_delimiter,
            self.mw.config,
        )
        worker.signals.result.connect(self.on_analysis_complete)
        worker.signals.error.connect(self.on_task_error)
        worker.signals.finished.connect(lambda: self.mw.ui_manager.set_ui_busy(False))
        self.mw.threadpool.start(worker)

    def on_analysis_complete(self, result):
        """Handles the successful completion of the analysis background task.

        This method is a slot connected to the `result` signal of the analysis
        worker. It unpacks the results, updates the main window's DataFrame
        and statistics attributes, and emits the `data_changed` signal to
        trigger a UI refresh. If the analysis was not successful, it shows
        an error message.

        Args:
            result (tuple): The tuple returned by `core.run_full_analysis`,
                containing the success status, a result message, the analysis
                DataFrame, and statistics.
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
        """Handles uncaught exceptions from background tasks.

        This method is a slot connected to the `error` signal of a `Worker`
        thread. It logs the exception and displays a critical error message
        box to the user with the traceback information.

        Args:
            error (tuple): A tuple containing the exception type, value, and
                traceback object.
        """
        exctype, value, tb = error
        self.log.error(f"An unexpected error occurred in a background task: {value}\n{tb}", exc_info=True)
        msg = f"An unexpected error occurred in a background task:\n{value}\n\nTraceback:\n{tb}"
        QMessageBox.critical(self.mw, "Task Exception", msg)

    def open_settings_window(self):
        """Opens the settings dialog.

        This method creates and displays the `SettingsWindow`. If the user
        accepts the dialog (e.g., clicks "Save"), the updated configuration
        data is saved back to the main window's `config` attribute and
        written to the `config.json` file.
        """
        dialog = SettingsWindow(self.mw, self.mw.config, self.mw.analysis_results_df)
        if dialog.exec():
            self.mw.config = dialog.config_data
            try:
                with open(self.mw.config_path, "w", encoding="utf-8") as f:
                    json.dump(self.mw.config, f, indent=2, ensure_ascii=False)
                self.mw.log_activity("Settings", "Settings saved successfully.")
                self.log.info("Settings saved.")
            except Exception as e:
                self.log.error(f"Failed to save settings: {e}", exc_info=True)
                QMessageBox.critical(self.mw, "Error", f"Failed to write settings to file: {e}")

    def open_report_selection_dialog(self, report_type):
        """Opens a dialog for the user to select and generate a report.

        Based on the `report_type`, this method retrieves the relevant list
        of report configurations (e.g., 'packing_lists' or 'stock_exports')
        and displays them in a `ReportSelectionDialog`. It connects the
        dialog's `reportSelected` signal to the `run_report_logic` method
        to trigger the generation of the chosen report.

        Args:
            report_type (str): The key for the report configurations in the
                main config file (e.g., 'packing_lists').
        """
        reports_config = self.mw.config.get(report_type, [])
        if not reports_config:
            msg = f"No {report_type.replace('_', ' ')} configured in settings."
            QMessageBox.information(self.mw, "No Reports", msg)
            return
        dialog = ReportSelectionDialog(report_type, reports_config, self.mw)
        dialog.reportSelected.connect(lambda rc: self.run_report_logic(report_type, rc))
        dialog.exec()

    def run_report_logic(self, report_type, report_config):
        """Runs the appropriate report generation logic in a background thread.

        This method is called when a user selects a report from the
        `ReportSelectionDialog`. It creates a `Worker` thread to execute either
        `core.create_packing_list_report` or `core.create_stock_export_report`
        based on the `report_type`. This keeps the GUI responsive while
        reports are being generated.

        Args:
            report_type (str): The type of report to generate ('packing_lists'
                or 'stock_exports').
            report_config (dict): The specific configuration dictionary for the
                chosen report.
        """
        if not self.mw.session_path:
            QMessageBox.critical(self.mw, "Session Error", "Please create a new session before generating reports.")
            return
        self.mw.log_activity("Report", f"Generating report: {report_config.get('name')}")
        self.log.info(f"Starting report generation for '{report_config.get('name')}'")
        if report_type == "packing_lists":
            relative_path = report_config.get("output_filename", "default_packing_list.xlsx")
            output_file = os.path.join(self.mw.session_path, os.path.basename(relative_path))
            report_config_copy = report_config.copy()
            report_config_copy["output_filename"] = output_file
            worker = Worker(
                core.create_packing_list_report,
                analysis_df=self.mw.analysis_results_df,
                report_config=report_config_copy,
            )
        elif report_type == "stock_exports":
            templates_path = resource_path(self.mw.config["paths"]["templates"])
            worker = Worker(
                core.create_stock_export_report,
                analysis_df=self.mw.analysis_results_df,
                report_config=report_config,
                templates_path=templates_path,
                output_path=self.mw.session_path,
            )
        else:
            QMessageBox.critical(self.mw, "Error", "Unknown report type.")
            return
        worker.signals.result.connect(self.on_report_generation_complete)
        worker.signals.error.connect(self.on_task_error)
        self.mw.threadpool.start(worker)

    def on_report_generation_complete(self, result):
        """Handles the completion of a report generation background task.

        This is a slot connected to the `result` signal of a report
        generation worker. It logs the result and, if the generation
        failed, displays an error message to the user.

        Args:
            result (tuple): A tuple containing the success status (bool) and a
                result message (str).
        """
        success, message = result
        if success:
            self.mw.log_activity("Report Generation", message)
            self.log.info(f"Report generated successfully: {message}")
        else:
            self.log.error(f"Report generation failed: {message}")
            QMessageBox.critical(self.mw, "Error", message)

    def toggle_fulfillment_status_for_order(self, order_number):
        """Toggles the fulfillment status of an order and updates the data.

        This method calls the backend `toggle_order_fulfillment` function,
        updates the main analysis DataFrame with the result, and emits the
        `data_changed` signal to refresh the UI. It displays an error message
        if the toggle operation fails (e.g., due to insufficient stock).

        Args:
            order_number (str): The order number for which to toggle the status.
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
        """Opens the custom report builder dialog.

        This method first checks if an analysis has been run. If so, it
        creates and displays the `ReportBuilderWindow`, allowing the user
        to create custom packing lists.
        """
        if self.mw.analysis_results_df.empty:
            QMessageBox.warning(self.mw, "No Data", "Please run an analysis before using the Report Builder.")
            return
        dialog = ReportBuilderWindow(self.mw.analysis_results_df, self.mw)
        dialog.exec()

    def add_tag_manually(self, order_number):
        """Opens a dialog to add a manual tag to all items in an order.

        This method prompts the user for a tag string. If a tag is entered,
        it is appended to the 'Status_Note' column for all rows associated
        with the given order number. It avoids adding duplicate tags.

        Args:
            order_number (str): The order number to which the tag will be added.
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
        """Removes a single item (a single row) from the analysis DataFrame.

        This method asks the user for confirmation before deleting the row.
        If confirmed, the row at the specified index is dropped from the
        DataFrame, and the `data_changed` signal is emitted.

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

        This method asks the user for confirmation. If confirmed, it filters
        the main analysis DataFrame to remove all rows matching the specified
        order number, then emits the `data_changed` signal.

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
