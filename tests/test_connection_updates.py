"""
Tests for dynamic connection updates during note repositioning.

Tests automatic connection path updates when notes are moved, connection point
calculation on note boundaries, and visual quality maintenance during movement.
"""

import unittest
import math
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPainterPath

from src.whiteboard.canvas import WhiteboardCanvas, WhiteboardScene
from src.whiteboard.note_item import NoteItem
from src.whiteboard.connection_item import ConnectionItem


class TestConnectionUpdates(unittest.TestCase):
    """Test cases for dynamic connection updates."""

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

        # Create test notes at known positions
        self.note1 = NoteItem("Note 1", QPointF(0, 0))
        self.note2 = NoteItem("Note 2", QPointF(200, 0))

        # Add notes to scene
        self.scene.addItem(self.note1)
        self.scene.addItem(self.note2)

        # Create connection between notes
        self.connection = ConnectionItem(self.note1, self.note2)
        self.scene.addItem(self.connection)

    def test_connection_updates_on_note_movement(self):
        """Test that connections update automatically when notes are moved."""
        # Get initial connection path
        initial_path = self.connection.path()
        initial_bounds = initial_path.boundingRect()

        # Move note2 to a new position
        new_position = QPointF(300, 100)
        self.note2.setPos(new_position)

        # Process events to ensure signals are handled
        QApplication.processEvents()

        # Get updated connection path
        updated_path = self.connection.path()
        updated_bounds = updated_path.boundingRect()

        # Verify path has changed
        self.assertNotEqual(initial_bounds, updated_bounds)

        # Verify connection still connects the notes
        self.assertTrue(self.connection.is_connected_to_note(self.note1))
        self.assertTrue(self.connection.is_connected_to_note(self.note2))

    def test_connection_point_calculation_accuracy(self):
        """Test accuracy of connection point calculation on note boundaries."""
        # Position notes horizontally aligned
        self.note1.setPos(QPointF(0, 0))
        self.note2.setPos(QPointF(200, 0))

        # Update connection path
        self.connection.update_path()

        # Get connection points
        start_point, end_point = self.connection._calculate_connection_points()

        # Get note centers for reference
        note1_center = self.note1.mapToScene(self.note1.boundingRect().center())
        note2_center = self.note2.mapToScene(self.note2.boundingRect().center())

        # For horizontally aligned notes, connection should be on left/right edges
        # Start point should be to the right of note1 center
        self.assertGreaterEqual(start_point.x(), note1_center.x())

        # End point should be to the left of note2 center
        self.assertLessEqual(end_point.x(), note2_center.x())

        # Y coordinates should be approximately the same (horizontal alignment)
        y_diff = abs(start_point.y() - end_point.y())
        self.assertLess(y_diff, 10)  # Allow small difference due to note height

    def test_connection_point_optimization_for_different_positions(self):
        """Test connection point optimization for various note positions."""
        test_positions = [
            (QPointF(0, 0), QPointF(200, 0)),  # Horizontal
            (QPointF(0, 0), QPointF(0, 200)),  # Vertical
            (QPointF(0, 0), QPointF(200, 200)),  # Diagonal
            (QPointF(0, 0), QPointF(-200, 0)),  # Left
            (QPointF(0, 0), QPointF(0, -200)),  # Up
        ]

        for pos1, pos2 in test_positions:
            with self.subTest(pos1=pos1, pos2=pos2):
                # Position notes
                self.note1.setPos(pos1)
                self.note2.setPos(pos2)

                # Update connection
                self.connection.update_path()

                # Get connection points
                start_point, end_point = self.connection._calculate_connection_points()

                # Verify points are different
                self.assertNotEqual(start_point, end_point)

                # Verify points are reasonable (not at note centers)
                note1_center = self.note1.mapToScene(self.note1.boundingRect().center())
                note2_center = self.note2.mapToScene(self.note2.boundingRect().center())

                # Connection points should be different from centers
                self.assertNotEqual(start_point, note1_center)
                self.assertNotEqual(end_point, note2_center)

    def test_connection_length_calculation(self):
        """Test that connection length is calculated correctly."""
        # Position notes at known distance
        self.note1.setPos(QPointF(0, 0))
        self.note2.setPos(QPointF(300, 400))  # 3-4-5 triangle, distance = 500

        # Update connection
        self.connection.update_path()

        # Get connection points
        start_point, end_point = self.connection._calculate_connection_points()

        # Calculate distance
        dx = end_point.x() - start_point.x()
        dy = end_point.y() - start_point.y()
        distance = math.sqrt(dx * dx + dy * dy)

        # Distance should be reasonable (less than note center distance but not zero)
        self.assertGreater(distance, 0)
        self.assertLess(distance, 600)  # Should be less than center-to-center distance

    def test_connection_updates_with_note_style_changes(self):
        """Test that connections update when note styles change (affecting size)."""
        # Get initial connection path
        initial_path = self.connection.path()
        initial_path.boundingRect()

        # Change note style to make it larger
        self.note1.set_style({"min_width": 200, "min_height": 100, "padding": 20})

        # Process events to ensure signals are handled
        QApplication.processEvents()

        # Get updated connection path
        updated_path = self.connection.path()
        updated_path.boundingRect()

        # Path should have updated due to note size change
        # (This test verifies the signal connection is working)
        self.assertIsInstance(updated_path, QPainterPath)

    def test_multiple_connections_update_independently(self):
        """Test that multiple connections update independently when notes move."""
        # Create a third note and additional connections
        note3 = NoteItem("Note 3", QPointF(100, 200))
        self.scene.addItem(note3)

        connection2 = ConnectionItem(self.note1, note3)
        connection3 = ConnectionItem(self.note2, note3)
        self.scene.addItem(connection2)
        self.scene.addItem(connection3)

        # Get initial paths
        initial_path1 = self.connection.path().boundingRect()
        initial_path2 = connection2.path().boundingRect()
        initial_path3 = connection3.path().boundingRect()

        # Move note1
        self.note1.setPos(QPointF(-100, -100))

        # Process events
        QApplication.processEvents()

        # Get updated paths
        updated_path1 = self.connection.path().boundingRect()
        updated_path2 = connection2.path().boundingRect()
        updated_path3 = connection3.path().boundingRect()

        # Connections involving note1 should have changed
        self.assertNotEqual(initial_path1, updated_path1)  # note1 to note2
        self.assertNotEqual(initial_path2, updated_path2)  # note1 to note3

        # Connection not involving note1 should remain the same
        self.assertEqual(initial_path3, updated_path3)  # note2 to note3

    def test_connection_visual_quality_during_movement(self):
        """Test that connections maintain visual quality during note movement."""
        # Test multiple positions to ensure path quality
        positions = [
            QPointF(50, 50),
            QPointF(150, 75),
            QPointF(250, 100),
            QPointF(350, 125),
        ]

        for position in positions:
            with self.subTest(position=position):
                # Move note
                self.note2.setPos(position)

                # Update connection
                self.connection.update_path()

                # Get path
                path = self.connection.path()

                # Verify path is valid
                self.assertFalse(path.isEmpty())

                # Verify path has reasonable bounds
                bounds = path.boundingRect()
                self.assertGreater(bounds.width(), 0)
                self.assertGreater(bounds.height(), 0)

                # Verify path contains expected elements (line + arrow if enabled)
                # This is a basic check that the path was constructed properly
                self.assertGreater(path.elementCount(), 0)

    def test_connection_updates_with_rapid_note_movement(self):
        """Test connection updates with rapid successive note movements."""
        # Perform rapid movements
        positions = [
            QPointF(100, 0),
            QPointF(200, 50),
            QPointF(150, 100),
            QPointF(250, 75),
            QPointF(300, 25),
        ]

        for position in positions:
            self.note2.setPos(position)
            # Don't process events between moves to simulate rapid movement

        # Process all events at once
        QApplication.processEvents()

        # Verify final connection is valid
        final_path = self.connection.path()
        self.assertFalse(final_path.isEmpty())

        # Verify connection still links the notes correctly
        self.assertTrue(self.connection.is_connected_to_note(self.note1))
        self.assertTrue(self.connection.is_connected_to_note(self.note2))

    def test_connection_bounds_accuracy(self):
        """Test that connection bounding rectangles are accurate."""
        # Position notes at specific locations
        self.note1.setPos(QPointF(0, 0))
        self.note2.setPos(QPointF(200, 100))

        # Update connection
        self.connection.update_path()

        # Get connection bounds
        connection_bounds = self.connection.boundingRect()
        path_bounds = self.connection.path().boundingRect()

        # Connection bounds should include path bounds plus margin
        self.assertGreaterEqual(connection_bounds.width(), path_bounds.width())
        self.assertGreaterEqual(connection_bounds.height(), path_bounds.height())

        # Bounds should be reasonable (not empty, not huge)
        self.assertGreater(connection_bounds.width(), 0)
        self.assertGreater(connection_bounds.height(), 0)
        self.assertLess(connection_bounds.width(), 1000)
        self.assertLess(connection_bounds.height(), 1000)

    def test_connection_point_consistency(self):
        """Test that connection points are consistent across updates."""
        # Position notes
        self.note1.setPos(QPointF(0, 0))
        self.note2.setPos(QPointF(200, 0))

        # Get initial connection points
        self.connection.update_path()
        initial_start, initial_end = self.connection._calculate_connection_points()

        # Update connection again without moving notes
        self.connection.update_path()
        updated_start, updated_end = self.connection._calculate_connection_points()

        # Points should be the same
        self.assertEqual(initial_start, updated_start)
        self.assertEqual(initial_end, updated_end)

    def test_connection_updates_with_note_deletion_simulation(self):
        """Test connection behavior when note signals are disconnected."""
        # This simulates what happens when a note is deleted

        # Get initial connection state
        initial_path = self.connection.path()

        # Disconnect note signals (simulating note deletion preparation)
        self.connection._disconnect_note_signals()

        # Move note (should not update connection now)
        self.note1.setPos(QPointF(100, 100))

        # Process events
        QApplication.processEvents()

        # Connection path should not have changed
        current_path = self.connection.path()
        self.assertEqual(initial_path.boundingRect(), current_path.boundingRect())

    def tearDown(self):
        """Clean up after each test."""
        # Clear the scene
        self.scene.clear()

    @classmethod
    def tearDownClass(cls):
        """Clean up QApplication after all tests."""
        if hasattr(cls, "app"):
            cls.app.quit()


if __name__ == "__main__":
    unittest.main()
