"""
Barcode Generator Widget - Generate warehouse barcode labels from packing lists.

Features:
- Select packing list to generate barcodes for
- Shows order count preview
- Background generation with progress tracking
- History table with thumbnails
- Open barcodes folder
- Export to PDF
"""

import os
import logging
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QLabel, QProgressBar, QTableWidget, QComboBox, QCheckBox,
    QMessageBox, QTableWidgetItem, QHeaderView, QFileDialog
)
from PySide6.QtCore import Qt, QThreadPool, Signal
from PySide6.QtGui import QPixmap, QDesktopServices
from PySide6.QtCore import QUrl

from gui.worker import Worker
from shopify_tool.barcode_history import BarcodeHistory


class BarcodeGeneratorWidget(QWidget):
    """Widget for generating barcode labels from packing lists."""

    # Signal emitted when generation completes
    generation_complete = Signal(dict)

    def __init__(self, main_window, parent=None):
        """
        Initialize Barcode Generator widget.

        Args:
            main_window: MainWindow instance for accessing session data
            parent: Parent widget
        """
        super().__init__(parent)
        self.mw = main_window
        self.log = logging.getLogger(__name__)

        # Current state
        self.current_packing_list = None
        self.filtered_orders_df = None
        self.barcodes_dir = None
        self.history = None

        self._init_ui()
        self._connect_signals()
        self._update_state()

    def _init_ui(self):
        """Initialize UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Section 1: Packing List Selection
        layout.addWidget(self._create_packing_list_section())

        # Section 2: Options
        layout.addWidget(self._create_options_section())

        # Section 3: Generation
        layout.addWidget(self._create_generation_section())

        # Section 4: History
        layout.addWidget(self._create_history_section(), 1)  # Stretch

    def _create_packing_list_section(self):
        """Create packing list selection section."""
        group = QGroupBox("Packing List Selection")
        layout = QVBoxLayout(group)

        # Packing list dropdown
        list_row = QHBoxLayout()
        list_row.addWidget(QLabel("Select Packing List:"))

        self.packing_list_combo = QComboBox()
        self.packing_list_combo.setMinimumWidth(250)
        list_row.addWidget(self.packing_list_combo, 1)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setMaximumWidth(80)
        refresh_btn.setToolTip("Refresh packing lists")
        refresh_btn.clicked.connect(self._refresh_packing_lists)
        list_row.addWidget(refresh_btn)

        layout.addLayout(list_row)

        # Order count preview
        self.order_count_label = QLabel("No packing list selected")
        self.order_count_label.setStyleSheet("color: #666; font-style: italic; padding: 5px;")
        layout.addWidget(self.order_count_label)

        # Info label
        info_label = QLabel(
            "Barcodes will be generated for all Fulfillable orders in the selected packing list.\n"
            "Each packing list has its own barcode folder for organization."
        )
        info_label.setStyleSheet("color: #444; font-size: 9pt; padding: 5px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        return group

    def _create_options_section(self):
        """Create options section."""
        group = QGroupBox("Options")
        layout = QVBoxLayout(group)

        # Auto-open folder checkbox
        self.auto_open_folder_checkbox = QCheckBox("Auto-open barcodes folder after generation")
        self.auto_open_folder_checkbox.setChecked(True)
        layout.addWidget(self.auto_open_folder_checkbox)

        # Generate PDF checkbox
        self.generate_pdf_checkbox = QCheckBox("Also generate PDF file (all barcodes in one PDF)")
        self.generate_pdf_checkbox.setChecked(False)
        layout.addWidget(self.generate_pdf_checkbox)

        # Output directory label
        output_row = QHBoxLayout()
        output_row.addWidget(QLabel("Output:"))
        self.output_dir_label = QLabel("No packing list selected")
        self.output_dir_label.setStyleSheet("font-weight: bold; color: #666;")
        self.output_dir_label.setWordWrap(True)
        output_row.addWidget(self.output_dir_label, 1)
        layout.addLayout(output_row)

        return group

    def _create_generation_section(self):
        """Create generation section."""
        group = QGroupBox("Generate Barcodes")
        layout = QVBoxLayout(group)

        # Generate button
        self.generate_btn = QPushButton("Generate Barcode Labels")
        self.generate_btn.setMinimumHeight(50)
        self.generate_btn.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                font-weight: bold;
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.generate_btn.setEnabled(False)
        self.generate_btn.clicked.connect(self._on_generate_clicked)
        layout.addWidget(self.generate_btn)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("Select a packing list to begin")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("padding: 5px;")
        layout.addWidget(self.status_label)

        return group

    def _create_history_section(self):
        """Create history section."""
        group = QGroupBox("Generated Barcodes")
        layout = QVBoxLayout(group)

        # History table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels([
            "Preview",
            "Seq #",
            "Order Number",
            "Courier",
            "Country",
            "Items",
            "Size (KB)"
        ])
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setSelectionMode(QTableWidget.SingleSelection)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.verticalHeader().setVisible(False)

        # Set column widths
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.resizeSection(0, 60)  # Preview thumbnail
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.resizeSection(1, 50)  # Seq #
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Order Number
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.resizeSection(3, 80)  # Courier
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.resizeSection(4, 60)  # Country
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        header.resizeSection(5, 60)  # Items
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        header.resizeSection(6, 80)  # Size

        # Set row height for thumbnails
        self.history_table.verticalHeader().setDefaultSectionSize(55)

        layout.addWidget(self.history_table)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.open_folder_btn = QPushButton("Open Barcodes Folder")
        self.open_folder_btn.setEnabled(False)
        self.open_folder_btn.clicked.connect(self._open_barcodes_folder)
        button_layout.addWidget(self.open_folder_btn)

        self.export_pdf_btn = QPushButton("Export to PDF")
        self.export_pdf_btn.setEnabled(False)
        self.export_pdf_btn.clicked.connect(self._export_to_pdf)
        button_layout.addWidget(self.export_pdf_btn)

        clear_btn = QPushButton("Clear History")
        clear_btn.clicked.connect(self._clear_history)
        button_layout.addWidget(clear_btn)

        layout.addLayout(button_layout)

        return group

    def _connect_signals(self):
        """Connect signals and slots."""
        self.packing_list_combo.currentIndexChanged.connect(self._on_packing_list_changed)
        self.history_table.cellDoubleClicked.connect(self._on_preview_barcode)

    def _update_state(self):
        """Update widget state based on current session."""
        if not self.mw.session_path:
            self.packing_list_combo.clear()
            self.order_count_label.setText("No session selected")
            self.output_dir_label.setText("No session selected")
            self.status_label.setText("No session selected")
            self.generate_btn.setEnabled(False)
            self.open_folder_btn.setEnabled(False)
            self.export_pdf_btn.setEnabled(False)
            return

        # Refresh packing lists
        self._refresh_packing_lists()

    def _refresh_packing_lists(self):
        """Refresh available packing lists from session."""
        if not self.mw.session_path:
            return

        self.packing_list_combo.clear()

        # Scan packing_lists directory for generated lists
        packing_lists_dir = Path(self.mw.session_path) / "packing_lists"

        if not packing_lists_dir.exists():
            self.order_count_label.setText("No packing lists found")
            self.log.warning(f"Packing lists directory not found: {packing_lists_dir}")
            return

        # Find all .xlsx and .json files
        packing_files = list(packing_lists_dir.glob("*.xlsx")) + list(packing_lists_dir.glob("*.json"))

        if not packing_files:
            self.order_count_label.setText("No packing lists generated yet")
            self.log.info("No packing list files found in session")
            return

        # Add to combo box (use file stem as display name)
        for file in sorted(packing_files):
            # Remove file extension for display name
            display_name = file.stem
            self.packing_list_combo.addItem(display_name, file)

        self.log.info(f"Found {len(packing_files)} packing lists")

    def _on_packing_list_changed(self, index):
        """Handle packing list selection change."""
        if index < 0:
            self.current_packing_list = None
            self.filtered_orders_df = None
            self.barcodes_dir = None
            self.history = None

            self.order_count_label.setText("No packing list selected")
            self.output_dir_label.setText("No packing list selected")
            self.generate_btn.setEnabled(False)
            self.open_folder_btn.setEnabled(False)
            self.export_pdf_btn.setEnabled(False)
            return

        # Get selected packing list name
        packing_list_name = self.packing_list_combo.currentText()
        self.current_packing_list = packing_list_name

        self.log.info(f"Selected packing list: {packing_list_name}")

        # Filter analysis results for this packing list
        # Determine courier from packing list name (e.g., "DHL_Orders" -> "DHL")
        courier = packing_list_name.split('_')[0] if '_' in packing_list_name else packing_list_name

        if not hasattr(self.mw, 'analysis_results_df') or self.mw.analysis_results_df is None:
            self.order_count_label.setText("No analysis data loaded")
            self.log.warning("No analysis results DataFrame available")
            return

        # Filter orders by courier and Fulfillable status
        filtered_df = self.mw.analysis_results_df[
            (self.mw.analysis_results_df['Shipping_Provider'] == courier) &
            (self.mw.analysis_results_df['Order_Fulfillment_Status'] == 'Fulfillable')
        ].copy()

        self.filtered_orders_df = filtered_df

        # Get unique order count
        order_count = filtered_df['Order_Number'].nunique()

        self.order_count_label.setText(f"{order_count} orders ready for barcode generation")

        # Setup output directory
        session_path = Path(self.mw.session_path)
        self.barcodes_dir = session_path / "barcodes" / packing_list_name
        self.barcodes_dir.mkdir(parents=True, exist_ok=True)

        self.output_dir_label.setText(str(self.barcodes_dir))

        # Setup history manager
        history_file = self.barcodes_dir / "barcode_history.json"
        self.history = BarcodeHistory(history_file)

        # Load history
        self._load_history()

        # Enable generation if we have orders
        self.generate_btn.setEnabled(order_count > 0)
        self.open_folder_btn.setEnabled(True)
        self.export_pdf_btn.setEnabled(order_count > 0)

        self.log.info(f"Ready to generate {order_count} barcodes for {packing_list_name}")

    def _on_generate_clicked(self):
        """Handle generate button click."""
        if self.filtered_orders_df is None or len(self.filtered_orders_df) == 0:
            QMessageBox.warning(
                self,
                "No Orders",
                "No orders available for barcode generation."
            )
            return

        # Confirm generation
        order_count = self.filtered_orders_df['Order_Number'].nunique()

        reply = QMessageBox.question(
            self,
            "Confirm Generation",
            f"Generate barcodes for {order_count} orders?\n\n"
            f"Packing List: {self.current_packing_list}\n"
            f"Output: {self.barcodes_dir}",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Disable UI during generation
        self.generate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting barcode generation...")
        self.status_label.setStyleSheet("")

        # Start generation in background
        worker = Worker(self._generate_barcodes_worker)
        worker.signals.result.connect(self._on_generation_complete)
        worker.signals.error.connect(self._on_generation_error)
        worker.signals.finished.connect(self._on_generation_finished)

        QThreadPool.globalInstance().start(worker)

        self.log.info(f"Started barcode generation for {order_count} orders")

    def _generate_barcodes_worker(self):
        """Worker function for barcode generation."""
        from shopify_tool.barcode_processor import generate_barcodes_batch
        from shopify_tool.sequential_order import load_sequential_order_map

        session_path = Path(self.mw.session_path)

        # Load sequential order map
        sequential_map = load_sequential_order_map(session_path)

        if not sequential_map:
            self.log.warning("Sequential order map not found, generating on-the-fly")

        # Filter to unique orders only
        unique_orders = self.filtered_orders_df.groupby('Order_Number').first().reset_index()

        def progress_callback(current, total, message):
            """Update progress bar from worker thread."""
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
            self.status_label.setText(message)

        results = generate_barcodes_batch(
            df=unique_orders,
            output_dir=self.barcodes_dir,
            sequential_start=1,
            progress_callback=progress_callback
        )

        return results

    def _on_generation_complete(self, results):
        """Handle successful generation."""
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]

        self.progress_bar.setValue(100)
        self.status_label.setText(
            f"Complete: {len(successful)} barcodes generated"
        )
        self.status_label.setStyleSheet("color: green; font-weight: bold;")

        self.log.info(
            f"Barcode generation complete: {len(successful)} successful, "
            f"{len(failed)} failed"
        )

        # Add to history
        if self.history:
            for result in results:
                self.history.add_entry(result)

            self._load_history()

        # Generate PDF if requested
        if self.generate_pdf_checkbox.isChecked() and successful:
            self._generate_pdf_from_results(successful)

        # Show summary
        message = f"Successfully generated {len(successful)} barcode labels."

        if failed:
            message += f"\n\n{len(failed)} barcodes failed to generate."

        QMessageBox.information(self, "Generation Complete", message)

        # Auto-open folder if enabled
        if self.auto_open_folder_checkbox.isChecked():
            self._open_barcodes_folder()

        # Emit signal
        self.generation_complete.emit({
            'packing_list': self.current_packing_list,
            'successful': len(successful),
            'failed': len(failed),
            'total': len(results)
        })

    def _on_generation_error(self, error_info):
        """Handle generation error."""
        exctype, value, traceback_str = error_info

        self.status_label.setText("Generation failed")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")

        self.log.error(f"Barcode generation failed: {value}\n{traceback_str}")

        QMessageBox.critical(
            self,
            "Generation Error",
            f"Barcode generation failed:\n\n{value}\n\n"
            "See execution log for details."
        )

    def _on_generation_finished(self):
        """Re-enable UI after generation."""
        self.progress_bar.setVisible(False)
        self.generate_btn.setEnabled(True)

    def _generate_pdf_from_results(self, results):
        """Generate PDF automatically after barcode generation."""
        try:
            from shopify_tool.barcode_processor import generate_barcodes_pdf

            barcode_files = [r['file_path'] for r in results if r.get('file_path')]

            if not barcode_files:
                return

            pdf_filename = f"{self.current_packing_list}_barcodes.pdf"
            pdf_path = self.barcodes_dir / pdf_filename

            generate_barcodes_pdf(barcode_files, pdf_path)

            self.log.info(f"Auto-generated PDF: {pdf_path}")

            # Open PDF
            url = QUrl.fromLocalFile(str(pdf_path))
            QDesktopServices.openUrl(url)

        except Exception as e:
            self.log.error(f"Auto PDF generation failed: {e}")

    def _load_history(self):
        """Load history into table."""
        if not self.history:
            return

        self.history_table.setRowCount(0)

        entries = self.history.data.get('generated_barcodes', [])

        for entry in reversed(entries):  # Newest first
            row = self.history_table.rowCount()
            self.history_table.insertRow(row)

            # Preview thumbnail
            file_path = entry.get('file_path')
            if file_path and Path(file_path).exists():
                pixmap = QPixmap(str(file_path))
                pixmap_scaled = pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)

                label = QLabel()
                label.setPixmap(pixmap_scaled)
                label.setAlignment(Qt.AlignCenter)
                self.history_table.setCellWidget(row, 0, label)

            # Sequential #
            self.history_table.setItem(row, 1, QTableWidgetItem(str(entry.get('sequential_num', ''))))

            # Order Number
            self.history_table.setItem(row, 2, QTableWidgetItem(entry.get('order_number', '')))

            # Courier
            self.history_table.setItem(row, 3, QTableWidgetItem(entry.get('courier', '')))

            # Country
            self.history_table.setItem(row, 4, QTableWidgetItem(entry.get('country', '')))

            # Items
            self.history_table.setItem(row, 5, QTableWidgetItem(str(entry.get('item_count', ''))))

            # Size (KB)
            self.history_table.setItem(row, 6, QTableWidgetItem(str(entry.get('file_size_kb', ''))))

    def _on_preview_barcode(self, row, column):
        """Handle double-click on barcode row to preview."""
        order_number_item = self.history_table.item(row, 2)

        if not order_number_item:
            return

        order_number = order_number_item.text()

        # Find barcode file
        barcode_file = self.barcodes_dir / f"{order_number}.png"

        if not barcode_file.exists():
            QMessageBox.warning(
                self,
                "File Not Found",
                f"Barcode file not found:\n{barcode_file}"
            )
            return

        # Open in default image viewer
        url = QUrl.fromLocalFile(str(barcode_file))
        QDesktopServices.openUrl(url)

    def _open_barcodes_folder(self):
        """Open barcodes folder in file explorer."""
        if not self.barcodes_dir or not self.barcodes_dir.exists():
            QMessageBox.warning(
                self,
                "Folder Not Found",
                "Barcodes folder not found."
            )
            return

        url = QUrl.fromLocalFile(str(self.barcodes_dir))
        QDesktopServices.openUrl(url)

        self.log.info(f"Opened barcodes folder: {self.barcodes_dir}")

    def _export_to_pdf(self):
        """Export all barcodes to PDF."""
        if not self.barcodes_dir or not self.barcodes_dir.exists():
            QMessageBox.warning(
                self,
                "No Barcodes",
                "No barcodes available to export."
            )
            return

        # Get all PNG files
        barcode_files = list(self.barcodes_dir.glob("*.png"))

        if not barcode_files:
            QMessageBox.information(
                self,
                "No Barcodes",
                "No barcode files found in folder."
            )
            return

        # Ask for PDF filename
        pdf_filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Barcodes to PDF",
            str(self.barcodes_dir / f"{self.current_packing_list}_barcodes.pdf"),
            "PDF Files (*.pdf)"
        )

        if not pdf_filename:
            return

        try:
            from shopify_tool.barcode_processor import generate_barcodes_pdf

            pdf_path = generate_barcodes_pdf(
                barcode_files,
                Path(pdf_filename)
            )

            QMessageBox.information(
                self,
                "Export Complete",
                f"Exported {len(barcode_files)} barcodes to PDF:\n\n{pdf_path}"
            )

            # Open PDF
            url = QUrl.fromLocalFile(str(pdf_path))
            QDesktopServices.openUrl(url)

            self.log.info(f"Exported barcodes to PDF: {pdf_path}")

        except Exception as e:
            self.log.error(f"PDF export failed: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "PDF Export Failed",
                f"Failed to export PDF:\n\n{e}"
            )

    def _clear_history(self):
        """Clear barcode history."""
        if not self.history:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Clear History",
            "Clear all barcode generation history?\n\n"
            "This will not delete the barcode files.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        self.history.clear_history()
        self._load_history()

        self.log.info("Cleared barcode history")
