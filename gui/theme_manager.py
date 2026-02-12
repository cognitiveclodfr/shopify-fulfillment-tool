"""Theme Manager - Centralized theme management for the application.

This module provides a centralized theme system with light and dark color palettes,
theme switching capabilities, and persistent theme settings.
"""

import logging
from dataclasses import dataclass
from typing import Optional
from PySide6.QtCore import QObject, Signal, QSettings
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor

logger = logging.getLogger(__name__)


@dataclass
class ThemeColors:
    """Color palette for a theme.

    Defines all colors used throughout the application UI.
    Colors are stored as hex strings (e.g., "#FFFFFF").
    """
    # Main backgrounds
    background: str              # Main window background
    background_elevated: str     # Cards, dialogs (slightly lighter/darker)

    # Text colors
    text: str                    # Primary text
    text_secondary: str          # Secondary/muted text

    # Borders
    border: str                  # Main borders (crisp and clear)
    border_subtle: str           # Internal dividers (less prominent)

    # Interactive states
    hover: str                   # Hover state background
    active_background: str       # Active item background
    active_border: str           # Active item border

    # Accent colors (semantic colors - same for both themes)
    accent_green: str = "#4CAF50"    # Success, fulfillable items
    accent_blue: str = "#1565C0"     # Selection, info, primary actions (muted blue)
    accent_orange: str = "#FF9800"   # Badges, warnings, emphasis
    accent_red: str = "#F44336"      # Errors, not fulfillable items

    # Button hover states (theme-specific)
    button_hover_light: str = "#0D47A1"  # Darker blue for light theme
    button_hover_dark: str = "#1976D2"   # Lighter blue for dark theme


# Light Theme (Current/Default)
LightTheme = ThemeColors(
    background="#FFFFFF",
    background_elevated="#F5F5F5",  # Light gray for input fields visibility
    text="#333333",
    text_secondary="#666666",
    border="#CCCCCC",
    border_subtle="#E0E0E0",
    hover="#EEEEEE",
    active_background="#F0F8F0",
    active_border="#4CAF50",
    button_hover_light="#1976D2",
    button_hover_dark="#42A5F5",
)

# Dark Theme (High Contrast - user requirement)
DarkTheme = ThemeColors(
    background="#000000",         # Pure black background (user requirement)
    background_elevated="#000000",  # Pure black for maximum contrast
    text="#FFFFFF",
    text_secondary="#B0B0B0",
    border="#FFFFFF",           # Crisp white borders (user requirement)
    border_subtle="#404040",    # Less prominent dividers
    hover="#1A1A1A",            # Subtle hover (slightly lighter than black)
    active_background="#1A3D1A",  # Dark green tint
    active_border="#4CAF50",      # Bright green
    button_hover_light="#1976D2",
    button_hover_dark="#42A5F5",
)


