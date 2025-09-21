"""
Note styling dialog for the Digital Whiteboard application.

This module contains the NoteStyleDialog class which provides a comprehensive
interface for customizing note appearance including colors, fonts, and formatting.
"""

from typing import Any
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QColorDialog,
    QFontDialog,
    QSpinBox,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QFrame,
    QDialogButtonBox,
    QWidget,
)

from .utils.logging_config import get_logger


class ColorButton(QPushButton):
    """A button that displays a color and opens a color picker when clicked."""

    color_changed = pyqtSignal(QColor)

    def __init__(self, initial_color: QColor = QColor(255, 255, 255)):
        super().__init__()
        self._color = initial_color
        self.setFixedSize(60, 30)
        self.clicked.connect(self._pick_color)
        self._update_appearance()

    def _update_appearance(self):
        """Update button appearance to show current color."""
        # Create style sheet with current color
        style = f"""
            QPushButton {{
                background-color: {self._color.name()};
                border: 2px solid #666;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 2px solid #333;
            }}
            QPushButton:pressed {{
                border: 2px solid #000;
            }}
        """
        self.setStyleSheet(style)

        # Set tooltip with color info
        self.setToolTip(f"Color: {self._color.name()}\nClick to change")

    def _pick_color(self):
        """Open color picker dialog."""
        color = QColorDialog.getColor(self._color, self, "Choose Color")
        if color.isValid():
            self.set_color(color)

    def set_color(self, color: QColor):
        """Set the current color."""
        self._color = color
        self._update_appearance()
        self.color_changed.emit(color)

    def get_color(self) -> QColor:
        """Get the current color."""
        return self._color


class FontPreviewLabel(QLabel):
    """A label that shows a font preview."""

    def __init__(self, text: str = "Sample Text"):
        super().__init__(text)
        self.setMinimumHeight(40)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet("QLabel { background-color: white; padding: 5px; }")

    def update_font_preview(self, font: QFont, color: QColor):
        """Update the preview with new font and color."""
        self.setFont(font)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.WindowText, color)
        self.setPalette(palette)


