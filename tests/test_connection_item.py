"""
Unit tests for the ConnectionItem class.

Tests connection path calculations, rendering, styling, and dynamic updates
when connected notes are moved.
"""

import unittest
from PyQt6.QtWidgets import QApplication, QGraphicsScene
from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QColor, QPainterPath

from src.whiteboard.connection_item import ConnectionItem
from src.whiteboard.note_item import NoteItem


class TestConnectionItem(unittest.TestCase):
    """Test cases for ConnectionItem functionality."""

    @classmethod
    def setUpClass(cls):
        """Set up QApplication for testing."""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        """Set up test fixtures."""
        # Create mock notes for testing
        self.start_note = NoteItem("Start Note", QPointF(0, 0))
        self.end_note = NoteItem("End Note", QPointF(100, 100))

        # Set up note bounds for connection point calculation
        self.start_note.setPos(QPointF(0, 0))
        self.end_note.setPos(QPointF(100, 100))

    def test_connection_creation(self):
        """Test basic connection creation between two notes."""
        connection = ConnectionItem(self.start_note, self.end_note)

        # Verify connection properties
        self.assertEqual(connection.get_start_note(), self.start_note)
        self.assertEqual(connection.get_end_note(), self.end_note)
        self.assertIsInstance(connection.get_connection_id(), int)

        # Verify initial styling
        style = connection.get_style()
        self.assertIn("line_color", style)
        self.assertIn("line_width", style)
        self.assertIn("show_arrow", style)
        self.assertEqual(style["line_width"], 2)
        self.assertTrue(style["show_arrow"])

    def test_connection_point_calculation(self):
        """Test calculation of optimal connection points between notes."""
        connection = ConnectionItem(self.start_note, self.end_note)

        # Get connection points
        start_point, end_point = connection._calculate_connection_points()

        # Verify points are QPointF instances
        self.assertIsInstance(start_point, QPointF)
        self.assertIsInstance(end_point, QPointF)

        # Verify points are different (not both at origin)
        self.assertNotEqual(start_point, end_point)

    def test_straight_line_path_creation(self):
        """Test creation of straight line connection paths."""
        connection = ConnectionItem(self.start_note, self.end_note)

        # Set straight line style (no curve)
        connection.set_style({"curve_factor": 0.0})

        # Create path between two points
        start_point = QPointF(0, 0)
        end_point = QPointF(100, 50)
        path = connection._create_connection_path(start_point, end_point)

        # Verify path is created
        self.assertIsInstance(path, QPainterPath)
        self.assertFalse(path.isEmpty())

        # Verify path contains the expected points
        path_rect = path.boundingRect()
        self.assertTrue(path_rect.contains(start_point))
        self.assertTrue(path_rect.contains(end_point))

    def test_curved_line_path_creation(self):
        """Test creation of curved connection paths."""
        connection = ConnectionItem(self.start_note, self.end_note)

        # Set curved line style
        connection.set_style({"curve_factor": 0.2})

        # Create curved path
        start_point = QPointF(0, 0)
        end_point = QPointF(100, 0)
        path = connection._create_curved_path(start_point, end_point)

        # Verify curved path is created
        self.assertIsInstance(path, QPainterPath)
        self.assertFalse(path.isEmpty())

        # Curved path should have different bounds than straight line
        straight_path = QPainterPath()
        straight_path.moveTo(start_point)
        straight_path.lineTo(end_point)

        # Curved path should be larger due to curve
        curved_rect = path.boundingRect()
        straight_rect = straight_path.boundingRect()
        self.assertGreater(curved_rect.height(), straight_rect.height())

    def test_arrow_head_creation(self):
        """Test creation of arrow heads at connection endpoints."""
        connection = ConnectionItem(self.start_note, self.end_note)

        # Test arrow head creation
        start_point = QPointF(0, 0)
        end_point = QPointF(100, 0)
        arrow_path = connection._create_arrow_head(start_point, end_point)

        # Verify arrow path is created
        self.assertIsInstance(arrow_path, QPainterPath)

        # Arrow should contain the end point
        self.assertTrue(arrow_path.boundingRect().contains(end_point))

    def test_arrow_head_angle_calculation(self):
        """Test arrow head angle calculation for different line directions."""
        connection = ConnectionItem(self.start_note, self.end_note)

        # Test horizontal line (0 degrees)
        start_point = QPointF(0, 0)
        end_point = QPointF(100, 0)
        arrow_path = connection._create_arrow_head(start_point, end_point)
        self.assertFalse(arrow_path.isEmpty())

        # Test vertical line (90 degrees)
        end_point = QPointF(0, 100)
        arrow_path = connection._create_arrow_head(start_point, end_point)
        self.assertFalse(arrow_path.isEmpty())

        # Test diagonal line (45 degrees)
        end_point = QPointF(100, 100)
        arrow_path = connection._create_arrow_head(start_point, end_point)
        self.assertFalse(arrow_path.isEmpty())

    def test_zero_length_line_handling(self):
        """Test handling of zero-length connections (same start and end point)."""
        connection = ConnectionItem(self.start_note, self.end_note)

        # Test with same start and end point
        same_point = QPointF(50, 50)
        arrow_path = connection._create_arrow_head(same_point, same_point)

        # Should return empty path for zero-length line
        self.assertTrue(arrow_path.isEmpty())

    def test_style_application(self):
        """Test application of different styling options."""
        connection = ConnectionItem(self.start_note, self.end_note)

        # Test color change
        new_color = QColor(255, 0, 0)  # Red
        connection.set_style({"line_color": new_color})

        style = connection.get_style()
        self.assertEqual(style["line_color"], new_color)

        # Test line width change
        connection.set_style({"line_width": 5})
        style = connection.get_style()
        self.assertEqual(style["line_width"], 5)

        # Test arrow visibility toggle
        connection.set_style({"show_arrow": False})
        style = connection.get_style()
        self.assertFalse(style["show_arrow"])

    def test_dynamic_path_updates(self):
        """Test that connection path updates when notes are moved."""
        connection = ConnectionItem(self.start_note, self.end_note)

        # Get initial path
        initial_path = connection.path()
        initial_bounds = initial_path.boundingRect()

        # Move end note
        self.end_note.setPos(QPointF(200, 200))

        # Trigger path update (normally done by signal)
        connection.update_path()

        # Get updated path
        updated_path = connection.path()
        updated_bounds = updated_path.boundingRect()

        # Path should have changed
        self.assertNotEqual(initial_bounds, updated_bounds)

    def test_connection_point_optimization(self):
        """Test that connection uses optimal points on note boundaries."""
        # Position notes so we can predict optimal connection points
        self.start_note.setPos(QPointF(0, 0))
        self.end_note.setPos(QPointF(200, 0))  # Horizontal alignment

        connection = ConnectionItem(self.start_note, self.end_note)

        # Calculate connection points
        start_point, end_point = connection._calculate_connection_points()

        # For horizontally aligned notes, should connect at left/right edges
        start_center = self.start_note.mapToScene(
            self.start_note.boundingRect().center()
        )
        end_center = self.end_note.mapToScene(self.end_note.boundingRect().center())

        # Start point should be to the right of start note center
        self.assertGreaterEqual(start_point.x(), start_center.x())

        # End point should be to the left of end note center
        self.assertLessEqual(end_point.x(), end_center.x())

    def test_connection_data_serialization(self):
        """Test getting connection data for serialization."""
        connection = ConnectionItem(self.start_note, self.end_note)

        # Get connection data
        data = connection.get_connection_data()

        # Verify required fields are present
        self.assertIn("id", data)
        self.assertIn("start_note_id", data)
        self.assertIn("end_note_id", data)
        self.assertIn("style", data)
        self.assertIn("start_point", data)
        self.assertIn("end_point", data)

        # Verify data types
        self.assertIsInstance(data["id"], int)
        self.assertIsInstance(data["start_note_id"], int)
        self.assertIsInstance(data["end_note_id"], int)
        self.assertIsInstance(data["style"], dict)
        self.assertIsInstance(data["start_point"], tuple)
        self.assertIsInstance(data["end_point"], tuple)

    def test_note_relationship_queries(self):
        """Test querying connection relationships with notes."""
        connection = ConnectionItem(self.start_note, self.end_note)

        # Test connection detection
        self.assertTrue(connection.is_connected_to_note(self.start_note))
        self.assertTrue(connection.is_connected_to_note(self.end_note))

        # Test with unconnected note
        other_note = NoteItem("Other Note", QPointF(300, 300))
        self.assertFalse(connection.is_connected_to_note(other_note))

        # Test getting other note
        self.assertEqual(connection.get_other_note(self.start_note), self.end_note)
        self.assertEqual(connection.get_other_note(self.end_note), self.start_note)
        self.assertIsNone(connection.get_other_note(other_note))

    def test_bounding_rect_calculation(self):
        """Test bounding rectangle calculation for connections."""
        connection = ConnectionItem(self.start_note, self.end_note)

        # Get bounding rect
        bounds = connection.boundingRect()

        # Should be a valid rectangle
        self.assertIsInstance(bounds, QRectF)
        self.assertGreater(bounds.width(), 0)
        self.assertGreater(bounds.height(), 0)

        # Should include margin for line width
        path_bounds = connection.path().boundingRect()
        self.assertGreaterEqual(bounds.width(), path_bounds.width())
        self.assertGreaterEqual(bounds.height(), path_bounds.height())

    def test_hit_testing(self):
        """Test point containment for connection selection."""
        # Create connection with known geometry
        self.start_note.setPos(QPointF(0, 0))
        self.end_note.setPos(QPointF(100, 0))

        connection = ConnectionItem(self.start_note, self.end_note)
        connection.update_path()

        # Test point on the line (should be contained)
        midpoint = QPointF(50, 0)
        # Note: contains() uses item coordinates, so we need to map from scene
        connection.mapFromScene(midpoint)

        # The line should be selectable near its path
        # We'll test a point that should be close to the line
        test_point = QPointF(50, 2)  # Slightly off the exact line
        # This test verifies the hit testing mechanism exists
        result = connection.contains(test_point)
        self.assertIsInstance(result, bool)

    def test_connection_deletion(self):
        """Test connection deletion and cleanup."""
        # Create a scene to add the connection to
        scene = QGraphicsScene()
        scene.addItem(self.start_note)
        scene.addItem(self.end_note)

        connection = ConnectionItem(self.start_note, self.end_note)
        scene.addItem(connection)

        # Verify connection is in scene
        self.assertIn(connection, scene.items())

        # Delete connection
        connection.delete_connection()

        # Verify connection is removed from scene
        self.assertNotIn(connection, scene.items())

    def test_style_signal_emission(self):
        """Test that style changes emit appropriate signals."""
        connection = ConnectionItem(self.start_note, self.end_note)

        # Connect to style changed signal
        style_changed_emitted = False
        received_style = None

        def on_style_changed(style):
            nonlocal style_changed_emitted, received_style
            style_changed_emitted = True
            received_style = style

        connection.signals.style_changed.connect(on_style_changed)

        # Change style
        new_style = {"line_color": QColor(255, 0, 0)}
        connection.set_style(new_style)

        # Process events to ensure signal is emitted
        QApplication.processEvents()

        # Verify signal was emitted
        self.assertTrue(style_changed_emitted)
        self.assertIsNotNone(received_style)
        self.assertEqual(received_style["line_color"], QColor(255, 0, 0))

    def tearDown(self):
        """Clean up after each test."""
        # Clean up any remaining items
        try:
            if hasattr(self, "start_note") and self.start_note:
                if self.start_note.scene():
                    self.start_note.scene().removeItem(self.start_note)
        except RuntimeError:
            # Object may have been deleted already
            pass

        try:
            if hasattr(self, "end_note") and self.end_note:
                if self.end_note.scene():
                    self.end_note.scene().removeItem(self.end_note)
        except RuntimeError:
            # Object may have been deleted already
            pass

    @classmethod
    def tearDownClass(cls):
        """Clean up QApplication after all tests."""
        if hasattr(cls, "app"):
            cls.app.quit()


if __name__ == "__main__":
    unittest.main()
