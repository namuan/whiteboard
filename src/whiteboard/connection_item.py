"""
Connection item implementation for the Digital Whiteboard application.

This module contains the ConnectionItem class which represents visual connections
between items on the whiteboard canvas with arrow rendering and dynamic updates.
"""

import math
from typing import Any, Protocol
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal, QObject
from PyQt6.QtGui import (
    QPainter,
    QPen,
    QBrush,
    QColor,
    QPainterPath,
    QPolygonF,
    QPainterPathStroker,
    QKeySequence,
)
from PyQt6.QtWidgets import (
    QGraphicsPathItem,
    QStyleOptionGraphicsItem,
    QWidget,
    QGraphicsSceneContextMenuEvent,
    QMenu,
)

from .utils.logging_config import get_logger


class ConnectionEndpoint(Protocol):
    """Protocol defining the interface for connection endpoints."""

    def get_connection_points(self) -> list[QPointF]:
        """Return points where connections can attach to this item."""
        ...

    def mapToScene(self, point: QPointF) -> QPointF:
        """Map a point from item coordinates to scene coordinates."""
        ...

    def boundingRect(self) -> QRectF:
        """Return the bounding rectangle of the item."""
        ...


class ConnectionSignals(QObject):
    """Signal emitter for ConnectionItem."""

    connection_deleted = pyqtSignal()
    style_changed = pyqtSignal(dict)


