"""
Unit tests for context menu functionality across all whiteboard components.
"""

import unittest
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF, Qt, QPoint
from PyQt6.QtGui import QContextMenuEvent, QKeyEvent

from src.whiteboard.canvas import WhiteboardCanvas, WhiteboardScene
from src.whiteboard.note_item import NoteItem


class TestContextMenuFunctionality(unittest.TestCase):
    """Test cases for context menu functionality."""

    @classmethod
    def setUpClass(cls):
        """Set up QApplication for testing."""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        """Set up test fixtures."""
        scene = WhiteboardScene()
        self.canvas = WhiteboardCanvas(scene)

    def test_context_menu_shortcut_handlers_exist(self):
        """Test that context menu shortcut handler methods exist."""
        # Test that the main handler method exists
        self.assertTrue(hasattr(self.canvas, "_handle_context_menu_shortcuts"))

        # Test that individual shortcut handlers exist
        self.assertTrue(hasattr(self.canvas, "_handle_delete_shortcut"))
        self.assertTrue(hasattr(self.canvas, "_handle_copy_shortcut"))
        self.assertTrue(hasattr(self.canvas, "_handle_select_all_shortcut"))
        self.assertTrue(hasattr(self.canvas, "_handle_new_note_shortcut"))

    def test_shortcut_routing(self):
        """Test that shortcuts are routed to correct handlers."""
        # Test Delete key
        with patch.object(
            self.canvas, "_handle_delete_shortcut", return_value=True
        ) as mock_delete:
            result = self.canvas._handle_context_menu_shortcuts(
                Qt.Key.Key_Delete, Qt.KeyboardModifier.NoModifier
            )
            self.assertTrue(result)
            mock_delete.assert_called_once()

        # Test Ctrl+C
        with patch.object(
            self.canvas, "_handle_copy_shortcut", return_value=True
        ) as mock_copy:
            result = self.canvas._handle_context_menu_shortcuts(
                Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier
            )
            self.assertTrue(result)
            mock_copy.assert_called_once()

        # Test Ctrl+A
        with patch.object(
            self.canvas, "_handle_select_all_shortcut", return_value=True
        ) as mock_select:
            result = self.canvas._handle_context_menu_shortcuts(
                Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier
            )
            self.assertTrue(result)
            mock_select.assert_called_once()

        # Test Ctrl+N
        with patch.object(
            self.canvas, "_handle_new_note_shortcut", return_value=True
        ) as mock_new:
            result = self.canvas._handle_context_menu_shortcuts(
                Qt.Key.Key_N, Qt.KeyboardModifier.ControlModifier
            )
            self.assertTrue(result)
            mock_new.assert_called_once()

    def test_unhandled_shortcuts(self):
        """Test that unhandled shortcuts return False."""
        # Test random key
        result = self.canvas._handle_context_menu_shortcuts(
            Qt.Key.Key_X, Qt.KeyboardModifier.NoModifier
        )
        self.assertFalse(result)

        # Test key without proper modifier
        result = self.canvas._handle_context_menu_shortcuts(
            Qt.Key.Key_C, Qt.KeyboardModifier.NoModifier
        )
        self.assertFalse(result)

    def test_keyboard_integration_in_key_press_event(self):
        """Test that keyPressEvent calls context menu shortcuts."""
        from PyQt6.QtCore import QEvent

        with patch.object(
            self.canvas, "_handle_context_menu_shortcuts", return_value=True
        ) as mock_handler:
            event = QKeyEvent(
                QEvent.Type.KeyPress, Qt.Key.Key_Delete, Qt.KeyboardModifier.NoModifier
            )
            self.canvas.keyPressEvent(event)
            mock_handler.assert_called_once_with(
                Qt.Key.Key_Delete, Qt.KeyboardModifier.NoModifier
            )

    def test_canvas_context_menu_creation(self):
        """Test that context menu is created and event is handled properly."""
        # Create a mock context menu event
        event = Mock(spec=QContextMenuEvent)
        event.pos.return_value = QPoint(100, 100)
        event.globalPos.return_value = QPoint(200, 200)
        event.accept = Mock()

        # Mock the scene and itemAt to return None (no item at position)
        mock_scene = Mock()
        mock_scene.itemAt.return_value = None

        with patch.object(self.canvas, "mapToScene", return_value=QPointF(100, 100)):
            with patch.object(self.canvas, "transform", return_value=Mock()):
                with patch.object(self.canvas, "scene", return_value=mock_scene):
                    with patch("src.whiteboard.canvas.QMenu") as mock_menu_class:
                        mock_menu = Mock()
                        mock_menu_class.return_value = mock_menu

                        # Mock menu methods
                        mock_create_menu = Mock()
                        mock_menu.addMenu.return_value = mock_create_menu
                        mock_create_menu.addAction.return_value = Mock()
                        mock_create_menu.addMenu.return_value = Mock()
                        mock_menu.addSeparator.return_value = None
                        mock_menu.addAction.return_value = Mock()
                        mock_menu.exec.return_value = None

                        # Call the method
                        self.canvas.contextMenuEvent(event)

                        # Verify menu was created with correct parent
                        mock_menu_class.assert_called_once_with(self.canvas)
                        # Verify menu was executed at correct position
                        mock_menu.exec.assert_called_once_with(event.globalPos())
                        # Verify event was accepted
                        event.accept.assert_called_once()

    def test_canvas_context_menu_structure(self):
        """Test that canvas context menu has the correct structure."""
        event = Mock(spec=QContextMenuEvent)
        event.pos.return_value = QPoint(100, 100)
        event.globalPos.return_value = QPoint(200, 200)
        event.accept = Mock()

        mock_scene = Mock()
        mock_scene.itemAt.return_value = None

        with patch.object(self.canvas, "mapToScene", return_value=QPointF(100, 100)):
            with patch.object(self.canvas, "transform", return_value=Mock()):
                with patch.object(self.canvas, "scene", return_value=mock_scene):
                    with patch("src.whiteboard.canvas.QMenu") as mock_menu_class:
                        mock_menu = Mock()
                        mock_menu_class.return_value = mock_menu

                        # Mock menu structure - need nested structure
                        mock_create_menu = Mock()
                        mock_template_menu = Mock()
                        mock_operations_menu = Mock()
                        mock_zoom_menu = Mock()
                        mock_action = Mock()

                        # Set up the nested menu structure
                        mock_menu.addMenu.side_effect = [
                            mock_create_menu,
                            mock_operations_menu,
                            mock_zoom_menu,
                        ]
                        mock_create_menu.addMenu.return_value = mock_template_menu
                        mock_menu.addAction.return_value = mock_action
                        mock_create_menu.addAction.return_value = mock_action
                        mock_template_menu.addAction.return_value = mock_action
                        mock_operations_menu.addAction.return_value = mock_action
                        mock_zoom_menu.addAction.return_value = mock_action

                        # Mock template population
                        with patch.object(
                            self.canvas, "_populate_canvas_template_menu"
                        ) as mock_populate:
                            self.canvas.contextMenuEvent(event)

                            # Verify menu structure - should have multiple addMenu and addAction calls
                            self.assertGreater(mock_menu.addMenu.call_count, 0)
                            self.assertGreater(mock_menu.addAction.call_count, 0)
                            mock_menu.addSeparator.assert_called()
                            mock_populate.assert_called_once_with(
                                mock_template_menu, QPointF(100, 100)
                            )

    def test_canvas_context_menu_note_creation(self):
        """Test that canvas context menu note creation works."""
        event = Mock(spec=QContextMenuEvent)
        event.pos.return_value = QPoint(100, 100)
        event.globalPos.return_value = QPoint(200, 200)
        event.accept = Mock()

        mock_scene = Mock()
        mock_scene.itemAt.return_value = None

        with patch.object(self.canvas, "mapToScene", return_value=QPointF(100, 100)):
            with patch.object(self.canvas, "transform", return_value=Mock()):
                with patch.object(self.canvas, "scene", return_value=mock_scene):
                    with patch("src.whiteboard.canvas.QMenu") as mock_menu_class:
                        mock_menu = Mock()
                        mock_menu_class.return_value = mock_menu

                        # Mock menu structure - need nested structure
                        mock_create_menu = Mock()
                        mock_template_menu = Mock()
                        mock_operations_menu = Mock()
                        mock_zoom_menu = Mock()
                        mock_action = Mock()

                        # Set up the nested menu structure
                        mock_menu.addMenu.side_effect = [
                            mock_create_menu,
                            mock_operations_menu,
                            mock_zoom_menu,
                        ]
                        mock_create_menu.addMenu.return_value = mock_template_menu
                        mock_menu.addAction.return_value = mock_action
                        mock_create_menu.addAction.return_value = mock_action
                        mock_template_menu.addAction.return_value = mock_action
                        mock_operations_menu.addAction.return_value = mock_action
                        mock_zoom_menu.addAction.return_value = mock_action

                        with patch.object(self.canvas, "_create_note_at_position"):
                            self.canvas.contextMenuEvent(event)

                            # Verify action was created with correct shortcut
                            mock_create_menu.addAction.assert_called_with(
                                "✏️ Quick Note"
                            )

                            # The _create_note_at_position method should be available for action triggers
                            # but not called during menu creation
                            self.assertTrue(
                                hasattr(self.canvas, "_create_note_at_position")
                            )

    def test_canvas_context_menu_with_item_present(self):
        """Test that canvas context menu defers to item when item is present."""
        event = Mock(spec=QContextMenuEvent)
        event.pos.return_value = QPoint(100, 100)
        event.globalPos.return_value = QPoint(200, 200)

        # Mock scene with item present
        mock_item = Mock()
        mock_scene = Mock()
        mock_scene.itemAt.return_value = mock_item

        with patch.object(self.canvas, "mapToScene", return_value=QPointF(100, 100)):
            with patch.object(self.canvas, "transform", return_value=Mock()):
                with patch.object(self.canvas, "scene", return_value=mock_scene):
                    with patch("src.whiteboard.canvas.QMenu") as mock_menu_class:
                        # Mock super() call
                        with patch("builtins.super") as mock_super:
                            mock_super_instance = Mock()
                            mock_super.return_value = mock_super_instance

                            self.canvas.contextMenuEvent(event)

                            # Verify super().contextMenuEvent was called
                            mock_super_instance.contextMenuEvent.assert_called_once_with(
                                event
                            )

                            # Verify no canvas menu was created
                            mock_menu_class.assert_not_called()

    def test_canvas_info_action(self):
        """Test that canvas info action is properly configured."""
        event = Mock(spec=QContextMenuEvent)
        event.pos.return_value = QPoint(100, 100)
        event.globalPos.return_value = QPoint(200, 200)
        event.accept = Mock()

        mock_scene = Mock()
        mock_scene.itemAt.return_value = None

        with patch.object(self.canvas, "mapToScene", return_value=QPointF(100, 100)):
            with patch.object(self.canvas, "transform", return_value=Mock()):
                with patch.object(self.canvas, "scene", return_value=mock_scene):
                    with patch("src.whiteboard.canvas.QMenu") as mock_menu_class:
                        mock_menu = Mock()
                        mock_menu_class.return_value = mock_menu

                        mock_info_action = Mock()
                        mock_menu.addAction.return_value = mock_info_action

                        with patch.object(
                            self.canvas, "_show_canvas_info"
                        ) as mock_show_info:
                            self.canvas.contextMenuEvent(event)

                            # Verify info action was created
                            mock_menu.addAction.assert_called_with("ℹ️ Canvas Info")

                            # Simulate action trigger
                            action_callback = (
                                mock_info_action.triggered.connect.call_args[0][0]
                            )
                            action_callback()

                            # Verify info method was called
                            mock_show_info.assert_called_once()

    def test_context_menu_event_propagation_prevention(self):
        """Test that context menu events are properly handled to prevent propagation."""
        event = Mock(spec=QContextMenuEvent)
        event.pos.return_value = QPoint(100, 100)
        event.globalPos.return_value = QPoint(200, 200)
        event.accept = Mock()

        mock_scene = Mock()
        mock_scene.itemAt.return_value = None

        with patch.object(self.canvas, "mapToScene", return_value=QPointF(100, 100)):
            with patch.object(self.canvas, "transform", return_value=Mock()):
                with patch.object(self.canvas, "scene", return_value=mock_scene):
                    with patch("src.whiteboard.canvas.QMenu") as mock_menu_class:
                        mock_menu = Mock()
                        mock_menu_class.return_value = mock_menu
                        mock_menu.exec.return_value = None

                        self.canvas.contextMenuEvent(event)

                        # Verify event was accepted to prevent propagation
                        event.accept.assert_called_once()

    def test_template_menu_population(self):
        """Test that template menu is properly populated."""
        # This test verifies that the _populate_canvas_template_menu method is called
        # The actual implementation of template population is tested separately
        event = Mock(spec=QContextMenuEvent)
        event.pos.return_value = QPoint(100, 100)
        event.globalPos.return_value = QPoint(200, 200)
        event.accept = Mock()

        mock_scene = Mock()
        mock_scene.itemAt.return_value = None
        scene_pos = QPointF(100, 100)

        with patch.object(self.canvas, "mapToScene", return_value=scene_pos):
            with patch.object(self.canvas, "transform", return_value=Mock()):
                with patch.object(self.canvas, "scene", return_value=mock_scene):
                    with patch("src.whiteboard.canvas.QMenu") as mock_menu_class:
                        mock_menu = Mock()
                        mock_menu_class.return_value = mock_menu

                        mock_create_menu = Mock()
                        mock_template_menu = Mock()
                        mock_menu.addMenu.return_value = mock_create_menu
                        mock_create_menu.addMenu.return_value = mock_template_menu

                        with patch.object(
                            self.canvas, "_populate_canvas_template_menu"
                        ) as mock_populate:
                            self.canvas.contextMenuEvent(event)

                            # Verify template menu was populated with correct parameters
                            mock_populate.assert_called_once_with(
                                mock_template_menu, scene_pos
                            )

    def test_context_menu_with_no_selection(self):
        """Test context menu behavior when no items are selected."""
        event = Mock(spec=QContextMenuEvent)
        event.pos.return_value = QPoint(100, 100)
        event.globalPos.return_value = QPoint(200, 200)
        event.accept = Mock()

        # Mock scene with no items selected
        mock_scene = Mock()
        mock_scene.itemAt.return_value = None
        mock_scene.selectedItems.return_value = []

        with patch.object(self.canvas, "mapToScene", return_value=QPointF(100, 100)):
            with patch.object(self.canvas, "transform", return_value=Mock()):
                with patch.object(self.canvas, "scene", return_value=mock_scene):
                    with patch("src.whiteboard.canvas.QMenu") as mock_menu_class:
                        mock_menu = Mock()
                        mock_menu_class.return_value = mock_menu

                        # Mock menu structure
                        mock_create_menu = Mock()
                        mock_operations_menu = Mock()
                        mock_zoom_menu = Mock()
                        mock_action = Mock()

                        mock_menu.addMenu.side_effect = [
                            mock_create_menu,
                            mock_operations_menu,
                            mock_zoom_menu,
                        ]
                        mock_create_menu.addMenu.return_value = Mock()
                        mock_menu.addAction.return_value = mock_action
                        mock_create_menu.addAction.return_value = mock_action
                        mock_operations_menu.addAction.return_value = mock_action
                        mock_zoom_menu.addAction.return_value = mock_action

                        self.canvas.contextMenuEvent(event)

                        # Verify menu was created and executed
                        mock_menu.exec.assert_called_once_with(event.globalPos())
                        event.accept.assert_called_once()

                        # Verify operations menu includes select all and clear selection
                        mock_operations_menu.addAction.assert_any_call(
                            "🔲 Select All Notes"
                        )
                        mock_operations_menu.addAction.assert_any_call(
                            "❌ Clear Selection"
                        )

    def test_context_menu_with_single_selection(self):
        """Test context menu behavior when a single item is selected."""
        event = Mock(spec=QContextMenuEvent)
        event.pos.return_value = QPoint(100, 100)
        event.globalPos.return_value = QPoint(200, 200)
        event.accept = Mock()

        # Mock scene with one item selected
        mock_selected_item = Mock()
        mock_scene = Mock()
        mock_scene.itemAt.return_value = None
        mock_scene.selectedItems.return_value = [mock_selected_item]

        with patch.object(self.canvas, "mapToScene", return_value=QPointF(100, 100)):
            with patch.object(self.canvas, "transform", return_value=Mock()):
                with patch.object(self.canvas, "scene", return_value=mock_scene):
                    with patch("src.whiteboard.canvas.QMenu") as mock_menu_class:
                        mock_menu = Mock()
                        mock_menu_class.return_value = mock_menu

                        # Mock menu structure
                        mock_create_menu = Mock()
                        mock_operations_menu = Mock()
                        mock_zoom_menu = Mock()
                        mock_action = Mock()

                        mock_menu.addMenu.side_effect = [
                            mock_create_menu,
                            mock_operations_menu,
                            mock_zoom_menu,
                        ]
                        mock_create_menu.addMenu.return_value = Mock()
                        mock_menu.addAction.return_value = mock_action
                        mock_create_menu.addAction.return_value = mock_action
                        mock_operations_menu.addAction.return_value = mock_action
                        mock_zoom_menu.addAction.return_value = mock_action

                        self.canvas.contextMenuEvent(event)

                        # Verify menu was created and executed
                        mock_menu.exec.assert_called_once_with(event.globalPos())
                        event.accept.assert_called_once()

                        # Verify operations menu includes clear selection (since items are selected)
                        mock_operations_menu.addAction.assert_any_call(
                            "❌ Clear Selection"
                        )

    def test_context_menu_with_multiple_selection(self):
        """Test context menu behavior when multiple items are selected."""
        event = Mock(spec=QContextMenuEvent)
        event.pos.return_value = QPoint(100, 100)
        event.globalPos.return_value = QPoint(200, 200)
        event.accept = Mock()

        # Mock scene with multiple items selected
        mock_selected_item1 = Mock()
        mock_selected_item2 = Mock()
        mock_scene = Mock()
        mock_scene.itemAt.return_value = None
        mock_scene.selectedItems.return_value = [
            mock_selected_item1,
            mock_selected_item2,
        ]

        with patch.object(self.canvas, "mapToScene", return_value=QPointF(100, 100)):
            with patch.object(self.canvas, "transform", return_value=Mock()):
                with patch.object(self.canvas, "scene", return_value=mock_scene):
                    with patch("src.whiteboard.canvas.QMenu") as mock_menu_class:
                        mock_menu = Mock()
                        mock_menu_class.return_value = mock_menu

                        # Mock menu structure
                        mock_create_menu = Mock()
                        mock_operations_menu = Mock()
                        mock_zoom_menu = Mock()
                        mock_action = Mock()

                        mock_menu.addMenu.side_effect = [
                            mock_create_menu,
                            mock_operations_menu,
                            mock_zoom_menu,
                        ]
                        mock_create_menu.addMenu.return_value = Mock()
                        mock_menu.addAction.return_value = mock_action
                        mock_create_menu.addAction.return_value = mock_action
                        mock_operations_menu.addAction.return_value = mock_action
                        mock_zoom_menu.addAction.return_value = mock_action

                        self.canvas.contextMenuEvent(event)

                        # Verify menu was created and executed
                        mock_menu.exec.assert_called_once_with(event.globalPos())
                        event.accept.assert_called_once()

                        # Verify operations menu includes clear selection (since multiple items are selected)
                        mock_operations_menu.addAction.assert_any_call(
                            "❌ Clear Selection"
                        )

    def test_selection_operations_functionality(self):
        """Test that selection operations work correctly."""

        # Test select all functionality
        mock_scene = Mock()
        mock_note1 = Mock(spec=NoteItem)
        mock_note2 = Mock(spec=NoteItem)
        mock_other_item = Mock()  # Not a NoteItem

        # Mock isinstance to return True for NoteItems and False for others
        with patch("src.whiteboard.canvas.isinstance") as mock_isinstance:

            def isinstance_side_effect(obj, cls):
                if cls == NoteItem:
                    return obj in [mock_note1, mock_note2]
                return False

            mock_isinstance.side_effect = isinstance_side_effect
            mock_scene.items.return_value = [mock_note1, mock_note2, mock_other_item]

            with patch.object(self.canvas, "_scene", mock_scene):
                self.canvas._select_all_notes()

                # Verify only NoteItems were selected
                mock_note1.setSelected.assert_called_once_with(True)
                mock_note2.setSelected.assert_called_once_with(True)
                mock_other_item.setSelected.assert_not_called()

        # Test clear selection functionality
        with patch.object(self.canvas, "_scene", mock_scene):
            self.canvas._clear_selection()

            # Verify scene clearSelection was called
            mock_scene.clearSelection.assert_called_once()


if __name__ == "__main__":
    unittest.main()
