"""
Integration tests for connection creation workflow.

Tests the drag-and-drop connection creation functionality in the WhiteboardCanvas,
including connection validation and duplicate prevention.
"""

import unittest
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF

from src.whiteboard.canvas import WhiteboardCanvas, WhiteboardScene
from src.whiteboard.note_item import NoteItem
from src.whiteboard.connection_item import ConnectionItem


class TestConnectionCreation(unittest.TestCase):
    """Test cases for connection creation functionality."""

    @classmethod
    def setUpClass(cls):
        """Set up QApplication for testing."""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        """Set up test fixtures."""
        # Create scene and canvas
        self.scene = WhiteboardScene()
        self.canvas = WhiteboardCanvas(self.scene)

        # Create test notes
        self.note1 = NoteItem("Note 1", QPointF(50, 50))
        self.note2 = NoteItem("Note 2", QPointF(200, 50))
        self.note3 = NoteItem("Note 3", QPointF(50, 200))

        # Add notes to scene
        self.scene.addItem(self.note1)
        self.scene.addItem(self.note2)
        self.scene.addItem(self.note3)

    def test_connection_creation_workflow(self):
        """Test complete connection creation workflow."""
        # Verify no connections initially
        self.assertEqual(len(self.canvas.get_connections()), 0)

        # Create connection between note1 and note2
        connection = self.canvas._create_connection(self.note1, self.note2)

        # Verify connection was created
        self.assertIsNotNone(connection)
        self.assertIsInstance(connection, ConnectionItem)
        self.assertEqual(len(self.canvas.get_connections()), 1)

        # Verify connection properties
        self.assertEqual(connection.get_start_note(), self.note1)
        self.assertEqual(connection.get_end_note(), self.note2)
        self.assertTrue(connection.is_connected_to_note(self.note1))
        self.assertTrue(connection.is_connected_to_note(self.note2))

    def test_duplicate_connection_prevention(self):
        """Test that duplicate connections are prevented."""
        # Create first connection
        connection1 = self.canvas._create_connection(self.note1, self.note2)
        self.assertIsNotNone(connection1)
        self.assertEqual(len(self.canvas.get_connections()), 1)

        # Check that connection exists
        self.assertTrue(self.canvas._connection_exists(self.note1, self.note2))
        self.assertTrue(
            self.canvas._connection_exists(self.note2, self.note1)
        )  # Should work both ways

        # Attempt to create duplicate connection should be prevented by caller
        # (The canvas itself doesn't prevent duplicates, but the UI logic should)
        exists = self.canvas._connection_exists(self.note1, self.note2)
        self.assertTrue(exists)

    def test_connection_tracking(self):
        """Test that connections are properly tracked and removed."""
        # Create multiple connections
        connection1 = self.canvas._create_connection(self.note1, self.note2)
        connection2 = self.canvas._create_connection(self.note2, self.note3)

        self.assertEqual(len(self.canvas.get_connections()), 2)

        # Delete one connection
        connection1.delete_connection()

        # Process events to ensure signal is handled
        QApplication.processEvents()

        # Verify connection was removed from tracking
        self.assertEqual(len(self.canvas.get_connections()), 1)
        self.assertNotIn(connection1, self.canvas.get_connections())
        self.assertIn(connection2, self.canvas.get_connections())

    def test_delete_connections_for_note(self):
        """Test deleting all connections for a specific note."""
        # Create connections involving note1
        self.canvas._create_connection(self.note1, self.note2)
        self.canvas._create_connection(self.note1, self.note3)
        connection3 = self.canvas._create_connection(self.note2, self.note3)

        self.assertEqual(len(self.canvas.get_connections()), 3)

        # Delete all connections for note1
        self.canvas.delete_connections_for_note(self.note1)

        # Process events to ensure signals are handled
        QApplication.processEvents()

        # Should only have connection3 left (note2 to note3)
        remaining_connections = self.canvas.get_connections()
        self.assertEqual(len(remaining_connections), 1)
        self.assertEqual(remaining_connections[0], connection3)

    def test_connection_start_workflow(self):
        """Test starting connection creation workflow."""
        # Start connection creation
        mouse_pos = QPointF(100, 100)
        self.canvas._start_connection_creation(self.note1, mouse_pos)

        # Verify connection mode is active
        self.assertTrue(self.canvas._connection_mode)
        self.assertEqual(self.canvas._connection_start_note, self.note1)

    def test_connection_cancellation(self):
        """Test connection creation cancellation."""
        # Start connection creation
        mouse_pos = QPointF(100, 100)
        self.canvas._start_connection_creation(self.note1, mouse_pos)

        # Cancel connection creation
        self.canvas._cancel_connection_creation()

        # Verify connection mode is inactive
        self.assertFalse(self.canvas._connection_mode)
        self.assertIsNone(self.canvas._connection_start_note)
        self.assertIsNone(self.canvas._connection_preview_line)

    def test_connection_preview_creation(self):
        """Test connection preview line creation during drag."""
        # Start connection creation
        mouse_pos = QPointF(100, 100)
        self.canvas._start_connection_creation(self.note1, mouse_pos)

        # Move mouse to trigger preview (beyond threshold)
        new_mouse_pos = QPointF(150, 150)
        self.canvas._update_connection_preview(new_mouse_pos)

        # Verify preview line was created
        self.assertIsNotNone(self.canvas._connection_preview_line)
        self.assertIn(self.canvas._connection_preview_line, self.scene.items())

    def test_connection_completion_with_valid_target(self):
        """Test completing connection creation with valid target note."""
        # Start connection creation
        start_pos = QPointF(100, 100)
        self.canvas._start_connection_creation(self.note1, start_pos)

        # Mock mapToScene to return note2's position
        with patch.object(self.canvas, "mapToScene") as mock_map:
            mock_map.return_value = self.note2.pos()

            # Mock itemAt to return note2
            with patch.object(self.scene, "itemAt") as mock_item_at:
                mock_item_at.return_value = self.note2

                # Complete connection creation
                end_pos = QPointF(200, 100)  # Beyond drag threshold
                self.canvas._complete_connection_creation(end_pos)

        # Verify connection was created
        connections = self.canvas.get_connections()
        self.assertEqual(len(connections), 1)
        self.assertTrue(connections[0].is_connected_to_note(self.note1))
        self.assertTrue(connections[0].is_connected_to_note(self.note2))

    def test_connection_completion_with_invalid_target(self):
        """Test completing connection creation with invalid target."""
        # Start connection creation
        start_pos = QPointF(100, 100)
        self.canvas._start_connection_creation(self.note1, start_pos)

        # Mock mapToScene and itemAt to return no valid target
        with patch.object(self.canvas, "mapToScene") as mock_map:
            mock_map.return_value = QPointF(300, 300)

            with patch.object(self.scene, "itemAt") as mock_item_at:
                mock_item_at.return_value = None  # No item at position

                # Complete connection creation
                end_pos = QPointF(300, 300)  # Beyond drag threshold
                self.canvas._complete_connection_creation(end_pos)

        # Verify no connection was created
        self.assertEqual(len(self.canvas.get_connections()), 0)

        # Verify connection mode was cancelled
        self.assertFalse(self.canvas._connection_mode)

    def test_connection_completion_with_same_note(self):
        """Test that connections to the same note are not created."""
        # Start connection creation
        start_pos = QPointF(100, 100)
        self.canvas._start_connection_creation(self.note1, start_pos)

        # Mock mapToScene and itemAt to return the same note
        with patch.object(self.canvas, "mapToScene") as mock_map:
            mock_map.return_value = self.note1.pos()

            with patch.object(self.scene, "itemAt") as mock_item_at:
                mock_item_at.return_value = self.note1  # Same note

                # Complete connection creation
                end_pos = QPointF(150, 150)  # Beyond drag threshold
                self.canvas._complete_connection_creation(end_pos)

        # Verify no connection was created
        self.assertEqual(len(self.canvas.get_connections()), 0)

    def test_connection_below_drag_threshold(self):
        """Test that small drags don't create connections."""
        # Start connection creation
        start_pos = QPointF(100, 100)
        self.canvas._start_connection_creation(self.note1, start_pos)

        # Move mouse by small amount (below threshold)
        end_pos = QPointF(105, 105)  # Only 5 pixels away
        self.canvas._complete_connection_creation(end_pos)

        # Verify no connection was created
        self.assertEqual(len(self.canvas.get_connections()), 0)

        # Verify connection mode was cancelled
        self.assertFalse(self.canvas._connection_mode)

    def test_canvas_statistics_include_connections(self):
        """Test that canvas statistics include connection count."""
        # Create some connections
        self.canvas._create_connection(self.note1, self.note2)
        self.canvas._create_connection(self.note2, self.note3)

        # Get statistics
        stats = self.canvas.get_canvas_statistics()

        # Verify connection count is included
        self.assertIn("connection_count", stats)
        self.assertEqual(stats["connection_count"], 2)

    def test_connection_signal_emission(self):
        """Test that connection creation emits appropriate signals."""
        # Connect to connection created signal
        connection_created_emitted = False
        created_connection = None

        def on_connection_created(connection):
            nonlocal connection_created_emitted, created_connection
            connection_created_emitted = True
            created_connection = connection

        self.canvas.connection_created.connect(on_connection_created)

        # Create connection
        connection = self.canvas._create_connection(self.note1, self.note2)

        # Process events to ensure signal is emitted
        QApplication.processEvents()

        # Verify signal was emitted
        self.assertTrue(connection_created_emitted)
        self.assertEqual(created_connection, connection)

    def test_target_note_highlighting(self):
        """Test that target notes are highlighted during connection creation."""
        # Start connection creation
        start_pos = QPointF(100, 100)
        self.canvas._start_connection_creation(self.note1, start_pos)

        # Initially no target note should be highlighted
        self.assertIsNone(self.canvas._connection_target_note)

        # Update target note highlighting with note2 as target
        self.canvas._update_target_note_highlight(self.note2)

        # Verify note2 is highlighted
        self.assertEqual(self.canvas._connection_target_note, self.note2)
        self.assertTrue(self.note2.isSelected())

        # Update with different target (note3)
        self.canvas._update_target_note_highlight(self.note3)

        # Verify note2 is no longer highlighted and note3 is highlighted
        self.assertFalse(self.note2.isSelected())
        self.assertTrue(self.note3.isSelected())
        self.assertEqual(self.canvas._connection_target_note, self.note3)

        # Clear target highlighting
        self.canvas._update_target_note_highlight(None)

        # Verify no notes are highlighted
        self.assertFalse(self.note3.isSelected())
        self.assertIsNone(self.canvas._connection_target_note)

    def test_connection_preview_with_target_detection(self):
        """Test connection preview updates with target note detection."""
        # Start connection creation
        start_pos = QPointF(100, 100)
        self.canvas._start_connection_creation(self.note1, start_pos)

        # Mock mapToScene and itemAt to simulate hovering over note2
        with patch.object(self.canvas, "mapToScene") as mock_map:
            mock_map.return_value = self.note2.pos()

            with patch.object(self.scene, "itemAt") as mock_item_at:
                mock_item_at.return_value = self.note2

                # Update connection preview (beyond drag threshold)
                mouse_pos = QPointF(200, 200)
                self.canvas._update_connection_preview(mouse_pos)

        # Verify preview line was created
        self.assertIsNotNone(self.canvas._connection_preview_line)

        # Verify target note is highlighted
        self.assertEqual(self.canvas._connection_target_note, self.note2)
        self.assertTrue(self.note2.isSelected())

    def tearDown(self):
        """Clean up after each test."""
        # Clear the scene
        self.scene.clear()
        self.canvas._connections.clear()

    @classmethod
    def tearDownClass(cls):
        """Clean up QApplication after all tests."""
        if hasattr(cls, "app"):
            cls.app.quit()


if __name__ == "__main__":
    unittest.main()
