from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QScrollArea, QWidget,
    QCheckBox, QHBoxLayout, QComboBox, QLineEdit, QPushButton,
    QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt
import pandas as pd

class ReportBuilderWindow(QDialog):
    def __init__(self, dataframe, parent=None):
        super().__init__(parent)
        self.df = dataframe
        self.setWindowTitle("Report Builder")
        self.setMinimumSize(600, 500)

        main_layout = QVBoxLayout(self)

        # --- Step 1: Column Selection ---
        columns_box = QGroupBox("Step 1: Select Columns to Include")
        columns_layout = QVBoxLayout(columns_box)
        scroll_area = QScrollArea(); scroll_area.setWidgetResizable(True)
        scroll_content = QWidget(); scroll_layout = QVBoxLayout(scroll_content)
        self.column_vars = {}
        for col in self.df.columns:
            cb = QCheckBox(col); cb.setChecked(True)
            self.column_vars[col] = cb
            scroll_layout.addWidget(cb)
        scroll_area.setWidget(scroll_content)
        columns_layout.addWidget(scroll_area)
        main_layout.addWidget(columns_box)

        # --- Step 2: Filter ---
        filter_box = QGroupBox("Step 2: Add a Filter (Optional)")
        filter_layout = QHBoxLayout(filter_box)
        self.filter_column_combo = QComboBox(); self.filter_column_combo.addItems(self.df.columns)
        self.filter_op_combo = QComboBox(); self.filter_op_combo.addItems(["==", "!=", ">", "<", "contains"])
        self.filter_value_edit = QLineEdit(); self.filter_value_edit.setPlaceholderText("Value")
        filter_layout.addWidget(self.filter_column_combo)
        filter_layout.addWidget(self.filter_op_combo)
        filter_layout.addWidget(self.filter_value_edit, 1)
        main_layout.addWidget(filter_box)

        # --- Step 3: Generate ---
        self.generate_btn = QPushButton("Step 3: Generate and Save Custom Report")
        main_layout.addWidget(self.generate_btn)

        # --- Connections ---
        self.generate_btn.clicked.connect(self.generate_custom_report)

    def generate_custom_report(self):
        selected_columns = [col for col, var in self.column_vars.items() if var.isChecked()]
        if not selected_columns:
            QMessageBox.critical(self, "Error", "Please select at least one column.")
            return

        filtered_df = self.df.copy()
        filter_col = self.filter_column_combo.currentText()
        operator = self.filter_op_combo.currentText()
        value = self.filter_value_edit.text()

        if value:
            try:
                numeric_value = pd.to_numeric(value, errors='coerce')
                if not pd.isna(numeric_value):
                    value = numeric_value
                    filtered_df[filter_col] = pd.to_numeric(filtered_df[filter_col], errors='coerce')

                if operator == "==": filtered_df = filtered_df[filtered_df[filter_col] == value]
                elif operator == "!=": filtered_df = filtered_df[filtered_df[filter_col] != value]
                elif operator == ">": filtered_df = filtered_df[filtered_df[filter_col] > value]
                elif operator == "<": filtered_df = filtered_df[filtered_df[filter_col] < value]
                elif operator == "contains": filtered_df = filtered_df[filtered_df[filter_col].astype(str).str.contains(value, case=False, na=False)]
            except Exception as e:
                QMessageBox.critical(self, "Filter Error", f"Could not apply filter:\n{e}")
                return

        report_df = filtered_df[selected_columns]

        save_path, _ = QFileDialog.getSaveFileName(self, "Save Custom Report", "", "Excel Files (*.xlsx);;All Files (*)")
        if not save_path:
            return

        try:
            # Note: This should be run in a worker thread in a real app
            report_df.to_excel(save_path, index=False)
            # Access parent's log_activity if it exists
            if hasattr(self.parent(), 'log_activity'):
                self.parent().log_activity("Custom Report", f"Custom report saved to: {save_path}")
            QMessageBox.information(self, "Success", "Custom report saved successfully.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save the report:\n{e}")
