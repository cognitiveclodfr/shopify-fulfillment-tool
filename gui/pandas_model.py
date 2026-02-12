from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from PySide6.QtGui import QColor
import pandas as pd
from gui.theme_manager import get_theme_manager


class PandasModel(QAbstractTableModel):
    """A Qt model to interface a pandas DataFrame with a QTableView.

    This class acts as a wrapper around a pandas DataFrame, allowing it to be
    displayed and manipulated in a Qt view (like QTableView) while adhering to
    the Qt Model/View programming paradigm.

    It handles data retrieval, header information, and custom styling (e.g.,
    row colors) based on the DataFrame's content.

    Attributes:
        _dataframe (pd.DataFrame): The underlying pandas DataFrame.
        colors (dict): A mapping of status strings to QColor objects for row
                       styling.
        enable_checkboxes (bool): Whether to show checkbox column for bulk operations.
    """

    def __init__(self, dataframe: pd.DataFrame, parent=None, enable_checkboxes: bool = False):
        """Initializes the PandasModel.

        Args:
            dataframe (pd.DataFrame): The pandas DataFrame to be modeled.
            parent (QObject, optional): The parent object. Defaults to None.
            enable_checkboxes (bool): Whether to add a checkbox column at position 0.
        """
        super().__init__(parent)
        self._dataframe = dataframe
        self.enable_checkboxes = enable_checkboxes

        # Initialize colors based on current theme
        self._update_colors()

        # Connect to theme changes
        theme_manager = get_theme_manager()
        theme_manager.theme_changed.connect(self._update_colors)

    def rowCount(self, parent=QModelIndex()) -> int:
        """Returns the number of rows in the model."""
        if parent.isValid():
            return 0
        return len(self._dataframe)

    def columnCount(self, parent=QModelIndex()) -> int:
        """Returns the number of columns in the model."""
        if parent.isValid():
            return 0
        # Add 1 for checkbox column if enabled
        if self.enable_checkboxes:
            return len(self._dataframe.columns) + 1
        return len(self._dataframe.columns)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        """Returns the data for a given model index and role.

        This method is called by the view to get the data to display. It
        handles:
        - `DisplayRole`: The text to be displayed in a cell.
        - `BackgroundRole`: The background color of a row, based on the
          'System_note' or 'Order_Fulfillment_Status' columns.

        Args:
            index (QModelIndex): The index of the item to retrieve data for.
            role (Qt.ItemDataRole): The role for which to retrieve data.

        Returns:
            Any: The data for the given role, or None if not applicable.
        """
        if not index.isValid():
            return None

        row = index.row()

        # Handle checkbox column (column 0 when checkboxes enabled)
        # Checkbox rendering is handled by CheckboxDelegate
        if self.enable_checkboxes and index.column() == 0:
            return None

        # Adjust column index if checkboxes enabled
        col_index = index.column()
        if self.enable_checkboxes:
            col_index = index.column() - 1

        if role == Qt.ItemDataRole.DisplayRole:
            try:
                value = self._dataframe.iloc[row, col_index]
                if pd.isna(value):
                    return ""
                return str(value)
            except IndexError:
                return None

        if role == Qt.ItemDataRole.BackgroundRole:
            try:
                # Check for "Repeat" in system note first (yellow highlight)
                # Only highlight for "Repeat", not for other messages like "Cannot fulfill"
                if (
                    "System_note" in self._dataframe.columns
                    and pd.notna(self._dataframe.iloc[row]["System_note"])
                ):
                    system_note = str(self._dataframe.iloc[row]["System_note"])
                    # Check if it's specifically a Repeat order (not just any system note)
                    if "Repeat" in system_note and not system_note.startswith("Cannot fulfill"):
                        return self.colors["SystemNoteHighlight"]

                # Otherwise, color based on fulfillment status
                if "Order_Fulfillment_Status" in self._dataframe.columns:
                    status = self._dataframe.iloc[row]["Order_Fulfillment_Status"]
                    if status == "Fulfillable":
                        return self.colors["Fulfillable"]
                    elif status == "Not Fulfillable":
                        return self.colors["NotFulfillable"]
            except (IndexError, KeyError):
                return None  # In case columns are missing

        if role == Qt.ItemDataRole.ForegroundRole:
            # Return text color for rows with background colors
            # Ensures readability in both light and dark themes
            try:
                # Check if this row has a background color
                if (
                    "System_note" in self._dataframe.columns
                    and pd.notna(self._dataframe.iloc[row]["System_note"])
                ):
                    system_note = str(self._dataframe.iloc[row]["System_note"])
                    if "Repeat" in system_note and not system_note.startswith("Cannot fulfill"):
                        return self.text_colors["SystemNoteHighlight"]

                if "Order_Fulfillment_Status" in self._dataframe.columns:
                    status = self._dataframe.iloc[row]["Order_Fulfillment_Status"]
                    if status == "Fulfillable":
                        return self.text_colors["Fulfillable"]
                    elif status == "Not Fulfillable":
                        return self.text_colors["NotFulfillable"]
            except (IndexError, KeyError):
                return None

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.ItemDataRole.DisplayRole):
        """Returns the header data for the given section and orientation.

        Args:
            section (int): The row or column number.
            orientation (Qt.Orientation): The header orientation (Horizontal
                or Vertical).
            role (Qt.ItemDataRole): The role for which to retrieve data.

        Returns:
            str | None: The header title, or None.
        """
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                # Handle checkbox column header
                if self.enable_checkboxes:
                    if section == 0:
                        return ""  # Checkbox column header (empty or could be "")
                    return str(self._dataframe.columns[section - 1])
                return str(self._dataframe.columns[section])
            if orientation == Qt.Orientation.Vertical:
                return str(section + 1)
        return None

    def get_column_index(self, column_name):
        """Returns the numerical index of a column from its string name.

        Args:
            column_name (str): The name of the column.

        Returns:
            int | None: The index of the column, or None if not found.
        """
        try:
            df_index = self._dataframe.columns.get_loc(column_name)
            # Adjust for checkbox column if enabled
            if self.enable_checkboxes:
                return df_index + 1
            return df_index
        except KeyError:
            return None

    def set_column_order_and_visibility(self, all_columns_in_order, visible_columns):
        """Reorders and filters columns in the underlying DataFrame.

        Note: This method seems to be obsolete or not fully implemented, as
        column visibility is now handled by the view/proxy.

        Args:
            all_columns_in_order (list[str]): A list of all column names in
                the desired order.
            visible_columns (list[str]): A list of columns that should remain
                visible.
        """
        self.beginResetModel()
        existing_columns = [col for col in all_columns_in_order if col in self._dataframe.columns]
        self._dataframe = self._dataframe[existing_columns]
        self.hidden_columns = [col for col in all_columns_in_order if col not in visible_columns]
        self.endResetModel()

    def _update_colors(self):
        """Update row colors based on current theme.

        Sets background and text colors for table rows based on fulfillment status.
        Uses different color palettes for light and dark themes to maintain contrast.
        """
        theme_manager = get_theme_manager()

        if theme_manager.is_dark_theme():
            # Dark theme: dark tinted backgrounds with white text
            self.colors = {
                "Fulfillable": QColor("#1B3A1B"),          # Dark green tint
                "NotFulfillable": QColor("#3A1B1B"),       # Dark red tint
                "SystemNoteHighlight": QColor("#3A3020"),  # Dark orange tint
            }
            self.text_colors = {
                "Fulfillable": QColor("#FFFFFF"),          # White text
                "NotFulfillable": QColor("#FFFFFF"),       # White text
                "SystemNoteHighlight": QColor("#FFFFFF"),  # White text
            }
        else:
            # Light theme: brighter tinted backgrounds with dark text (more visible)
            self.colors = {
                "Fulfillable": QColor("#C8E6C9"),          # Brighter green tint (was #E8F5E9)
                "NotFulfillable": QColor("#FFCDD2"),       # Brighter red tint (was #FFEBEE)
                "SystemNoteHighlight": QColor("#FFE0B2"),  # Brighter orange tint (was #FFF3E0)
            }
            self.text_colors = {
                "Fulfillable": QColor("#1B5E20"),          # Darker green text for contrast
                "NotFulfillable": QColor("#B71C1C"),       # Darker red text for contrast
                "SystemNoteHighlight": QColor("#E65100"),  # Darker orange text for contrast
            }

        # Notify views that data has changed (triggers repaint)
        if self.rowCount() > 0:
            top_left = self.index(0, 0)
            bottom_right = self.index(self.rowCount() - 1, self.columnCount() - 1)
            self.dataChanged.emit(top_left, bottom_right, [Qt.BackgroundRole, Qt.ForegroundRole])
