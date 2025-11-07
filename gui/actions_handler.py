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
        """Opens the settings window for the active client."""
        if not self.mw.current_client_id:
            QMessageBox.warning(
                self.mw,
                "No Client Selected",
                "Please select a client first."
            )
            return

        # Reload fresh config
        try:
            fresh_config = self.mw.profile_manager.load_shopify_config(
                self.mw.current_client_id
            )

            if not fresh_config:
                raise Exception("Failed to load configuration")

        except Exception as e:
            QMessageBox.critical(
                self.mw,
                "Error",
                f"Failed to load settings:\n{str(e)}"
            )
            return

        # Open settings with fresh data
        from gui.settings_window_pyside import SettingsWindow

        settings_win = SettingsWindow(
            client_id=self.mw.current_client_id,
            client_config=fresh_config,  # Fresh data
            profile_manager=self.mw.profile_manager,
            analysis_df=self.mw.analysis_results_df,
            parent=self.mw
        )

        if settings_win.exec():
            # Settings saved successfully
            try:
                # Reload config in MainWindow
                self.mw.active_profile_config = self.mw.profile_manager.load_shopify_config(
                    self.mw.current_client_id
                )

                # Re-validate files with new settings
                self.log.info("Re-validating files with updated settings...")

                if self.mw.orders_file_path:
                    self.mw.file_handler.validate_file("orders")

                if self.mw.stock_file_path:
                    self.mw.file_handler.validate_file("stock")

                # Success message
                QMessageBox.information(
                    self.mw,
                    "Settings Updated",
                    "Settings saved successfully!\n\n"
                    "Files have been re-validated with new configuration."
                )

                self.log.info("Settings updated and files re-validated successfully")

            except Exception as e:
                self.log.error(f"Error updating config after save: {e}")
                QMessageBox.warning(
                    self.mw,
                    "Warning",
                    f"Settings were saved, but failed to reload configuration:\n{str(e)}\n\n"
                    "Please restart the application."
                )

    def open_report_selection_dialog(self, report_type):
        """Opens dialog for selecting which reports to generate.

        Args:
            report_type (str): Either "packing_lists" or "stock_exports"
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

        session_path = self.mw.session_path

        if not session_path:
            QMessageBox.warning(
                self.mw,
                "No Active Session",
                "No active session. Please create a new session or open an existing one."
            )
            return

        # ✅ FIX: Reload fresh config before opening dialog
        try:
            fresh_config = self.mw.profile_manager.load_shopify_config(
                self.mw.current_client_id
            )

            if not fresh_config:
                raise Exception("Failed to load configuration")

            # Update main window config
            self.mw.active_profile_config = fresh_config

        except Exception as e:
            QMessageBox.critical(
                self.mw,
                "Configuration Error",
                f"Failed to load client configuration:\n{str(e)}"
            )
            return

        # ✅ FIX: Use correct config keys
        if report_type == "packing_lists":
            config_key = "packing_list_configs"  # Correct key
        else:  # stock_exports
            config_key = "stock_export_configs"  # Correct key

        report_configs = fresh_config.get(config_key, [])

        if not report_configs:
            QMessageBox.information(
                self.mw,
                "No Reports Configured",
                f"No {report_type.replace('_', ' ')} are configured for this client.\n\n"
                f"Please configure them in Client Settings."
            )
            return

        # Open selection dialog
        from gui.report_selection_dialog import ReportSelectionDialog

        dialog = ReportSelectionDialog(report_type, report_configs, self.mw)
        dialog.reportSelected.connect(
            lambda rc: self._generate_single_report(report_type, rc, session_path)
        )
        dialog.exec()

    def _apply_filters(self, df, filters):
        """Apply filters from report config to DataFrame.

        Args:
            df: DataFrame to filter
            filters: List of filter dicts with 'field', 'operator', 'value'

        Returns:
            Filtered DataFrame
        """
        filtered_df = df.copy()

        for filt in filters:
            field = filt.get("field")
            operator = filt.get("operator")
            value = filt.get("value")

            if not field or field not in filtered_df.columns:
                continue

            try:
                if operator == "==":
                    filtered_df = filtered_df[filtered_df[field] == value]
                elif operator == "!=":
                    filtered_df = filtered_df[filtered_df[field] != value]
                elif operator == "in":
                    values = [v.strip() for v in value.split(',')]
                    filtered_df = filtered_df[filtered_df[field].isin(values)]
                elif operator == "not in":
                    values = [v.strip() for v in value.split(',')]
                    filtered_df = filtered_df[~filtered_df[field].isin(values)]
                elif operator == "contains":
                    filtered_df = filtered_df[filtered_df[field].astype(str).str.contains(value, na=False)]
            except Exception as e:
                self.log.warning(f"Failed to apply filter {field} {operator} {value}: {e}")

        return filtered_df

    def _create_analysis_json(self, df):
        """Convert DataFrame to analysis_data.json format for Packing Tool.

        Args:
            df: Filtered DataFrame with orders data

        Returns:
            dict: JSON structure for Packing Tool
        """
        from datetime import datetime

        orders_data = []

        # Group by Order_Number
        for order_num, group in df.groupby('Order_Number'):
            items = []
            for _, row in group.iterrows():
                items.append({
                    "sku": str(row.get('SKU', '')),
                    "product_name": str(row.get('Product_Name', '')),
                    "quantity": int(row.get('Quantity', 1)),
                    "stock_status": str(row.get('Order_Fulfillment_Status', ''))
                })

            # Get order-level info from first row
            first_row = group.iloc[0]

            orders_data.append({
                "order_number": str(order_num),
                "order_type": str(first_row.get('Order_Type', '')),
                "items": items,
                "courier": str(first_row.get('Shipping_Provider', '')),
                "destination": str(first_row.get('Destination_Country', '')),
                "tags": first_row.get('Tags', '').split(',') if first_row.get('Tags') else []
            })

        return {
            "session_id": self.mw.session_path.name if self.mw.session_path else "unknown",
            "created_at": datetime.now().isoformat(),
            "total_orders": len(orders_data),
            "total_items": int(df['Quantity'].sum()) if 'Quantity' in df.columns else len(df),
            "orders": orders_data
        }

    def _generate_single_report(self, report_type, report_config, session_path):
        """Generates a single report (XLSX + JSON for packing lists).

        Args:
            report_type (str): "packing_lists" or "stock_exports"
            report_config (dict): Report configuration
            session_path (Path): Current session directory
        """
        report_name = report_config.get("name", "Unknown")
        self.log.info(f"Generating {report_type}: {report_name}")
        self.mw.log_activity("Report", f"Generating report: {report_name}")

        try:
            # Create output directory
            if report_type == "packing_lists":
                output_dir = os.path.join(session_path, "packing_lists")
            else:  # stock_exports
                output_dir = os.path.join(session_path, "stock_exports")

            os.makedirs(output_dir, exist_ok=True)

            # ========================================
            # APPLY FILTERS
            # ========================================
            filters = report_config.get("filters", [])
            filtered_df = self._apply_filters(self.mw.analysis_results_df, filters)

            if filtered_df.empty:
                QMessageBox.warning(
                    self.mw,
                    "No Data",
                    f"No data matches the filters for report: {report_name}"
                )
                return

            # ========================================
            # GENERATE XLSX
            # ========================================
            base_filename = report_config.get("output_filename", f"{report_name}.xlsx")

            if report_type == "stock_exports":
                # Add timestamp for stock exports
                datestamp = datetime.now().strftime("%Y-%m-%d")
                name, ext = os.path.splitext(os.path.basename(base_filename))
                timestamped_filename = f"{name}_{datestamp}{ext}"
                output_file = os.path.join(output_dir, timestamped_filename)
            else:
                output_file = os.path.join(output_dir, os.path.basename(base_filename))

            # Save to Excel
            try:
                filtered_df.to_excel(output_file, index=False, engine='openpyxl')
                self.log.info(f"Generated XLSX: {output_file}")
            except Exception as e:
                raise Exception(f"Failed to save XLSX: {str(e)}")

            # ========================================
            # GENERATE JSON (packing lists only)
            # ========================================
            if report_type == "packing_lists":
                json_path = os.path.join(output_dir, "analysis_data.json")

                try:
                    analysis_json = self._create_analysis_json(filtered_df)

                    import json
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(analysis_json, f, indent=2, ensure_ascii=False)

                    self.log.info(f"Generated JSON for Packing Tool: {json_path}")

                except Exception as e:
                    self.log.error(f"Failed to generate JSON: {e}")
                    # Don't fail the whole operation if JSON generation fails

            # ========================================
            # SUCCESS MESSAGE
            # ========================================
            self.mw.log_activity("Report", f"Report generated: {output_file}")

            message = f"Report generated successfully:\n\n{os.path.basename(output_file)}\n\nLocation: {output_dir}"

            if report_type == "packing_lists":
                message += f"\n\nJSON file for Packing Tool:\n{json_path}"

            QMessageBox.information(
                self.mw,
                "Report Generated",
                message
            )

        except Exception as e:
            self.log.error(f"Failed to generate report: {e}", exc_info=True)
            QMessageBox.critical(
                self.mw,
                "Report Generation Failed",
                f"Failed to generate report '{report_name}':\n\n{str(e)}"
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
