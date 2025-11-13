from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QComboBox, QSpinBox, QLabel, QPushButton,
    QGroupBox, QMessageBox, QWidget
)
from PySide6.QtCore import Qt
import logging

logger = logging.getLogger(__name__)


class AddProductDialog(QDialog):
    """
    Dialog for manually adding product to order.

    Usage:
        dialog = AddProductDialog(
            parent=main_window,
            orders_df=analysis_df,
            stock_df=stock_df
        )

        if dialog.exec() == QDialog.Accepted:
            result = dialog.get_result()
            # result = {
            #     "order_number": "1001",
            #     "sku": "SKU-HAT",
            #     "product_name": "Зимова шапка",
            #     "quantity": 2
            # }
    """

    def __init__(self, parent, orders_df, stock_df):
        super().__init__(parent)

        self.orders_df = orders_df
        self.stock_df = stock_df
        self.result = None

        self.setup_ui()
        self.populate_orders()
        self.populate_products()

    def setup_ui(self):
        """Setup dialog UI components."""
        self.setWindowTitle("Add Product to Order")
        self.setModal(True)
        self.resize(500, 600)

        layout = QVBoxLayout(self)

        # Section 1: Order Selection
        layout.addWidget(self._create_order_section())

        # Section 2: Product Selection
        layout.addWidget(self._create_product_section())

        # Section 3: Quantity
        layout.addWidget(self._create_quantity_section())

        # Section 4: Info/Warning Box
        self.warning_box = self._create_warning_box()
        self.warning_box.setVisible(False)
        layout.addWidget(self.warning_box)

        self.info_box = self._create_info_box()
        layout.addWidget(self.info_box)

        # Section 5: Buttons
        layout.addWidget(self._create_buttons())

    def _create_order_section(self):
        """Create order selection section."""
        group = QGroupBox("ORDER SELECTION")
        layout = QVBoxLayout(group)

        layout.addWidget(QLabel("Select the order to add product to:"))

        self.order_combo = QComboBox()
        self.order_combo.setPlaceholderText("Select order...")
        layout.addWidget(self.order_combo)

        return group

    def _create_product_section(self):
        """Create product selection section."""
        group = QGroupBox("PRODUCT SELECTION")
        layout = QVBoxLayout(group)

        layout.addWidget(QLabel("Select product to add:"))

        self.product_combo = QComboBox()
        self.product_combo.setPlaceholderText("Select product from stock...")
        self.product_combo.currentIndexChanged.connect(self._on_product_changed)
        layout.addWidget(self.product_combo)

        return group

    def _create_quantity_section(self):
        """Create quantity input section."""
        group = QGroupBox("QUANTITY")
        layout = QVBoxLayout(group)

        layout.addWidget(QLabel("Quantity to add:"))

        self.quantity_spin = QSpinBox()
        self.quantity_spin.setMinimum(1)
        self.quantity_spin.setMaximum(9999)
        self.quantity_spin.setValue(1)
        layout.addWidget(self.quantity_spin)

        return group

    def _create_warning_box(self):
        """Create warning box for low/zero stock."""
        label = QLabel()
        label.setWordWrap(True)
        label.setStyleSheet("""
            QLabel {
                background-color: #FFEBEE;
                border: 2px solid #F44336;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        return label

    def _create_info_box(self):
        """Create info box."""
        text = (
            "ℹ️ INFO\n\n"
            "• Product will be added with Source: 'Manual'\n"
            "• Order fulfillment status will be marked 'Pending'\n"
            "• Re-run analysis to update fulfillment\n"
            "• Manual addition will be saved in session"
        )

        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("""
            QLabel {
                background-color: #E3F2FD;
                border: 2px solid #2196F3;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        return label

    def _create_buttons(self):
        """Create Cancel/Add buttons."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

        self.add_btn = QPushButton("Add Product")
        self.add_btn.clicked.connect(self._on_add_clicked)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        layout.addWidget(self.add_btn)

        return widget

    def populate_orders(self):
        """Populate order dropdown from analysis DataFrame."""
        if self.orders_df is None or self.orders_df.empty:
            logger.warning("No orders available")
            return

        # Group by Order_Number, count items, get fulfillment status
        orders_grouped = self.orders_df.groupby("Order_Number").agg({
            "SKU": "count",  # item count
            "Order_Fulfillment_Status": "first"  # status
        }).reset_index()

        for _, row in orders_grouped.iterrows():
            order_num = row["Order_Number"]
            item_count = row["SKU"]
            status = row["Order_Fulfillment_Status"]

            # Format display text
            display_text = f"{order_num} ({item_count} items, {status})"

            # Add to combo with order_num as user data
            self.order_combo.addItem(display_text, userData=order_num)

    def populate_products(self):
        """Populate product dropdown from stock DataFrame."""
        if self.stock_df is None or self.stock_df.empty:
            logger.warning("No stock data available")
            return

        if "Product_Name" not in self.stock_df.columns:
            logger.warning("Stock file has no Product_Name column")
            # Fall back to showing just SKU
            for _, row in self.stock_df.iterrows():
                sku = row["SKU"]
                stock = row.get("Stock", 0)
                display_text = f"{sku} ({stock} in stock)"
                user_data = {
                    "sku": sku,
                    "name": sku,  # Use SKU as name if no Product_Name
                    "stock": stock
                }
                self.product_combo.addItem(display_text, userData=user_data)
            return

        for _, row in self.stock_df.iterrows():
            sku = row["SKU"]
            name = row.get("Product_Name", "")
            stock = row.get("Stock", 0)

            # Format display text
            display_text = f"{sku} - {name} ({stock} in stock)"

            # Store full data as userData
            user_data = {
                "sku": sku,
                "name": name,
                "stock": stock
            }

            self.product_combo.addItem(display_text, userData=user_data)

    def _on_product_changed(self, index):
        """Handle product selection change."""
        if index < 0:
            return

        product_data = self.product_combo.itemData(index)
        if not product_data:
            return

        stock = product_data.get("stock", 0)

        # Show warning if low/zero stock
        if stock == 0:
            warning_text = (
                "⚠️ WARNING\n\n"
                f"Selected product {product_data['sku']} has 0 stock available!\n"
                "Adding this product may affect order fulfillment.\n\n"
                "Do you want to continue?"
            )
            self.warning_box.setText(warning_text)
            self.warning_box.setVisible(True)
            self.warning_box.setStyleSheet("""
                QLabel {
                    background-color: #FFEBEE;
                    border: 2px solid #F44336;
                    border-radius: 5px;
                    padding: 10px;
                }
            """)
        elif stock < 5:
            warning_text = (
                "⚠️ WARNING\n\n"
                f"Selected product {product_data['sku']} has low stock ({stock} units).\n"
                "Consider checking availability."
            )
            self.warning_box.setText(warning_text)
            self.warning_box.setVisible(True)
            self.warning_box.setStyleSheet("""
                QLabel {
                    background-color: #FFF8E1;
                    border: 2px solid #FFC107;
                    border-radius: 5px;
                    padding: 10px;
                }
            """)
        else:
            self.warning_box.setVisible(False)

    def _on_add_clicked(self):
        """Handle Add Product button click."""
        # Validate inputs
        if not self._validate():
            return

        # Get selected values
        order_number = self.order_combo.currentData()
        product_data = self.product_combo.currentData()
        quantity = self.quantity_spin.value()

        # Store result
        self.result = {
            "order_number": order_number,
            "sku": product_data["sku"],
            "product_name": product_data["name"],
            "quantity": quantity
        }

        logger.info(f"Adding product: {self.result}")

        # Close dialog with accepted
        self.accept()

    def _validate(self):
        """Validate user inputs."""
        # Check order selected
        if self.order_combo.currentIndex() < 0:
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please select an order."
            )
            self.order_combo.setFocus()
            return False

        # Check product selected
        if self.product_combo.currentIndex() < 0:
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please select a product."
            )
            self.product_combo.setFocus()
            return False

        # Check quantity
        if self.quantity_spin.value() < 1:
            QMessageBox.warning(
                self,
                "Validation Error",
                "Quantity must be at least 1."
            )
            self.quantity_spin.setFocus()
            return False

        return True

    def get_result(self):
        """Get dialog result after accept."""
        return self.result
