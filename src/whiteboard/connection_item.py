"""
Connection item implementation for the Digital Whiteboard application.

This module contains the ConnectionItem class which represents visual connections
between notes on the whiteboard canvas with arrow rendering and dynamic updates.
"""

import math
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
from .note_item import NoteItem


class ConnectionSignals(QObject):
    """Signal emitter for ConnectionItem."""

    connection_deleted = pyqtSignal()
    style_changed = pyqtSignal(dict)


class ConnectionItem(QGraphicsPathItem):
    """
    Connection line/arrow between two notes.

    A custom QGraphicsPathItem that draws lines or arrows connecting two notes,
    with automatic path calculation, arrow head rendering, and dynamic updates
    when connected notes are moved.

    Requirements addressed:
    - 2.1: Visual connection lines between notes
    - 2.2: Arrow head rendering and line styling options
    - 2.3: Dynamic connection updates when notes move
    """

    def __init__(self, start_note: NoteItem, end_note: NoteItem):
        """
        Initialize a connection between two notes.

        Args:
            start_note: Source note for the connection
            end_note: Target note for the connection
        """
        super().__init__()
        self.logger = get_logger(__name__)

        # Signal emitter
        self.signals = ConnectionSignals()

        # Connection properties
        self._connection_id = id(self)
        self._start_note = start_note
        self._end_note = end_note

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

        # Connect to note position changes
        self._connect_note_signals()

        # Set helpful tooltip
        self.setToolTip("Right-click for connection options")

        self.logger.debug(
            f"Created ConnectionItem {self._connection_id} between notes "
            f"{self._start_note.get_note_id()} and {self._end_note.get_note_id()}"
        )

    def _setup_connection(self) -> None:
        """Configure the connection item properties."""
        # Set item flags
        self.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIsFocusable, True)

        # Set Z-value to render behind notes
        self.setZValue(-1)

        # Calculate initial path
        self.update_path()

    def _connect_note_signals(self) -> None:
        """Connect to note position change signals for dynamic updates."""
        self._start_note.position_changed.connect(self.update_path)
        self._end_note.position_changed.connect(self.update_path)

        # Also connect to geometry changes that might affect connection points
        if hasattr(self._start_note, "style_changed"):
            self._start_note.style_changed.connect(self.update_path)
        if hasattr(self._end_note, "style_changed"):
            self._end_note.style_changed.connect(self.update_path)

    def update_path(self) -> None:
        """
        Recalculate and update the connection path when notes move.

        This method finds the optimal connection points on each note's boundary
        and creates a path between them with optional arrow head.
        """
        # Get optimal connection points
        start_point, end_point = self._calculate_connection_points()

        self._start_point = start_point
        self._end_point = end_point

        # Create the path
        path = self._create_connection_path(start_point, end_point)

        # Set the path
        self.setPath(path)

        # Update pen style
        self._update_pen_style()

        self.logger.debug(f"Updated connection path from {start_point} to {end_point}")

    def _calculate_connection_points(self) -> tuple[QPointF, QPointF]:
        """
        Calculate the optimal connection points on the note boundaries.

        Returns:
            Tuple of (start_point, end_point) in scene coordinates
        """
        # Get note centers in scene coordinates
        start_center = self._start_note.mapToScene(
            self._start_note.boundingRect().center()
        )
        end_center = self._end_note.mapToScene(self._end_note.boundingRect().center())

        # Get all possible connection points for each note
        start_points = self._start_note.get_connection_points()
        end_points = self._end_note.get_connection_points()

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
        delete_action.triggered.connect(self.delete_connection)

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

    def delete_connection(self) -> None:
        """Delete this connection from the scene."""
        # Disconnect from note signals
        self._disconnect_note_signals()

        # Remove from scene
        if self.scene():
            self.scene().removeItem(self)

        # Emit deletion signal
        self.signals.connection_deleted.emit()

        self.logger.debug(f"Deleted connection {self._connection_id}")

    def _disconnect_note_signals(self) -> None:
        """Disconnect from note position change signals."""
        try:
            self._start_note.position_changed.disconnect(self.update_path)
            self._end_note.position_changed.disconnect(self.update_path)

            if hasattr(self._start_note, "style_changed"):
                self._start_note.style_changed.disconnect(self.update_path)
            if hasattr(self._end_note, "style_changed"):
                self._end_note.style_changed.disconnect(self.update_path)
        except TypeError:
            # Signals may already be disconnected
            pass

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

    def get_start_note(self) -> NoteItem:
        """
        Get the start note of this connection.

        Returns:
            Start note item
        """
        return self._start_note

    def get_end_note(self) -> NoteItem:
        """
        Get the end note of this connection.

        Returns:
            End note item
        """
        return self._end_note

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
        return {
            "id": self._connection_id,
            "start_note_id": self._start_note.get_note_id(),
            "end_note_id": self._end_note.get_note_id(),
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

    def is_connected_to_note(self, note: NoteItem) -> bool:
        """
        Check if this connection is connected to the specified note.

        Args:
            note: Note to check connection to

        Returns:
            True if connected to the note, False otherwise
        """
        return note == self._start_note or note == self._end_note

    def get_other_note(self, note: NoteItem) -> NoteItem | None:
        """
        Get the other note in this connection.

        Args:
            note: One of the connected notes

        Returns:
            The other connected note, or None if the provided note is not connected
        """
        if note == self._start_note:
            return self._end_note
        elif note == self._end_note:
            return self._start_note
        else:
            return None
