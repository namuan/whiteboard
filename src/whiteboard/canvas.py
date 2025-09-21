"""
Canvas components for the Digital Whiteboard application.

This module contains the core canvas infrastructure including the scene and view classes
that provide infinite scrolling, zooming, and interactive note management.
"""

from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter, QWheelEvent, QKeyEvent, QMouseEvent
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsItem

from .utils.logging_config import get_logger
from .note_item import NoteItem


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
        for item in self._tracked_items:
            if content_rect.isNull():
                content_rect = item.sceneBoundingRect()
            else:
                content_rect = content_rect.united(item.sceneBoundingRect())

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
    note_created = pyqtSignal(NoteItem)  # Emits when a new note is created
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

        # Configure view properties
        self._setup_view()

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
        Handle mouse wheel events for zooming.

        Args:
            event: Wheel event containing scroll information
        """
        # Check if Ctrl is pressed for zoom, otherwise scroll
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Zoom in/out based on wheel direction
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        else:
            # Default scroll behavior
            super().wheelEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse press events for pan initiation.

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
        else:
            # Default behavior for other mouse interactions
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse move events for panning.

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
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse release events to end panning.

        Args:
            event: Mouse release event
        """
        if event.button() == Qt.MouseButton.MiddleButton or (
            event.button() == Qt.MouseButton.LeftButton and self._pan_mode
        ):
            # End panning
            self._pan_mode = False
            self.setCursor(Qt.CursorShape.ArrowCursor)

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
        Handle keyboard shortcuts for canvas navigation.

        Args:
            event: Key press event
        """
        key = event.key()
        modifiers = event.modifiers()

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

    def _handle_pan_shortcuts(self, key: int) -> bool:
        """
        Handle pan-related keyboard shortcuts.

        Args:
            key: Key code

        Returns:
            True if shortcut was handled, False otherwise
        """
        pan_distance = 50

        if key == Qt.Key.Key_Left:
            self.pan(-pan_distance, 0)
            return True
        elif key == Qt.Key.Key_Right:
            self.pan(pan_distance, 0)
            return True
        elif key == Qt.Key.Key_Up:
            self.pan(0, -pan_distance)
            return True
        elif key == Qt.Key.Key_Down:
            self.pan(0, pan_distance)
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
        """Zoom in on the canvas."""
        new_zoom = min(self._zoom_factor * self._zoom_step, self._max_zoom)
        self._set_zoom(new_zoom)

    def zoom_out(self) -> None:
        """Zoom out on the canvas."""
        new_zoom = max(self._zoom_factor / self._zoom_step, self._min_zoom)
        self._set_zoom(new_zoom)

    def reset_zoom(self) -> None:
        """Reset zoom to 100% (1.0)."""
        self._set_zoom(1.0)

    def set_zoom(self, zoom_factor: float) -> None:
        """
        Set specific zoom level.

        Args:
            zoom_factor: Zoom level (1.0 = 100%)
        """
        clamped_zoom = max(self._min_zoom, min(zoom_factor, self._max_zoom))
        self._set_zoom(clamped_zoom)

    def _set_zoom(self, zoom_factor: float) -> None:
        """
        Internal method to apply zoom transformation.

        Args:
            zoom_factor: Target zoom level
        """
        if zoom_factor == self._zoom_factor:
            return

        # Calculate scale factor relative to current zoom
        scale_factor = zoom_factor / self._zoom_factor

        # Apply scaling transformation
        self.scale(scale_factor, scale_factor)

        # Update zoom factor
        self._zoom_factor = zoom_factor

        # Emit zoom changed signal
        self.zoom_changed.emit(self._zoom_factor)

        self.logger.debug(f"Zoom set to {self._zoom_factor:.2f}")

    def pan(self, dx: float, dy: float) -> None:
        """
        Pan the view by specified amounts.

        Args:
            dx: Horizontal pan distance in pixels
            dy: Vertical pan distance in pixels
        """
        h_bar = self.horizontalScrollBar()
        v_bar = self.verticalScrollBar()

        h_bar.setValue(h_bar.value() + int(dx))
        v_bar.setValue(v_bar.value() + int(dy))

        # Emit pan changed signal
        self.pan_changed.emit(self.mapToScene(self.rect().center()))

    def center_on_content(self) -> None:
        """Center the view on all content in the scene."""
        content_center = self._scene.center_on_content()
        self.centerOn(content_center)
        self.pan_changed.emit(content_center)
        self.logger.debug(f"Centered on content at {content_center}")

    def fit_content_in_view(self) -> None:
        """Fit all content to be visible in the current view."""
        content_bounds = self._scene.get_content_bounds()
        if not content_bounds.isNull():
            # Add some margin around content
            margin = 50
            content_bounds.adjust(-margin, -margin, margin, margin)

            # Fit the content bounds in view
            self.fitInView(content_bounds, Qt.AspectRatioMode.KeepAspectRatio)

            # Update zoom factor based on transformation
            transform = self.transform()
            self._zoom_factor = transform.m11()  # Get scale factor

            self.zoom_changed.emit(self._zoom_factor)
            self.logger.debug("Fitted content in view")

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
            **scene_stats,
        }
