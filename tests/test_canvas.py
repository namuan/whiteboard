"""
Unit tests for canvas components (WhiteboardScene and WhiteboardCanvas).
"""

import unittest
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QApplication, QGraphicsRectItem, QGraphicsEllipseItem
from PyQt6.QtCore import QPointF, Qt

from src.whiteboard.canvas import WhiteboardScene, WhiteboardCanvas


class TestWhiteboardScene(unittest.TestCase):
    """Test cases for WhiteboardScene class."""

    @classmethod
    def setUpClass(cls):
        """Set up QApplication for testing."""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        """Set up test fixtures."""
        self.scene = WhiteboardScene()

    def tearDown(self):
        """Clean up after tests."""
        self.scene.clear_all_items()

    def test_scene_initialization(self):
        """Test that scene initializes with correct properties."""
        # Check initial scene rectangle
        scene_rect = self.scene.sceneRect()
        self.assertEqual(scene_rect.width(), 10000)
        self.assertEqual(scene_rect.height(), 10000)
        self.assertEqual(scene_rect.center(), QPointF(0, 0))

        # Check background
        self.assertEqual(self.scene.backgroundBrush().color(), Qt.GlobalColor.white)

        # Check initial state
        self.assertEqual(len(self.scene._tracked_items), 0)

    def test_add_item_tracking(self):
        """Test that items are properly tracked when added."""
        # Create test item
        item = QGraphicsRectItem(0, 0, 100, 100)

        # Add item to scene
        self.scene.addItem(item)

        # Verify item is tracked
        self.assertIn(item, self.scene._tracked_items)
        self.assertEqual(len(self.scene._tracked_items), 1)

    def test_remove_item_tracking(self):
        """Test that items are properly untracked when removed."""
        # Create and add test item
        item = QGraphicsRectItem(0, 0, 100, 100)
        self.scene.addItem(item)

        # Remove item
        self.scene.removeItem(item)

        # Verify item is no longer tracked
        self.assertNotIn(item, self.scene._tracked_items)
        self.assertEqual(len(self.scene._tracked_items), 0)

    def test_scene_expansion(self):
        """Test that scene expands when items are near boundaries."""
        # Get initial scene bounds
        initial_rect = self.scene.sceneRect()

        # Create item near right boundary
        item = QGraphicsRectItem(4000, 0, 100, 100)  # Near right edge
        self.scene.addItem(item)

        # Scene should have expanded
        new_rect = self.scene.sceneRect()
        self.assertGreater(new_rect.width(), initial_rect.width())

    def test_content_bounds_empty(self):
        """Test content bounds calculation with no items."""
        bounds = self.scene.get_content_bounds()
        self.assertTrue(bounds.isNull())

    def test_content_bounds_with_items(self):
        """Test content bounds calculation with items."""
        # Add items at different positions
        item1 = QGraphicsRectItem(0, 0, 100, 100)
        item2 = QGraphicsRectItem(200, 200, 100, 100)

        self.scene.addItem(item1)
        self.scene.addItem(item2)

        # Get content bounds
        bounds = self.scene.get_content_bounds()

        # Should contain both items
        self.assertFalse(bounds.isNull())
        self.assertGreaterEqual(bounds.width(), 300)  # At least spans both items
        self.assertGreaterEqual(bounds.height(), 300)

    def test_center_on_content_empty(self):
        """Test center calculation with no content."""
        center = self.scene.center_on_content()
        self.assertEqual(center, QPointF(0, 0))

    def test_center_on_content_with_items(self):
        """Test center calculation with content."""
        # Add items symmetrically around origin
        item1 = QGraphicsRectItem(-100, -100, 100, 100)
        item2 = QGraphicsRectItem(100, 100, 100, 100)

        self.scene.addItem(item1)
        self.scene.addItem(item2)

        center = self.scene.center_on_content()

        # Center should be approximately at origin
        self.assertAlmostEqual(center.x(), 50, delta=50)  # Allow some tolerance
        self.assertAlmostEqual(center.y(), 50, delta=50)

    def test_clear_all_items(self):
        """Test clearing all items and resetting scene."""
        # Add some items
        item1 = QGraphicsRectItem(0, 0, 100, 100)
        item2 = QGraphicsEllipseItem(200, 200, 50, 50)

        self.scene.addItem(item1)
        self.scene.addItem(item2)

        # Clear all items
        self.scene.clear_all_items()

        # Verify scene is reset
        self.assertEqual(len(self.scene._tracked_items), 0)
        self.assertEqual(len(self.scene.items()), 0)

        # Scene should be reset to initial size
        scene_rect = self.scene.sceneRect()
        self.assertEqual(scene_rect.width(), 10000)
        self.assertEqual(scene_rect.height(), 10000)

    def test_scene_statistics(self):
        """Test scene statistics calculation."""
        # Add some items
        item1 = QGraphicsRectItem(0, 0, 100, 100)
        item2 = QGraphicsRectItem(200, 200, 100, 100)

        self.scene.addItem(item1)
        self.scene.addItem(item2)

        # Get statistics
        stats = self.scene.get_scene_statistics()

        # Verify statistics structure
        self.assertIn("item_count", stats)
        self.assertIn("scene_width", stats)
        self.assertIn("scene_height", stats)
        self.assertIn("content_width", stats)
        self.assertIn("content_height", stats)
        self.assertIn("scene_center", stats)
        self.assertIn("content_center", stats)

        # Verify values
        self.assertEqual(stats["item_count"], 2)
        self.assertGreater(stats["content_width"], 0)
        self.assertGreater(stats["content_height"], 0)

    def test_signals_emitted(self):
        """Test that appropriate signals are emitted."""
        # Mock signal handlers
        bounds_changed_handler = Mock()
        item_added_handler = Mock()
        item_removed_handler = Mock()

        self.scene.scene_bounds_changed.connect(bounds_changed_handler)
        self.scene.item_added.connect(item_added_handler)
        self.scene.item_removed.connect(item_removed_handler)

        # Add item (should trigger expansion and item_added signal)
        item = QGraphicsRectItem(4000, 0, 100, 100)  # Near boundary
        self.scene.addItem(item)

        # Verify signals were emitted
        item_added_handler.assert_called_once_with(item)
        bounds_changed_handler.assert_called_once()

        # Remove item
        self.scene.removeItem(item)
        item_removed_handler.assert_called_once_with(item)


