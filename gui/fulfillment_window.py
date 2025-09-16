import sys
import os
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTableView,
    QGroupBox,
    QStyle,
)
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QFont
from PySide6.QtMultimedia import QSoundEffect
import pandas as pd

from shopify_tool.utils import resource_path

from PySide6.QtCore import QAbstractTableModel
from PySide6.QtGui import QBrush, QColor

class FulfillmentTableModel(QAbstractTableModel):
    def __init__(self, data=None):
        super().__init__()
        self._data = data if data is not None else pd.DataFrame()
        self.HEADERS = ["Product Name", "SKU", "Required", "Collected", "Status"]

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()
        col_name = self.HEADERS[col]
        item = self._data.iloc[row]

        if role == Qt.DisplayRole:
            if col_name == "Product Name":
                return str(item.get("Product_Name", ""))
            elif col_name == "SKU":
                return str(item.get("SKU", ""))
            elif col_name == "Required":
                return str(item.get("Quantity", 0))
            elif col_name == "Collected":
                return str(item.get("Collected", 0))
            elif col_name == "Status":
                return str(item.get("Status", ""))
            return None

        if role == Qt.BackgroundRole:
            if item.get("Status") == "Complete":
                return QBrush(QColor("#C8E6C9"))  # A light green color
            return None

        if role == Qt.TextAlignmentRole:
            if col_name in ["Required", "Collected", "Status"]:
                return Qt.AlignCenter
            return None

        if role == Qt.DecorationRole:
            if col_name == "Status" and item.get("Status") == "Complete":
                # Return a standard checkmark icon from the current application style
                return QApplication.style().standardIcon(QStyle.SP_DialogApplyButton)
            return None

        return None

    def load_order(self, order_items_df):
        self.beginResetModel()
        self._data = order_items_df.copy()
        # Initialize packer-specific columns
        self._data["Collected"] = 0
        self._data["Status"] = "Pending"
        self.endResetModel()

    def update_collected_count(self, sku_to_update):
        if self._data.empty:
            return False, "No order loaded."

        matches = self._data[self._data["SKU"] == sku_to_update]
        if matches.empty:
            return False, "Scanned SKU not in this order."

        # Find the first row for this SKU that is not yet complete
        for index, row in matches.iterrows():
            if row["Collected"] < row["Quantity"]:
                self._data.loc[index, "Collected"] += 1

                # Update status if this item is now fully collected
                if self._data.loc[index, "Collected"] == self._data.loc[index, "Quantity"]:
                    self._data.loc[index, "Status"] = "Complete"

                model_index_row = self._data.index.get_loc(index)
                start_index = self.index(model_index_row, 0)
                end_index = self.index(model_index_row, self.columnCount() - 1)
                self.dataChanged.emit(start_index, end_index)
                return True, "Item collected."

        return False, "All units for this SKU already collected."

    def is_order_complete(self):
        if self._data.empty:
            return False
        return all(self._data["Status"] == "Complete")


