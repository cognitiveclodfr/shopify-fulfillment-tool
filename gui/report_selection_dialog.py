from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QCheckBox, QFrame
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
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)

        self.report_type = report_type  # Store report type
        layout = QVBoxLayout(self)

        # Add writeoff checkbox for stock_exports
        if report_type == "stock_exports":
            self.writeoff_checkbox = QCheckBox("Include Packaging Materials (SKU Writeoff)")
            self.writeoff_checkbox.setToolTip(
                "When enabled, packaging materials (based on Internal Tags) will be\n"
                "automatically added to the stock export as separate SKU lines.\n"
                "Example: Orders with 'BOX' tag will add PKG-BOX-SMALL to the export."
            )
            self.writeoff_checkbox.setChecked(False)
            layout.addWidget(self.writeoff_checkbox)

            # Add separator line
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setFrameShadow(QFrame.Sunken)
            layout.addWidget(line)

        if not reports_config:
            no_reports_label = QLabel("No reports configured for this type.")
            no_reports_label.setStyleSheet("color: gray; font-style: italic; padding: 20px;")
            layout.addWidget(no_reports_label)
        else:
            for report_config in reports_config:
                # Create a button for each report with tooltip
                button = self._create_report_button(report_config)
                layout.addWidget(button)

        layout.addStretch()

    def _create_report_button(self, report_config):
        """Create a button for a single report with tooltip showing filters.

        Args:
            report_config (dict): Report configuration dictionary.

        Returns:
            QPushButton: Button for selecting this report.
        """
        button_text = report_config.get("name", "Unknown Report")
        button = QPushButton(button_text)
        button.clicked.connect(lambda checked=False, rc=report_config: self.on_report_button_clicked(rc))
        button.setMinimumHeight(40)

        # Create tooltip with filters information
        tooltip = self._create_tooltip_text(report_config)
        button.setToolTip(tooltip)

        button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 10px;
                font-size: 13px;
                font-weight: bold;
                text-align: left;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)

        return button

    def _create_tooltip_text(self, report_config):
        """Create tooltip text showing report filters.

        Args:
            report_config (dict): Report configuration dictionary.

        Returns:
            str: Formatted tooltip text with filters.
        """
        tooltip_lines = [f"<b>{report_config.get('name', 'Unknown Report')}</b>", ""]

        filters = report_config.get("filters", {})
        if filters:
            tooltip_lines.append("<b>Applied Filters:</b>")

            # Handle both dict and list formats for filters
            if isinstance(filters, dict):
                # Dictionary format: {key: value}
                for filter_key, filter_value in filters.items():
                    filter_text = self._format_filter(filter_key, filter_value)
                    tooltip_lines.append(f"• {filter_text}")
            elif isinstance(filters, list):
                # List format: [{"field": "key", "value": "val"}, ...]
                for filter_item in filters:
                    if isinstance(filter_item, dict):
                        field = filter_item.get("field", "Unknown")
                        value = filter_item.get("value", "")
                        filter_text = self._format_filter(field, value)
                        tooltip_lines.append(f"• {filter_text}")
            else:
                # Unknown format - display as string
                tooltip_lines.append(f"• {str(filters)}")
        else:
            tooltip_lines.append("<i>No filters (includes all data)</i>")

        return "<br>".join(tooltip_lines)

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
        # Inject writeoff setting into report_config if checkbox exists
        if hasattr(self, 'writeoff_checkbox'):
            report_config["apply_writeoff"] = self.writeoff_checkbox.isChecked()

        self.reportSelected.emit(report_config)
        self.accept()
