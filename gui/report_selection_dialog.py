from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton
from PySide6.QtCore import Signal, Slot

class ReportSelectionDialog(QDialog):
    # Signal that emits the selected report configuration when a button is clicked
    reportSelected = Signal(dict)

    def __init__(self, report_type, reports_config, parent=None):
        super().__init__(parent)

        self.setWindowTitle(f"Select {report_type.replace('_', ' ').title()}")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)

        if not reports_config:
            # You can add a QLabel here to show a message
            pass
        else:
            for report_config in reports_config:
                button = QPushButton(report_config.get('name', 'Unknown Report'))
                # Use a lambda to capture the specific config for this button
                button.clicked.connect(lambda checked=False, rc=report_config: self.on_report_button_clicked(rc))
                layout.addWidget(button)

    @Slot(dict)
    def on_report_button_clicked(self, report_config):
        """
        When a report button is clicked, emit the signal with its config
        and accept the dialog to close it.
        """
        self.reportSelected.emit(report_config)
        self.accept()