class NoteStyleDialog(QDialog):
    """
    Dialog for customizing note appearance.

    Provides comprehensive styling options including:
    - Background and text colors
    - Font family, size, and formatting
    - Border and corner radius settings
    - Preview of changes

    Requirements addressed:
    - 4.1: Note appearance customization
    - 4.2: Text and background color customization
    - 4.3: Font selection and text formatting options
    """

    style_applied = pyqtSignal(dict)

    def __init__(self, initial_style: dict[str, Any], parent: QWidget | None = None):
        super().__init__(parent)
        self.logger = get_logger(__name__)

        # Store initial style
        self._initial_style = initial_style.copy()
        self._current_style = initial_style.copy()

        # Setup dialog
        self._setup_dialog()
        self._create_widgets()
        self._setup_layout()
        self._connect_signals()
        self._update_from_style()

        self.logger.debug("NoteStyleDialog initialized")

    def _setup_dialog(self):
        """Configure dialog properties."""
        self.setWindowTitle("Note Style")
        self.setModal(True)
        self.setMinimumSize(400, 500)
        self.resize(450, 600)

    def _create_widgets(self):
        """Create all dialog widgets."""
        # Color section
        self._create_color_widgets()

        # Font section
        self._create_font_widgets()

        # Border and appearance section
        self._create_appearance_widgets()

        # Preview section
        self._create_preview_widgets()

        # Button box
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Reset
        )

    def _create_color_widgets(self):
        """Create color selection widgets."""
        self._color_group = QGroupBox("Colors")

        # Background color
        self._bg_color_label = QLabel("Background:")
        self._bg_color_button = ColorButton()

        # Text color
        self._text_color_label = QLabel("Text:")
        self._text_color_button = ColorButton()

        # Border color
        self._border_color_label = QLabel("Border:")
        self._border_color_button = ColorButton()

    def _create_font_widgets(self):
        """Create font selection widgets."""
        self._font_group = QGroupBox("Font")

        # Font family
        self._font_family_label = QLabel("Family:")
        self._font_family_combo = QComboBox()
        self._font_family_combo.setEditable(False)

        # Populate with common fonts
        common_fonts = [
            "Arial",
            "Helvetica",
            "Times New Roman",
            "Courier New",
            "Verdana",
            "Georgia",
            "Comic Sans MS",
            "Impact",
            "Trebuchet MS",
            "Palatino",
            "Garamond",
        ]
        self._font_family_combo.addItems(common_fonts)

        # Font size
        self._font_size_label = QLabel("Size:")
        self._font_size_spin = QSpinBox()
        self._font_size_spin.setRange(8, 72)
        self._font_size_spin.setSuffix(" pt")

        # Font style checkboxes
        self._font_bold_check = QCheckBox("Bold")
        self._font_italic_check = QCheckBox("Italic")

        # Font picker button
        self._font_picker_button = QPushButton("Choose Font...")
        self._font_picker_button.setToolTip("Open font selection dialog")

    def _create_appearance_widgets(self):
        """Create appearance setting widgets."""
        self._appearance_group = QGroupBox("Appearance")

        # Border width
        self._border_width_label = QLabel("Border Width:")
        self._border_width_spin = QSpinBox()
        self._border_width_spin.setRange(0, 10)
        self._border_width_spin.setSuffix(" px")

        # Corner radius
        self._corner_radius_label = QLabel("Corner Radius:")
        self._corner_radius_spin = QSpinBox()
        self._corner_radius_spin.setRange(0, 20)
        self._corner_radius_spin.setSuffix(" px")

        # Padding
        self._padding_label = QLabel("Padding:")
        self._padding_spin = QSpinBox()
        self._padding_spin.setRange(5, 30)
        self._padding_spin.setSuffix(" px")

        # Minimum size
        self._min_width_label = QLabel("Min Width:")
        self._min_width_spin = QSpinBox()
        self._min_width_spin.setRange(50, 300)
        self._min_width_spin.setSuffix(" px")

        self._min_height_label = QLabel("Min Height:")
        self._min_height_spin = QSpinBox()
        self._min_height_spin.setRange(30, 200)
        self._min_height_spin.setSuffix(" px")

    def _create_preview_widgets(self):
        """Create preview widgets."""
        self._preview_group = QGroupBox("Preview")

        # Preview label
        self._preview_label = FontPreviewLabel("Sample Note Text")
        self._preview_label.setMinimumHeight(80)

        # Preview description
        self._preview_desc = QLabel("This shows how your note will look")
        self._preview_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_desc.setStyleSheet("color: #666; font-size: 11px;")

    def _setup_layout(self):
        """Setup dialog layout."""
        main_layout = QVBoxLayout(self)

        # Color group layout
        color_layout = QGridLayout(self._color_group)
        color_layout.addWidget(self._bg_color_label, 0, 0)
        color_layout.addWidget(self._bg_color_button, 0, 1)
        color_layout.addWidget(self._text_color_label, 1, 0)
        color_layout.addWidget(self._text_color_button, 1, 1)
        color_layout.addWidget(self._border_color_label, 2, 0)
        color_layout.addWidget(self._border_color_button, 2, 1)
        color_layout.setColumnStretch(2, 1)  # Add stretch to right

        # Font group layout
        font_layout = QGridLayout(self._font_group)
        font_layout.addWidget(self._font_family_label, 0, 0)
        font_layout.addWidget(self._font_family_combo, 0, 1, 1, 2)
        font_layout.addWidget(self._font_size_label, 1, 0)
        font_layout.addWidget(self._font_size_spin, 1, 1)

        # Font style checkboxes in horizontal layout
        font_style_layout = QHBoxLayout()
        font_style_layout.addWidget(self._font_bold_check)
        font_style_layout.addWidget(self._font_italic_check)
        font_style_layout.addStretch()

        font_layout.addLayout(font_style_layout, 2, 0, 1, 3)
        font_layout.addWidget(self._font_picker_button, 3, 0, 1, 3)

        # Appearance group layout
        appearance_layout = QGridLayout(self._appearance_group)
        appearance_layout.addWidget(self._border_width_label, 0, 0)
        appearance_layout.addWidget(self._border_width_spin, 0, 1)
        appearance_layout.addWidget(self._corner_radius_label, 1, 0)
        appearance_layout.addWidget(self._corner_radius_spin, 1, 1)
        appearance_layout.addWidget(self._padding_label, 2, 0)
        appearance_layout.addWidget(self._padding_spin, 2, 1)
        appearance_layout.addWidget(self._min_width_label, 3, 0)
        appearance_layout.addWidget(self._min_width_spin, 3, 1)
        appearance_layout.addWidget(self._min_height_label, 4, 0)
        appearance_layout.addWidget(self._min_height_spin, 4, 1)
        appearance_layout.setColumnStretch(2, 1)  # Add stretch to right

        # Preview group layout
        preview_layout = QVBoxLayout(self._preview_group)
        preview_layout.addWidget(self._preview_label)
        preview_layout.addWidget(self._preview_desc)

        # Add all groups to main layout
        main_layout.addWidget(self._color_group)
        main_layout.addWidget(self._font_group)
        main_layout.addWidget(self._appearance_group)
        main_layout.addWidget(self._preview_group)
        main_layout.addWidget(self._button_box)

    def _connect_signals(self):
        """Connect widget signals."""
        # Color changes
        self._bg_color_button.color_changed.connect(self._on_bg_color_changed)
        self._text_color_button.color_changed.connect(self._on_text_color_changed)
        self._border_color_button.color_changed.connect(self._on_border_color_changed)

        # Font changes
        self._font_family_combo.currentTextChanged.connect(self._on_font_family_changed)
        self._font_size_spin.valueChanged.connect(self._on_font_size_changed)
        self._font_bold_check.toggled.connect(self._on_font_bold_changed)
        self._font_italic_check.toggled.connect(self._on_font_italic_changed)
        self._font_picker_button.clicked.connect(self._open_font_dialog)

        # Appearance changes
        self._border_width_spin.valueChanged.connect(self._on_border_width_changed)
        self._corner_radius_spin.valueChanged.connect(self._on_corner_radius_changed)
        self._padding_spin.valueChanged.connect(self._on_padding_changed)
        self._min_width_spin.valueChanged.connect(self._on_min_width_changed)
        self._min_height_spin.valueChanged.connect(self._on_min_height_changed)

        # Button box
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)
        self._button_box.button(QDialogButtonBox.StandardButton.Reset).clicked.connect(
            self._reset_to_defaults
        )

    def _update_from_style(self):
        """Update all widgets from current style."""
        # Colors
        self._bg_color_button.set_color(self._current_style["background_color"])
        self._text_color_button.set_color(self._current_style["text_color"])
        self._border_color_button.set_color(self._current_style["border_color"])

        # Font
        font_family = self._current_style["font_family"]
        index = self._font_family_combo.findText(font_family)
        if index >= 0:
            self._font_family_combo.setCurrentIndex(index)
        else:
            self._font_family_combo.setCurrentText(font_family)

        self._font_size_spin.setValue(self._current_style["font_size"])
        self._font_bold_check.setChecked(self._current_style["font_bold"])
        self._font_italic_check.setChecked(self._current_style["font_italic"])

        # Appearance
        self._border_width_spin.setValue(self._current_style["border_width"])
        self._corner_radius_spin.setValue(self._current_style["corner_radius"])
        self._padding_spin.setValue(self._current_style["padding"])
        self._min_width_spin.setValue(self._current_style["min_width"])
        self._min_height_spin.setValue(self._current_style["min_height"])

        # Update preview
        self._update_preview()

    def _update_preview(self):
        """Update the preview with current style."""
        # Create font from current settings
        font = QFont(
            self._current_style["font_family"], self._current_style["font_size"]
        )
        font.setBold(self._current_style["font_bold"])
        font.setItalic(self._current_style["font_italic"])

        # Update preview
        self._preview_label.update_font_preview(font, self._current_style["text_color"])

        # Update preview background to match note background
        bg_color = self._current_style["background_color"]
        border_color = self._current_style["border_color"]
        border_width = self._current_style["border_width"]
        corner_radius = self._current_style["corner_radius"]

        style = f"""
            QLabel {{
                background-color: {bg_color.name()};
                border: {border_width}px solid {border_color.name()};
                border-radius: {corner_radius}px;
                padding: {self._current_style["padding"]}px;
            }}
        """
        self._preview_label.setStyleSheet(style)

    # Color change handlers
    def _on_bg_color_changed(self, color: QColor):
        """Handle background color change."""
        self._current_style["background_color"] = color
        self._update_preview()

    def _on_text_color_changed(self, color: QColor):
        """Handle text color change."""
        self._current_style["text_color"] = color
        self._update_preview()

    def _on_border_color_changed(self, color: QColor):
        """Handle border color change."""
        self._current_style["border_color"] = color
        self._update_preview()

    # Font change handlers
    def _on_font_family_changed(self, family: str):
        """Handle font family change."""
        self._current_style["font_family"] = family
        self._update_preview()

    def _on_font_size_changed(self, size: int):
        """Handle font size change."""
        self._current_style["font_size"] = size
        self._update_preview()

    def _on_font_bold_changed(self, bold: bool):
        """Handle font bold change."""
        self._current_style["font_bold"] = bold
        self._update_preview()

    def _on_font_italic_changed(self, italic: bool):
        """Handle font italic change."""
        self._current_style["font_italic"] = italic
        self._update_preview()

    def _open_font_dialog(self):
        """Open font selection dialog."""
        current_font = QFont(
            self._current_style["font_family"], self._current_style["font_size"]
        )
        current_font.setBold(self._current_style["font_bold"])
        current_font.setItalic(self._current_style["font_italic"])

        font, ok = QFontDialog.getFont(current_font, self, "Choose Font")
        if ok:
            # Update style from selected font
            self._current_style["font_family"] = font.family()
            self._current_style["font_size"] = font.pointSize()
            self._current_style["font_bold"] = font.bold()
            self._current_style["font_italic"] = font.italic()

            # Update widgets
            self._update_from_style()

    # Appearance change handlers
    def _on_border_width_changed(self, width: int):
        """Handle border width change."""
        self._current_style["border_width"] = width
        self._update_preview()

    def _on_corner_radius_changed(self, radius: int):
        """Handle corner radius change."""
        self._current_style["corner_radius"] = radius
        self._update_preview()

    def _on_padding_changed(self, padding: int):
        """Handle padding change."""
        self._current_style["padding"] = padding
        self._update_preview()

    def _on_min_width_changed(self, width: int):
        """Handle minimum width change."""
        self._current_style["min_width"] = width

    def _on_min_height_changed(self, height: int):
        """Handle minimum height change."""
        self._current_style["min_height"] = height

    def _reset_to_defaults(self):
        """Reset style to default values."""
        default_style = {
            "background_color": QColor(255, 255, 200),  # Light yellow
            "border_color": QColor(200, 200, 150),  # Darker yellow
            "text_color": QColor(0, 0, 0),  # Black text
            "border_width": 2,
            "corner_radius": 8,
            "padding": 10,
            "font_family": "Arial",
            "font_size": 12,
            "font_bold": False,
            "font_italic": False,
            "min_width": 100,
            "min_height": 60,
        }

        self._current_style = default_style
        self._update_from_style()

        self.logger.debug("Reset style to defaults")

    def get_style(self) -> dict[str, Any]:
        """Get the current style settings."""
        return self._current_style.copy()

    def accept(self):
        """Handle dialog acceptance."""
        self.style_applied.emit(self._current_style.copy())
        self.logger.debug(f"Style dialog accepted with style: {self._current_style}")
        super().accept()

    @staticmethod
    def get_note_style(
        initial_style: dict[str, Any], parent: QWidget | None = None
    ) -> dict[str, Any] | None:
        """
        Static method to get note style from user.

        Args:
            initial_style: Current note style
            parent: Parent widget

        Returns:
            New style dict if accepted, None if cancelled
        """
        dialog = NoteStyleDialog(initial_style, parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_style()
        return None
