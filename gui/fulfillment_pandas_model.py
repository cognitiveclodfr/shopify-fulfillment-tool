from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from PySide6.QtGui import QColor
import pandas as pd

class FulfillmentPandasModel(QAbstractTableModel):
    """
    A Qt model to interface a pandas DataFrame with the Fulfillment Window's QTableView.
    This model is specialized to handle the state of the packing process.
    """
    def __init__(self, dataframe: pd.DataFrame, parent=None):
        super().__init__(parent)
        self._dataframe = dataframe.copy()
        # Add 'Packed' and 'Status' columns if they don't exist
        if 'Packed' not in self._dataframe.columns:
            self._dataframe['Packed'] = 0
        if 'Status' not in self._dataframe.columns:
            self._dataframe['Status'] = 'Pending' # Pending, Packed

        self.colors = {
            "Pending": QColor("#FFFFFF"),  # White
            "Packed": QColor("#90EE90"),  # LightGreen
        }

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._dataframe)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self._dataframe.columns)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        row = index.row()
        col_name = self._dataframe.columns[index.column()]

        if role == Qt.ItemDataRole.DisplayRole:
            value = self._dataframe.iloc[row, index.column()]
            return str(value)

        if role == Qt.ItemDataRole.BackgroundRole:
            status = self._dataframe.iloc[row]['Status']
            return self.colors.get(status, QColor("#FFFFFF"))

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self._dataframe.columns[section])
            if orientation == Qt.Orientation.Vertical:
                return str(section + 1)
        return None

    def setData(self, index: QModelIndex, value, role=Qt.ItemDataRole.EditRole) -> bool:
        if role == Qt.ItemDataRole.EditRole:
            row = index.row()
            col = index.column()
            self._dataframe.iloc[row, col] = value
            self.dataChanged.emit(index, index, [role])

            # Update status based on Packed vs Quantity
            if 'Packed' in self._dataframe.columns and 'Quantity' in self._dataframe.columns:
                packed_val = self._dataframe.iloc[row]['Packed']
                quantity_val = self.get_data_by_row_colname(row, 'Quantity') #self._dataframe.iloc[row]['Quantity']

                if packed_val >= quantity_val:
                    self._dataframe.iloc[row, self._dataframe.columns.get_loc('Status')] = 'Packed'
                else:
                    self._dataframe.iloc[row, self._dataframe.columns.get_loc('Status')] = 'Pending'

                # Emit dataChanged for the whole row to trigger background color update
                self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))

            return True
        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        return super().flags(index) | Qt.ItemFlag.ItemIsEditable

    def get_data_by_row_colname(self, row, col_name):
        try:
            col_idx = self._dataframe.columns.get_loc(col_name)
            return self._dataframe.iloc[row, col_idx]
        except (KeyError, IndexError):
            return None

    def get_row_by_sku(self, sku):
        try:
            return self._dataframe.index[self._dataframe['SKU'] == sku].tolist()
        except (KeyError, IndexError):
            return []

    def get_dataframe(self):
        return self._dataframe
