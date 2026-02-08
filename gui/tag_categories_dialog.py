"""Tag Categories Management Dialog for Internal Tags system.

This module provides UI for creating, editing, and managing tag categories
with support for v2 format including order, colors, and SKU writeoff configuration.
"""

import logging
from typing import Dict, Optional, List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QWidget, QFormLayout, QSpinBox,
    QDialogButtonBox, QMessageBox, QColorDialog, QSplitter, QGroupBox,
    QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from shopify_tool.tag_manager import validate_tag_categories_v2

logger = logging.getLogger(__name__)


class TagCategoriesDialog(QDialog):
    """Dialog for managing tag categories (v2 format)."""

    # Signal emitted when categories are saved
    categories_updated = Signal(dict)

    def __init__(self, tag_categories: Dict, parent=None):
        """
        Initialize Tag Categories Dialog.

        Args:
            tag_categories: Tag categories dict (v2 format expected)
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Tag Categories Management")
        self.setModal(True)
        self.setMinimumSize(900, 600)

        # Store original and working copy
        self.original_categories = tag_categories.copy()
        self.working_categories = tag_categories.copy()

        # Ensure v2 format
        if "version" not in self.working_categories:
            self.working_categories = {
                "version": 2,
                "categories": self.working_categories
            }

        self.current_category_id: Optional[str] = None
        self.modified = False

        self._init_ui()
        self._load_categories()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Title
        title_label = QLabel("Manage Tag Categories")
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold; padding: 10px;")
        layout.addWidget(title_label)

        # Create splitter for two-panel layout
        splitter = QSplitter(Qt.Horizontal)

        # Left panel: Categories list
        left_panel = self._create_categories_list_panel()
        splitter.addWidget(left_panel)

        # Right panel: Category editor
        right_panel = self._create_category_editor_panel()
        splitter.addWidget(right_panel)

        # Set initial splitter sizes (30% left, 70% right)
        splitter.setSizes([270, 630])

        layout.addWidget(splitter)

        # Button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        button_box.accepted.connect(self._on_save)
        button_box.rejected.connect(self._on_cancel)
        button_box.button(QDialogButtonBox.Apply).clicked.connect(self._on_apply)
        layout.addWidget(button_box)

        self.button_box = button_box

    def _create_categories_list_panel(self) -> QWidget:
        """Create left panel with categories list."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header_label = QLabel("Categories")
        header_label.setStyleSheet("font-weight: bold; font-size: 11pt; padding: 5px;")
        layout.addWidget(header_label)

        # List widget
        self.categories_list = QListWidget()
        self.categories_list.currentItemChanged.connect(self._on_category_selected)
        layout.addWidget(self.categories_list)

        # Buttons
        buttons_layout = QHBoxLayout()

        self.new_category_btn = QPushButton("+ New")
        self.new_category_btn.setToolTip("Create new category")
        self.new_category_btn.clicked.connect(self._on_new_category)
        buttons_layout.addWidget(self.new_category_btn)

        self.delete_category_btn = QPushButton("Delete")
        self.delete_category_btn.setToolTip("Delete selected category")
        self.delete_category_btn.clicked.connect(self._on_delete_category)
        self.delete_category_btn.setEnabled(False)
        buttons_layout.addWidget(self.delete_category_btn)

        layout.addLayout(buttons_layout)

        return panel

    def _create_category_editor_panel(self) -> QWidget:
        """Create right panel with category editor."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        self.editor_header_label = QLabel("Category Editor")
        self.editor_header_label.setStyleSheet("font-weight: bold; font-size: 11pt; padding: 5px;")
        layout.addWidget(self.editor_header_label)

        # Form layout for category fields
        form_layout = QFormLayout()

        # Category ID (read-only for existing, editable for new)
        self.category_id_input = QLineEdit()
        self.category_id_input.setPlaceholderText("e.g., my_category")
        self.category_id_input.setToolTip(
            "Category ID (lowercase, underscores only)\n"
            "Cannot be changed for existing categories"
        )
        self.category_id_input.textChanged.connect(self._on_editor_changed)
        form_layout.addRow("Category ID:", self.category_id_input)

        # Display Label
        self.label_input = QLineEdit()
        self.label_input.setPlaceholderText("e.g., My Category")
        self.label_input.setToolTip("Display name for this category")
        self.label_input.textChanged.connect(self._on_editor_changed)
        form_layout.addRow("Display Label:", self.label_input)

        # Color picker
        color_layout = QHBoxLayout()
        self.color_display = QLabel()
        self.color_display.setFixedSize(40, 30)
        self.color_display.setStyleSheet("border: 1px solid #ccc; background-color: #9E9E9E;")
        color_layout.addWidget(self.color_display)

        self.color_button = QPushButton("Choose Color")
        self.color_button.clicked.connect(self._choose_color)
        color_layout.addWidget(self.color_button)
        color_layout.addStretch()

        self.current_color = "#9E9E9E"
        form_layout.addRow("Color:", color_layout)

        # Display Order
        self.order_spin = QSpinBox()
        self.order_spin.setMinimum(1)
        self.order_spin.setMaximum(999)
        self.order_spin.setValue(1)
        self.order_spin.setToolTip("Display order (lower numbers appear first)")
        self.order_spin.valueChanged.connect(self._on_editor_changed)
        form_layout.addRow("Display Order:", self.order_spin)

        layout.addLayout(form_layout)

        # Tags section
        tags_group = QGroupBox("Tags")
        tags_layout = QVBoxLayout(tags_group)

        # Tags list
        self.tags_list = QListWidget()
        self.tags_list.setMaximumHeight(150)
        tags_layout.addWidget(self.tags_list)

        # Add/Remove tag buttons
        tag_buttons_layout = QHBoxLayout()

        self.add_tag_btn = QPushButton("+ Add Tag")
        self.add_tag_btn.clicked.connect(self._on_add_tag)
        tag_buttons_layout.addWidget(self.add_tag_btn)

        self.remove_tag_btn = QPushButton("Remove Tag")
        self.remove_tag_btn.clicked.connect(self._on_remove_tag)
        self.remove_tag_btn.setEnabled(False)
        tag_buttons_layout.addWidget(self.remove_tag_btn)

        tag_buttons_layout.addStretch()

        tags_layout.addLayout(tag_buttons_layout)

        self.tags_list.itemSelectionChanged.connect(
            lambda: self.remove_tag_btn.setEnabled(len(self.tags_list.selectedItems()) > 0)
        )

        layout.addWidget(tags_group)

        # Placeholder for SKU Writeoff (Phase 3)
        # Will be implemented in Phase 3

        layout.addStretch()

        # Initially disable editor
        self._set_editor_enabled(False)

        return panel

    def _load_categories(self):
        """Load categories into the list widget."""
        self.categories_list.clear()

        categories = self.working_categories.get("categories", {})

        # Sort by order
        sorted_categories = sorted(
            categories.items(),
            key=lambda x: x[1].get("order", 999)
        )

        for category_id, category_config in sorted_categories:
            item = QListWidgetItem(category_config.get("label", category_id))
            item.setData(Qt.UserRole, category_id)

            # Show color indicator
            color = category_config.get("color", "#9E9E9E")
            item.setBackground(QColor(color).lighter(180))

            self.categories_list.addItem(item)

    def _on_category_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        """Handle category selection change."""
        if current is None:
            self._set_editor_enabled(False)
            self.current_category_id = None
            return

        category_id = current.data(Qt.UserRole)
        self.current_category_id = category_id

        # Load category into editor
        self._load_category_into_editor(category_id)
        self._set_editor_enabled(True)
        self.delete_category_btn.setEnabled(True)

    def _load_category_into_editor(self, category_id: str):
        """Load category data into editor fields."""
        categories = self.working_categories.get("categories", {})
        category = categories.get(category_id, {})

        # Block signals while loading
        self.category_id_input.blockSignals(True)
        self.label_input.blockSignals(True)
        self.order_spin.blockSignals(True)

        # Load fields
        self.category_id_input.setText(category_id)
        self.category_id_input.setReadOnly(True)  # Cannot change ID for existing

        self.label_input.setText(category.get("label", ""))
        self.current_color = category.get("color", "#9E9E9E")
        self.color_display.setStyleSheet(f"border: 1px solid #ccc; background-color: {self.current_color};")
        self.order_spin.setValue(category.get("order", 1))

        # Load tags
        self.tags_list.clear()
        for tag in category.get("tags", []):
            self.tags_list.addItem(tag)

        # Unblock signals
        self.category_id_input.blockSignals(False)
        self.label_input.blockSignals(False)
        self.order_spin.blockSignals(False)

        # Update header
        self.editor_header_label.setText(f"Editing: {category.get('label', category_id)}")

    def _set_editor_enabled(self, enabled: bool):
        """Enable/disable editor fields."""
        self.category_id_input.setEnabled(enabled)
        self.label_input.setEnabled(enabled)
        self.color_button.setEnabled(enabled)
        self.order_spin.setEnabled(enabled)
        self.tags_list.setEnabled(enabled)
        self.add_tag_btn.setEnabled(enabled)

        if not enabled:
            self.editor_header_label.setText("Category Editor")
            self.category_id_input.clear()
            self.label_input.clear()
            self.tags_list.clear()

    def _on_editor_changed(self):
        """Handle editor field changes."""
        if not self.current_category_id:
            return

        # Save changes to working copy
        self._save_editor_to_working_copy()
        self.modified = True

    def _save_editor_to_working_copy(self):
        """Save current editor state to working copy."""
        if not self.current_category_id:
            return

        categories = self.working_categories.setdefault("categories", {})

        # Get or create category
        category = categories.setdefault(self.current_category_id, {})

        # Update fields
        category["label"] = self.label_input.text()
        category["color"] = self.current_color
        category["order"] = self.order_spin.value()

        # Update tags
        tags = []
        for i in range(self.tags_list.count()):
            tags.append(self.tags_list.item(i).text())
        category["tags"] = tags

        # Ensure sku_writeoff structure exists
        if "sku_writeoff" not in category:
            category["sku_writeoff"] = {
                "enabled": False,
                "mappings": {}
            }

        # Update list item
        current_item = self.categories_list.currentItem()
        if current_item:
            current_item.setText(category["label"])
            current_item.setBackground(QColor(self.current_color).lighter(180))

    def _choose_color(self):
        """Open color picker dialog."""
        color = QColorDialog.getColor(
            QColor(self.current_color),
            self,
            "Choose Category Color"
        )

        if color.isValid():
            self.current_color = color.name()
            self.color_display.setStyleSheet(
                f"border: 1px solid #ccc; background-color: {self.current_color};"
            )
            self._on_editor_changed()

    def _on_add_tag(self):
        """Handle add tag button click."""
        from PySide6.QtWidgets import QInputDialog

        tag, ok = QInputDialog.getText(
            self,
            "Add Tag",
            "Enter tag name (UPPERCASE):",
            QLineEdit.Normal,
            ""
        )

        if ok and tag:
            tag = tag.strip().upper()

            if not tag:
                QMessageBox.warning(self, "Invalid Tag", "Tag cannot be empty.")
                return

            # Check for duplicates in current category
            existing_tags = [self.tags_list.item(i).text() for i in range(self.tags_list.count())]
            if tag in existing_tags:
                QMessageBox.warning(self, "Duplicate Tag", f"Tag '{tag}' already exists in this category.")
                return

            # Check for duplicates in other categories
            if self._is_tag_in_other_categories(tag):
                QMessageBox.warning(
                    self,
                    "Duplicate Tag",
                    f"Tag '{tag}' already exists in another category.\n"
                    "Each tag can only belong to one category."
                )
                return

            # Add tag
            self.tags_list.addItem(tag)
            self._on_editor_changed()

    def _on_remove_tag(self):
        """Handle remove tag button click."""
        selected_items = self.tags_list.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            self.tags_list.takeItem(self.tags_list.row(item))

        self._on_editor_changed()

    def _is_tag_in_other_categories(self, tag: str) -> bool:
        """Check if tag exists in other categories."""
        categories = self.working_categories.get("categories", {})

        for category_id, category_config in categories.items():
            if category_id == self.current_category_id:
                continue

            if tag in category_config.get("tags", []):
                return True

        return False

    def _on_new_category(self):
        """Handle new category button click."""
        from PySide6.QtWidgets import QInputDialog

        category_id, ok = QInputDialog.getText(
            self,
            "New Category",
            "Enter category ID (lowercase, underscores only):",
            QLineEdit.Normal,
            ""
        )

        if not ok or not category_id:
            return

        category_id = category_id.strip().lower()

        # Validate ID
        if not category_id:
            QMessageBox.warning(self, "Invalid ID", "Category ID cannot be empty.")
            return

        if not category_id.replace("_", "").isalnum():
            QMessageBox.warning(
                self,
                "Invalid ID",
                "Category ID can only contain lowercase letters, numbers, and underscores."
            )
            return

        # Check for duplicates
        categories = self.working_categories.get("categories", {})
        if category_id in categories:
            QMessageBox.warning(self, "Duplicate ID", f"Category '{category_id}' already exists.")
            return

        # Create new category
        new_category = {
            "label": category_id.replace("_", " ").title(),
            "color": "#9E9E9E",
            "order": len(categories) + 1,
            "tags": [],
            "sku_writeoff": {
                "enabled": False,
                "mappings": {}
            }
        }

        categories[category_id] = new_category
        self.modified = True

        # Reload list and select new category
        self._load_categories()

        # Find and select new item
        for i in range(self.categories_list.count()):
            item = self.categories_list.item(i)
            if item.data(Qt.UserRole) == category_id:
                self.categories_list.setCurrentItem(item)
                break

    def _on_delete_category(self):
        """Handle delete category button click."""
        if not self.current_category_id:
            return

        categories = self.working_categories.get("categories", {})
        category = categories.get(self.current_category_id, {})

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Delete Category",
            f"Are you sure you want to delete category '{category.get('label', self.current_category_id)}'?\n\n"
            f"This category has {len(category.get('tags', []))} tags.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            del categories[self.current_category_id]
            self.modified = True

            # Clear selection and reload
            self.current_category_id = None
            self._load_categories()
            self._set_editor_enabled(False)
            self.delete_category_btn.setEnabled(False)

    def _validate_categories(self) -> bool:
        """Validate current categories configuration."""
        # Save current editor state first
        if self.current_category_id:
            self._save_editor_to_working_copy()

        # Validate using tag_manager validator
        is_valid, errors = validate_tag_categories_v2(self.working_categories)

        if not is_valid:
            error_msg = "Validation errors:\n\n" + "\n".join(f"- {err}" for err in errors)
            QMessageBox.critical(self, "Validation Failed", error_msg)
            return False

        return True

    def _on_apply(self):
        """Handle Apply button click (save without closing)."""
        if not self._validate_categories():
            return

        self.categories_updated.emit(self.working_categories)
        self.modified = False

        QMessageBox.information(
            self,
            "Saved",
            "Tag categories have been saved successfully."
        )

    def _on_save(self):
        """Handle Save button click (save and close)."""
        if not self._validate_categories():
            return

        self.categories_updated.emit(self.working_categories)
        self.accept()

    def _on_cancel(self):
        """Handle Cancel button click."""
        if self.modified:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Are you sure you want to cancel?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.No:
                return

        self.reject()

    def get_categories(self) -> Dict:
        """Get the current categories configuration."""
        return self.working_categories
