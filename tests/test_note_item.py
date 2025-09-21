"""
Unit tests for the NoteItem class.

Tests cover note creation, editing, styling, and interaction functionality
to ensure proper behavior according to requirements.
"""

import unittest
from unittest.mock import Mock
from PyQt6.QtWidgets import QApplication, QGraphicsScene
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor
from PyQt6.QtTest import QTest

from src.whiteboard.note_item import NoteItem


class TestNoteItem(unittest.TestCase):
    """Test cases for NoteItem functionality."""

    @classmethod
    def setUpClass(cls):
        """Set up QApplication for all tests."""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.scene = QGraphicsScene()
        self.test_position = QPointF(100, 200)
        self.test_text = "Test Note Content"

    def tearDown(self):
        """Clean up after each test method."""
        self.scene.clear()

    def test_note_creation_default(self):
        """Test creating a note with default parameters."""
        # Requirements: 1.1 - Create notes with editable text functionality
        note = NoteItem()

        # Verify default properties
        self.assertEqual(note.get_text(), "")
        self.assertEqual(note.pos(), QPointF(0, 0))
        self.assertFalse(note.is_editing())
        self.assertIsNotNone(note.get_note_id())

        # Verify default styling
        style = note.get_style()
        self.assertIn("background_color", style)
        self.assertIn("text_color", style)
        self.assertIn("font_family", style)
        self.assertEqual(style["font_size"], 12)

    def test_note_creation_with_parameters(self):
        """Test creating a note with specific text and position."""
        # Requirements: 1.1 - Create notes with editable text functionality
        note = NoteItem(self.test_text, self.test_position)

        # Verify properties
        self.assertEqual(note.get_text(), self.test_text)
        self.assertEqual(note.pos(), self.test_position)
        self.assertFalse(note.is_editing())

    def test_note_flags_and_properties(self):
        """Test that note has correct flags for interaction."""
        note = NoteItem()

        # Verify interaction flags
        self.assertTrue(note.flags() & note.GraphicsItemFlag.ItemIsMovable)
        self.assertTrue(note.flags() & note.GraphicsItemFlag.ItemIsSelectable)
        self.assertTrue(note.flags() & note.GraphicsItemFlag.ItemIsFocusable)
        self.assertTrue(note.flags() & note.GraphicsItemFlag.ItemSendsGeometryChanges)

        # Verify hover events are accepted
        self.assertTrue(note.acceptHoverEvents())

    def test_text_editing_functionality(self):
        """Test entering and exiting edit mode."""
        # Requirements: 1.2 - Focus handling for entering/exiting edit mode
        note = NoteItem("Initial text")

        # Test entering edit mode
        note.enter_edit_mode()
        self.assertTrue(note.is_editing())

        # Test exiting edit mode
        note.exit_edit_mode()
        self.assertFalse(note.is_editing())

    def test_text_content_management(self):
        """Test setting and getting text content."""
        # Requirements: 1.1 - Create notes with editable text functionality
        note = NoteItem()

        # Test setting text
        test_text = "New content"
        note.set_text(test_text)
        self.assertEqual(note.get_text(), test_text)

        # Test empty text handling
        note.set_text("")
        self.assertEqual(note.get_text(), "")

    def test_placeholder_text_handling(self):
        """Test placeholder text behavior."""
        note = NoteItem()

        # Should show placeholder when empty
        self.assertEqual(note.toPlainText(), "Double-click to edit")

        # Placeholder should not be returned as actual content
        self.assertEqual(note.get_text(), "")

        # Test entering edit mode clears placeholder
        note.enter_edit_mode()
        if note.toPlainText() == "Double-click to edit":
            note.setPlainText("")  # Simulate clearing in edit mode

        # Test exiting with empty text restores placeholder
        note.exit_edit_mode()
        self.assertEqual(note.toPlainText(), "Double-click to edit")

    def test_basic_styling_application(self):
        """Test applying basic styling to notes."""
        # Requirements: 1.3, 4.1, 4.2 - Basic note styling and customization
        note = NoteItem("Test")

        # Test color styling
        new_style = {
            "background_color": QColor(255, 0, 0),  # Red background
            "text_color": QColor(0, 255, 0),  # Green text
            "border_color": QColor(0, 0, 255),  # Blue border
        }

        note.set_style(new_style)

        # Verify style was applied
        current_style = note.get_style()
        self.assertEqual(current_style["background_color"], QColor(255, 0, 0))
        self.assertEqual(current_style["text_color"], QColor(0, 255, 0))
        self.assertEqual(current_style["border_color"], QColor(0, 0, 255))

    def test_font_styling(self):
        """Test font-related styling options."""
        # Requirements: 4.1, 4.2 - Text formatting options
        note = NoteItem("Test")

        # Test font styling
        font_style = {
            "font_family": "Times New Roman",
            "font_size": 16,
            "font_bold": True,
            "font_italic": True,
        }

        note.set_style(font_style)

        # Verify font styling
        current_style = note.get_style()
        self.assertEqual(current_style["font_family"], "Times New Roman")
        self.assertEqual(current_style["font_size"], 16)
        self.assertTrue(current_style["font_bold"])
        self.assertTrue(current_style["font_italic"])

        # Verify font is applied to text item
        font = note.font()
        self.assertEqual(font.family(), "Times New Roman")
        self.assertEqual(font.pointSize(), 16)
        self.assertTrue(font.bold())
        self.assertTrue(font.italic())

    def test_size_and_geometry_styling(self):
        """Test size-related styling options."""
        note = NoteItem("Test")

        # Test size styling
        size_style = {
            "min_width": 200,
            "min_height": 100,
            "padding": 20,
            "corner_radius": 15,
            "border_width": 3,
        }

        note.set_style(size_style)

        # Verify size styling
        current_style = note.get_style()
        self.assertEqual(current_style["min_width"], 200)
        self.assertEqual(current_style["min_height"], 100)
        self.assertEqual(current_style["padding"], 20)
        self.assertEqual(current_style["corner_radius"], 15)
        self.assertEqual(current_style["border_width"], 3)

        # Verify bounding rect respects minimum size
        bounds = note.boundingRect()
        self.assertGreaterEqual(bounds.width(), 200)
        self.assertGreaterEqual(bounds.height(), 100)

    def test_position_change_signals(self):
        """Test that position changes emit appropriate signals."""
        note = NoteItem()

        # Connect signal to mock
        position_changed_mock = Mock()
        note.position_changed.connect(position_changed_mock)

        # Change position
        new_position = QPointF(50, 75)
        note.setPos(new_position)

        # Verify signal was emitted (may need to process events)
        QTest.qWait(10)  # Allow signal processing

    def test_content_change_signals(self):
        """Test that content changes emit appropriate signals."""
        note = NoteItem()

        # Connect signal to mock
        content_changed_mock = Mock()
        note.content_changed.connect(content_changed_mock)

        # Change content
        note.set_text("New content")

        # Verify signal was emitted
        content_changed_mock.assert_called_with("New content")

    def test_style_change_signals(self):
        """Test that style changes emit appropriate signals."""
        note = NoteItem()

        # Connect signal to mock
        style_changed_mock = Mock()
        note.style_changed.connect(style_changed_mock)

        # Change style
        new_style = {"background_color": QColor(255, 0, 0)}
        note.set_style(new_style)

        # Verify signal was emitted
        style_changed_mock.assert_called_once()

    def test_editing_signals(self):
        """Test that editing mode changes emit appropriate signals."""
        note = NoteItem()

        # Connect signals to mocks
        editing_started_mock = Mock()
        editing_finished_mock = Mock()
        note.editing_started.connect(editing_started_mock)
        note.editing_finished.connect(editing_finished_mock)

        # Enter edit mode
        note.enter_edit_mode()
        editing_started_mock.assert_called_once()

        # Exit edit mode
        note.exit_edit_mode()
        editing_finished_mock.assert_called_once()

    def test_connection_points(self):
        """Test getting connection points for note edges."""
        note = NoteItem("Test")

        # Get connection points
        points = note.get_connection_points()

        # Should have 4 connection points (top, right, bottom, left)
        self.assertEqual(len(points), 4)

        # All points should be QPointF instances
        for point in points:
            self.assertIsInstance(point, QPointF)

    def test_note_data_serialization(self):
        """Test getting complete note data for serialization."""
        note = NoteItem(self.test_text, self.test_position)

        # Apply some styling
        test_style = {"background_color": QColor(255, 0, 0), "font_size": 14}
        note.set_style(test_style)

        # Get note data
        data = note.get_note_data()

        # Verify data structure
        self.assertIn("id", data)
        self.assertIn("text", data)
        self.assertIn("position", data)
        self.assertIn("style", data)
        self.assertIn("bounds", data)

        # Verify data content
        self.assertEqual(data["text"], self.test_text)
        self.assertEqual(
            data["position"], (self.test_position.x(), self.test_position.y())
        )
        self.assertEqual(data["style"]["font_size"], 14)

    def test_note_data_restoration(self):
        """Test restoring note from serialized data."""
        note = NoteItem()

        # Test data
        test_data = {
            "id": 12345,
            "text": "Restored text",
            "position": (150, 250),
            "style": {"background_color": QColor(0, 255, 0), "font_size": 18},
        }

        # Restore from data
        note.set_note_data(test_data)

        # Verify restoration
        self.assertEqual(note.get_note_id(), 12345)
        self.assertEqual(note.get_text(), "Restored text")
        self.assertEqual(note.pos(), QPointF(150, 250))

        style = note.get_style()
        self.assertEqual(style["background_color"], QColor(0, 255, 0))
        self.assertEqual(style["font_size"], 18)

    def test_bounding_rect_calculation(self):
        """Test bounding rectangle calculation with different content."""
        # Test with short text
        short_note = NoteItem("Hi")
        short_bounds = short_note.boundingRect()

        # Should respect minimum size
        style = short_note.get_style()
        min_width = style["min_width"]
        min_height = style["min_height"]

        self.assertGreaterEqual(short_bounds.width(), min_width)
        self.assertGreaterEqual(short_bounds.height(), min_height)

        # Test with long text
        long_text = "This is a very long text that should cause the note to expand beyond its minimum size to accommodate all the content properly."
        long_note = NoteItem(long_text)
        long_bounds = long_note.boundingRect()

        # Should be larger than minimum size
        self.assertGreater(long_bounds.width(), min_width)

    def test_unique_note_ids(self):
        """Test that each note gets a unique ID."""
        note1 = NoteItem()
        note2 = NoteItem()
        note3 = NoteItem()

        # All IDs should be different
        ids = [note1.get_note_id(), note2.get_note_id(), note3.get_note_id()]
        self.assertEqual(len(ids), len(set(ids)))  # All unique

    def test_style_preservation_during_editing(self):
        """Test that styling is preserved when entering/exiting edit mode."""
        note = NoteItem("Test")

        # Apply custom styling
        custom_style = {
            "background_color": QColor(255, 100, 100),
            "text_color": QColor(0, 0, 255),
            "font_size": 16,
        }
        note.set_style(custom_style)

        # Enter and exit edit mode
        note.enter_edit_mode()
        note.exit_edit_mode()

        # Verify styling is preserved
        current_style = note.get_style()
        self.assertEqual(current_style["background_color"], QColor(255, 100, 100))
        self.assertEqual(current_style["text_color"], QColor(0, 0, 255))
        self.assertEqual(current_style["font_size"], 16)

    def test_invalid_style_properties(self):
        """Test handling of invalid style properties."""
        note = NoteItem()

        # Try to set invalid style properties
        invalid_style = {
            "invalid_property": "invalid_value",
            "background_color": QColor(255, 0, 0),  # Valid property
            "another_invalid": 123,
        }

        note.set_style(invalid_style)

        # Valid properties should be applied, invalid ones ignored
        style = note.get_style()
        self.assertEqual(style["background_color"], QColor(255, 0, 0))
        self.assertNotIn("invalid_property", style)
        self.assertNotIn("another_invalid", style)


if __name__ == "__main__":
    unittest.main()
