import os
import json
import logging
from datetime import datetime
import pandas as pd

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox, QInputDialog

from gui.worker import Worker
from shopify_tool import core
from shopify_tool.analysis import recalculate_statistics, toggle_order_fulfillment
from shopify_tool.utils import resource_path
from gui.settings_window_pyside import SettingsWindow
from gui.report_selection_dialog import ReportSelectionDialog
from gui.column_manager_window_pyside import ColumnManagerWindow
from gui.report_builder_window_pyside import ReportBuilderWindow


class ActionsHandler(QObject):
    """Handles application logic triggered by user actions."""

    analysis_finished = Signal(pd.DataFrame)

    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window
        self.log = logging.getLogger(__name__)

    def create_new_session(self):
        """Creates a new session folder for output files."""
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
        """Runs the main analysis in a background thread."""
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
        """Handles the completion of the analysis."""
        self.log.info("Analysis thread finished.")
        success, result_msg, df, stats = result
        if success:
            self.mw.analysis_results_df = df
            self.mw.analysis_stats = stats
            self.analysis_finished.emit(df)  # Emit the signal with the dataframe
            self.mw.log_activity("Analysis", f"Analysis complete. Report saved to: {result_msg}")
        else:
            self.log.error(f"Analysis failed: {result_msg}")
            QMessageBox.critical(self.mw, "Analysis Error", f"An error occurred during analysis:\n{result_msg}")

    def on_task_error(self, error):
        """Handles errors from background tasks."""
        exctype, value, tb = error
        self.log.error(f"An unexpected error occurred in a background task: {value}\n{tb}", exc_info=True)
        msg = f"An unexpected error occurred in a background task:\n{value}\n\nTraceback:\n{tb}"
        QMessageBox.critical(self.mw, "Task Exception", msg)

    def open_settings_window(self):
        """Opens the settings dialog."""
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
        """Opens a dialog to select and generate a report."""
        reports_config = self.mw.config.get(report_type, [])
        if not reports_config:
            msg = f"No {report_type.replace('_', ' ')} configured in settings."
            QMessageBox.information(self.mw, "No Reports", msg)
            return
        dialog = ReportSelectionDialog(report_type, reports_config, self.mw)
        dialog.reportSelected.connect(lambda rc: self.run_report_logic(report_type, rc))
        dialog.exec()

    def run_report_logic(self, report_type, report_config):
        """Runs the report generation in a background thread."""
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
        """Handles the completion of report generation."""
        success, message = result
        if success:
            self.mw.log_activity("Report Generation", message)
            self.log.info(f"Report generated successfully: {message}")
        else:
            self.log.error(f"Report generation failed: {message}")
            QMessageBox.critical(self.mw, "Error", message)

    def toggle_fulfillment_status_for_order(self, order_number):
        """Toggles the fulfillment status of an order."""
        success, result, updated_df = toggle_order_fulfillment(self.mw.analysis_results_df, order_number)
        if success:
            self.mw.analysis_results_df = updated_df
            self.mw.analysis_stats = recalculate_statistics(self.mw.analysis_results_df)
            self.mw._post_analysis_ui_update()
            df = self.mw.analysis_results_df
            new_status = df.loc[df["Order_Number"] == order_number, "Order_Fulfillment_Status"].iloc[0]
            self.mw.log_activity("Manual Edit", f"Order {order_number} status changed to '{new_status}'.")
            self.log.info(f"Order {order_number} status changed to '{new_status}'.")
        else:
            self.log.warning(f"Failed to toggle status for order {order_number}: {result}")
            QMessageBox.critical(self.mw, "Error", result)

    def open_column_manager(self):
        """Opens the column manager dialog."""
        if not self.mw.all_columns:
            QMessageBox.warning(self.mw, "No Data", "Please run an analysis to load data first.")
            return
        dialog = ColumnManagerWindow(self.mw.all_columns, self.mw.visible_columns, self.mw)
        if dialog.exec():
            self.mw.visible_columns = dialog.new_visible_columns
            self.mw.update_data_viewer()
            self.log.info("Column settings applied.")

    def open_report_builder_window(self):
        """Opens the report builder dialog."""
        if self.mw.analysis_results_df.empty:
            QMessageBox.warning(self.mw, "No Data", "Please run an analysis before using the Report Builder.")
            return
        dialog = ReportBuilderWindow(self.mw.analysis_results_df, self.mw)
        dialog.exec()

    def add_tag_manually(self, order_number):
        """Adds a manual tag to an order."""
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
            self.mw._post_analysis_ui_update()
            self.mw.log_activity("Manual Tag", f"Added note '{tag_to_add}' to order {order_number}.")

    def remove_item_from_order(self, row_index):
        """Removes a single item (row) from an order."""
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
            self.mw.analysis_stats = recalculate_statistics(self.mw.analysis_results_df)
            self.mw._post_analysis_ui_update()
            self.mw.log_activity("Data Edit", f"Removed item {sku} from order {order_number}.")

    def remove_entire_order(self, order_number):
        """Removes all items associated with an order number."""
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
            self.mw.analysis_stats = recalculate_statistics(self.mw.analysis_results_df)
            self.mw._post_analysis_ui_update()
            self.mw.log_activity("Data Edit", f"Removed order {order_number}.")
