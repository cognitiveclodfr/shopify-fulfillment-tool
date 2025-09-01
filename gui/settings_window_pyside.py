import sys
import json
from PySide6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QVBoxLayout, QTabWidget,
    QWidget, QFormLayout, QLabel, QLineEdit, QMessageBox
)

class SettingsWindow(QDialog):
    def __init__(self, parent, config):
        super().__init__(parent)
        self.parent = parent
        # Make a deep copy of the config to edit, so we can cancel without side effects
        self.config_data = json.loads(json.dumps(config))

        self.setWindowTitle("Application Settings")
        self.setMinimumSize(600, 400)
        self.setModal(True)

        main_layout = QVBoxLayout(self)

        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        self.create_general_tab()
        self.create_rules_tab()
        self.create_packing_lists_tab()
        self.create_stock_exports_tab()

        # --- Dialog Buttons ---
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_settings)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    def create_general_tab(self):
        """Creates widgets for the 'General & Paths' tab."""
        tab = QWidget()
        layout = QFormLayout(tab)

        self.stock_delimiter_edit = QLineEdit()
        self.low_stock_edit = QLineEdit()
        self.templates_path_edit = QLineEdit()
        self.stock_output_path_edit = QLineEdit()

        layout.addRow(QLabel("Stock CSV Delimiter:"), self.stock_delimiter_edit)
        layout.addRow(QLabel("Low Stock Threshold:"), self.low_stock_edit)
        layout.addRow(QLabel("Templates Directory:"), self.templates_path_edit)
        layout.addRow(QLabel("Stock Export Output Directory:"), self.stock_output_path_edit)

        # Load initial data
        settings = self.config_data.get('settings', {})
        paths = self.config_data.get('paths', {})
        self.stock_delimiter_edit.setText(settings.get('stock_csv_delimiter', ';'))
        self.low_stock_edit.setText(str(settings.get('low_stock_threshold', 10)))
        self.templates_path_edit.setText(paths.get('templates', ''))
        self.stock_output_path_edit.setText(paths.get('output_dir_stock', ''))

        self.tab_widget.addTab(tab, "General & Paths")

    def create_rules_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("Rule builder will be implemented here."))
        self.tab_widget.addTab(tab, "Rules")

    def create_packing_lists_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("Packing list configuration will be implemented here."))
        self.tab_widget.addTab(tab, "Packing Lists")

    def create_stock_exports_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("Stock export configuration will be implemented here."))
        self.tab_widget.addTab(tab, "Stock Exports")

    def save_settings(self):
        """Saves the current settings from the UI back to the config object."""
        try:
            # Update settings
            self.config_data['settings']['stock_csv_delimiter'] = self.stock_delimiter_edit.text()
            self.config_data['settings']['low_stock_threshold'] = int(self.low_stock_edit.text())

            # Update paths
            self.config_data['paths']['templates'] = self.templates_path_edit.text()
            self.config_data['paths']['output_dir_stock'] = self.stock_output_path_edit.text()

            # TODO: Save data from other tabs here once implemented

            self.accept() # This will close the dialog and return QDialog.Accepted
        except ValueError:
            QMessageBox.critical(self, "Validation Error", "Low Stock Threshold must be a valid number.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")

if __name__ == '__main__':
    # For standalone testing
    app = QApplication(sys.argv)
    # A dummy config for testing
    dummy_config = {
        "settings": {"stock_csv_delimiter": ";", "low_stock_threshold": 5},
        "paths": {"templates": "data/templates", "output_dir_stock": "data/output"}
    }
    dialog = SettingsWindow(None, dummy_config)
    if dialog.exec():
        print("Settings saved:", dialog.config_data)
    else:
        print("Cancelled.")
    sys.exit(0)