class ConnectionItem(QGraphicsPathItem):
    """
    Connection line/arrow between two items.

    A custom QGraphicsPathItem that draws lines or arrows connecting two items,
    with automatic path calculation, arrow head rendering, and dynamic updates
    when connected items are moved or resized.

    The ConnectionItem uses duck typing to accept any endpoint that implements:
    - get_connection_points() -> list[QPointF]
    - mapToScene(QPointF) -> QPointF
    - boundingRect() -> QRectF
    - position_changed signal (optional)
    - style_changed signal (optional)

    Requirements addressed:
    - 2.1: Visual connection lines between items
    - 2.2: Arrow head rendering and line styling options
    - 2.3: Dynamic connection updates when items move/resize
    - 2.4: Support for both NoteItem and ImageItem endpoints
    """

    def __init__(self, start_item: ConnectionEndpoint, end_item: ConnectionEndpoint):
        """
        Initialize a connection between two items.

        Args:
            start_item: Source item for the connection (must implement ConnectionEndpoint protocol)
            end_item: Target item for the connection (must implement ConnectionEndpoint protocol)
        """
        super().__init__()
        self.logger = get_logger(__name__)

        # Signal emitter
        self.signals = ConnectionSignals()

        # Connection properties
        self._connection_id = id(self)
        self._start_item = start_item
        self._end_item = end_item

        # Connection points (will be calculated)
        self._start_point = QPointF()
        self._end_point = QPointF()

        # Default styling
        self._style = {
            "line_color": QColor(100, 100, 100),  # Dark gray
            "line_width": 2,
            "arrow_size": 12,
            "arrow_angle": 30,  # degrees
            "line_style": Qt.PenStyle.SolidLine,
            "show_arrow": True,
            "curve_factor": 0.0,  # 0 = straight line, >0 = curved
        }

        # Setup connection
        self._setup_connection()

        # Connect to item position/style changes
        self._connect_item_signals()

        # Set helpful tooltip
        self.setToolTip("Right-click for connection options")

        # Get item identifiers for logging (duck-typed)
        start_id = self._get_item_id(start_item)
        end_id = self._get_item_id(end_item)

        self.logger.debug(
            f"Created ConnectionItem {self._connection_id} between items "
            f"{start_id} and {end_id}"
        )

    def _get_item_id(self, item: ConnectionEndpoint) -> str:
        """
        Get a string identifier for an item using duck typing.

        Args:
            item: The item to get an identifier for

        Returns:
            String identifier for the item
        """
        # Try different methods to get an ID, falling back to object id
        if hasattr(item, "get_note_id"):
            return f"note_{item.get_note_id()}"
        elif hasattr(item, "get_image_id"):
            return f"image_{item.get_image_id()}"
        else:
            return f"item_{id(item)}"

    def _setup_connection(self) -> None:
        """Configure the connection item properties."""
        # Set item flags
        self.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIsFocusable, True)

        # Set Z-value to render behind items
        self.setZValue(-1)

        # Calculate initial path
        self.update_path()

    def _connect_item_signals(self) -> None:
        """Connect to item position/style change signals for dynamic updates."""

        # Helper to connect either direct signals or nested 'signals'
        def _connect_signals_for(item: ConnectionEndpoint, label: str) -> None:
            # Direct signals on the item (NoteItem pattern)
            if hasattr(item, "position_changed"):
                try:
                    item.position_changed.connect(self.update_path)
                    self.logger.debug(f"Connected direct position_changed for {label}")
                except Exception as e:
                    self.logger.debug(
                        f"Failed connecting direct position_changed for {label}: {e}"
                    )
            if hasattr(item, "style_changed"):
                try:
                    item.style_changed.connect(self.update_path)
                    self.logger.debug(f"Connected direct style_changed for {label}")
                except Exception as e:
                    self.logger.debug(
                        f"Failed connecting direct style_changed for {label}: {e}"
                    )
            if hasattr(item, "content_changed"):
                try:
                    item.content_changed.connect(self._on_endpoint_content_changed)
                    self.logger.debug(f"Connected direct content_changed for {label}")
                except Exception as e:
                    self.logger.debug(
                        f"Failed connecting direct content_changed for {label}: {e}"
                    )

            # Signals exposed via a nested QObject, e.g., ImageItem.signals
            nested = getattr(item, "signals", None)
            if nested is not None:
                if hasattr(nested, "position_changed"):
                    try:
                        nested.position_changed.connect(self.update_path)
                        self.logger.debug(
                            f"Connected nested position_changed for {label}"
                        )
                    except Exception as e:
                        self.logger.debug(
                            f"Failed connecting nested position_changed for {label}: {e}"
                        )
                if hasattr(nested, "style_changed"):
                    try:
                        nested.style_changed.connect(self.update_path)
                        self.logger.debug(f"Connected nested style_changed for {label}")
                    except Exception as e:
                        self.logger.debug(
                            f"Failed connecting nested style_changed for {label}: {e}"
                        )
                if hasattr(nested, "content_changed"):
                    try:
                        nested.content_changed.connect(
                            self._on_endpoint_content_changed
                        )
                        self.logger.debug(
                            f"Connected nested content_changed for {label}"
                        )
                    except Exception as e:
                        self.logger.debug(
                            f"Failed connecting nested content_changed for {label}: {e}"
                        )

        _connect_signals_for(self._start_item, "start_item")
        _connect_signals_for(self._end_item, "end_item")

    def _on_endpoint_content_changed(self, _text_or_payload: Any) -> None:
        """Handle content changes on endpoints to recompute path when their bounds change."""
        try:
            self.logger.debug(
                f"Endpoint content changed; recomputing connection path for {self._connection_id}"
            )
            self.update_path()
        except Exception as e:
            self.logger.error(f"Error updating path on endpoint content change: {e}")

    def delete_connection(self) -> None:
        """Delete this connection from the scene."""
        # Disconnect from item signals
        self._disconnect_item_signals()

        # Remove from scene
        if self.scene():
            self.scene().removeItem(self)

        # Emit deletion signal
        self.signals.connection_deleted.emit()

        self.logger.debug(f"Deleted connection {self._connection_id}")

    def _disconnect_item_signals(self) -> None:
        """Disconnect from item position/style change signals (both direct and nested)."""

        def _disconnect_for(item: ConnectionEndpoint, label: str) -> None:
            try:
                if hasattr(item, "position_changed"):
                    item.position_changed.disconnect(self.update_path)
                    self.logger.debug(
                        f"Disconnected direct position_changed for {label}"
                    )
            except TypeError:
                pass
            except Exception as e:
                self.logger.debug(
                    f"Failed disconnecting direct position_changed for {label}: {e}"
                )

            try:
                if hasattr(item, "style_changed"):
                    item.style_changed.disconnect(self.update_path)
                    self.logger.debug(f"Disconnected direct style_changed for {label}")
            except TypeError:
                pass
            except Exception as e:
                self.logger.debug(
                    f"Failed disconnecting direct style_changed for {label}: {e}"
                )

            nested = getattr(item, "signals", None)
            if nested is not None:
                try:
                    if hasattr(nested, "position_changed"):
                        nested.position_changed.disconnect(self.update_path)
                        self.logger.debug(
                            f"Disconnected nested position_changed for {label}"
                        )
                except TypeError:
                    pass
                except Exception as e:
                    self.logger.debug(
                        f"Failed disconnecting nested position_changed for {label}: {e}"
                    )
                try:
                    if hasattr(nested, "style_changed"):
                        nested.style_changed.disconnect(self.update_path)
                        self.logger.debug(
                            f"Disconnected nested style_changed for {label}"
                        )
                except TypeError:
                    pass
                except Exception as e:
                    self.logger.debug(
                        f"Failed disconnecting nested style_changed for {label}: {e}"
                    )

        _disconnect_for(self._start_item, "start_item")
        _disconnect_for(self._end_item, "end_item")

    def update_path(self) -> None:
        """
        Recalculate and update the connection path when items move or resize.

        This method finds the optimal connection points on each item's boundary
        and creates a path between them with optional arrow head.
        """
        # Get optimal connection points
        start_point, end_point = self._calculate_connection_points()

        self._start_point = start_point
        self._end_point = end_point

        # Create the path
        path = self._create_connection_path(start_point, end_point)

        # Prepare geometry change to ensure correct invalidation region and avoid trails
        try:
            self.prepareGeometryChange()
        except Exception as e:
            self.logger.debug(f"prepareGeometryChange failed (non-fatal): {e}")

        # Set the path
        self.setPath(path)

        # Update pen style
        self._update_pen_style()

        # Debug bounding rect after update
        br = self.boundingRect()
        self.logger.debug(f"ConnectionItem boundingRect after update: {br}")

    def _calculate_connection_points(self) -> tuple[QPointF, QPointF]:
        """
        Calculate the optimal connection points on the item boundaries.

        Returns:
            Tuple of (start_point, end_point) in scene coordinates
        """
        # Get item centers in scene coordinates as fallback
        start_center = self._start_item.mapToScene(
            self._start_item.boundingRect().center()
        )
        end_center = self._end_item.mapToScene(self._end_item.boundingRect().center())

        # Get all possible connection points for each item
        start_points = self._start_item.get_connection_points()
        end_points = self._end_item.get_connection_points()

        # Find the closest pair of connection points
        min_distance = float("inf")
        best_start = start_points[0] if start_points else start_center
        best_end = end_points[0] if end_points else end_center

        for start_point in start_points:
            for end_point in end_points:
                # Calculate distance between points
                dx = end_point.x() - start_point.x()
                dy = end_point.y() - start_point.y()
                distance = math.sqrt(dx * dx + dy * dy)

                if distance < min_distance:
                    min_distance = distance
                    best_start = start_point
                    best_end = end_point

        return best_start, best_end

    def _create_connection_path(
        self, start_point: QPointF, end_point: QPointF
    ) -> QPainterPath:
        """
        Create the visual path for the connection.

        Args:
            start_point: Starting point of the connection
            end_point: Ending point of the connection

        Returns:
            QPainterPath representing the connection line and arrow
        """
        path = QPainterPath()

        # Create the main line
        if self._style["curve_factor"] > 0:
            # Create curved line
            path = self._create_curved_path(start_point, end_point)
        else:
            # Create straight line
            path.moveTo(start_point)
            path.lineTo(end_point)

        # Add arrow head if enabled
        if self._style["show_arrow"]:
            arrow_path = self._create_arrow_head(start_point, end_point)
            path.addPath(arrow_path)

        return path

    def _create_curved_path(
        self, start_point: QPointF, end_point: QPointF
    ) -> QPainterPath:
        """
        Create a curved path between two points.

        Args:
            start_point: Starting point
            end_point: Ending point

        Returns:
            QPainterPath with curved line
        """
        path = QPainterPath()
        path.moveTo(start_point)

        # Calculate control points for bezier curve
        dx = end_point.x() - start_point.x()
        dy = end_point.y() - start_point.y()

        # Create control points offset perpendicular to the line
        mid_x = start_point.x() + dx / 2
        mid_y = start_point.y() + dy / 2

        # Perpendicular offset
        perp_x = -dy * self._style["curve_factor"]
        perp_y = dx * self._style["curve_factor"]

        control1 = QPointF(mid_x + perp_x, mid_y + perp_y)

        # Create quadratic bezier curve
        path.quadTo(control1, end_point)

        return path

    def _create_arrow_head(
        self, start_point: QPointF, end_point: QPointF
    ) -> QPainterPath:
        """
        Create an arrow head at the end point.

        Args:
            start_point: Starting point (for direction calculation)
            end_point: Ending point where arrow should be drawn

        Returns:
            QPainterPath containing the arrow head
        """
        # Calculate arrow direction
        dx = end_point.x() - start_point.x()
        dy = end_point.y() - start_point.y()

        # Handle zero-length line
        if dx == 0 and dy == 0:
            return QPainterPath()

        # Calculate angle of the line
        angle = math.atan2(dy, dx)

        # Arrow parameters
        arrow_size = self._style["arrow_size"]
        arrow_angle_rad = math.radians(self._style["arrow_angle"])

        # Calculate arrow head points
        arrow_point1 = QPointF(
            end_point.x() - arrow_size * math.cos(angle - arrow_angle_rad),
            end_point.y() - arrow_size * math.sin(angle - arrow_angle_rad),
        )

        arrow_point2 = QPointF(
            end_point.x() - arrow_size * math.cos(angle + arrow_angle_rad),
            end_point.y() - arrow_size * math.sin(angle + arrow_angle_rad),
        )

        # Create arrow head path
        arrow_path = QPainterPath()
        arrow_polygon = QPolygonF([end_point, arrow_point1, arrow_point2])
        arrow_path.addPolygon(arrow_polygon)

        return arrow_path

    def _update_pen_style(self) -> None:
        """Update the pen style based on current styling options."""
        pen = QPen(
            self._style["line_color"],
            self._style["line_width"],
            self._style["line_style"],
        )

        # Enable antialiasing for smooth lines
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)

        self.setPen(pen)

    def paint(
        self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget
    ) -> None:
        """
        Custom painting for connection appearance.

        Args:
            painter: QPainter for drawing
            option: Style options
            widget: Widget being painted on
        """
        # Enable antialiasing for smooth lines
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Get current pen and modify if selected
        pen = self.pen()
        line_color = self._style["line_color"]

        if self.isSelected():
            # Highlight selected connections
            line_color = line_color.lighter(150)
            pen.setColor(line_color)
            pen.setWidth(self._style["line_width"] + 1)
        else:
            pen.setColor(line_color)

        painter.setPen(pen)

        # Draw the line part (without arrow head)
        line_path = self._create_line_path_only(self._start_point, self._end_point)
        painter.drawPath(line_path)

        # Draw filled arrow head if enabled
        if self._style["show_arrow"]:
            self._draw_filled_arrow_head(painter, line_color)

        # Draw selection indicators if selected
        if self.isSelected():
            self._draw_selection_indicators(painter)

    def _create_line_path_only(
        self, start_point: QPointF, end_point: QPointF
    ) -> QPainterPath:
        """
        Create the visual path for just the connection line (without arrow head).

        Args:
            start_point: Starting point of the connection
            end_point: Ending point of the connection

        Returns:
            QPainterPath representing just the connection line
        """
        path = QPainterPath()

        # Create the main line
        if self._style["curve_factor"] > 0:
            # Create curved line
            path = self._create_curved_path(start_point, end_point)
        else:
            # Create straight line
            path.moveTo(start_point)
            path.lineTo(end_point)

        return path

    def _draw_filled_arrow_head(self, painter: QPainter, color: QColor) -> None:
        """
        Draw a filled arrow head at the end point.

        Args:
            painter: QPainter for drawing
            color: Color to use for the arrow head
        """
        # Calculate arrow direction
        dx = self._end_point.x() - self._start_point.x()
        dy = self._end_point.y() - self._start_point.y()

        # Handle zero-length line
        if dx == 0 and dy == 0:
            return

        # Calculate angle of the line
        angle = math.atan2(dy, dx)

        # Arrow parameters
        arrow_size = self._style["arrow_size"]
        arrow_angle_rad = math.radians(self._style["arrow_angle"])

        # Calculate arrow head points
        arrow_point1 = QPointF(
            self._end_point.x() - arrow_size * math.cos(angle - arrow_angle_rad),
            self._end_point.y() - arrow_size * math.sin(angle - arrow_angle_rad),
        )

        arrow_point2 = QPointF(
            self._end_point.x() - arrow_size * math.cos(angle + arrow_angle_rad),
            self._end_point.y() - arrow_size * math.sin(angle + arrow_angle_rad),
        )

        # Create arrow head polygon
        arrow_polygon = QPolygonF([self._end_point, arrow_point1, arrow_point2])

        # Set up brush and pen for filled arrow
        arrow_brush = QBrush(color)
        arrow_pen = QPen(color, 1)  # Thin pen for clean edges

        painter.setBrush(arrow_brush)
        painter.setPen(arrow_pen)

        # Draw filled arrow head
        painter.drawPolygon(arrow_polygon)

    def _draw_selection_indicators(self, painter: QPainter) -> None:
        """
        Draw selection indicators on the connection.

        Args:
            painter: QPainter for drawing
        """
        # Draw small circles at start and end points
        indicator_size = 6
        indicator_pen = QPen(QColor(0, 120, 215), 2)  # Blue selection color
        indicator_brush = QBrush(QColor(255, 255, 255))  # White fill

        painter.setPen(indicator_pen)
        painter.setBrush(indicator_brush)

        # Draw indicators
        painter.drawEllipse(self._start_point, indicator_size / 2, indicator_size / 2)
        painter.drawEllipse(self._end_point, indicator_size / 2, indicator_size / 2)

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent) -> None:
        """
        Handle context menu (right-click) events.

        Args:
            event: Context menu event
        """
        menu = QMenu()

        # Delete connection
        delete_action = menu.addAction("🗑️ Delete Connection")
        delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        # Route to centralized deletion on canvas
        delete_action.triggered.connect(lambda: self._request_centralized_delete())

        menu.addSeparator()

        # Style options
        style_menu = menu.addMenu("🎨 Style")

        # Line color options
        color_menu = style_menu.addMenu("Line Color")

        gray_action = color_menu.addAction("⚫ Gray")
        gray_action.triggered.connect(
            lambda: self.set_style({"line_color": QColor(100, 100, 100)})
        )

        blue_action = color_menu.addAction("🔵 Blue")
        blue_action.triggered.connect(
            lambda: self.set_style({"line_color": QColor(0, 120, 215)})
        )

        red_action = color_menu.addAction("🔴 Red")
        red_action.triggered.connect(
            lambda: self.set_style({"line_color": QColor(220, 50, 50)})
        )

        green_action = color_menu.addAction("🟢 Green")
        green_action.triggered.connect(
            lambda: self.set_style({"line_color": QColor(50, 150, 50)})
        )

        # Line width options
        width_menu = style_menu.addMenu("Line Width")

        thin_action = width_menu.addAction("Thin (1px)")
        thin_action.triggered.connect(lambda: self.set_style({"line_width": 1}))

        normal_action = width_menu.addAction("Normal (2px)")
        normal_action.triggered.connect(lambda: self.set_style({"line_width": 2}))

        thick_action = width_menu.addAction("Thick (3px)")
        thick_action.triggered.connect(lambda: self.set_style({"line_width": 3}))

        # Arrow options
        arrow_menu = style_menu.addMenu("Arrow")

        show_arrow_action = arrow_menu.addAction(
            "✅ Show Arrow" if self._style["show_arrow"] else "☑️ Show Arrow"
        )
        show_arrow_action.triggered.connect(
            lambda: self.set_style({"show_arrow": not self._style["show_arrow"]})
        )

        # Show menu at cursor position
        menu.exec(event.screenPos())

        # Accept the event to prevent propagation
        event.accept()

    def set_style(self, style_dict: dict) -> None:
        """
        Apply custom styling to the connection.

        Args:
            style_dict: Dictionary containing style properties
        """
        # Update style properties
        for key, value in style_dict.items():
            if key in self._style:
                self._style[key] = value

        # Update visual appearance
        self._update_pen_style()
        self.update_path()  # Recreate path with new styling
        self.update()

        # Emit style changed signal
        self.signals.style_changed.emit(self._style.copy())

        self.logger.debug(
            f"Applied style to connection {self._connection_id}: {style_dict}"
        )

    def get_style(self) -> dict:
        """
        Get current connection styling.

        Returns:
            Dictionary containing current style properties
        """
        return self._style.copy()

    def get_start_item(self) -> ConnectionEndpoint:
        """
        Get the start item of this connection.

        Returns:
            Start item
        """
        return self._start_item

    def get_end_item(self) -> ConnectionEndpoint:
        """
        Get the end item of this connection.

        Returns:
            End item
        """
        return self._end_item

    # Legacy methods for backward compatibility
    def get_start_note(self) -> Any:
        """
        Get the start note of this connection (legacy method).

        Returns:
            Start item (may not be a note)
        """
        return self._start_item

    def get_end_note(self) -> Any:
        """
        Get the end note of this connection (legacy method).

        Returns:
            End item (may not be a note)
        """
        return self._end_item

    def get_connection_id(self) -> int:
        """
        Get the unique identifier for this connection.

        Returns:
            Unique connection ID
        """
        return self._connection_id

    def get_connection_data(self) -> dict:
        """
        Get complete connection data for serialization.

        Returns:
            Dictionary containing all connection data
        """
        # Get item IDs using duck typing
        start_id = self._get_item_id(self._start_item)
        end_id = self._get_item_id(self._end_item)

        # Legacy numeric note IDs for compatibility with existing tests
        start_note_id = (
            self._start_item.get_note_id()
            if hasattr(self._start_item, "get_note_id")
            else None
        )
        end_note_id = (
            self._end_item.get_note_id()
            if hasattr(self._end_item, "get_note_id")
            else None
        )

        return {
            "id": self._connection_id,
            "start_item_id": start_id,
            "end_item_id": end_id,
            "start_note_id": start_note_id,  # Legacy compatibility expects int for notes
            "end_note_id": end_note_id,  # Legacy compatibility expects int for notes
            "style": self._style.copy(),
            "start_point": (self._start_point.x(), self._start_point.y()),
            "end_point": (self._end_point.x(), self._end_point.y()),
        }

    def boundingRect(self) -> QRectF:
        """
        Return the bounding rectangle of the connection.

        Returns:
            QRectF representing the connection's bounds
        """
        # Get path bounding rect
        path_rect = self.path().boundingRect()

        # Add some margin for line width and selection indicators
        margin = max(self._style["line_width"], 10)
        path_rect.adjust(-margin, -margin, margin, margin)

        return path_rect

    def contains(self, point: QPointF) -> bool:
        """
        Check if a point is contained within the connection (for selection).

        Args:
            point: Point to test in item coordinates

        Returns:
            True if point is on the connection line
        """
        # Create a stroked path for hit testing
        stroker = QPainterPathStroker()
        stroker.setWidth(
            max(self._style["line_width"] + 4, 8)
        )  # Make it easier to select
        stroker.setCapStyle(Qt.PenCapStyle.RoundCap)

        stroked_path = stroker.createStroke(self.path())
        return stroked_path.contains(point)

    def is_connected_to_note(self, note: Any) -> bool:
        """
        Check if this connection is connected to the given note.

        Args:
            note: The note to check

        Returns:
            True if the note is connected to this connection
        """
        return note == self._start_item or note == self._end_item

    def get_other_note(self, note: Any) -> Any | None:
        """
        Get the other note in this connection.

        Args:
            note: One of the connected notes

        Returns:
            The other connected note, or None if the provided note is not connected
        """
        if note == self._start_item:
            return self._end_item
        elif note == self._end_item:
            return self._start_item
        return None

    def _disconnect_note_signals(self) -> None:
        """Compatibility shim: disconnect note signals (delegates to item signals)."""
        # Some tests call this legacy method; delegate to unified handler
        try:
            self.logger.debug(
                "Compatibility: _disconnect_note_signals called; delegating to _disconnect_item_signals"
            )
            self._disconnect_item_signals()
        except Exception as e:
            # Silently ignore to match legacy behavior where signals may already be disconnected
            self.logger.debug(
                f"_disconnect_note_signals encountered non-fatal issue: {e}"
            )

    def _request_centralized_delete(self) -> None:
        """Ask the canvas to delete this connection via centralized confirmation dialog."""
        try:
            if self.scene() and self.scene().views():
                view = self.scene().views()[0]
                canvas = getattr(view, "_canvas", None)
                if canvas and hasattr(canvas, "delete_items_with_confirmation"):
                    canvas.delete_items_with_confirmation([self])
                    return
        except Exception as e:
            self.logger.error(f"Failed to route connection deletion to canvas: {e}")
        # Fallback: direct delete without extra dialog
        self.delete_connection()