class ThemeManager(QObject):
    """Manages application themes.

    Provides centralized theme management with:
    - Light and dark theme switching
    - Persistent theme settings via QSettings
    - Global stylesheet application
    - Theme change signals for dynamic widget updates

    Signals:
        theme_changed: Emitted when theme is changed (no parameters)
    """

    theme_changed = Signal()

    # Singleton instance
    _instance: Optional['ThemeManager'] = None

    def __new__(cls):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize ThemeManager."""
        if self._initialized:
            return

        super().__init__()
        self._initialized = True
        self._current_theme_name = "light"  # Default
        self._themes = {
            "light": LightTheme,
            "dark": DarkTheme,
        }

        # Load saved theme preference
        self._load_theme_preference()

        logger.info(f"ThemeManager initialized with theme: {self._current_theme_name}")

    def get_current_theme(self) -> ThemeColors:
        """Get the currently active theme colors.

        Returns:
            ThemeColors: The active theme's color palette
        """
        return self._themes[self._current_theme_name]

    def is_dark_theme(self) -> bool:
        """Check if dark theme is active.

        Returns:
            bool: True if dark theme is active
        """
        return self._current_theme_name == "dark"

    def get_current_theme_name(self) -> str:
        """Get the name of the current theme.

        Returns:
            str: "light" or "dark"
        """
        return self._current_theme_name

    def toggle_theme(self):
        """Toggle between light and dark themes."""
        new_theme = "dark" if self._current_theme_name == "light" else "light"
        self.set_theme(new_theme)

    def set_theme(self, theme_name: str):
        """Set the active theme.

        Args:
            theme_name: "light" or "dark"
        """
        if theme_name not in self._themes:
            logger.warning(f"Unknown theme: {theme_name}, using light theme")
            theme_name = "light"

        if theme_name == self._current_theme_name:
            return  # No change

        self._current_theme_name = theme_name
        self._save_theme_preference()
        self.apply_theme()
        self.theme_changed.emit()

        logger.info(f"Theme changed to: {theme_name}")

    def apply_theme(self):
        """Apply the current theme to the application.

        Sets global stylesheet and QPalette for Qt widgets.
        """
        theme = self.get_current_theme()
        app = QApplication.instance()

        if app is None:
            logger.warning("QApplication not found, cannot apply theme")
            return

        # Build global stylesheet
        stylesheet = self._build_global_stylesheet(theme)
        app.setStyleSheet(stylesheet)

        # Set QPalette for native Qt widgets
        palette = self._build_palette(theme)
        app.setPalette(palette)

        logger.debug(f"Applied {self._current_theme_name} theme globally")

    def _build_global_stylesheet(self, theme: ThemeColors) -> str:
        """Build global Qt stylesheet.

        Args:
            theme: Theme colors to use

        Returns:
            str: Complete stylesheet string
        """
        # Determine button hover color based on theme
        button_hover = theme.button_hover_light if self._current_theme_name == "light" else theme.button_hover_dark

        stylesheet = f"""
            /* Global Widget Styling */
            QWidget {{
                background-color: {theme.background};
                color: {theme.text};
            }}

            /* Push Buttons */
            QPushButton {{
                background-color: {theme.accent_blue};
                color: white;
                border: 1px solid {theme.border};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 10pt;
            }}
            QPushButton:hover {{
                background-color: {button_hover};
            }}
            QPushButton:pressed {{
                background-color: #0D47A1;
            }}
            QPushButton:disabled {{
                background-color: {theme.background};
                color: {theme.text};
                border: 1px solid {theme.border};
            }}

            /* Input Fields */
            QLineEdit, QTextEdit, QPlainTextEdit {{
                background-color: {theme.background_elevated};
                color: {theme.text};
                border: 1px solid {theme.border};
                border-radius: 6px;
                padding: 4px 8px;
            }}
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
                border: 2px solid {theme.accent_blue};
            }}

            /* Combo Boxes */
            QComboBox {{
                background-color: {theme.background_elevated};
                color: {theme.text};
                border: 1px solid {theme.border};
                border-radius: 6px;
                padding: 4px 8px;
            }}
            QComboBox:hover {{
                border: 1px solid {theme.accent_blue};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {theme.background_elevated};
                color: {theme.text};
                selection-background-color: {theme.accent_blue};
                selection-color: white;
            }}

            /* Spin Boxes */
            QSpinBox, QDoubleSpinBox {{
                background-color: {theme.background_elevated};
                color: {theme.text};
                border: 1px solid {theme.border};
                border-radius: 6px;
                padding: 4px 8px;
            }}

            /* Check Boxes and Radio Buttons */
            QCheckBox, QRadioButton {{
                color: {theme.text};
                spacing: 8px;
                background-color: transparent;
            }}
            QCheckBox::indicator, QRadioButton::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {theme.border};
                border-radius: 4px;
                background-color: {theme.background};
            }}
            QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
                border: 2px solid {theme.accent_blue};
            }}
            QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
                background-color: {theme.accent_blue};
                border: 2px solid {theme.accent_blue};
                image: url(none);
            }}
            QCheckBox::indicator:checked:hover, QRadioButton::indicator:checked:hover {{
                background-color: {button_hover};
                border: 2px solid {button_hover};
            }}

            /* Group Boxes */
            QGroupBox {{
                color: {theme.text};
                border: 1px solid {theme.border};
                border-radius: 8px;
                padding-top: 24px;
                padding-bottom: 8px;
                padding-left: 8px;
                padding-right: 8px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: padding;
                subcontrol-position: top left;
                padding: 4px 8px;
                left: 8px;
                top: 4px;
            }}

            /* Labels */
            QLabel {{
                color: {theme.text};
                background-color: transparent;
            }}

            /* Tables */
            QTableView {{
                background-color: {theme.background};
                color: {theme.text};
                gridline-color: {theme.border_subtle};
                border: 1px solid {theme.border};
                border-radius: 8px;
            }}
            QTableView::item:selected {{
                background-color: {theme.accent_blue};
                color: white;
            }}
            QTableView::item:hover {{
                background-color: {theme.hover};
            }}
            QHeaderView::section {{
                background-color: {theme.background_elevated};
                color: {theme.text};
                border: 1px solid {theme.border};
                padding: 4px;
                font-weight: bold;
            }}
            QTableCornerButton::section {{
                background-color: {theme.background_elevated};
                border: 1px solid {theme.border};
            }}

            /* List Widgets */
            QListWidget {{
                background-color: {theme.background};
                color: {theme.text};
                border: 1px solid {theme.border};
                border-radius: 8px;
            }}
            QListWidget::item:selected {{
                background-color: {theme.accent_blue};
                color: white;
            }}
            QListWidget::item:hover {{
                background-color: {theme.hover};
            }}

            /* Scroll Bars */
            QScrollBar:vertical {{
                background-color: {theme.background};
                width: 12px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background-color: {theme.border};
                min-height: 20px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {theme.text_secondary};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background-color: {theme.background};
                height: 12px;
                border: none;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {theme.border};
                min-width: 20px;
                border-radius: 6px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: {theme.text_secondary};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}

            /* Tab Widget */
            QTabWidget::pane {{
                border: 1px solid {theme.border};
                background-color: {theme.background};
            }}
            QTabBar::tab {{
                background-color: {theme.background_elevated};
                color: {theme.text};
                border: 1px solid {theme.border};
                padding: 8px 16px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {theme.background};
                border-bottom-color: {theme.background};
                font-weight: bold;
            }}
            QTabBar::tab:hover {{
                background-color: {theme.hover};
            }}

            /* Status Bar */
            QStatusBar {{
                background-color: {theme.background_elevated};
                color: {theme.text};
                border-top: 1px solid {theme.border};
            }}

            /* Menu Bar */
            QMenuBar {{
                background-color: {theme.background};
                color: {theme.text};
            }}
            QMenuBar::item:selected {{
                background-color: {theme.hover};
            }}
            QMenu {{
                background-color: {theme.background_elevated};
                color: {theme.text};
                border: 1px solid {theme.border};
            }}
            QMenu::item:selected {{
                background-color: {theme.accent_blue};
                color: white;
            }}

            /* Tool Bar */
            QToolBar {{
                background-color: {theme.background_elevated};
                border: 1px solid {theme.border};
                spacing: 4px;
            }}

            /* Dialogs */
            QDialog {{
                background-color: {theme.background};
                color: {theme.text};
            }}
        """

        return stylesheet

    def _build_palette(self, theme: ThemeColors) -> QPalette:
        """Build QPalette for Qt widgets.

        Args:
            theme: Theme colors to use

        Returns:
            QPalette: Configured palette
        """
        palette = QPalette()

        # Window and base colors
        palette.setColor(QPalette.Window, QColor(theme.background))
        palette.setColor(QPalette.WindowText, QColor(theme.text))
        palette.setColor(QPalette.Base, QColor(theme.background_elevated))
        palette.setColor(QPalette.AlternateBase, QColor(theme.hover))
        palette.setColor(QPalette.Text, QColor(theme.text))

        # Button colors
        palette.setColor(QPalette.Button, QColor(theme.background_elevated))
        palette.setColor(QPalette.ButtonText, QColor(theme.text))

        # Highlight colors
        palette.setColor(QPalette.Highlight, QColor(theme.accent_blue))
        palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))

        # Link colors
        palette.setColor(QPalette.Link, QColor(theme.accent_blue))
        palette.setColor(QPalette.LinkVisited, QColor("#9C27B0"))

        # Disabled colors
        palette.setColor(QPalette.Disabled, QPalette.Text, QColor(theme.text_secondary))
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(theme.text_secondary))

        return palette

    def _save_theme_preference(self):
        """Save theme preference to QSettings."""
        try:
            settings = QSettings("ShopifyFulfillmentTool", "FulfillmentApp")
            settings.setValue("theme", self._current_theme_name)
            settings.sync()
            logger.debug(f"Saved theme preference: {self._current_theme_name}")
        except Exception as e:
            logger.error(f"Failed to save theme preference: {e}")

    def _load_theme_preference(self):
        """Load theme preference from QSettings."""
        try:
            settings = QSettings("ShopifyFulfillmentTool", "FulfillmentApp")
            saved_theme = settings.value("theme", "light")

            if saved_theme in self._themes:
                self._current_theme_name = saved_theme
                logger.debug(f"Loaded theme preference: {saved_theme}")
            else:
                logger.warning(f"Invalid saved theme: {saved_theme}, using light theme")
                self._current_theme_name = "light"
        except Exception as e:
            logger.error(f"Failed to load theme preference: {e}")
            self._current_theme_name = "light"


# Global singleton instance
_theme_manager_instance: Optional[ThemeManager] = None


def get_theme_manager() -> ThemeManager:
    """Get the global ThemeManager instance.

    Returns:
        ThemeManager: The singleton theme manager instance
    """
    global _theme_manager_instance
    if _theme_manager_instance is None:
        _theme_manager_instance = ThemeManager()
    return _theme_manager_instance
