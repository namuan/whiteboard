"""
Canvas components for the Digital Whiteboard application.

This module contains the core canvas infrastructure including the scene and view classes
that provide infinite scrolling, zooming, and interactive note management.
"""

from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (
    QPainter,
    QWheelEvent,
    QKeyEvent,
    QMouseEvent,
    QColor,
    QPen,
    QContextMenuEvent,
    QKeySequence,
)
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsItem, QMenu

from .utils.logging_config import get_logger
from .note_item import NoteItem
from .connection_item import ConnectionItem


class WhiteboardScene(QGraphicsScene):
    """
    Custom QGraphicsScene with infinite canvas support.

    Provides an unbounded workspace for notes, connections, and groups with
    efficient coordinate system management and bounds handling.

    Requirements addressed:
    - 7.1: Infinite scrolling canvas support
    - 7.2: Scene coordinate system and bounds management
    """

    # Signals
    scene_bounds_changed = pyqtSignal(QRectF)
    item_added = pyqtSignal(QGraphicsItem)
    item_removed = pyqtSignal(QGraphicsItem)

    def __init__(self, parent=None):
        """
        Initialize the whiteboard scene.

        Args:
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.logger = get_logger(__name__)

        # Scene configuration
        self._initial_size = 10000  # Large initial scene size
        self._expansion_threshold = 1000  # Distance from edge to trigger expansion
        self._expansion_amount = 5000  # Amount to expand scene by

        # Set initial scene rectangle (will expand as needed)
        initial_rect = QRectF(
            -self._initial_size / 2,
            -self._initial_size / 2,
            self._initial_size,
            self._initial_size,
        )
        self.setSceneRect(initial_rect)

        # Scene properties
        self.setBackgroundBrush(Qt.GlobalColor.white)

        # Track items for bounds management
        self._tracked_items: list[QGraphicsItem] = []

        self.logger.info(f"WhiteboardScene initialized with bounds: {initial_rect}")

    def addItem(self, item: QGraphicsItem) -> None:
        """
        Add an item to the scene and track it for bounds management.

        Args:
            item: Graphics item to add
        """
        super().addItem(item)
        self._tracked_items.append(item)

        # Check if scene needs expansion
        self._check_and_expand_scene(item.sceneBoundingRect())

        self.item_added.emit(item)
        self.logger.debug(f"Added item to scene: {type(item).__name__}")

    def removeItem(self, item: QGraphicsItem) -> None:
        """
        Remove an item from the scene and stop tracking it.

        Args:
            item: Graphics item to remove
        """
        super().removeItem(item)
        if item in self._tracked_items:
            self._tracked_items.remove(item)

        self.item_removed.emit(item)
        self.logger.debug(f"Removed item from scene: {type(item).__name__}")

    def _check_and_expand_scene(self, item_rect: QRectF) -> None:
        """
        Check if the scene needs to be expanded to accommodate the item.

        Args:
            item_rect: Bounding rectangle of the item in scene coordinates
        """
        current_rect = self.sceneRect()
        needs_expansion = False
        new_rect = QRectF(current_rect)

        # Check if item is near or outside current bounds
        margin = self._expansion_threshold

        if item_rect.left() < current_rect.left() + margin:
            new_rect.setLeft(item_rect.left() - self._expansion_amount)
            needs_expansion = True

        if item_rect.right() > current_rect.right() - margin:
            new_rect.setRight(item_rect.right() + self._expansion_amount)
            needs_expansion = True

        if item_rect.top() < current_rect.top() + margin:
            new_rect.setTop(item_rect.top() - self._expansion_amount)
            needs_expansion = True

        if item_rect.bottom() > current_rect.bottom() - margin:
            new_rect.setBottom(item_rect.bottom() + self._expansion_amount)
            needs_expansion = True

        if needs_expansion:
            self.setSceneRect(new_rect)
            self.scene_bounds_changed.emit(new_rect)
            self.logger.debug(f"Scene expanded to: {new_rect}")

    def get_content_bounds(self) -> QRectF:
        """
        Get the bounding rectangle of all items in the scene.

        Returns:
            QRectF containing all scene items, or empty rect if no items
        """
        if not self._tracked_items:
            return QRectF()

        # Calculate union of all item bounds
        content_rect = QRectF()
        valid_items = []

        for item in self._tracked_items:
            try:
                # Check if the item is still valid (not deleted)
                item_rect = item.sceneBoundingRect()
                valid_items.append(item)

                if content_rect.isNull():
                    content_rect = item_rect
                else:
                    content_rect = content_rect.united(item_rect)
            except RuntimeError:
                # Item has been deleted, skip it
                self.logger.debug(f"Skipping deleted item: {type(item).__name__}")
                continue

        # Update tracked items to remove any deleted ones
        self._tracked_items = valid_items

        return content_rect

    def center_on_content(self) -> QPointF:
        """
        Get the center point of all content in the scene.

        Returns:
            QPointF representing the center of all items, or (0,0) if no items
        """
        content_bounds = self.get_content_bounds()
        if content_bounds.isNull():
            return QPointF(0, 0)

        return content_bounds.center()

    def clear_all_items(self) -> None:
        """
        Remove all items from the scene and reset tracking.
        """
        self.clear()
        self._tracked_items.clear()

        # Reset scene to initial size
        initial_rect = QRectF(
            -self._initial_size / 2,
            -self._initial_size / 2,
            self._initial_size,
            self._initial_size,
        )
        self.setSceneRect(initial_rect)

        self.logger.info("Scene cleared and reset to initial bounds")

    def get_scene_statistics(self) -> dict:
        """
        Get statistics about the current scene state.

        Returns:
            Dictionary containing scene statistics
        """
        content_bounds = self.get_content_bounds()
        scene_rect = self.sceneRect()

        return {
            "item_count": len(self._tracked_items),
            "scene_width": scene_rect.width(),
            "scene_height": scene_rect.height(),
            "content_width": content_bounds.width()
            if not content_bounds.isNull()
            else 0,
            "content_height": content_bounds.height()
            if not content_bounds.isNull()
            else 0,
            "scene_center": (scene_rect.center().x(), scene_rect.center().y()),
            "content_center": (content_bounds.center().x(), content_bounds.center().y())
            if not content_bounds.isNull()
            else (0, 0),
        }


class WhiteboardCanvas(QGraphicsView):
    """
    Custom QGraphicsView with zoom and pan functionality.

    Handles user interactions including mouse navigation, keyboard shortcuts,
    and coordinate transformations for the infinite canvas.

    Requirements addressed:
    - 7.1: Zoom and pan functionality
    - 7.2: Mouse event handlers for navigation
    - 7.3: Keyboard shortcuts for canvas navigation
    """

    # Signals
    zoom_changed = pyqtSignal(float)  # Emits current zoom factor
    pan_changed = pyqtSignal(QPointF)  # Emits current center point
    viewport_changed = pyqtSignal(QRectF)  # Emits current viewport rectangle
    note_created = pyqtSignal(NoteItem)  # Emits when a new note is created
    connection_created = pyqtSignal(
        ConnectionItem
    )  # Emits when a new connection is created
    note_hover_hint = pyqtSignal(str)  # Emits hint text for status bar
    note_hover_ended = pyqtSignal()  # Emits when hover ends

    def __init__(self, scene: WhiteboardScene, parent=None):
        """
        Initialize the whiteboard canvas.

        Args:
            scene: WhiteboardScene to display
            parent: Parent widget (optional)
        """
        super().__init__(scene, parent)
        self.logger = get_logger(__name__)

        # Store scene reference
        self._scene = scene

        # Connect to scene signals to handle notes added from other sources
        self._scene.item_added.connect(self._on_item_added_to_scene)

        # Zoom configuration
        self._zoom_factor = 1.0
        self._min_zoom = 0.1
        self._max_zoom = 10.0
        self._zoom_step = 1.2

        # Pan configuration
        self._pan_mode = False
        self._last_pan_point = QPointF()

        # Connection creation configuration
        self._connection_mode = False
        self._connection_start_note = None
        self._connection_preview_line = None
        self._connection_drag_threshold = (
            10  # Minimum drag distance to start connection
        )
        self._connection_target_note = None  # Currently highlighted target note

        # Configure view properties
        self._setup_view()

        # Track existing connections to prevent duplicates
        self._connections = []

        self.logger.info("WhiteboardCanvas initialized")

    def _setup_view(self) -> None:
        """Configure view properties and settings."""
        # Enable antialiasing for smooth rendering
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # Configure drag mode and interaction
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setInteractive(True)

        # Configure scroll bars
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)

        # Set focus policy to receive keyboard events
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event: QWheelEvent) -> None:
        """
        Handle mouse wheel events for zooming with zoom-to-cursor functionality.

        Args:
            event: Wheel event containing scroll information
        """
        # Check if Ctrl is pressed for zoom, otherwise scroll
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Get mouse position in view coordinates
            mouse_pos = event.position()

            # Get the scene point under the mouse before zooming
            scene_pos = self.mapToScene(mouse_pos.toPoint())

            # Store the current zoom factor
            old_zoom = self._zoom_factor

            # Zoom in/out based on wheel direction
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()

            # Calculate the new scene position under the mouse after zooming
            new_scene_pos = self.mapToScene(mouse_pos.toPoint())

            # Calculate the difference and adjust the view to keep the scene point under the cursor
            delta = new_scene_pos - scene_pos

            # Pan the view to compensate for the zoom shift
            self.pan(-delta.x(), -delta.y())

            self.logger.debug(
                f"Zoom-to-cursor: old_zoom={old_zoom:.2f}, new_zoom={self._zoom_factor:.2f}, scene_pos=({scene_pos.x():.1f}, {scene_pos.y():.1f})"
            )
        else:
            # Default scroll behavior
            super().wheelEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse press events for pan initiation and connection creation.

        Args:
            event: Mouse press event
        """
        if event.button() == Qt.MouseButton.MiddleButton:
            # Start panning with middle mouse button
            self._pan_mode = True
            self._last_pan_point = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif (
            event.button() == Qt.MouseButton.LeftButton
            and event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            # Alternative pan with Shift+Left click
            self._pan_mode = True
            self._last_pan_point = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif (
            event.button() == Qt.MouseButton.LeftButton
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            # Connection creation mode with Ctrl+Left click
            scene_pos = self.mapToScene(event.pos())
            item_at_pos = self.scene().itemAt(scene_pos, self.transform())

            if isinstance(item_at_pos, NoteItem):
                self._start_connection_creation(item_at_pos, event.position())
            else:
                # Default behavior if not clicking on a note
                super().mousePressEvent(event)
        else:
            # Default behavior for other mouse interactions
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse move events for panning and connection creation.

        Args:
            event: Mouse move event
        """
        if self._pan_mode:
            # Calculate pan delta
            delta = event.position() - self._last_pan_point
            self._last_pan_point = event.position()

            # Apply pan by adjusting scroll bars
            h_bar = self.horizontalScrollBar()
            v_bar = self.verticalScrollBar()

            h_bar.setValue(h_bar.value() - int(delta.x()))
            v_bar.setValue(v_bar.value() - int(delta.y()))

            # Emit pan changed signal
            self.pan_changed.emit(self.mapToScene(self.rect().center()))
        elif self._connection_mode:
            # Update connection preview
            self._update_connection_preview(event.position())
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse release events to end panning and complete connections.

        Args:
            event: Mouse release event
        """
        if event.button() == Qt.MouseButton.MiddleButton or (
            event.button() == Qt.MouseButton.LeftButton and self._pan_mode
        ):
            # End panning
            self._pan_mode = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        elif event.button() == Qt.MouseButton.LeftButton and self._connection_mode:
            # Complete connection creation
            self._complete_connection_creation(event.position())

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse double-click events for note creation.

        Creates a new note at the double-click position if the click is on empty canvas.

        Args:
            event: Mouse double-click event
        """
        if event.button() == Qt.MouseButton.LeftButton:
            # Convert click position to scene coordinates
            scene_pos = self.mapToScene(event.pos())

            # Check if click is on empty canvas (not on an existing item)
            item_at_pos = self.scene().itemAt(scene_pos, self.transform())

            if item_at_pos is None:
                # Create new note at click position
                self._create_note_at_position(scene_pos)
                self.logger.debug(f"Created note via double-click at {scene_pos}")
            else:
                # Let the item handle the double-click (e.g., for editing)
                super().mouseDoubleClickEvent(event)
        else:
            super().mouseDoubleClickEvent(event)

    def _create_note_at_position(self, position: QPointF) -> NoteItem:
        """
        Create a new note at the specified position.

        Args:
            position: Scene position where the note should be created

        Returns:
            The newly created NoteItem
        """
        # Create new note
        note = NoteItem("", position)

        # Connect note signals for user feedback
        note.hover_started.connect(self._on_note_hover_started)
        note.hover_ended.connect(self._on_note_hover_ended)

        # Add to scene
        self.scene().addItem(note)

        # Automatically enter edit mode for new notes
        note.setFocus()
        note.enter_edit_mode()

        # Emit signal
        self.note_created.emit(note)

        self.logger.info(f"Created new note at position {position}")

        return note

    def _on_note_hover_started(self, hint_text: str) -> None:
        """
        Handle note hover start events.

        Args:
            hint_text: Hint text to display in status bar
        """
        self.note_hover_hint.emit(hint_text)

    def _on_note_hover_ended(self) -> None:
        """Handle note hover end events."""
        self.note_hover_ended.emit()

    def _on_item_added_to_scene(self, item) -> None:
        """
        Handle items added to the scene to connect note signals.

        Args:
            item: Graphics item added to scene
        """
        # Connect hover signals if it's a NoteItem
        if isinstance(item, NoteItem):
            item.hover_started.connect(self._on_note_hover_started)
            item.hover_ended.connect(self._on_note_hover_ended)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        Handle keyboard shortcuts for canvas navigation and context menu actions.

        Args:
            event: Key press event
        """
        key = event.key()
        modifiers = event.modifiers()

        # Handle context menu shortcuts
        if self._handle_context_menu_shortcuts(key, modifiers):
            return

        # Handle zoom shortcuts
        if self._handle_zoom_shortcuts(key, modifiers):
            return

        # Handle pan shortcuts
        if self._handle_pan_shortcuts(key):
            return

        # Handle other navigation shortcuts
        if self._handle_navigation_shortcuts(key):
            return

        # Default behavior
        super().keyPressEvent(event)

    def _handle_zoom_shortcuts(self, key: int, modifiers) -> bool:
        """
        Handle zoom-related keyboard shortcuts.

        Args:
            key: Key code
            modifiers: Keyboard modifiers

        Returns:
            True if shortcut was handled, False otherwise
        """
        if not (modifiers & Qt.KeyboardModifier.ControlModifier):
            return False

        if key == Qt.Key.Key_Plus or key == Qt.Key.Key_Equal:
            self.zoom_in()
            return True
        elif key == Qt.Key.Key_Minus:
            self.zoom_out()
            return True
        elif key == Qt.Key.Key_0:
            self.reset_zoom()
            return True

        return False

    def _handle_context_menu_shortcuts(self, key: int, modifiers) -> bool:
        """
        Handle context menu related keyboard shortcuts.

        Args:
            key: Key code
            modifiers: Keyboard modifiers

        Returns:
            True if shortcut was handled, False otherwise
        """
        # Delete key - delete selected items
        if key == Qt.Key.Key_Delete or key == Qt.Key.Key_Backspace:
            return self._handle_delete_shortcut()

        # Ctrl+C - Copy selected note content
        if (modifiers & Qt.KeyboardModifier.ControlModifier) and key == Qt.Key.Key_C:
            return self._handle_copy_shortcut()

        # Ctrl+A - Select all items
        if (modifiers & Qt.KeyboardModifier.ControlModifier) and key == Qt.Key.Key_A:
            return self._handle_select_all_shortcut()

        # Ctrl+N - Create new note at center
        if (modifiers & Qt.KeyboardModifier.ControlModifier) and key == Qt.Key.Key_N:
            return self._handle_new_note_shortcut()

        return False

    def _handle_delete_shortcut(self) -> bool:
        """Handle delete key shortcut for selected items."""
        selected_items = self.scene().selectedItems()
        if not selected_items:
            return False

        from PyQt6.QtWidgets import QMessageBox

        # Get parent window for dialog
        parent = self.window()

        # Confirm deletion
        item_count = len(selected_items)
        item_types = []
        for item in selected_items:
            if hasattr(item, "_note_id"):
                item_types.append("note")
            elif hasattr(item, "_connection_id"):
                item_types.append("connection")

        if not item_types:
            return False

        type_summary = ", ".join(set(item_types))
        reply = QMessageBox.question(
            parent,
            "Delete Items",
            f"Are you sure you want to delete {item_count} {type_summary}(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            for item in selected_items:
                if hasattr(item, "_delete_note"):
                    item._delete_note()
                elif hasattr(item, "delete_connection"):
                    item.delete_connection()

            self.logger.info(f"Deleted {item_count} items via keyboard shortcut")
            return True

        return True  # Handled even if cancelled

    def _handle_copy_shortcut(self) -> bool:
        """Handle copy shortcut for selected note content."""
        selected_items = self.scene().selectedItems()
        note_items = [item for item in selected_items if hasattr(item, "_note_id")]

        if not note_items:
            return False

        if len(note_items) == 1:
            # Single note - copy its content
            note_items[0]._copy_note_content()
        else:
            # Multiple notes - copy all content
            from PyQt6.QtWidgets import QApplication

            all_text = []
            for note in note_items:
                text = note.get_text().strip()
                if text:
                    all_text.append(text)

            if all_text:
                clipboard = QApplication.clipboard()
                clipboard.setText("\n\n".join(all_text))
                self.logger.info(
                    f"Copied content from {len(note_items)} notes to clipboard"
                )

        return True

    def _handle_select_all_shortcut(self) -> bool:
        """Handle select all shortcut."""
        # Select all items in the scene
        for item in self.scene().items():
            if hasattr(item, "_note_id") or hasattr(item, "_connection_id"):
                item.setSelected(True)

        self.logger.debug("Selected all items via keyboard shortcut")
        return True

    def _handle_new_note_shortcut(self) -> bool:
        """Handle new note shortcut - create note at center of view."""
        # Get center of current view
        center_point = self.mapToScene(self.rect().center())

        # Create note at center
        self._create_note_at_position(center_point)
        return True

    def _handle_pan_shortcuts(self, key: int) -> bool:
        """
        Handle pan-related keyboard shortcuts with enhanced user experience.

        Args:
            key: Key code

        Returns:
            True if shortcut was handled, False otherwise
        """
        # Adaptive pan distance based on zoom level for better UX
        base_pan_distance = 50
        zoom_adjusted_distance = base_pan_distance / max(self._zoom_factor, 0.1)
        pan_distance = max(20, min(zoom_adjusted_distance, 200))  # Clamp between 20-200

        if key == Qt.Key.Key_Left:
            self.pan(-pan_distance, 0)
            self.logger.debug(
                f"Pan left by {pan_distance:.1f} pixels (zoom: {self._zoom_factor:.2f})"
            )
            return True
        elif key == Qt.Key.Key_Right:
            self.pan(pan_distance, 0)
            self.logger.debug(
                f"Pan right by {pan_distance:.1f} pixels (zoom: {self._zoom_factor:.2f})"
            )
            return True
        elif key == Qt.Key.Key_Up:
            self.pan(0, -pan_distance)
            self.logger.debug(
                f"Pan up by {pan_distance:.1f} pixels (zoom: {self._zoom_factor:.2f})"
            )
            return True
        elif key == Qt.Key.Key_Down:
            self.pan(0, pan_distance)
            self.logger.debug(
                f"Pan down by {pan_distance:.1f} pixels (zoom: {self._zoom_factor:.2f})"
            )
            return True

        return False

    def _handle_navigation_shortcuts(self, key: int) -> bool:
        """
        Handle other navigation shortcuts.

        Args:
            key: Key code

        Returns:
            True if shortcut was handled, False otherwise
        """
        if key == Qt.Key.Key_Home:
            self.center_on_content()
            return True

        return False

    def zoom_in(self) -> None:
        """Zoom in on the canvas with enhanced user experience."""
        old_zoom = self._zoom_factor
        new_zoom = min(self._zoom_factor * self._zoom_step, self._max_zoom)

        if new_zoom != old_zoom:
            self._set_zoom(new_zoom)
            self.logger.info(f"Zoomed in from {old_zoom:.1f}x to {new_zoom:.1f}x")
        else:
            self.logger.debug(f"Maximum zoom level reached: {self._max_zoom:.1f}x")

    def zoom_out(self) -> None:
        """Zoom out on the canvas with enhanced user experience."""
        old_zoom = self._zoom_factor
        new_zoom = max(self._zoom_factor / self._zoom_step, self._min_zoom)

        if new_zoom != old_zoom:
            self._set_zoom(new_zoom)
            self.logger.info(f"Zoomed out from {old_zoom:.1f}x to {new_zoom:.1f}x")
        else:
            self.logger.debug(f"Minimum zoom level reached: {self._min_zoom:.1f}x")

    def reset_zoom(self) -> None:
        """Reset zoom to 100% (1.0) with enhanced feedback."""
        old_zoom = self._zoom_factor
        self._set_zoom(1.0)
        self.logger.info(f"Zoom reset from {old_zoom:.1f}x to 1.0x (100%)")

    def set_zoom(self, zoom_factor: float) -> None:
        """
        Set specific zoom level with enhanced validation and feedback.

        Args:
            zoom_factor: Zoom level (1.0 = 100%)
        """
        old_zoom = self._zoom_factor
        clamped_zoom = max(self._min_zoom, min(zoom_factor, self._max_zoom))

        if clamped_zoom != zoom_factor:
            self.logger.debug(
                f"Zoom factor {zoom_factor:.2f} clamped to {clamped_zoom:.2f}"
            )

        self._set_zoom(clamped_zoom)

        if clamped_zoom != old_zoom:
            self.logger.info(f"Zoom set from {old_zoom:.1f}x to {clamped_zoom:.1f}x")

    def _set_zoom(self, zoom_factor: float) -> None:
        """
        Internal method to apply zoom transformation with enhanced precision.

        Args:
            zoom_factor: Target zoom level
        """
        if abs(zoom_factor - self._zoom_factor) < 0.001:  # More precise comparison
            return

        # Store center point before zoom for better user experience
        center_before = self.mapToScene(self.rect().center())

        # Calculate scale factor relative to current zoom
        scale_factor = zoom_factor / self._zoom_factor

        # Apply scaling transformation
        self.scale(scale_factor, scale_factor)

        # Update zoom factor
        self._zoom_factor = zoom_factor

        # Maintain center point after zoom for consistent experience
        center_after = self.mapToScene(self.rect().center())
        delta = center_after - center_before
        if not (
            abs(delta.x()) < 1 and abs(delta.y()) < 1
        ):  # Only adjust if significant drift
            self.pan(-delta.x(), -delta.y())

        # Emit zoom changed signal
        self.zoom_changed.emit(self._zoom_factor)

        self.logger.debug(
            f"Zoom applied: {self._zoom_factor:.3f}x (scale factor: {scale_factor:.3f})"
        )

    def pan(self, dx: float, dy: float) -> None:
        """
        Pan the view by specified amounts with enhanced bounds checking.

        Args:
            dx: Horizontal pan distance in pixels
            dy: Vertical pan distance in pixels
        """
        h_bar = self.horizontalScrollBar()
        v_bar = self.verticalScrollBar()

        # Store old values for logging
        old_h = h_bar.value()
        old_v = v_bar.value()

        # Apply pan with bounds checking
        new_h = max(h_bar.minimum(), min(h_bar.value() + int(dx), h_bar.maximum()))
        new_v = max(v_bar.minimum(), min(v_bar.value() + int(dy), v_bar.maximum()))

        h_bar.setValue(new_h)
        v_bar.setValue(new_v)

        # Log actual pan distance
        actual_dx = new_h - old_h
        actual_dy = new_v - old_v

        if actual_dx != 0 or actual_dy != 0:
            self.logger.debug(
                f"Pan applied: dx={actual_dx}, dy={actual_dy} (requested: dx={dx:.1f}, dy={dy:.1f})"
            )

        # Emit pan changed signal
        center_point = self.mapToScene(self.rect().center())
        self.pan_changed.emit(center_point)

    def center_on_content(self) -> None:
        """Center the view on all content in the scene with enhanced feedback."""
        content_center = self._scene.center_on_content()
        old_center = self.mapToScene(self.rect().center())

        self.centerOn(content_center)
        self.pan_changed.emit(content_center)

        # Calculate distance moved for user feedback
        distance = (
            (content_center.x() - old_center.x()) ** 2
            + (content_center.y() - old_center.y()) ** 2
        ) ** 0.5
        self.logger.info(
            f"Centered on content at ({content_center.x():.0f}, {content_center.y():.0f}), moved {distance:.0f} pixels"
        )

    def center_on_point(self, x: float, y: float) -> None:
        """Center the view on a specific point with enhanced feedback."""
        target_point = QPointF(x, y)
        old_center = self.mapToScene(self.rect().center())

        self.centerOn(target_point)
        self.pan_changed.emit(target_point)

        # Calculate distance moved for user feedback
        distance = (
            (target_point.x() - old_center.x()) ** 2
            + (target_point.y() - old_center.y()) ** 2
        ) ** 0.5
        self.logger.info(
            f"Centered on point ({target_point.x():.0f}, {target_point.y():.0f}), moved {distance:.0f} pixels"
        )

    def fit_content_in_view(self) -> None:
        """Fit all content to be visible in the current view with enhanced feedback."""
        content_bounds = self._scene.get_content_bounds()
        if content_bounds.isNull():
            self.logger.info("No content to fit in view")
            return

        old_zoom = self._zoom_factor

        # Add adaptive margin based on content size
        content_size = max(content_bounds.width(), content_bounds.height())
        margin = max(
            20, min(content_size * 0.1, 100)
        )  # 10% of content size, clamped 20-100
        content_bounds.adjust(-margin, -margin, margin, margin)

        # Fit the content bounds in view
        self.fitInView(content_bounds, Qt.AspectRatioMode.KeepAspectRatio)

        # Update zoom factor based on transformation
        transform = self.transform()
        self._zoom_factor = max(self._min_zoom, min(transform.m11(), self._max_zoom))

        # Emit zoom changed signal and log the change
        self.zoom_changed.emit(self._zoom_factor)
        self.logger.info(
            f"Fitted content in view: zoom changed from {old_zoom:.2f}x to {self._zoom_factor:.2f}x"
        )

    def get_zoom_factor(self) -> float:
        """
        Get current zoom factor.

        Returns:
            Current zoom level (1.0 = 100%)
        """
        return self._zoom_factor

    def get_center_point(self) -> QPointF:
        """
        Get current center point in scene coordinates.

        Returns:
            Center point of the current view
        """
        return self.mapToScene(self.rect().center())

    def get_canvas_statistics(self) -> dict:
        """
        Get statistics about the current canvas state.

        Returns:
            Dictionary containing canvas statistics
        """
        center_point = self.get_center_point()
        scene_stats = self._scene.get_scene_statistics()

        return {
            "zoom_factor": self._zoom_factor,
            "center_x": center_point.x(),
            "center_y": center_point.y(),
            "view_width": self.width(),
            "view_height": self.height(),
            "connection_count": len(self._connections),
            **scene_stats,
        }

    def _start_connection_creation(
        self, start_note: NoteItem, mouse_pos: QPointF
    ) -> None:
        """
        Start connection creation from a note.

        Args:
            start_note: Note to start the connection from
            mouse_pos: Mouse position in view coordinates
        """
        self._connection_mode = True
        self._connection_start_note = start_note
        self._last_pan_point = mouse_pos  # Store initial position for drag threshold

        # Change cursor to indicate connection mode
        self.setCursor(Qt.CursorShape.CrossCursor)

        self.logger.debug(
            f"Started connection creation from note {start_note.get_note_id()}"
        )

    def _update_connection_preview(self, mouse_pos: QPointF) -> None:
        """
        Update the connection preview line during dragging.

        Args:
            mouse_pos: Current mouse position in view coordinates
        """
        if not self._connection_start_note:
            return

        # Check if we've moved enough to start showing preview
        drag_distance = (mouse_pos - self._last_pan_point).manhattanLength()
        if drag_distance < self._connection_drag_threshold:
            return

        # Convert positions to scene coordinates
        start_scene_pos = self._connection_start_note.mapToScene(
            self._connection_start_note.boundingRect().center()
        )
        end_scene_pos = self.mapToScene(mouse_pos.toPoint())

        # Check if mouse is over a valid target note
        item_at_pos = self.scene().itemAt(end_scene_pos, self.transform())
        target_note = None

        if (
            isinstance(item_at_pos, NoteItem)
            and item_at_pos != self._connection_start_note
        ):
            # Check if connection doesn't already exist
            if not self._connection_exists(self._connection_start_note, item_at_pos):
                target_note = item_at_pos

        # Update target note highlighting
        self._update_target_note_highlight(target_note)

        # Create or update preview line
        if not self._connection_preview_line:
            from PyQt6.QtWidgets import QGraphicsLineItem

            self._connection_preview_line = QGraphicsLineItem()
            self._connection_preview_line.setZValue(
                -0.5
            )  # Behind notes but above background
            self.scene().addItem(self._connection_preview_line)

        # Update preview line style based on whether we have a valid target
        if target_note:
            # Green dashed line when over valid target
            pen = QPen(QColor(50, 150, 50), 3, Qt.PenStyle.DashLine)
            # Emit hint for status bar
            self.note_hover_hint.emit("🔗 Release to create connection")
        else:
            # Gray dashed line when not over valid target
            pen = QPen(Qt.GlobalColor.gray, 2, Qt.PenStyle.DashLine)
            # Emit hint for status bar
            self.note_hover_hint.emit("🔗 Drag to another note to create connection")

        self._connection_preview_line.setPen(pen)

        # Update preview line position
        self._connection_preview_line.setLine(
            start_scene_pos.x(),
            start_scene_pos.y(),
            end_scene_pos.x(),
            end_scene_pos.y(),
        )

    def _update_target_note_highlight(self, target_note: NoteItem) -> None:
        """
        Update the visual highlighting of the target note during connection creation.

        Args:
            target_note: Note to highlight as connection target, or None to clear highlight
        """
        # Clear previous target highlight
        if self._connection_target_note and self._connection_target_note != target_note:
            self._connection_target_note.setSelected(False)
            self._connection_target_note.update()

        # Set new target highlight
        if target_note and target_note != self._connection_target_note:
            target_note.setSelected(True)
            target_note.update()

        self._connection_target_note = target_note

    def _complete_connection_creation(self, mouse_pos: QPointF) -> None:
        """
        Complete connection creation by finding the target note.

        Args:
            mouse_pos: Final mouse position in view coordinates
        """
        if not self._connection_start_note:
            self._cancel_connection_creation()
            return

        # Check if we've moved enough to create a connection
        drag_distance = (mouse_pos - self._last_pan_point).manhattanLength()
        if drag_distance < self._connection_drag_threshold:
            self._cancel_connection_creation()
            return

        # Find target note
        scene_pos = self.mapToScene(mouse_pos.toPoint())
        item_at_pos = self.scene().itemAt(scene_pos, self.transform())

        if (
            isinstance(item_at_pos, NoteItem)
            and item_at_pos != self._connection_start_note
        ):
            # Create connection between notes
            if not self._connection_exists(self._connection_start_note, item_at_pos):
                connection = self._create_connection(
                    self._connection_start_note, item_at_pos
                )
                if connection:
                    self.logger.info(
                        f"Created connection between notes {self._connection_start_note.get_note_id()} "
                        f"and {item_at_pos.get_note_id()}"
                    )
            else:
                self.logger.debug("Connection already exists between these notes")

        # Clean up connection creation mode
        self._cancel_connection_creation()

    def _cancel_connection_creation(self) -> None:
        """Cancel connection creation and clean up."""
        self._connection_mode = False
        self._connection_start_note = None

        # Clear target note highlight
        if self._connection_target_note:
            self._connection_target_note.setSelected(False)
            self._connection_target_note.update()
            self._connection_target_note = None

        # Remove preview line if it exists
        if self._connection_preview_line:
            self.scene().removeItem(self._connection_preview_line)
            self._connection_preview_line = None

        # Clear status bar hint
        self.note_hover_ended.emit()

        # Reset cursor
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def _connection_exists(self, note1: NoteItem, note2: NoteItem) -> bool:
        """
        Check if a connection already exists between two notes.

        Args:
            note1: First note
            note2: Second note

        Returns:
            True if connection exists, False otherwise
        """
        for connection in self._connections:
            if connection.is_connected_to_note(
                note1
            ) and connection.is_connected_to_note(note2):
                return True
        return False

    def _create_connection(
        self, start_note: NoteItem, end_note: NoteItem
    ) -> ConnectionItem:
        """
        Create a new connection between two notes.

        Args:
            start_note: Starting note
            end_note: Ending note

        Returns:
            The created ConnectionItem, or None if creation failed
        """
        try:
            # Create connection
            connection = ConnectionItem(start_note, end_note)

            # Add to scene
            self.scene().addItem(connection)

            # Track connection
            self._connections.append(connection)

            # Connect to deletion signal to remove from tracking
            connection.signals.connection_deleted.connect(
                lambda: self._on_connection_deleted(connection)
            )

            # Emit signal
            self.connection_created.emit(connection)

            return connection

        except Exception as e:
            self.logger.error(f"Failed to create connection: {e}")
            return None

    def _on_connection_deleted(self, connection: ConnectionItem) -> None:
        """
        Handle connection deletion.

        Args:
            connection: Connection that was deleted
        """
        if connection in self._connections:
            self._connections.remove(connection)
            self.logger.debug(
                f"Removed connection {connection.get_connection_id()} from tracking"
            )

    def get_connections(self) -> list[ConnectionItem]:
        """
        Get all connections in the canvas.

        Returns:
            List of ConnectionItem objects
        """
        return self._connections.copy()

    def delete_connection(self, connection: ConnectionItem) -> None:
        """
        Delete a specific connection.

        Args:
            connection: Connection to delete
        """
        if connection in self._connections:
            connection.delete_connection()

    def delete_connections_for_note(self, note: NoteItem) -> None:
        """
        Delete all connections associated with a note.

        Args:
            note: Note whose connections should be deleted
        """
        # Create a copy of the list to avoid modification during iteration
        connections_to_delete = [
            conn for conn in self._connections if conn.is_connected_to_note(note)
        ]

        for connection in connections_to_delete:
            connection.delete_connection()

    def set_connection_mode(self, enabled: bool) -> None:
        """
        Enable or disable connection creation mode.

        Args:
            enabled: True to enable connection mode, False to disable
        """
        if not enabled and self._connection_mode:
            self._cancel_connection_creation()

        # This could be used for a toolbar button to toggle connection mode
        # For now, we use Ctrl+click for connection creation

    def resizeEvent(self, event) -> None:
        """Handle resize events and emit viewport changes."""
        super().resizeEvent(event)

        # Emit viewport changed signal when view is resized
        viewport_rect = self.mapToScene(self.rect()).boundingRect()
        self.viewport_changed.emit(viewport_rect)

        self.logger.debug(f"Canvas resized to {event.size()}, viewport updated")

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """
        Handle context menu (right-click) events on the canvas.

        Args:
            event: Context menu event
        """
        # Check if we clicked on an item - if so, let the item handle it
        scene_pos = self.mapToScene(event.pos())
        item = self.scene().itemAt(scene_pos, self.transform())

        if item is not None:
            # Let the item handle its own context menu
            super().contextMenuEvent(event)
            return

        # Create canvas context menu
        menu = QMenu(self)

        # Note creation section
        create_menu = menu.addMenu("📝 Create Note")

        # Quick note creation
        quick_note_action = create_menu.addAction("✏️ Quick Note")
        quick_note_action.setShortcut(QKeySequence("Ctrl+N"))
        quick_note_action.triggered.connect(
            lambda: self._create_note_at_position(scene_pos)
        )

        # Template notes
        template_menu = create_menu.addMenu("📋 From Template")
        self._populate_canvas_template_menu(template_menu, scene_pos)

        menu.addSeparator()

        # Canvas operations section
        operations_menu = menu.addMenu("🔧 Canvas Operations")

        # Select all notes
        select_all_action = operations_menu.addAction("🔲 Select All Notes")
        select_all_action.setShortcut(QKeySequence("Ctrl+A"))
        select_all_action.triggered.connect(self._select_all_notes)

        # Clear selection
        clear_selection_action = operations_menu.addAction("❌ Clear Selection")
        clear_selection_action.triggered.connect(self._clear_selection)

        operations_menu.addSeparator()

        # Center on content
        center_action = operations_menu.addAction("🎯 Center on Content")
        center_action.triggered.connect(self._center_on_content)

        # Fit all content
        fit_action = operations_menu.addAction("🔍 Fit All Content")
        fit_action.triggered.connect(self._fit_all_content)

        menu.addSeparator()

        # Zoom controls section
        zoom_menu = menu.addMenu("🔍 Zoom")

        zoom_in_action = zoom_menu.addAction("🔍+ Zoom In")
        zoom_in_action.triggered.connect(self.zoom_in)

        zoom_out_action = zoom_menu.addAction("🔍- Zoom Out")
        zoom_out_action.triggered.connect(self.zoom_out)

        zoom_menu.addSeparator()

        zoom_reset_action = zoom_menu.addAction("🔍 Reset Zoom (100%)")
        zoom_reset_action.triggered.connect(self.reset_zoom)

        menu.addSeparator()

        # View information
        info_action = menu.addAction("ℹ️ Canvas Info")
        info_action.triggered.connect(self._show_canvas_info)

        # Show menu at cursor position
        menu.exec(event.globalPos())

        # Accept the event to prevent propagation
        event.accept()

    def _create_note_at_position(
        self, scene_pos: QPointF, text: str = "New Note"
    ) -> NoteItem:
        """
        Create a new note at the specified scene position.

        Args:
            scene_pos: Position in scene coordinates
            text: Initial text for the note

        Returns:
            The newly created NoteItem
        """
        note = NoteItem(text, scene_pos)
        self._scene.addItem(note)

        # Connect note signals
        self._connect_note_signals(note)

        # Emit signal
        self.note_created.emit(note)

        # Enter edit mode immediately
        note.enter_edit_mode()

        self.logger.info(
            f"Created note at position ({scene_pos.x():.1f}, {scene_pos.y():.1f})"
        )

        return note

    def _populate_canvas_template_menu(
        self, template_menu: QMenu, scene_pos: QPointF
    ) -> None:
        """
        Populate the template menu with available note templates.

        Args:
            template_menu: Menu to populate
            scene_pos: Position where note will be created
        """
        from .style_manager import get_style_manager

        style_manager = get_style_manager()
        template_names = style_manager.get_template_names()

        if not template_names:
            no_templates_action = template_menu.addAction("No templates available")
            no_templates_action.setEnabled(False)
            return

        for template_name in template_names:
            action = template_menu.addAction(f"📄 {template_name}")
            action.triggered.connect(
                lambda checked,
                name=template_name,
                pos=scene_pos: self._create_note_from_template(name, pos)
            )

    def _create_note_from_template(
        self, template_name: str, scene_pos: QPointF
    ) -> None:
        """
        Create a note from a template at the specified position.

        Args:
            template_name: Name of the template to use
            scene_pos: Position in scene coordinates
        """
        from .style_manager import get_style_manager

        style_manager = get_style_manager()
        template = style_manager.get_template_style(template_name)

        if not template:
            self.logger.warning(f"Template '{template_name}' not found")
            return

        # Create note with template text
        note_text = f"{template_name} Note"
        note = NoteItem(note_text, scene_pos)

        # Apply template style
        note.set_style(template)

        self._scene.addItem(note)
        self._connect_note_signals(note)
        self.note_created.emit(note)

        # Enter edit mode
        note.enter_edit_mode()

        self.logger.info(
            f"Created note from template '{template_name}' at position ({scene_pos.x():.1f}, {scene_pos.y():.1f})"
        )

    def _select_all_notes(self) -> None:
        """Select all notes on the canvas."""
        for item in self._scene.items():
            if isinstance(item, NoteItem):
                item.setSelected(True)

        self.logger.debug("Selected all notes on canvas")

    def _clear_selection(self) -> None:
        """Clear all selections on the canvas."""
        self._scene.clearSelection()
        self.logger.debug("Cleared all selections on canvas")

    def _center_on_content(self) -> None:
        """Center the view on all content."""
        content_center = self._scene.center_on_content()
        self.centerOn(content_center)
        self.logger.debug(
            f"Centered view on content at ({content_center.x():.1f}, {content_center.y():.1f})"
        )

    def _fit_all_content(self) -> None:
        """Fit all content in the view."""
        content_bounds = self._scene.get_content_bounds()
        if not content_bounds.isNull():
            # Add some padding around the content
            padding = 50
            padded_bounds = content_bounds.adjusted(
                -padding, -padding, padding, padding
            )
            self.fitInView(padded_bounds, Qt.AspectRatioMode.KeepAspectRatio)

            # Update zoom factor based on the new view
            self._zoom_factor = self.transform().m11()
            self.zoom_changed.emit(self._zoom_factor)

            self.logger.debug(
                f"Fitted all content in view, new zoom: {self._zoom_factor:.2f}"
            )

    def _show_canvas_info(self) -> None:
        """Show canvas information in the status bar."""
        stats = self._scene.get_scene_statistics()
        info_text = (
            f"📊 Canvas: {stats['item_count']} items, "
            f"Zoom: {self._zoom_factor:.1%}, "
            f"Scene: {stats['scene_width']:.0f}×{stats['scene_height']:.0f}, "
            f"Content: {stats['content_width']:.0f}×{stats['content_height']:.0f}"
        )

        # Emit as hover hint to show in status bar
        self.note_hover_hint.emit(info_text)

        self.logger.debug(f"Canvas info: {stats}")

    def _connect_note_signals(self, note) -> None:
        """
        Connect note signals to canvas handlers.

        Args:
            note: The note item to connect signals for
        """
        # Connect note signals if they exist
        if hasattr(note, "text_changed"):
            note.text_changed.connect(self._on_note_text_changed)
        if hasattr(note, "position_changed"):
            note.position_changed.connect(self._on_note_position_changed)
        if hasattr(note, "style_changed"):
            note.style_changed.connect(self._on_note_style_changed)

    def _on_note_text_changed(self, note_id: str, text: str) -> None:
        """Handle note text changes."""
        self.logger.debug(f"Note {note_id} text changed: {text[:50]}...")

    def _on_note_position_changed(self, position) -> None:
        """Handle note position changes."""
        self.logger.debug(
            f"Note position changed to ({position.x():.1f}, {position.y():.1f})"
        )

    def _on_note_style_changed(self, note_id: str, style: dict) -> None:
        """Handle note style changes."""
        self.logger.debug(f"Note {note_id} style changed: {style}")