class FulfillmentWindow(QDialog):
    """
    A UI window for the interactive Packer Mode.

    This dialog allows a warehouse packer to scan an order barcode, view the
    required items, and then scan each item's SKU to verify that the order
    is packed correctly. It provides real-time visual and audio feedback.
    """
    def __init__(self, final_df, parent=None):
        """
        Initializes the FulfillmentWindow.

        Args:
            final_df (pd.DataFrame): The main analysis DataFrame containing all
                                     order and fulfillment data.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.setWindowTitle("Fulfillment Mode")
        self.final_df = final_df
        self.current_order_items = pd.DataFrame()

        # Set a larger size for the window
        self.setMinimumSize(800, 600)

        self._init_ui()
        self._init_sounds()
        self._connect_signals()
        self.reset_ui()

    def _init_sounds(self):
        """Initializes the QSoundEffect objects for audio feedback."""
        self.sounds = {
            "success": QSoundEffect(),
            "error": QSoundEffect(),
            "complete": QSoundEffect(),
        }

        for key, sound_effect in self.sounds.items():
            sound_path = resource_path(f"resources/sounds/{key}.wav")
            if os.path.exists(sound_path):
                sound_effect.setSource(QUrl.fromLocalFile(sound_path))
                sound_effect.setVolume(1.0)
            else:
                # If the file doesn't exist, the sound effect will be invalid and won't play.
                # This prevents crashes if sound files are missing.
                print(f"Warning: Sound file not found at {sound_path}")

    def _init_ui(self):
        """Initializes the user interface widgets and layout."""
        main_layout = QVBoxLayout(self)

        # --- Order Scanning Section ---
        order_group = QGroupBox("Scan Order")
        order_layout = QHBoxLayout(order_group)
        self.order_scan_input = QLineEdit()
        self.order_scan_input.setFont(QFont("Arial", 16))
        self.order_scan_input.setPlaceholderText("Scan Order Barcode...")
        order_layout.addWidget(self.order_scan_input)
        main_layout.addWidget(order_group)

        # --- Order Items Table ---
        table_group = QGroupBox("Order Contents")
        table_layout = QVBoxLayout(table_group)
        self.items_table_view = QTableView()
        self.items_table_view.horizontalHeader().setStretchLastSection(True)
        self.items_table_view.setAlternatingRowColors(True)
        self.items_table_view.setSelectionBehavior(QTableView.SelectRows)
        self.items_table_view.setEditTriggers(QTableView.NoEditTriggers)
        # Set font size for table content
        table_font = QFont()
        table_font.setPointSize(12)
        self.items_table_view.setFont(table_font)
        # Set font size for table header
        header_font = QFont()
        header_font.setPointSize(10)
        header_font.setBold(True)
        self.items_table_view.horizontalHeader().setFont(header_font)

        # Using the new FulfillmentTableModel
        self.items_model = FulfillmentTableModel()
        self.items_table_view.setModel(self.items_model)
        table_layout.addWidget(self.items_table_view)
        main_layout.addWidget(table_group, 1)  # Give table more stretch

        # --- SKU Scanning Section ---
        sku_group = QGroupBox("Scan SKU")
        sku_layout = QHBoxLayout(sku_group)
        self.sku_scan_input = QLineEdit()
        self.sku_scan_input.setFont(QFont("Arial", 16))
        self.sku_scan_input.setPlaceholderText("Scan Item SKU...")
        sku_layout.addWidget(self.sku_scan_input)
        main_layout.addWidget(sku_group)

        # --- Status Bar ---
        self.status_label = QLabel("Scan an order to begin.")
        self.status_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("padding: 10px; border-radius: 5px;")
        main_layout.addWidget(self.status_label)

    def _connect_signals(self):
        """Connects widget signals to handler slots."""
        self.order_scan_input.returnPressed.connect(self.handle_order_scan)
        self.sku_scan_input.returnPressed.connect(self.handle_sku_scan)

    def handle_order_scan(self):
        """Handles the 'returnPressed' signal from the order scan input."""
        order_number = self.order_scan_input.text().strip()
        if not order_number:
            return

        order_items = self.final_df[self.final_df["Order_Number"] == order_number]

        if order_items.empty:
            self.set_status_message(f"Order '{order_number}' not found.", "error")
            self.sounds["error"].play()
            self.order_scan_input.clear()
        else:
            self.current_order_items = order_items
            self.items_model.load_order(self.current_order_items)
            self.items_table_view.resizeColumnsToContents()
            self.set_status_message(f"Order #{order_number} loaded. Scan items.", "info")
            self.order_scan_input.setEnabled(False)
            self.sku_scan_input.setEnabled(True)
            self.sku_scan_input.setFocus()

    def handle_sku_scan(self):
        """Handles the 'returnPressed' signal from the SKU scan input."""
        sku = self.sku_scan_input.text().strip()
        if not sku:
            return

        success, message = self.items_model.update_collected_count(sku)

        if success:
            self.set_status_message(message, "success")
            self.sounds["success"].play()
            if self.items_model.is_order_complete():
                self.handle_order_completion()
        else:
            self.set_status_message(message, "error")
            self.sounds["error"].play()

        self.sku_scan_input.clear()

    def handle_order_completion(self):
        """Handles the logic when all items in an order are collected."""
        order_number = self.current_order_items.iloc[0]["Order_Number"]
        self.set_status_message(f"Order #{order_number} complete!", "success_final")
        self.sku_scan_input.setEnabled(False)
        self.sounds["complete"].play()

        # Reset after a delay
        QTimer.singleShot(3000, self.reset_ui)

    def set_status_message(self, message, style):
        """Updates the status label with a message and color-coding."""
        self.status_label.setText(message)
        if style == "error":
            self.status_label.setStyleSheet("background-color: #FFCDD2; padding: 10px; border-radius: 5px;")
        elif style == "success":
            self.status_label.setStyleSheet("background-color: #C8E6C9; padding: 10px; border-radius: 5px;")
        elif style == "success_final":
            self.status_label.setStyleSheet(
                "background-color: #4CAF50; color: white; padding: 10px; border-radius: 5px;"
            )
        else:  # info
            self.status_label.setStyleSheet("background-color: #BBDEFB; padding: 10px; border-radius: 5px;")


    def reset_ui(self):
        """Resets the UI to its initial state, ready for a new order."""
        self.order_scan_input.clear()
        self.order_scan_input.setEnabled(True)
        self.sku_scan_input.clear()
        self.sku_scan_input.setEnabled(False)
        self.items_model.load_order(pd.DataFrame()) # Clear the model
        self.set_status_message("Scan an order to begin.", "info")
        self.order_scan_input.setFocus()
        self.current_order_items = pd.DataFrame()


if __name__ == '__main__':
    # A simple example to test the window
    app = QApplication(sys.argv)
    # Create a dummy dataframe
    data = {'Order_Number': ['1001', '1001', '1002'],
            'SKU': ['A-1', 'B-2', 'C-3'],
            'Product_Name': ['Product A', 'Product B', 'Product C'],
            'Quantity': [1, 2, 5]}
    dummy_df = pd.DataFrame(data)
    window = FulfillmentWindow(final_df=dummy_df)
    window.show()
    sys.exit(app.exec())
