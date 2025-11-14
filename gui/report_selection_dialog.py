from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QGroupBox, QWidget
from PySide6.QtCore import Signal, Slot


class ReportSelectionDialog(QDialog):
    """A dialog that dynamically creates buttons for selecting a pre-configured report.

    This dialog is populated with a button for each report found in the
    application's configuration file for a given report type (e.g.,
    'packing_lists' or 'stock_exports'). When the user clicks a button, the
    dialog emits a signal containing the configuration for that specific
    report and then closes.

    Signals:
        reportSelected (dict): Emitted when a report button is clicked,
                               carrying the configuration dictionary for that
                               report.
    """

    # Signal that emits the selected report configuration when a button is clicked
    reportSelected = Signal(dict)

    def __init__(self, report_type, reports_config, parent=None):
        """Initializes the ReportSelectionDialog.

        Args:
            report_type (str): The type of reports to display (e.g.,
                "packing_lists"). Used for the window title.
            reports_config (list[dict]): A list of report configuration
                dictionaries, each used to create a button.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)

        self.setWindowTitle(f"Select {report_type.replace('_', ' ').title()}")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        layout = QVBoxLayout(self)

        if not reports_config:
            no_reports_label = QLabel("No reports configured for this type.")
            no_reports_label.setStyleSheet("color: gray; font-style: italic; padding: 20px;")
            layout.addWidget(no_reports_label)
        else:
            for report_config in reports_config:
                # Create a group box for each report
                report_widget = self._create_report_widget(report_config)
                layout.addWidget(report_widget)

        layout.addStretch()

    def _create_report_widget(self, report_config):
        """Create a widget for a single report with button and filters display.

        Args:
            report_config (dict): Report configuration dictionary.

        Returns:
            QGroupBox: Widget containing button and filters.
        """
        group = QGroupBox(report_config.get("name", "Unknown Report"))
        group_layout = QVBoxLayout(group)

        # Create select button
        button = QPushButton("Generate This Report")
        button.clicked.connect(lambda checked=False, rc=report_config: self.on_report_button_clicked(rc))
        button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        group_layout.addWidget(button)

        # Display filters if they exist
        filters = report_config.get("filters", {})
        if filters:
            filters_label = QLabel("Applied Filters:")
            filters_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
            group_layout.addWidget(filters_label)

            # Display each filter
            for filter_key, filter_value in filters.items():
                # Format the filter nicely
                filter_text = self._format_filter(filter_key, filter_value)
                filter_label = QLabel(f"  • {filter_text}")
                filter_label.setWordWrap(True)
                filter_label.setStyleSheet("color: #555; margin-left: 10px;")
                group_layout.addWidget(filter_label)
        else:
            no_filters_label = QLabel("No filters applied (includes all data)")
            no_filters_label.setStyleSheet("color: gray; font-style: italic; margin-top: 5px;")
            group_layout.addWidget(no_filters_label)

        return group

    def _format_filter(self, filter_key, filter_value):
        """Format a filter for display.

        Args:
            filter_key (str): The filter field name.
            filter_value: The filter value (can be str, list, etc.).

        Returns:
            str: Formatted filter string.
        """
        # Convert key to more readable format
        readable_key = filter_key.replace("_", " ").title()

        # Format value
        if isinstance(filter_value, list):
            if len(filter_value) == 1:
                return f"{readable_key}: {filter_value[0]}"
            else:
                return f"{readable_key}: {', '.join(str(v) for v in filter_value)}"
        else:
            return f"{readable_key}: {filter_value}"

    @Slot(dict)
    def on_report_button_clicked(self, report_config):
        """Handles the click of any report button.

        Emits the `reportSelected` signal with the configuration of the
        clicked report and then closes the dialog.

        Args:
            report_config (dict): The configuration dictionary associated
                with the button that was clicked.
        """
        self.reportSelected.emit(report_config)
        self.accept()
