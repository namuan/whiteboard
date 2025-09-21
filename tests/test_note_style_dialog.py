"""
Tests for the note style dialog functionality.

This module tests the NoteStyleDialog class and its integration with note styling.
"""

import pytest
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor, QFont

from src.whiteboard.note_style_dialog import (
    NoteStyleDialog,
    ColorButton,
    FontPreviewLabel,
)
from src.whiteboard.note_item import NoteItem


class TestColorButton:
    """Test the ColorButton widget."""

    @pytest.fixture
    def app(self):
        """Create QApplication instance."""
        return QApplication.instance() or QApplication([])

    @pytest.fixture
    def color_button(self, app):
        """Create a ColorButton instance."""
        return ColorButton(QColor(255, 0, 0))

    def test_color_button_initialization(self, color_button):
        """Test ColorButton initialization."""
        assert color_button.get_color() == QColor(255, 0, 0)
        assert color_button.size().width() == 60
        assert color_button.size().height() == 30

    def test_color_button_set_color(self, color_button):
        """Test setting color programmatically."""
        new_color = QColor(0, 255, 0)
        color_button.set_color(new_color)
        assert color_button.get_color() == new_color

    def test_color_button_signal_emission(self, color_button):
        """Test that color_changed signal is emitted."""
        signal_spy = Mock()
        color_button.color_changed.connect(signal_spy)

        new_color = QColor(0, 0, 255)
        color_button.set_color(new_color)

        signal_spy.assert_called_once_with(new_color)

    @patch("src.whiteboard.note_style_dialog.QColorDialog.getColor")
    def test_color_button_picker(self, mock_color_dialog, color_button):
        """Test color picker functionality."""
        # Mock color dialog to return a specific color
        new_color = QColor(128, 128, 128)
        mock_color_dialog.return_value = new_color

        # Simulate button click
        color_button._pick_color()

        assert color_button.get_color() == new_color
        mock_color_dialog.assert_called_once()


class TestFontPreviewLabel:
    """Test the FontPreviewLabel widget."""

    @pytest.fixture
    def app(self):
        """Create QApplication instance."""
        return QApplication.instance() or QApplication([])

    @pytest.fixture
    def preview_label(self, app):
        """Create a FontPreviewLabel instance."""
        return FontPreviewLabel("Test Text")

    def test_font_preview_initialization(self, preview_label):
        """Test FontPreviewLabel initialization."""
        assert preview_label.text() == "Test Text"
        assert preview_label.minimumHeight() == 40

    def test_font_preview_update(self, preview_label):
        """Test updating font preview."""
        font = QFont("Arial", 14)
        font.setBold(True)
        color = QColor(255, 0, 0)

        preview_label.update_font_preview(font, color)

        assert preview_label.font().family() == "Arial"
        assert preview_label.font().pointSize() == 14
        assert preview_label.font().bold()


