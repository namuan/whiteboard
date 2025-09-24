"""
Image resize handle implementation for the Digital Whiteboard application.

This module contains the ImageResizeHandle class which provides interactive
resize handles for ImageItem objects, supporting corner and edge resizing
with aspect ratio preservation and modifier key support.
"""

from enum import Enum
from collections.abc import Callable
from PyQt6.QtCore import Qt, QPointF, QRectF, QSizeF
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QCursor
from PyQt6.QtWidgets import (
    QGraphicsItem,
    QGraphicsSceneMouseEvent,
    QGraphicsSceneHoverEvent,
    QApplication,
)

from .utils.logging_config import get_logger


class HandleType(Enum):
    """Types of resize handles."""

    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"


class ImageResizeHandle(QGraphicsItem):
    """
    Interactive resize handle for ImageItem objects.

    Provides visual handles at corners and edges of images that allow
    users to resize images by dragging. Supports aspect ratio preservation
    and modifier keys for free resize.
    """

    def __init__(self, handle_type: HandleType, parent_item: QGraphicsItem):
        """
        Initialize a resize handle.

        Args:
            handle_type: Type of handle (corner or edge)
            parent_item: The ImageItem this handle belongs to
        """
        super().__init__(parent_item)
        self.logger = get_logger(__name__)

        self._handle_type = handle_type
        self._parent_item = parent_item
        self._handle_size = 8
        self._is_dragging = False
        self._drag_start_pos = QPointF()
        self._original_rect = QRectF()

        # Callback functions instead of signals
        self._resize_started_callback: Callable[[], None] | None = None
        self._resize_updated_callback: Callable[[QRectF], None] | None = None
        self._resize_finished_callback: Callable[[QRectF], None] | None = None

        # Visual properties
        self._handle_color = QColor(0, 120, 215)  # Blue handle
        self._handle_border_color = QColor(255, 255, 255)  # White border
        self._handle_hover_color = QColor(0, 100, 180)  # Darker blue on hover

        # Set up graphics item properties
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setAcceptHoverEvents(True)
        self.setZValue(1000)  # Always on top

    def set_callbacks(
        self,
        resize_started: Callable[[], None] | None = None,
        resize_updated: Callable[[QRectF], None] | None = None,
        resize_finished: Callable[[QRectF], None] | None = None,
    ) -> None:
        """Set callback functions for resize events."""
        self._resize_started_callback = resize_started
        self._resize_updated_callback = resize_updated
        self._resize_finished_callback = resize_finished

        # Set cursor based on handle type
        self._setup_cursor()

        self.logger.debug(f"Created resize handle: {self._handle_type.value}")

    def _setup_cursor(self) -> None:
        """Set appropriate cursor for the handle type."""
        cursor_map = {
            HandleType.TOP_LEFT: Qt.CursorShape.SizeFDiagCursor,
            HandleType.TOP_RIGHT: Qt.CursorShape.SizeBDiagCursor,
            HandleType.BOTTOM_LEFT: Qt.CursorShape.SizeBDiagCursor,
            HandleType.BOTTOM_RIGHT: Qt.CursorShape.SizeFDiagCursor,
            HandleType.TOP: Qt.CursorShape.SizeVerCursor,
            HandleType.BOTTOM: Qt.CursorShape.SizeVerCursor,
            HandleType.LEFT: Qt.CursorShape.SizeHorCursor,
            HandleType.RIGHT: Qt.CursorShape.SizeHorCursor,
        }
        self.setCursor(QCursor(cursor_map[self._handle_type]))

    def boundingRect(self) -> QRectF:
        """Return the bounding rectangle of the handle."""
        return QRectF(
            -self._handle_size / 2,
            -self._handle_size / 2,
            self._handle_size,
            self._handle_size,
        )

    def paint(self, painter: QPainter, option, widget=None) -> None:
        """Paint the resize handle."""
        # Determine color based on hover state
        if self.isUnderMouse():
            fill_color = self._handle_hover_color
        else:
            fill_color = self._handle_color

        # Draw handle
        rect = self.boundingRect()
        painter.setPen(QPen(self._handle_border_color, 1))
        painter.setBrush(QBrush(fill_color))
        painter.drawRect(rect)

    def update_position(self, parent_rect: QRectF) -> None:
        """Update handle position based on parent item's rectangle."""
        # Position handle at appropriate location on parent's boundary
        if self._handle_type == HandleType.TOP_LEFT:
            pos = parent_rect.topLeft()
        elif self._handle_type == HandleType.TOP_RIGHT:
            pos = parent_rect.topRight()
        elif self._handle_type == HandleType.BOTTOM_LEFT:
            pos = parent_rect.bottomLeft()
        elif self._handle_type == HandleType.BOTTOM_RIGHT:
            pos = parent_rect.bottomRight()
        elif self._handle_type == HandleType.TOP:
            pos = QPointF(parent_rect.center().x(), parent_rect.top())
        elif self._handle_type == HandleType.BOTTOM:
            pos = QPointF(parent_rect.center().x(), parent_rect.bottom())
        elif self._handle_type == HandleType.LEFT:
            pos = QPointF(parent_rect.left(), parent_rect.center().y())
        elif self._handle_type == HandleType.RIGHT:
            pos = QPointF(parent_rect.right(), parent_rect.center().y())

        self.setPos(pos)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Handle mouse press to start resize operation."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._drag_start_pos = event.scenePos()
            self._original_rect = self._parent_item.boundingRect()
            if self._resize_started_callback:
                self._resize_started_callback()
            self.logger.debug(f"Started resize with {self._handle_type.value} handle")
            event.accept()  # Accept the event to prevent propagation
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Handle mouse move to update resize."""
        if not self._is_dragging:
            super().mouseMoveEvent(event)
            return

        # Calculate movement delta
        current_pos = event.scenePos()
        delta = current_pos - self._drag_start_pos

        # Check for modifier keys
        modifiers = QApplication.keyboardModifiers()
        maintain_aspect_ratio = not (modifiers & Qt.KeyboardModifier.ShiftModifier)

        # Calculate new rectangle based on handle type and movement
        new_rect = self._calculate_new_rect(delta, maintain_aspect_ratio)

        # Call resize update callback
        if self._resize_updated_callback:
            self._resize_updated_callback(new_rect)

        event.accept()  # Accept the event to prevent propagation
        self.logger.debug(
            f"Resizing with {self._handle_type.value} handle, delta: {delta}"
        )

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Handle mouse release to finish resize operation."""
        if self._is_dragging and event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False

            # Calculate final rectangle
            current_pos = event.scenePos()
            delta = current_pos - self._drag_start_pos

            modifiers = QApplication.keyboardModifiers()
            maintain_aspect_ratio = not (modifiers & Qt.KeyboardModifier.ShiftModifier)

            final_rect = self._calculate_new_rect(delta, maintain_aspect_ratio)
            if self._resize_finished_callback:
                self._resize_finished_callback(final_rect)

            self.logger.debug(f"Finished resize with {self._handle_type.value} handle")
            event.accept()  # Accept the event to prevent propagation
        else:
            super().mouseReleaseEvent(event)

    def _calculate_new_rect(self, delta: QPointF, preserve_aspect: bool) -> QRectF:
        """Calculate new rectangle based on handle movement."""
        if not self._parent_item:
            return QRectF()

        current_rect = self._parent_item.boundingRect()
        new_rect = QRectF(current_rect)

        # Apply resize based on handle type
        new_rect = self._apply_resize_delta(new_rect, delta)

        # Apply aspect ratio preservation if needed
        if preserve_aspect:
            new_rect = self._preserve_aspect_ratio(current_rect, new_rect)

        # Ensure minimum size
        return self._enforce_minimum_size(new_rect)

    def _apply_resize_delta(self, rect: QRectF, delta: QPointF) -> QRectF:
        """Apply resize delta based on handle type."""
        resize_methods = {
            HandleType.TOP_LEFT: self._resize_top_left,
            HandleType.TOP_RIGHT: self._resize_top_right,
            HandleType.BOTTOM_LEFT: self._resize_bottom_left,
            HandleType.BOTTOM_RIGHT: self._resize_bottom_right,
            HandleType.TOP: self._resize_top,
            HandleType.BOTTOM: self._resize_bottom,
            HandleType.LEFT: self._resize_left,
            HandleType.RIGHT: self._resize_right,
        }

        resize_method = resize_methods.get(self._handle_type)
        if resize_method:
            return resize_method(rect, delta)
        return rect

    def _resize_top_left(self, rect: QRectF, delta: QPointF) -> QRectF:
        """Resize from top-left corner."""
        rect.setTopLeft(rect.topLeft() + delta)
        return rect

    def _resize_top_right(self, rect: QRectF, delta: QPointF) -> QRectF:
        """Resize from top-right corner."""
        rect.setTopRight(rect.topRight() + delta)
        return rect

    def _resize_bottom_left(self, rect: QRectF, delta: QPointF) -> QRectF:
        """Resize from bottom-left corner."""
        rect.setBottomLeft(rect.bottomLeft() + delta)
        return rect

    def _resize_bottom_right(self, rect: QRectF, delta: QPointF) -> QRectF:
        """Resize from bottom-right corner."""
        rect.setBottomRight(rect.bottomRight() + delta)
        return rect

    def _resize_top(self, rect: QRectF, delta: QPointF) -> QRectF:
        """Resize from top edge."""
        rect.setTop(rect.top() + delta.y())
        return rect

    def _resize_bottom(self, rect: QRectF, delta: QPointF) -> QRectF:
        """Resize from bottom edge."""
        rect.setBottom(rect.bottom() + delta.y())
        return rect

    def _resize_left(self, rect: QRectF, delta: QPointF) -> QRectF:
        """Resize from left edge."""
        rect.setLeft(rect.left() + delta.x())
        return rect

    def _resize_right(self, rect: QRectF, delta: QPointF) -> QRectF:
        """Resize from right edge."""
        rect.setRight(rect.right() + delta.x())
        return rect

    def _preserve_aspect_ratio(self, original: QRectF, new_rect: QRectF) -> QRectF:
        """Preserve aspect ratio during resize."""
        # Prevent division by zero
        if original.height() == 0 or new_rect.height() == 0:
            return new_rect

        original_ratio = original.width() / original.height()

        # Calculate new dimensions maintaining aspect ratio
        new_width = new_rect.width()
        new_height = new_rect.height()

        if abs(new_width / new_height - original_ratio) > 0.01:
            # Adjust based on which dimension changed more
            width_change = abs(new_width - original.width())
            height_change = abs(new_height - original.height())

            if width_change > height_change:
                new_height = new_width / original_ratio
            else:
                new_width = new_height * original_ratio

            new_rect.setSize(QSizeF(new_width, new_height))

        return new_rect

    def _enforce_minimum_size(self, rect: QRectF) -> QRectF:
        """Enforce minimum size constraints."""
        min_size = 20.0

        if rect.width() < min_size:
            rect.setWidth(min_size)
        if rect.height() < min_size:
            rect.setHeight(min_size)

        return rect

    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        """Handle hover enter for visual feedback."""
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        """Handle hover leave to remove visual feedback."""
        self.update()
        super().hoverLeaveEvent(event)
