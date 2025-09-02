from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from PySide6.QtGui import QColor
import pandas as pd

class PandasModel(QAbstractTableModel):
    """A model to interface a pandas DataFrame with a QTableView."""
    def __init__(self, dataframe: pd.DataFrame, parent=None):
        super().__init__(parent)
        self._dataframe = dataframe
        # Define colors for styling
        self.colors = {
            "Fulfillable": QColor("#2A4B3A"),
            "NotFulfillable": QColor("#5E2E2E"),
            "SystemNoteHighlight": QColor("#756B0D")
        }

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._dataframe)

    def columnCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._dataframe.columns)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        row = index.row()

        if role == Qt.ItemDataRole.DisplayRole:
            try:
                value = self._dataframe.iloc[row, index.column()]
                if pd.isna(value):
                    return ""
                return str(value)
            except IndexError:
                return None

        if role == Qt.ItemDataRole.BackgroundRole:
            try:
                # Check for system note first, as it takes precedence
                if 'System_note' in self._dataframe.columns and pd.notna(self._dataframe.iloc[row]['System_note']) and self._dataframe.iloc[row]['System_note']:
                    return self.colors["SystemNoteHighlight"]

                # Otherwise, color based on fulfillment status
                if 'Order_Fulfillment_Status' in self._dataframe.columns:
                    status = self._dataframe.iloc[row]['Order_Fulfillment_Status']
                    if status == "Fulfillable":
                        return self.colors["Fulfillable"]
                    elif status == "Not Fulfillable":
                        return self.colors["NotFulfillable"]
            except (IndexError, KeyError):
                return None # In case columns are missing

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self._dataframe.columns[section])
            if orientation == Qt.Orientation.Vertical:
                return str(section + 1)
        return None