class TestNoteStyleDialog:
    """Test the NoteStyleDialog class."""

    @pytest.fixture
    def app(self):
        """Create QApplication instance."""
        return QApplication.instance() or QApplication([])

    @pytest.fixture
    def initial_style(self):
        """Create initial style dictionary."""
        return {
            "background_color": QColor(255, 255, 200),
            "border_color": QColor(200, 200, 150),
            "text_color": QColor(0, 0, 0),
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

    @pytest.fixture
    def style_dialog(self, app, initial_style):
        """Create a NoteStyleDialog instance."""
        return NoteStyleDialog(initial_style)

    def test_dialog_initialization(self, style_dialog, initial_style):
        """Test dialog initialization."""
        assert style_dialog.windowTitle() == "Note Style"
        assert style_dialog.isModal()
        assert style_dialog.get_style() == initial_style

    def test_color_widget_initialization(self, style_dialog, initial_style):
        """Test that color widgets are initialized with correct values."""
        assert (
            style_dialog._bg_color_button.get_color()
            == initial_style["background_color"]
        )
        assert (
            style_dialog._text_color_button.get_color() == initial_style["text_color"]
        )
        assert (
            style_dialog._border_color_button.get_color()
            == initial_style["border_color"]
        )

    def test_font_widget_initialization(self, style_dialog, initial_style):
        """Test that font widgets are initialized with correct values."""
        assert (
            style_dialog._font_family_combo.currentText()
            == initial_style["font_family"]
        )
        assert style_dialog._font_size_spin.value() == initial_style["font_size"]
        assert style_dialog._font_bold_check.isChecked() == initial_style["font_bold"]
        assert (
            style_dialog._font_italic_check.isChecked() == initial_style["font_italic"]
        )

    def test_appearance_widget_initialization(self, style_dialog, initial_style):
        """Test that appearance widgets are initialized with correct values."""
        assert style_dialog._border_width_spin.value() == initial_style["border_width"]
        assert (
            style_dialog._corner_radius_spin.value() == initial_style["corner_radius"]
        )
        assert style_dialog._padding_spin.value() == initial_style["padding"]
        assert style_dialog._min_width_spin.value() == initial_style["min_width"]
        assert style_dialog._min_height_spin.value() == initial_style["min_height"]

    def test_background_color_change(self, style_dialog):
        """Test changing background color."""
        new_color = QColor(255, 0, 0)
        style_dialog._bg_color_button.set_color(new_color)

        current_style = style_dialog.get_style()
        assert current_style["background_color"] == new_color

    def test_text_color_change(self, style_dialog):
        """Test changing text color."""
        new_color = QColor(0, 255, 0)
        style_dialog._text_color_button.set_color(new_color)

        current_style = style_dialog.get_style()
        assert current_style["text_color"] == new_color

    def test_font_family_change(self, style_dialog):
        """Test changing font family."""
        new_family = "Times New Roman"
        style_dialog._font_family_combo.setCurrentText(new_family)

        current_style = style_dialog.get_style()
        assert current_style["font_family"] == new_family

    def test_font_size_change(self, style_dialog):
        """Test changing font size."""
        new_size = 16
        style_dialog._font_size_spin.setValue(new_size)

        current_style = style_dialog.get_style()
        assert current_style["font_size"] == new_size

    def test_font_bold_change(self, style_dialog):
        """Test changing font bold."""
        style_dialog._font_bold_check.setChecked(True)

        current_style = style_dialog.get_style()
        assert current_style["font_bold"]

    def test_font_italic_change(self, style_dialog):
        """Test changing font italic."""
        style_dialog._font_italic_check.setChecked(True)

        current_style = style_dialog.get_style()
        assert current_style["font_italic"]

    def test_border_width_change(self, style_dialog):
        """Test changing border width."""
        new_width = 5
        style_dialog._border_width_spin.setValue(new_width)

        current_style = style_dialog.get_style()
        assert current_style["border_width"] == new_width

    def test_corner_radius_change(self, style_dialog):
        """Test changing corner radius."""
        new_radius = 15
        style_dialog._corner_radius_spin.setValue(new_radius)

        current_style = style_dialog.get_style()
        assert current_style["corner_radius"] == new_radius

    def test_reset_to_defaults(self, style_dialog):
        """Test resetting to default values."""
        # Change some values first
        style_dialog._bg_color_button.set_color(QColor(255, 0, 0))
        style_dialog._font_size_spin.setValue(20)

        # Reset to defaults
        style_dialog._reset_to_defaults()

        current_style = style_dialog.get_style()
        assert current_style["background_color"] == QColor(255, 255, 200)
        assert current_style["font_size"] == 12

    @patch("src.whiteboard.note_style_dialog.QFontDialog.getFont")
    def test_font_dialog_integration(self, mock_font_dialog, style_dialog):
        """Test font dialog integration."""
        # Create a mock font
        mock_font = QFont("Helvetica", 18)
        mock_font.setBold(True)
        mock_font.setItalic(True)
        mock_font_dialog.return_value = (mock_font, True)

        # Open font dialog
        style_dialog._open_font_dialog()

        current_style = style_dialog.get_style()
        assert current_style["font_family"] == "Helvetica"
        assert current_style["font_size"] == 18
        assert current_style["font_bold"]
        assert current_style["font_italic"]

    def test_style_applied_signal(self, style_dialog):
        """Test that style_applied signal is emitted on accept."""
        signal_spy = Mock()
        style_dialog.style_applied.connect(signal_spy)

        # Accept dialog
        style_dialog.accept()

        signal_spy.assert_called_once()
        # Check that the signal was called with the current style
        args = signal_spy.call_args[0]
        assert isinstance(args[0], dict)

    def test_static_get_note_style_accepted(self, initial_style):
        """Test static method when dialog is accepted."""
        with patch(
            "src.whiteboard.note_style_dialog.NoteStyleDialog"
        ) as mock_dialog_class:
            mock_dialog = Mock()
            mock_dialog.exec.return_value = 1  # QDialog.Accepted
            mock_dialog.get_style.return_value = initial_style
            mock_dialog_class.return_value = mock_dialog

            result = NoteStyleDialog.get_note_style(initial_style)

            assert result == initial_style
            mock_dialog.exec.assert_called_once()

    def test_static_get_note_style_rejected(self, initial_style):
        """Test static method when dialog is rejected."""
        with patch(
            "src.whiteboard.note_style_dialog.NoteStyleDialog"
        ) as mock_dialog_class:
            mock_dialog = Mock()
            mock_dialog.exec.return_value = 0  # QDialog.Rejected
            mock_dialog_class.return_value = mock_dialog

            result = NoteStyleDialog.get_note_style(initial_style)

            assert result is None
            mock_dialog.exec.assert_called_once()


class TestNoteItemStyleIntegration:
    """Test integration between NoteItem and style dialog."""

    @pytest.fixture
    def app(self):
        """Create QApplication instance."""
        return QApplication.instance() or QApplication([])

    @pytest.fixture
    def note_item(self, app):
        """Create a NoteItem instance."""
        return NoteItem("Test Note", QPointF(0, 0))

    def test_note_item_default_style(self, note_item):
        """Test that note item has default style."""
        style = note_item.get_style()

        assert "background_color" in style
        assert "text_color" in style
        assert "font_family" in style
        assert "font_size" in style
        assert isinstance(style["background_color"], QColor)
        assert isinstance(style["text_color"], QColor)

    def test_note_item_set_style(self, note_item):
        """Test setting style on note item."""
        new_style = {
            "background_color": QColor(255, 0, 0),
            "text_color": QColor(0, 255, 0),
            "font_size": 16,
            "font_bold": True,
        }

        note_item.set_style(new_style)

        current_style = note_item.get_style()
        assert current_style["background_color"] == QColor(255, 0, 0)
        assert current_style["text_color"] == QColor(0, 255, 0)
        assert current_style["font_size"] == 16
        assert current_style["font_bold"]

    def test_note_item_style_persistence(self, note_item):
        """Test that style changes persist."""
        original_style = note_item.get_style()

        # Change style
        new_style = {"background_color": QColor(100, 100, 100)}
        note_item.set_style(new_style)

        # Verify change persisted
        current_style = note_item.get_style()
        assert current_style["background_color"] == QColor(100, 100, 100)

        # Verify other properties unchanged
        assert current_style["text_color"] == original_style["text_color"]
        assert current_style["font_family"] == original_style["font_family"]

    def test_note_item_style_signal_emission(self, note_item):
        """Test that style_changed signal is emitted."""
        signal_spy = Mock()
        note_item.style_changed.connect(signal_spy)

        new_style = {"background_color": QColor(255, 255, 255)}
        note_item.set_style(new_style)

        signal_spy.assert_called_once()
        # Verify the signal contains the complete updated style
        args = signal_spy.call_args[0]
        assert isinstance(args[0], dict)
        assert args[0]["background_color"] == QColor(255, 255, 255)

    @patch("src.whiteboard.note_style_dialog.NoteStyleDialog.get_note_style")
    def test_note_item_open_style_dialog(self, mock_get_style, note_item):
        """Test opening style dialog from note item."""
        # Mock the dialog to return a new style
        new_style = {"background_color": QColor(200, 200, 200), "font_size": 14}
        mock_get_style.return_value = new_style

        # Open style dialog
        note_item._open_style_dialog()

        # Verify dialog was called with current style
        mock_get_style.assert_called_once()
        call_args = mock_get_style.call_args[0]
        assert isinstance(call_args[0], dict)

        # Verify style was applied (partial update)
        current_style = note_item.get_style()
        assert current_style["background_color"] == QColor(200, 200, 200)
        assert current_style["font_size"] == 14

    @patch("src.whiteboard.note_style_dialog.NoteStyleDialog.get_note_style")
    def test_note_item_style_dialog_cancelled(self, mock_get_style, note_item):
        """Test when style dialog is cancelled."""
        # Mock the dialog to return None (cancelled)
        mock_get_style.return_value = None

        original_style = note_item.get_style().copy()

        # Open style dialog
        note_item._open_style_dialog()

        # Verify style unchanged
        current_style = note_item.get_style()
        assert current_style == original_style

    def test_note_item_context_menu_has_style_option(self, note_item):
        """Test that context menu includes style option."""
        # This is a basic test - in a real scenario you'd need to simulate
        # the context menu event and check the menu items
        # For now, we just verify the method exists
        assert hasattr(note_item, "_open_style_dialog")
        assert callable(note_item._open_style_dialog)


class TestStylePersistence:
    """Test style persistence and data serialization."""

    @pytest.fixture
    def app(self):
        """Create QApplication instance."""
        return QApplication.instance() or QApplication([])

    @pytest.fixture
    def styled_note(self, app):
        """Create a note with custom styling."""
        note = NoteItem("Styled Note", QPointF(10, 20))

        custom_style = {
            "background_color": QColor(255, 100, 100),
            "text_color": QColor(255, 255, 255),
            "font_family": "Times New Roman",
            "font_size": 16,
            "font_bold": True,
            "font_italic": True,
            "border_width": 3,
            "corner_radius": 12,
            "padding": 15,
        }

        note.set_style(custom_style)
        return note

    def _verify_style_colors(self, style):
        """Helper to verify style colors."""
        assert style["background_color"] == QColor(255, 100, 100)
        assert style["text_color"] == QColor(255, 255, 255)

    def _verify_style_font(self, style):
        """Helper to verify style font properties."""
        assert style["font_family"] == "Times New Roman"
        assert style["font_size"] == 16
        assert style["font_bold"]
        assert style["font_italic"]

    def _verify_style_appearance(self, style):
        """Helper to verify style appearance properties."""
        assert style["border_width"] == 3
        assert style["corner_radius"] == 12
        assert style["padding"] == 15

    def test_note_data_includes_style(self, styled_note):
        """Test that note data includes complete style information."""
        note_data = styled_note.get_note_data()
        assert "style" in note_data

        style = note_data["style"]
        self._verify_style_colors(style)
        self._verify_style_font(style)
        self._verify_style_appearance(style)

    def _create_test_note_data(self):
        """Helper to create test note data."""
        return {
            "id": 12345,
            "text": "Restored Note",
            "position": (50, 75),
            "style": {
                "background_color": QColor(100, 255, 100),
                "text_color": QColor(50, 50, 50),
                "font_family": "Courier New",
                "font_size": 14,
                "font_bold": False,
                "font_italic": True,
                "border_width": 1,
                "corner_radius": 5,
                "padding": 8,
                "min_width": 120,
                "min_height": 80,
            },
        }

    def _verify_restored_note_basic_props(self, note):
        """Helper to verify basic note properties."""
        assert note.get_text() == "Restored Note"
        assert note.pos() == QPointF(50, 75)

    def _verify_restored_colors(self, style):
        """Helper to verify restored note colors."""
        assert style["background_color"] == QColor(100, 255, 100)
        assert style["text_color"] == QColor(50, 50, 50)

    def _verify_restored_font(self, style):
        """Helper to verify restored note font."""
        assert style["font_family"] == "Courier New"
        assert style["font_size"] == 14
        assert not style["font_bold"]
        assert style["font_italic"]

    def _verify_restored_dimensions(self, style):
        """Helper to verify restored note dimensions."""
        assert style["border_width"] == 1
        assert style["corner_radius"] == 5
        assert style["padding"] == 8
        assert style["min_width"] == 120
        assert style["min_height"] == 80

    def _verify_restored_note_style(self, style):
        """Helper to verify restored note style."""
        self._verify_restored_colors(style)
        self._verify_restored_font(style)
        self._verify_restored_dimensions(style)

    def test_note_restoration_from_data(self, app):
        """Test restoring note from serialized data."""
        note_data = self._create_test_note_data()

        note = NoteItem()
        note.set_note_data(note_data)

        self._verify_restored_note_basic_props(note)
        self._verify_restored_note_style(note.get_style())
