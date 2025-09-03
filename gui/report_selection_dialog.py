from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton
from PySide6.QtCore import Signal, Slot


class ReportSelectionDialog(QDialog):
    """A dialog that displays a button for each available report.

    This dialog is dynamically populated with buttons based on a list of
    report configurations. When a user clicks a button, the dialog emits a
    signal containing the configuration for that specific report and then closes.

    Attributes:
        reportSelected (Signal): A PySide6 signal that emits the report
            configuration dictionary when a report button is clicked.
    """

    # Signal that emits the selected report configuration when a button is clicked
    reportSelected = Signal(dict)

    def __init__(self, report_type, reports_config, parent=None):
        """Initializes the ReportSelectionDialog.

        Args:
            report_type (str): The type of reports, used for the window title
                (e.g., 'packing_lists').
            reports_config (list): A list of report configuration dictionaries.
                Each dictionary should contain at least a 'name' key.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)

        self.setWindowTitle(f"Select {report_type.replace('_', ' ').title()}")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)

        if not reports_config:
            # You can add a QLabel here to show a message
            pass
        else:
            for report_config in reports_config:
                button = QPushButton(report_config.get("name", "Unknown Report"))
                # Use a lambda to capture the specific config for this button
                button.clicked.connect(lambda checked=False, rc=report_config: self.on_report_button_clicked(rc))
                layout.addWidget(button)

    @Slot(dict)
    def on_report_button_clicked(self, report_config):
        """Emits the reportSelected signal and closes the dialog.

        This slot is connected to the `clicked` signal of each report button
        created in the constructor.

        Args:
            report_config (dict): The configuration dictionary associated with
                the clicked button.
        """
        self.reportSelected.emit(report_config)
        self.accept()
