import sys
import os
import pandas as pd
import time

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QTableView, QLabel, QMessageBox
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gui.fulfillment_pandas_model import FulfillmentPandasModel

class FulfillmentWindow(QWidget):
    """
    A dialog window for the 'Packer Mode' UI.

    This window provides an interface for warehouse packers to scan order barcodes
    and item SKUs to verify and pack orders efficiently.
    """
    def __init__(self, final_df, parent=None):
        """
        Initializes the FulfillmentWindow.

        Args:
            final_df (pd.DataFrame): The DataFrame containing all order data.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.final_df = final_df
        self.current_order_df = pd.DataFrame()
        self.current_order_number = None

        self.setWindowTitle("Packer Mode")
        self.setGeometry(100, 100, 800, 600)

        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        """Initializes the user interface of the window."""
        layout = QVBoxLayout(self)

        # 1. Order scanning input
        self.order_input = QLineEdit()
        self.order_input.setPlaceholderText("Scan Order Barcode...")
        self.order_input.setAlignment(Qt.AlignCenter)
        font = self.order_input.font()
        font.setPointSize(18)
        self.order_input.setFont(font)
        layout.addWidget(self.order_input)

        # 2. Order items table
        self.items_table = QTableView()
        self.items_table.setSortingEnabled(True)
        layout.addWidget(self.items_table)

        # 3. SKU scanning input
        self.sku_input = QLineEdit()
        self.sku_input.setPlaceholderText("Scan SKU Barcode...")
        self.sku_input.setAlignment(Qt.AlignCenter)
        self.sku_input.setFont(font)
        self.sku_input.setEnabled(False)
        layout.addWidget(self.sku_input)

        # 4. Status label
        self.status_label = QLabel("Scan an order to begin.")
        self.status_label.setAlignment(Qt.AlignCenter)
        status_font = self.status_label.font()
        status_font.setPointSize(14)
        status_font.setBold(True)
        self.status_label.setFont(status_font)
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def connect_signals(self):
        """Connects signals to slots."""
        self.order_input.returnPressed.connect(self.load_order)
        self.sku_input.returnPressed.connect(self.scan_sku)

    def load_order(self):
        """Loads an order into the view when an order barcode is scanned."""
        order_number = self.order_input.text()
        if not order_number:
            return

        order_data = self.final_df[self.final_df['Order_Number'] == order_number]

        if order_data.empty:
            self.show_status_message(f"Order '{order_number}' not found.", "red")
            self.order_input.selectAll()
            return

        self.current_order_number = order_number

        # We only need a few columns for the packer view
        columns = ['SKU', 'Product_Name', 'Quantity']
        self.current_order_df = order_data[columns].copy()

        self.model = FulfillmentPandasModel(self.current_order_df)
        self.items_table.setModel(self.model)
        self.items_table.resizeColumnsToContents()

        self.show_status_message(f"Order #{order_number} loaded. Scan SKUs.", "blue")
        self.order_input.setEnabled(False)
        self.sku_input.setEnabled(True)
        self.sku_input.setFocus()

    def scan_sku(self):
        """Processes a scanned SKU."""
        sku = self.sku_input.text()
        if not sku:
            return

        rows = self.model.get_row_by_sku(sku)

        if not rows:
            self.show_status_message(f"SKU '{sku}' not in this order.", "red")
            self.sku_input.clear()
            return

        # For this simple case, we assume one line per SKU.
        # A more complex implementation would handle multiple lines with the same SKU.
        row_index = rows[0]

        quantity_needed = self.model.get_data_by_row_colname(row_index, 'Quantity')
        packed_so_far = self.model.get_data_by_row_colname(row_index, 'Packed')

        if packed_so_far >= quantity_needed:
            self.show_status_message(f"SKU '{sku}' already fully packed.", "orange")
            self.sku_input.clear()
            return

        # Update packed count
        new_packed_value = packed_so_far + 1
        packed_col_idx = self.model.get_dataframe().columns.get_loc('Packed')
        self.model.setData(self.model.index(row_index, packed_col_idx), new_packed_value)

        self.show_status_message(f"Packed SKU: {sku} ({new_packed_value}/{quantity_needed})", "green")
        self.sku_input.clear()

        self.check_order_completion()

    def check_order_completion(self):
        """Checks if all items in the current order have been packed."""
        df = self.model.get_dataframe()
        if all(df['Packed'] >= df['Quantity']):
            self.show_status_message(f"Order #{self.current_order_number} complete!", "green", 3000)
            QTimer.singleShot(3000, self.reset_for_next_order)

    def reset_for_next_order(self):
        """Resets the UI to be ready for the next order scan."""
        self.current_order_number = None
        self.current_order_df = pd.DataFrame()
        self.model = FulfillmentPandasModel(self.current_order_df)
        self.items_table.setModel(self.model)

        self.order_input.clear()
        self.order_input.setEnabled(True)
        self.order_input.setFocus()

        self.sku_input.clear()
        self.sku_input.setEnabled(False)

        self.show_status_message("Scan next order.", "blue")

    def show_status_message(self, message, color, duration=0):
        """Displays a message in the status label with a specified color."""
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {color};")

        if duration > 0:
            QTimer.singleShot(duration, lambda: self.status_label.setText(""))

    def showEvent(self, event):
        """Called when the window is shown."""
        super().showEvent(event)
        self.reset_for_next_order()
