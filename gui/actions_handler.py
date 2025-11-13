import os
import logging
from datetime import datetime
import pandas as pd

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox, QInputDialog, QDialog

from gui.worker import Worker
from shopify_tool import core
from shopify_tool.analysis import toggle_order_fulfillment
from shopify_tool import packing_lists
from shopify_tool import stock_export
from gui.settings_window_pyside import SettingsWindow
from gui.report_selection_dialog import ReportSelectionDialog


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
        stock_delimiter = self.mw.active_profile_config.get("settings", {}).get("stock_csv_delimiter", ";")
        orders_delimiter = self.mw.active_profile_config.get("settings", {}).get("orders_csv_delimiter", ",")

        worker = Worker(
            core.run_full_analysis,
            self.mw.stock_file_path,
            self.mw.orders_file_path,
            None,  # output_dir_path (not used in session mode)
            stock_delimiter,
            orders_delimiter,
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

            # ========================================
            # NEW: RECORD STATISTICS TO SERVER
            # ========================================
            try:
                from pathlib import Path
                from shared.stats_manager import StatsManager

                self.log.info("Recording analysis statistics to server...")

                stats_mgr = StatsManager(
                    base_path=str(self.mw.profile_manager.base_path)
                )

                # Get session info
                session_name = Path(self.mw.session_path).name if self.mw.session_path else "unknown"

                # Count unique orders and items
                orders_count = len(df['Order_Number'].unique()) if 'Order_Number' in df.columns else 0
                items_count = len(df)

                # Calculate fulfillable orders for metadata
                fulfillable_orders = 0
                if 'Order_Fulfillment_Status' in df.columns:
                    fulfillable_df = df[df['Order_Fulfillment_Status'] == 'Fulfillable']
                    fulfillable_orders = len(fulfillable_df['Order_Number'].unique()) if not fulfillable_df.empty else 0

                # Record to stats
                stats_mgr.record_analysis(
                    client_id=self.mw.current_client_id,
                    session_id=session_name,
                    orders_count=orders_count,
                    metadata={
                        "items_count": items_count,
                        "fulfillable_orders": fulfillable_orders
                    }
                )

                self.log.info(f"Statistics recorded: {orders_count} orders, {items_count} items, {fulfillable_orders} fulfillable")

            except Exception as e:
                # Don't fail the analysis if stats recording fails
                self.log.error(f"Failed to record statistics: {e}", exc_info=True)
                # Continue with normal flow
            # ========================================
            # END STATISTICS RECORDING
            # ========================================
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

            # Handle tags - check if it's a string before splitting
            tags_value = first_row.get('Tags', '')
            if isinstance(tags_value, str) and tags_value.strip():
                tags_list = [t.strip() for t in tags_value.split(',') if t.strip()]
            else:
                tags_list = []

            orders_data.append({
                "order_number": str(order_num),
                "order_type": str(first_row.get('Order_Type', '')),
                "items": items,
                "courier": str(first_row.get('Shipping_Provider', '')),
                "destination": str(first_row.get('Destination_Country', '')),
                "tags": tags_list
            })

        # Extract session name from path (session_path could be string or Path)
        if self.mw.session_path:
            session_id = os.path.basename(str(self.mw.session_path))
        else:
            session_id = "unknown"

        return {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "total_orders": len(orders_data),
            "total_items": int(df['Quantity'].sum()) if 'Quantity' in df.columns else len(df),
            "orders": orders_data
        }

    def _generate_single_report(self, report_type, report_config, session_path):
        """Generates a single report (XLSX + JSON for packing lists).

        Args:
            report_type (str): "packing_lists" or "stock_exports"
            report_config (dict): Report configuration with name, filters, etc.
            session_path (Path): Current session directory
        """
        from pathlib import Path
        import json

        report_name = report_config.get("name", "Unknown")
        self.log.info(f"Generating {report_type}: {report_name}")
        self.mw.log_activity("Report", f"Generating report: {report_name}")

        try:
            # Create output directory
            if report_type == "packing_lists":
                output_dir = Path(session_path) / "packing_lists"
            else:  # stock_exports
                output_dir = Path(session_path) / "stock_exports"

            output_dir.mkdir(parents=True, exist_ok=True)

            # ========================================
            # GET FILTERS AND CONFIG
            # ========================================
            filters = report_config.get("filters", [])

            # ========================================
            # DETERMINE OUTPUT FILENAME
            # ========================================
            base_filename = report_config.get("output_filename", "")

            if not base_filename:
                # Generate default filename
                if report_type == "packing_lists":
                    base_filename = f"{report_name}.xlsx"
                else:
                    # Add timestamp for stock exports
                    datestamp = datetime.now().strftime("%Y-%m-%d")
                    base_filename = f"{report_name}_{datestamp}.xls"

            # Ensure correct extension
            if report_type == "packing_lists":
                if not base_filename.endswith('.xlsx'):
                    base_filename = base_filename.replace('.xls', '.xlsx')
            else:
                if not base_filename.endswith('.xls'):
                    base_filename = base_filename + '.xls'

            output_file = str(output_dir / base_filename)

            # ========================================
            # GENERATE REPORT USING PROPER MODULES
            # ========================================
            if report_type == "packing_lists":
                self.log.info(f"Creating packing list using packing_lists module")

                # Get exclude_skus from config
                exclude_skus = report_config.get("exclude_skus", [])
                self.log.info(f"[EXCLUDE_SKUS] Raw from config: {exclude_skus} (type: {type(exclude_skus)})")

                if isinstance(exclude_skus, str):
                    exclude_skus = [s.strip() for s in exclude_skus.split(',') if s.strip()]
                    self.log.info(f"[EXCLUDE_SKUS] After string split: {exclude_skus}")
                elif not isinstance(exclude_skus, list):
                    exclude_skus = []
                    self.log.warning(f"[EXCLUDE_SKUS] Unexpected type, reset to empty list")

                self.log.info(f"[EXCLUDE_SKUS] Final value passed to packing_lists: {exclude_skus}")

                # Use the proper packing_lists module
                # Pass UNFILTERED DataFrame - the module will apply filters itself
                packing_lists.create_packing_list(
                    analysis_df=self.mw.analysis_results_df,
                    output_file=output_file,
                    report_name=report_name,
                    filters=filters,
                    exclude_skus=exclude_skus
                )

                self.log.info(f"Packing list XLSX created: {output_file}")

                # ========================================
                # CREATE JSON COPY FOR PACKING TOOL
                # ========================================
                json_filename = base_filename.replace('.xlsx', '.json')
                json_path = str(output_dir / json_filename)

                try:
                    # Apply filters to get data for JSON
                    filtered_df = self._apply_filters(self.mw.analysis_results_df, filters)

                    # ========================================
                    # Apply exclude_skus to DataFrame for JSON (same as XLSX)
                    # ========================================
                    if isinstance(exclude_skus, str):
                        exclude_skus_list = [s.strip() for s in exclude_skus.split(',') if s.strip()]
                    elif isinstance(exclude_skus, list):
                        exclude_skus_list = exclude_skus
                    else:
                        exclude_skus_list = []

                    # Create DataFrame without excluded SKUs (same as XLSX)
                    json_df = filtered_df.copy()
                    if exclude_skus_list and not json_df.empty and 'SKU' in json_df.columns:
                        self.log.info(f"[JSON] Excluding SKUs from JSON: {exclude_skus_list}")
                        json_df = json_df[~json_df["SKU"].isin(exclude_skus_list)]
                        self.log.info(f"[JSON] Rows after exclude_skus: {len(json_df)}")

                    if not json_df.empty:
                        analysis_json = self._create_analysis_json(json_df)

                        with open(json_path, 'w', encoding='utf-8') as f:
                            json.dump(analysis_json, f, ensure_ascii=False, indent=2)

                        self.log.info(f"Packing list JSON created (exclude_skus applied): {json_path}")
                    else:
                        self.log.warning(f"Skipping JSON creation - no data after filtering and exclude_skus")

                except Exception as e:
                    self.log.error(f"Failed to create JSON: {e}", exc_info=True)
                    # Don't fail the whole report if JSON fails

            else:  # stock_exports
                self.log.info(f"Creating stock export using stock_export module")

                # Use the proper stock_export module
                # Pass UNFILTERED DataFrame - the module will apply filters itself
                stock_export.create_stock_export(
                    analysis_df=self.mw.analysis_results_df,
                    output_file=output_file,
                    report_name=report_name,
                    filters=filters
                )

                self.log.info(f"Stock export created: {output_file}")

            # ========================================
            # SUCCESS MESSAGE
            # ========================================
            QMessageBox.information(
                self.mw,
                "Report Generated",
                f"Report '{report_name}' generated successfully.\n\n"
                f"Location: {output_file}"
            )

            self.mw.log_activity("Report", f"Generated: {report_name}")

        except Exception as e:
            self.log.error(f"Failed to generate report '{report_name}': {e}", exc_info=True)
            QMessageBox.critical(
                self.mw,
                "Generation Failed",
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

    def show_add_product_dialog(self):
        """Show dialog to add product to order."""
        from gui.add_product_dialog import AddProductDialog

        # Validate prerequisites
        if not hasattr(self.mw, 'analysis_results_df') or self.mw.analysis_results_df is None or self.mw.analysis_results_df.empty:
            QMessageBox.warning(
                self.mw,
                "No Analysis",
                "Please run analysis first before adding products."
            )
            return

        if not hasattr(self.mw, 'stock_df') or self.mw.stock_df is None or self.mw.stock_df.empty:
            QMessageBox.warning(
                self.mw,
                "No Stock Data",
                "Stock file must be loaded to add products."
            )
            return

        # Show dialog
        dialog = AddProductDialog(
            parent=self.mw,
            orders_df=self.mw.analysis_results_df,
            stock_df=self.mw.stock_df
        )

        if dialog.exec() == QDialog.Accepted:
            result = dialog.get_result()
            self._add_product_to_dataframe(result)

    def _add_product_to_dataframe(self, product_data):
        """
        Add manually added product to analysis DataFrame.

        Args:
            product_data: dict {
                "order_number": str,
                "sku": str,
                "product_name": str,
                "quantity": int
            }
        """
        import pandas as pd

        # Get existing row as template
        existing_rows = self.mw.analysis_results_df[
            self.mw.analysis_results_df["Order_Number"] == product_data["order_number"]
        ]

        if existing_rows.empty:
            logger.error(f"Order {product_data['order_number']} not found")
            QMessageBox.warning(
                self.mw,
                "Order Not Found",
                f"Order {product_data['order_number']} not found in analysis data."
            )
            return

        template_row = existing_rows.iloc[0].copy()

        # Create new row
        new_row = template_row.copy()
        new_row["SKU"] = product_data["sku"]
        new_row["Product_Name"] = product_data["product_name"]
        new_row["Warehouse_Name"] = product_data["product_name"]  # Same as Product_Name for manual additions
        new_row["Quantity"] = product_data["quantity"]
        new_row["Source"] = "Manual"  # Mark as manual addition
        new_row["Order_Fulfillment_Status"] = "Pending"  # Mark as pending

        # Lookup stock value
        stock_row = self.mw.stock_df[self.mw.stock_df["SKU"] == product_data["sku"]]
        if not stock_row.empty:
            new_row["Stock"] = stock_row.iloc[0]["Stock"]
            new_row["Final_Stock"] = stock_row.iloc[0]["Stock"]  # Will be updated on re-run
        else:
            new_row["Stock"] = 0
            new_row["Final_Stock"] = 0

        # Append to DataFrame
        self.mw.analysis_results_df = pd.concat(
            [self.mw.analysis_results_df, pd.DataFrame([new_row])],
            ignore_index=True
        )

        logger.info(f"Added product {product_data['sku']} to order {product_data['order_number']}")

        # Save to session
        self._save_manual_addition(product_data)

        # Emit data changed signal to refresh UI
        self.data_changed.emit()

        # Log activity
        self.mw.log_activity(
            "Manual Addition",
            f"Added {product_data['sku']} ({product_data['quantity']}x) to order {product_data['order_number']}"
        )

        # Show success message
        QMessageBox.information(
            self.mw,
            "Product Added",
            f"Product {product_data['sku']} added to order {product_data['order_number']}.\n\n"
            "Note: You may want to re-run analysis to update fulfillment status."
        )

    def _save_manual_addition(self, product_data):
        """Save manual addition to session file."""
        import json
        import os
        from datetime import datetime

        if not hasattr(self.mw, 'session_path') or not self.mw.session_path:
            logger.warning("No active session, manual addition not saved")
            return

        # Path to manual_additions.json
        additions_file = os.path.join(self.mw.session_path, "manual_additions.json")

        # Load existing additions
        if os.path.exists(additions_file):
            try:
                with open(additions_file, 'r', encoding='utf-8') as f:
                    additions = json.load(f)
            except Exception as e:
                logger.error(f"Error loading manual additions: {e}")
                additions = []
        else:
            additions = []

        # Add new entry
        additions.append({
            "order_number": product_data["order_number"],
            "sku": product_data["sku"],
            "product_name": product_data["product_name"],
            "quantity": product_data["quantity"],
            "timestamp": datetime.now().isoformat()
        })

        # Save back
        try:
            with open(additions_file, 'w', encoding='utf-8') as f:
                json.dump(additions, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved manual addition to {additions_file}")
        except Exception as e:
            logger.error(f"Error saving manual additions: {e}")
