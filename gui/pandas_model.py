from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
import pandas as pd

class PandasModel(QAbstractTableModel):
    """A model to interface a pandas DataFrame with a QTableView."""
    def __init__(self, dataframe: pd.DataFrame, parent=None):
        super().__init__(parent)
        self._dataframe = dataframe

    def rowCount(self, parent=QModelIndex()) -> int:
        """Return the number of rows in the DataFrame."""
        if parent.isValid():
            return 0
        return len(self._dataframe)

    def columnCount(self, parent=QModelIndex()) -> int:
        """Return the number of columns in the DataFrame."""
        if parent.isValid():
            return 0
        return len(self._dataframe.columns)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        """Return data for a specific cell."""
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None

        try:
            value = self._dataframe.iloc[index.row(), index.column()]
            # Convert numpy types to native Python types for display
            if pd.isna(value):
                return ""
            if isinstance(value, (int, float)):
                return str(value)
            return str(value)
        except IndexError:
            return None

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.ItemDataRole.DisplayRole):
        """Return header data."""
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self._dataframe.columns[section])
            if orientation == Qt.Orientation.Vertical:
                return str(section + 1)
        return None
