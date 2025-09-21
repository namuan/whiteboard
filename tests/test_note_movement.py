"""
Tests for note movement and positioning functionality.

Tests cover drag-and-drop functionality, position change signals,
and ensuring notes can be moved freely without canvas restrictions.
"""

import unittest
from unittest.mock import Mock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF
from PyQt6.QtTest import QTest

from src.whiteboard.canvas import WhiteboardCanvas, WhiteboardScene
from src.whiteboard.note_item import NoteItem


class TestNoteMovement(unittest.TestCase):
    """Test cases for note movement and positioning functionality."""

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
        self.initial_position = QPointF(100, 100)
        self.note = NoteItem("Test Note", self.initial_position)
        self.scene.addItem(self.note)

    def tearDown(self):
        """Clean up after each test method."""
        self.scene.clear()

    def test_note_is_movable(self):
        """Test that notes have the movable flag set."""
        # Requirements: 3.1 - Drag-and-drop functionality
        self.assertTrue(self.note.flags() & self.note.GraphicsItemFlag.ItemIsMovable)

    def test_note_position_setting(self):
        """Test setting note position programmatically."""
        # Requirements: 3.1, 3.3 - Note positioning
        new_position = QPointF(200, 300)

        # Set position
        self.note.setPos(new_position)

        # Verify position
        self.assertEqual(self.note.pos(), new_position)

    def test_position_change_signal_emission(self):
        """Test that moving a note emits position_changed signal."""
        # Requirements: 3.2 - Position change signals and event handling
        position_changed_mock = Mock()
        self.note.position_changed.connect(position_changed_mock)

        # Move note to new position
        new_position = QPointF(150, 250)
        self.note.setPos(new_position)

        # Allow signal processing
        QTest.qWait(10)

        # Verify signal was emitted with correct position
        # Note: Signal may be called during setup, so check if it was called with new position
        calls = position_changed_mock.call_args_list
        self.assertTrue(any(call[0][0] == new_position for call in calls))

    def test_note_movement_without_restrictions(self):
        """Test that notes can be moved to any position without canvas restrictions."""
        # Requirements: 3.3 - Notes can be moved freely without canvas restrictions

        test_positions = [
            QPointF(0, 0),  # Origin
            QPointF(-500, -300),  # Negative coordinates
            QPointF(1000, 800),  # Large positive coordinates
            QPointF(-100, 200),  # Mixed coordinates
            QPointF(50.5, 75.7),  # Decimal coordinates
        ]

        for position in test_positions:
            with self.subTest(position=position):
                # Move note to position
                self.note.setPos(position)

                # Verify note is at the expected position
                self.assertEqual(self.note.pos(), position)

                # Verify note is still in the scene
                self.assertIn(self.note, self.scene.items())

    def test_multiple_notes_independent_movement(self):
        """Test that multiple notes can be moved independently."""
        # Requirements: 3.1, 3.2 - Independent note movement

        # Create additional notes
        note2 = NoteItem("Note 2", QPointF(200, 200))
        note3 = NoteItem("Note 3", QPointF(300, 300))

        self.scene.addItem(note2)
        self.scene.addItem(note3)

        # Move notes to different positions
        pos1 = QPointF(50, 50)
        pos2 = QPointF(400, 100)
        pos3 = QPointF(150, 400)

        self.note.setPos(pos1)
        note2.setPos(pos2)
        note3.setPos(pos3)

        # Verify each note is at its expected position
        self.assertEqual(self.note.pos(), pos1)
        self.assertEqual(note2.pos(), pos2)
        self.assertEqual(note3.pos(), pos3)

        # Verify all notes are still in scene
        scene_items = self.scene.items()
        self.assertIn(self.note, scene_items)
        self.assertIn(note2, scene_items)
        self.assertIn(note3, scene_items)

    def test_note_movement_preserves_content(self):
        """Test that moving notes preserves their content and styling."""
        # Requirements: 3.1, 3.2 - Movement preserves note properties

        # Set note content and styling
        test_text = "Important content"
        test_style = {
            "background_color": self.note.get_style()["background_color"],
            "font_size": 16,
        }

        self.note.set_text(test_text)
        self.note.set_style(test_style)

        # Move note
        new_position = QPointF(500, 600)
        self.note.setPos(new_position)

        # Verify content and styling are preserved
        self.assertEqual(self.note.get_text(), test_text)
        current_style = self.note.get_style()
        self.assertEqual(current_style["font_size"], 16)

        # Verify position changed
        self.assertEqual(self.note.pos(), new_position)

    def test_note_movement_during_editing(self):
        """Test that notes can be moved while in edit mode."""
        # Requirements: 3.1 - Movement during editing

        # Enter edit mode
        self.note.enter_edit_mode()
        self.assertTrue(self.note.is_editing())

        # Move note while editing
        new_position = QPointF(250, 350)
        self.note.setPos(new_position)

        # Verify note moved and is still in edit mode
        self.assertEqual(self.note.pos(), new_position)
        self.assertTrue(self.note.is_editing())

    def test_position_persistence_after_edit_mode(self):
        """Test that position is maintained when entering/exiting edit mode."""
        # Requirements: 3.3 - Position persistence

        # Move note to specific position
        target_position = QPointF(180, 220)
        self.note.setPos(target_position)

        # Enter and exit edit mode
        self.note.enter_edit_mode()
        self.note.exit_edit_mode()

        # Verify position is unchanged
        self.assertEqual(self.note.pos(), target_position)

    def test_scene_expansion_with_note_movement(self):
        """Test that moving notes to far positions triggers scene expansion."""
        # Requirements: 7.1, 7.2 - Scene expansion with movement

        # Get initial scene bounds
        initial_bounds = self.scene.sceneRect()

        # Move note to position that should trigger expansion
        far_position = QPointF(
            initial_bounds.right() + 1000, initial_bounds.bottom() + 1000
        )
        self.note.setPos(far_position)

        # Allow scene to process the change
        QTest.qWait(10)

        # Verify note is at the expected position
        self.assertEqual(self.note.pos(), far_position)

        # Verify scene bounds have expanded (scene should be larger)
        new_bounds = self.scene.sceneRect()
        self.assertTrue(
            new_bounds.width() > initial_bounds.width()
            or new_bounds.height() > initial_bounds.height()
        )

    def test_note_selection_during_movement(self):
        """Test note selection behavior during movement operations."""
        # Requirements: 3.1 - Selection during movement

        # Ensure note is selectable
        self.assertTrue(self.note.flags() & self.note.GraphicsItemFlag.ItemIsSelectable)

        # Select note
        self.note.setSelected(True)
        self.assertTrue(self.note.isSelected())

        # Move selected note
        new_position = QPointF(300, 400)
        self.note.setPos(new_position)

        # Verify note is still selected after movement
        self.assertTrue(self.note.isSelected())
        self.assertEqual(self.note.pos(), new_position)

    def test_note_bounds_after_movement(self):
        """Test that note bounding rectangle is correct after movement."""
        # Requirements: 3.1, 3.2 - Proper bounds after movement

        # Get initial bounds
        initial_bounds = self.note.boundingRect()

        # Move note
        new_position = QPointF(400, 500)
        self.note.setPos(new_position)

        # Get bounds after movement
        new_bounds = self.note.boundingRect()

        # Bounds should be the same size (only position changed)
        self.assertEqual(initial_bounds.size(), new_bounds.size())

        # Scene bounding rect should reflect new position
        scene_bounds = self.note.sceneBoundingRect()
        expected_scene_bounds = new_bounds.translated(new_position)

        # Allow for small floating point differences
        self.assertAlmostEqual(scene_bounds.x(), expected_scene_bounds.x(), delta=1.0)
        self.assertAlmostEqual(scene_bounds.y(), expected_scene_bounds.y(), delta=1.0)

    def test_connection_points_after_movement(self):
        """Test that connection points are updated after note movement."""
        # Requirements: 2.3, 3.2 - Connection updates during movement

        # Get initial connection points
        initial_points = self.note.get_connection_points()

        # Move note
        movement_delta = QPointF(100, 150)
        new_position = self.initial_position + movement_delta
        self.note.setPos(new_position)

        # Get connection points after movement
        new_points = self.note.get_connection_points()

        # Connection points should have moved by the same delta
        self.assertEqual(len(initial_points), len(new_points))

        for initial_point, new_point in zip(initial_points, new_points):
            expected_point = initial_point + movement_delta

            # Allow for small floating point differences
            self.assertAlmostEqual(new_point.x(), expected_point.x(), delta=1.0)
            self.assertAlmostEqual(new_point.y(), expected_point.y(), delta=1.0)

    def test_note_data_serialization_with_position(self):
        """Test that note position is correctly included in serialization."""
        # Requirements: 3.3 - Position persistence in data

        # Move note to specific position
        target_position = QPointF(275, 425)
        self.note.setPos(target_position)

        # Get serialized data
        note_data = self.note.get_note_data()

        # Verify position is correctly serialized
        self.assertIn("position", note_data)
        serialized_position = note_data["position"]

        self.assertEqual(serialized_position[0], target_position.x())
        self.assertEqual(serialized_position[1], target_position.y())

    def test_note_position_restoration(self):
        """Test restoring note position from serialized data."""
        # Requirements: 3.3 - Position restoration

        # Test data with specific position
        test_position = QPointF(350, 450)
        test_data = {
            "position": (test_position.x(), test_position.y()),
            "text": "Restored note",
            "style": self.note.get_style(),
        }

        # Restore note from data
        self.note.set_note_data(test_data)

        # Verify position was restored
        self.assertEqual(self.note.pos(), test_position)

    def test_note_movement_with_zoom_and_pan(self):
        """Test note movement works correctly with canvas zoom and pan."""
        # Requirements: 3.1, 7.1 - Movement with view transformations

        # Apply zoom and pan to canvas
        self.canvas.set_zoom(1.5)
        self.canvas.pan(100, 50)

        # Move note to new position
        target_scene_position = QPointF(300, 400)
        self.note.setPos(target_scene_position)

        # Verify note is at correct scene position regardless of view transformation
        self.assertEqual(self.note.pos(), target_scene_position)

        # Verify note is still visible and properly positioned in scene
        self.assertIn(self.note, self.scene.items())

    def test_overlapping_notes_movement(self):
        """Test that overlapping notes can be moved independently."""
        # Requirements: 3.1 - Independent movement of overlapping notes

        # Create overlapping notes
        overlap_position = QPointF(100, 100)
        note2 = NoteItem("Overlapping Note", overlap_position)
        self.scene.addItem(note2)

        # Move first note to same position (overlapping)
        self.note.setPos(overlap_position)

        # Move one of the overlapping notes
        new_position = QPointF(200, 200)
        self.note.setPos(new_position)

        # Verify notes are at different positions
        self.assertEqual(self.note.pos(), new_position)
        self.assertEqual(note2.pos(), overlap_position)

        # Both notes should still be in scene
        scene_items = self.scene.items()
        self.assertIn(self.note, scene_items)
        self.assertIn(note2, scene_items)


if __name__ == "__main__":
    unittest.main()
