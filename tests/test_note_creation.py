"""
Integration tests for note creation workflow.

Tests the complete workflow of creating notes via double-click on the canvas,
including automatic focus and edit mode activation.
"""

import unittest
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QMouseEvent

from src.whiteboard.canvas import WhiteboardCanvas, WhiteboardScene
from src.whiteboard.note_item import NoteItem


class TestNoteCreation(unittest.TestCase):
    """Test cases for note creation workflow."""

    @classmethod
    def setUpClass(cls):
        """Set up QApplication for all tests."""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.scene = WhiteboardScene()
        self.canvas = WhiteboardCanvas(self.scene)
        self.test_position = QPointF(100, 200)

    def tearDown(self):
        """Clean up after each test method."""
        self.scene.clear()

    def test_double_click_creates_note(self):
        """Test that double-clicking on empty canvas creates a note."""
        # Requirements: 1.1, 1.2 - Create notes via double-click
        initial_item_count = len(self.scene.items())

        # Create note at position
        note = self.canvas._create_note_at_position(self.test_position)

        # Verify note was created
        self.assertIsInstance(note, NoteItem)
        self.assertEqual(note.pos(), self.test_position)

        # Verify note was added to scene
        self.assertEqual(len(self.scene.items()), initial_item_count + 1)
        self.assertIn(note, self.scene.items())

    def test_note_creation_signal_emission(self):
        """Test that note creation emits the appropriate signal."""
        # Requirements: 1.1 - Signal emission for note creation
        note_created_mock = Mock()
        self.canvas.note_created.connect(note_created_mock)

        # Create note
        note = self.canvas._create_note_at_position(self.test_position)

        # Verify signal was emitted with correct note
        note_created_mock.assert_called_once_with(note)

    def test_new_note_enters_edit_mode(self):
        """Test that newly created notes automatically enter edit mode."""
        # Requirements: 1.2, 1.4 - Automatic focus and edit mode activation
        note = self.canvas._create_note_at_position(self.test_position)

        # Verify note is in edit mode (focus is set in _create_note_at_position)
        self.assertTrue(note.is_editing())

        # Note: Focus testing in unit tests can be unreliable due to window manager
        # The implementation calls setFocus() and enter_edit_mode() which we can verify

    def test_double_click_on_empty_canvas(self):
        """Test double-click event handling on empty canvas."""
        # Requirements: 1.1, 1.2 - Double-click note creation

        # Mock the scene itemAt method to return None (empty canvas)
        with patch.object(self.scene, "itemAt", return_value=None):
            # Mock the _create_note_at_position method to track calls
            with patch.object(self.canvas, "_create_note_at_position") as mock_create:
                # Simulate double-click event
                click_pos = self.canvas.mapFromScene(self.test_position)

                # Create mouse event (convert QPoint to QPointF)
                event = QMouseEvent(
                    QMouseEvent.Type.MouseButtonDblClick,
                    QPointF(click_pos),
                    Qt.MouseButton.LeftButton,
                    Qt.MouseButton.LeftButton,
                    Qt.KeyboardModifier.NoModifier,
                )

                # Handle the event
                self.canvas.mouseDoubleClickEvent(event)

                # Verify note creation was called
                mock_create.assert_called_once()

                # Get the position argument
                call_args = mock_create.call_args[0]
                created_position = call_args[0]

                # Verify position is approximately correct (allowing for coordinate transformation)
                self.assertAlmostEqual(
                    created_position.x(), self.test_position.x(), delta=1.0
                )
                self.assertAlmostEqual(
                    created_position.y(), self.test_position.y(), delta=1.0
                )

    def test_double_click_on_existing_item(self):
        """Test that double-clicking on existing item doesn't create new note."""
        # Requirements: 1.1 - Only create notes on empty canvas

        # Create an existing note
        existing_note = NoteItem("Existing", QPointF(50, 50))
        self.scene.addItem(existing_note)

        initial_item_count = len(self.scene.items())

        # Mock the scene itemAt method to return the existing note
        with patch.object(self.scene, "itemAt", return_value=existing_note):
            # Mock the _create_note_at_position method to track calls
            with patch.object(self.canvas, "_create_note_at_position") as mock_create:
                # Simulate double-click event on existing item
                click_pos = self.canvas.mapFromScene(QPointF(50, 50))

                event = QMouseEvent(
                    QMouseEvent.Type.MouseButtonDblClick,
                    QPointF(click_pos),
                    Qt.MouseButton.LeftButton,
                    Qt.MouseButton.LeftButton,
                    Qt.KeyboardModifier.NoModifier,
                )

                # Handle the event
                self.canvas.mouseDoubleClickEvent(event)

                # Verify note creation was NOT called
                mock_create.assert_not_called()

                # Verify no new items were added
                self.assertEqual(len(self.scene.items()), initial_item_count)

    def test_right_click_double_click_ignored(self):
        """Test that right-button double-clicks don't create notes."""
        # Requirements: 1.1 - Only left-click creates notes

        with patch.object(self.canvas, "_create_note_at_position") as mock_create:
            # Simulate right double-click event
            click_pos = self.canvas.mapFromScene(self.test_position)

            event = QMouseEvent(
                QMouseEvent.Type.MouseButtonDblClick,
                QPointF(click_pos),
                Qt.MouseButton.RightButton,
                Qt.MouseButton.RightButton,
                Qt.KeyboardModifier.NoModifier,
            )

            # Handle the event
            self.canvas.mouseDoubleClickEvent(event)

            # Verify note creation was NOT called
            mock_create.assert_not_called()

    def test_note_creation_at_various_positions(self):
        """Test creating notes at different canvas positions."""
        # Requirements: 1.1 - Create notes anywhere on canvas

        test_positions = [
            QPointF(0, 0),  # Origin
            QPointF(-100, -50),  # Negative coordinates
            QPointF(500, 300),  # Positive coordinates
            QPointF(-200, 150),  # Mixed coordinates
        ]

        created_notes = []

        for position in test_positions:
            note = self.canvas._create_note_at_position(position)
            created_notes.append(note)

            # Verify note position
            self.assertEqual(note.pos(), position)

        # Verify all notes were added to scene
        self.assertEqual(len(created_notes), len(test_positions))
        for note in created_notes:
            self.assertIn(note, self.scene.items())

    def test_note_creation_with_scene_expansion(self):
        """Test that note creation works with scene expansion."""
        # Requirements: 7.1, 7.2 - Infinite canvas support

        # Create note at position that might require scene expansion
        far_position = QPointF(10000, 10000)

        # Create note
        note = self.canvas._create_note_at_position(far_position)

        # Verify note was created
        self.assertIsInstance(note, NoteItem)
        self.assertEqual(note.pos(), far_position)

        # Verify note is in scene
        self.assertIn(note, self.scene.items())

        # Scene should have expanded to accommodate the note
        # (The scene expansion logic is tested in the canvas tests)

    def test_multiple_note_creation(self):
        """Test creating multiple notes in sequence."""
        # Requirements: 1.1 - Multiple note creation

        positions = [
            QPointF(100, 100),
            QPointF(200, 150),
            QPointF(300, 200),
        ]

        created_notes = []

        for position in positions:
            note = self.canvas._create_note_at_position(position)
            created_notes.append(note)

        # Verify all notes were created
        self.assertEqual(len(created_notes), len(positions))

        # Verify all notes are in scene
        scene_items = self.scene.items()
        for note in created_notes:
            self.assertIn(note, scene_items)

        # Verify each note has correct position
        for note, expected_pos in zip(created_notes, positions):
            self.assertEqual(note.pos(), expected_pos)

    def test_note_creation_workflow_integration(self):
        """Test the complete note creation workflow."""
        # Requirements: 1.1, 1.2, 1.4 - Complete workflow

        # Connect to signals to track workflow
        note_created_mock = Mock()
        editing_started_mock = Mock()

        self.canvas.note_created.connect(note_created_mock)

        # Create note
        note = self.canvas._create_note_at_position(self.test_position)

        # Connect to note's editing signal after creation
        note.editing_started.connect(editing_started_mock)

        # Verify complete workflow
        # 1. Note was created
        self.assertIsInstance(note, NoteItem)
        note_created_mock.assert_called_once_with(note)

        # 2. Note is at correct position
        self.assertEqual(note.pos(), self.test_position)

        # 3. Note is in scene
        self.assertIn(note, self.scene.items())

        # 4. Note is in edit mode (which indicates focus was set)
        self.assertTrue(note.is_editing())

        # Note: Focus testing in unit tests can be unreliable due to window manager
        # The fact that the note is in edit mode indicates focus was properly set

    def test_canvas_coordinate_transformation(self):
        """Test that coordinate transformation works correctly for note creation."""
        # Requirements: 7.1, 7.2 - Coordinate system management

        # Apply some zoom and pan to the canvas
        self.canvas.set_zoom(1.5)
        self.canvas.pan(50, 30)

        # Create note at a specific scene position
        scene_position = QPointF(200, 300)
        note = self.canvas._create_note_at_position(scene_position)

        # Verify note is at correct scene position regardless of view transformation
        self.assertEqual(note.pos(), scene_position)

        # Verify note is visible and properly positioned in the scene
        self.assertIn(note, self.scene.items())


if __name__ == "__main__":
    unittest.main()