class TestWhiteboardCanvas(unittest.TestCase):
    """Test cases for WhiteboardCanvas class."""

    @classmethod
    def setUpClass(cls):
        """Set up QApplication for testing."""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        """Set up test fixtures."""
        self.scene = WhiteboardScene()
        self.canvas = WhiteboardCanvas(self.scene)

    def tearDown(self):
        """Clean up after tests."""
        self.scene.clear_all_items()

    def test_canvas_initialization(self):
        """Test that canvas initializes with correct properties."""
        # Check scene reference
        self.assertEqual(self.canvas._scene, self.scene)

        # Check initial zoom
        self.assertEqual(self.canvas._zoom_factor, 1.0)

        # Check zoom limits
        self.assertEqual(self.canvas._min_zoom, 0.1)
        self.assertEqual(self.canvas._max_zoom, 10.0)

        # Check initial pan state
        self.assertFalse(self.canvas._pan_mode)

    def test_zoom_in(self):
        """Test zoom in functionality."""
        initial_zoom = self.canvas.get_zoom_factor()
        self.canvas.zoom_in()

        new_zoom = self.canvas.get_zoom_factor()
        self.assertGreater(new_zoom, initial_zoom)

    def test_zoom_out(self):
        """Test zoom out functionality."""
        # First zoom in to have room to zoom out
        self.canvas.zoom_in()
        initial_zoom = self.canvas.get_zoom_factor()

        self.canvas.zoom_out()
        new_zoom = self.canvas.get_zoom_factor()
        self.assertLess(new_zoom, initial_zoom)

    def test_reset_zoom(self):
        """Test zoom reset functionality."""
        # Change zoom level
        self.canvas.zoom_in()
        self.canvas.zoom_in()

        # Reset zoom
        self.canvas.reset_zoom()

        # Should be back to 1.0
        self.assertEqual(self.canvas.get_zoom_factor(), 1.0)

    def test_set_zoom_clamping(self):
        """Test that zoom is clamped to valid range."""
        # Test minimum clamping
        self.canvas.set_zoom(0.01)  # Below minimum
        self.assertEqual(self.canvas.get_zoom_factor(), 0.1)

        # Test maximum clamping
        self.canvas.set_zoom(20.0)  # Above maximum
        self.assertEqual(self.canvas.get_zoom_factor(), 10.0)

        # Test valid value
        self.canvas.set_zoom(2.0)
        self.assertEqual(self.canvas.get_zoom_factor(), 2.0)

    def test_zoom_signals(self):
        """Test that zoom signals are emitted."""
        # Mock signal handler
        zoom_changed_handler = Mock()
        self.canvas.zoom_changed.connect(zoom_changed_handler)

        # Change zoom
        self.canvas.set_zoom(2.0)

        # Verify signal was emitted
        zoom_changed_handler.assert_called_once_with(2.0)

    def test_center_on_content_empty(self):
        """Test centering on content when scene is empty."""
        # Should not raise exception
        self.canvas.center_on_content()

        # Center should be at origin
        center = self.canvas.get_center_point()
        self.assertAlmostEqual(center.x(), 0, delta=10)
        self.assertAlmostEqual(center.y(), 0, delta=10)

    def test_center_on_content_with_items(self):
        """Test centering on content with items in scene."""
        # Add item away from origin
        item = QGraphicsRectItem(1000, 1000, 100, 100)
        self.scene.addItem(item)

        # Center on content
        self.canvas.center_on_content()

        # View should be centered on the item area
        center = self.canvas.get_center_point()
        self.assertGreater(center.x(), 500)  # Should be closer to item
        self.assertGreater(center.y(), 500)

    def test_fit_content_in_view(self):
        """Test fitting content in view."""
        # Add items to create content bounds
        item1 = QGraphicsRectItem(0, 0, 100, 100)
        item2 = QGraphicsRectItem(500, 500, 100, 100)

        self.scene.addItem(item1)
        self.scene.addItem(item2)

        # Fit content in view
        self.canvas.fit_content_in_view()

        # Zoom should have changed to fit content
        zoom = self.canvas.get_zoom_factor()
        self.assertNotEqual(zoom, 1.0)

    def test_canvas_statistics(self):
        """Test canvas statistics calculation."""
        # Add some content
        item = QGraphicsRectItem(100, 100, 200, 200)
        self.scene.addItem(item)

        # Get statistics
        stats = self.canvas.get_canvas_statistics()

        # Verify statistics structure
        self.assertIn("zoom_factor", stats)
        self.assertIn("center_x", stats)
        self.assertIn("center_y", stats)
        self.assertIn("view_width", stats)
        self.assertIn("view_height", stats)
        self.assertIn("item_count", stats)  # From scene stats

        # Verify values
        self.assertEqual(stats["zoom_factor"], 1.0)
        self.assertEqual(stats["item_count"], 1)

    @patch("src.whiteboard.canvas.QWheelEvent")
    def test_wheel_event_zoom(self, mock_wheel_event):
        """Test wheel event handling for zoom."""
        # Mock wheel event with Ctrl modifier
        event = Mock()
        event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier
        event.angleDelta.return_value.y.return_value = 120  # Positive for zoom in

        initial_zoom = self.canvas.get_zoom_factor()

        # Simulate wheel event
        self.canvas.wheelEvent(event)

        # Zoom should have increased
        new_zoom = self.canvas.get_zoom_factor()
        self.assertGreater(new_zoom, initial_zoom)

    def test_keyboard_shortcuts(self):
        """Test keyboard shortcut handling."""
        # Mock key events
        zoom_in_event = Mock()
        zoom_in_event.key.return_value = Qt.Key.Key_Plus
        zoom_in_event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier

        zoom_out_event = Mock()
        zoom_out_event.key.return_value = Qt.Key.Key_Minus
        zoom_out_event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier

        reset_zoom_event = Mock()
        reset_zoom_event.key.return_value = Qt.Key.Key_0
        reset_zoom_event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier

        # Test zoom in
        initial_zoom = self.canvas.get_zoom_factor()
        self.canvas.keyPressEvent(zoom_in_event)
        self.assertGreater(self.canvas.get_zoom_factor(), initial_zoom)

        # Test zoom out
        current_zoom = self.canvas.get_zoom_factor()
        self.canvas.keyPressEvent(zoom_out_event)
        self.assertLess(self.canvas.get_zoom_factor(), current_zoom)

        # Test reset zoom
        self.canvas.keyPressEvent(reset_zoom_event)
        self.assertEqual(self.canvas.get_zoom_factor(), 1.0)


if __name__ == "__main__":
    unittest.main()
