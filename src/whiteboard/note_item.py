"""
Note item implementation for the Digital Whiteboard application.

This module contains the NoteItem class which represents individual editable notes
on the whiteboard canvas with styling and interaction capabilities.
"""

from typing import Any
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import (
    QPainter,
    QPen,
    QBrush,
    QColor,
    QFont,
    QTextCursor,
    QTextCharFormat,
)
from PyQt6.QtWidgets import (
    QGraphicsTextItem,
    QStyleOptionGraphicsItem,
    QWidget,
    QGraphicsSceneMouseEvent,
    QGraphicsSceneHoverEvent,
    QStyle,
    QMenu,
    QGraphicsSceneContextMenuEvent,
)

from .utils.logging_config import get_logger


class NoteItem(QGraphicsTextItem):
    """
    Individual note item with text editing and styling capabilities.

    A custom QGraphicsTextItem that provides editable text functionality,
    focus handling for entering/exiting edit mode, and basic note styling
    including background, border, and text formatting.

    Requirements addressed:
    - 1.1: Create notes with editable text functionality
    - 1.2: Focus handling for entering/exiting edit mode
    - 1.3: Basic note styling (background, border, text formatting)
    - 4.1: Note appearance customization
    - 4.2: Text and background color customization
    """

    # Signals
    position_changed = pyqtSignal(QPointF)
    content_changed = pyqtSignal(str)
    style_changed = pyqtSignal(dict)
    editing_started = pyqtSignal()
    editing_finished = pyqtSignal()
    hover_started = pyqtSignal(str)  # Emits hint text
    hover_ended = pyqtSignal()
    editing_started = pyqtSignal()
    editing_finished = pyqtSignal()

    def __init__(self, text: str = "", position: QPointF = QPointF(0, 0)):
        """
        Initialize a new note item.

        Args:
            text: Initial text content for the note
            position: Initial position of the note on the canvas
        """
        super().__init__()
        self.logger = get_logger(__name__)

        # Note properties
        self._note_id = id(self)  # Unique identifier
        self._is_editing = False
        self._original_text = text

        # Default styling
        self._style = {
            "background_color": QColor(255, 255, 200),  # Light yellow
            "border_color": QColor(200, 200, 150),  # Darker yellow
            "text_color": QColor(0, 0, 0),  # Black text
            "border_width": 2,
            "corner_radius": 8,
            "padding": 10,
            "font_family": "Arial",
            "font_size": 12,
            "font_bold": False,
            "font_italic": False,
            "min_width": 100,
            "min_height": 60,
        }

        # Setup note
        self._setup_note(text, position)

        # Set helpful tooltip
        self.setToolTip(
            "💡 Drag to move • Double-click to edit • Right-click for colors & options"
        )

        self.logger.debug(
            f"Created NoteItem with ID {self._note_id} at position {position}"
        )

    def _setup_note(self, text: str, position: QPointF) -> None:
        """
        Configure the note item properties and appearance.

        Args:
            text: Initial text content
            position: Initial position
        """
        # Set position
        self.setPos(position)

        # Configure text item properties - start with no text interaction
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIsFocusable, True)
        self.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

        # Enable hover events for visual feedback
        self.setAcceptHoverEvents(True)

        # Set initial text and apply styling
        self.setPlainText(text if text else "Double-click to edit")
        self._apply_text_styling()
        self._update_geometry()

        # Connect text change signal
        self.document().contentsChanged.connect(self._on_text_changed)

    def _apply_text_styling(self) -> None:
        """Apply current text styling to the note content."""
        # Create font from style settings
        font = QFont(self._style["font_family"], self._style["font_size"])
        font.setBold(self._style["font_bold"])
        font.setItalic(self._style["font_italic"])

        # Apply font to the text item
        self.setFont(font)

        # Apply text color
        self.setDefaultTextColor(self._style["text_color"])

        # Update text format for existing content
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)

        char_format = QTextCharFormat()
        char_format.setFont(font)
        char_format.setForeground(self._style["text_color"])

        cursor.mergeCharFormat(char_format)
        cursor.clearSelection()
        self.setTextCursor(cursor)

    def _update_geometry(self) -> None:
        """Update the note geometry based on content and minimum size."""
        # Get text bounds
        text_rect = self.boundingRect()

        # Ensure minimum size
        min_width = self._style["min_width"]
        padding = self._style["padding"]

        # Calculate required size including padding
        required_width = max(text_rect.width() + 2 * padding, min_width)

        # Set text width if needed to wrap text
        if text_rect.width() + 2 * padding > min_width:
            self.setTextWidth(required_width - 2 * padding)

    def boundingRect(self) -> QRectF:
        """
        Return the bounding rectangle of the note including background.

        Returns:
            QRectF representing the note's bounds
        """
        # Get text bounding rect
        text_rect = super().boundingRect()

        # Add padding and ensure minimum size
        padding = self._style["padding"]
        min_width = self._style["min_width"]
        min_height = self._style["min_height"]

        width = max(text_rect.width() + 2 * padding, min_width)
        height = max(text_rect.height() + 2 * padding, min_height)

        # Center the rect around the text
        x = text_rect.x() - padding
        y = text_rect.y() - padding

        return QRectF(x, y, width, height)

    def paint(
        self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget
    ) -> None:
        """
        Custom painting for note appearance including background and border.

        Args:
            painter: QPainter for drawing
            option: Style options
            widget: Widget being painted on
        """
        # Get bounding rectangle
        rect = self.boundingRect()

        # Setup painter
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Draw background
        background_color = self._style["background_color"]
        if self._is_editing:
            # Slightly brighter background when editing
            background_color = background_color.lighter(110)

        brush = QBrush(background_color)
        painter.setBrush(brush)

        # Draw border
        border_color = self._style["border_color"]
        border_width = self._style["border_width"]

        # Highlight border when selected or hovered
        if self.isSelected():
            border_color = border_color.darker(150)
            border_width += 2
            # Add a subtle glow effect for selected notes
            background_color = background_color.lighter(105)
        elif option.state & QStyle.StateFlag.State_MouseOver:
            border_color = border_color.darker(130)
            border_width += 1
            # Slightly lighter background on hover to indicate interactivity
            background_color = background_color.lighter(108)

        # Update brush with potentially modified background color
        brush = QBrush(background_color)
        painter.setBrush(brush)

        pen = QPen(border_color, border_width)
        painter.setPen(pen)

        # Draw rounded rectangle
        corner_radius = self._style["corner_radius"]
        painter.drawRoundedRect(rect, corner_radius, corner_radius)

        # Draw move grip indicator in bottom-right corner if hovered or selected
        if (option.state & QStyle.StateFlag.State_MouseOver) or self.isSelected():
            self._draw_move_grip(painter, rect)

        # Draw text content
        painter.setPen(QPen(self._style["text_color"]))
        super().paint(painter, option, widget)

    def _draw_move_grip(self, painter: QPainter, rect: QRectF) -> None:
        """
        Draw a small grip indicator to show the note can be moved.

        Args:
            painter: QPainter for drawing
            rect: Note bounding rectangle
        """
        # Draw small grip dots in bottom-right corner
        grip_size = 2
        grip_spacing = 4
        grip_margin = 6

        # Calculate grip position
        grip_x = rect.right() - grip_margin - grip_spacing
        grip_y = rect.bottom() - grip_margin - grip_spacing

        # Set grip color (slightly darker than border)
        grip_color = self._style["border_color"].darker(140)
        painter.setPen(QPen(grip_color, 1))
        painter.setBrush(QBrush(grip_color))

        # Draw 3x3 grid of small dots
        for i in range(3):
            for j in range(3):
                if (i + j) % 2 == 0:  # Checkerboard pattern
                    dot_x = grip_x - i * grip_spacing
                    dot_y = grip_y - j * grip_spacing
                    painter.drawEllipse(
                        QPointF(dot_x, dot_y), grip_size / 2, grip_size / 2
                    )

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """
        Handle mouse press events for note selection and drag initiation.

        Args:
            event: Mouse press event
        """
        if event.button() == Qt.MouseButton.LeftButton:
            # Handle selection and potential drag start
            if not self.isSelected():
                self.setSelected(True)

            # Change cursor to indicate dragging
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

            # Store original position for drag detection
            self._drag_start_position = event.pos()

        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """
        Handle double-click events to enter edit mode.

        Args:
            event: Mouse double-click event
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self.enter_edit_mode()

        super().mouseDoubleClickEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """
        Handle mouse release events to reset cursor after dragging.

        Args:
            event: Mouse release event
        """
        if event.button() == Qt.MouseButton.LeftButton:
            # Reset cursor to open hand when hovering
            self.setCursor(Qt.CursorShape.OpenHandCursor)

        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent) -> None:
        """
        Handle context menu (right-click) events.

        Args:
            event: Context menu event
        """
        menu = QMenu()

        # Add helpful actions
        edit_action = menu.addAction("✏️ Edit Note")
        edit_action.triggered.connect(self.enter_edit_mode)

        menu.addSeparator()

        # Add style options
        style_menu = menu.addMenu("🎨 Style")

        # Color options
        yellow_action = style_menu.addAction("💛 Yellow")
        yellow_action.triggered.connect(
            lambda: self.set_style({"background_color": QColor(255, 255, 200)})
        )

        blue_action = style_menu.addAction("💙 Blue")
        blue_action.triggered.connect(
            lambda: self.set_style({"background_color": QColor(200, 220, 255)})
        )

        green_action = style_menu.addAction("💚 Green")
        green_action.triggered.connect(
            lambda: self.set_style({"background_color": QColor(200, 255, 200)})
        )

        pink_action = style_menu.addAction("💗 Pink")
        pink_action.triggered.connect(
            lambda: self.set_style({"background_color": QColor(255, 200, 220)})
        )

        menu.addSeparator()

        # Add helpful info
        info_action = menu.addAction("ℹ️ How to move notes")
        info_action.triggered.connect(self._show_move_help)

        # Show menu at cursor position
        menu.exec(event.screenPos())

    def _show_move_help(self) -> None:
        """Show help information about moving notes."""
        # Emit a longer help message
        help_text = "💡 To move notes: Hover over a note and drag it to a new position. The cursor will change to indicate you can move the note."
        self.hover_started.emit(help_text)

    def focusInEvent(self, event) -> None:
        """
        Handle focus in events.

        Args:
            event: Focus event
        """
        # Don't automatically enter edit mode on focus
        # Edit mode should only be triggered by double-click
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:
        """
        Handle focus out events to exit edit mode and save content.

        Args:
            event: Focus event
        """
        # Only exit edit mode if we're actually in edit mode
        if self._is_editing:
            self.exit_edit_mode()
        super().focusOutEvent(event)

    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        """
        Handle hover enter events for visual feedback.

        Args:
            event: Hover event
        """
        # Change cursor to indicate the note can be moved
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        # Emit hover signal with helpful hint
        if self._is_editing:
            hint_text = (
                "💡 Click outside to finish editing, or drag to move while editing"
            )
        else:
            hint_text = "💡 Drag to move • Double-click to edit • Right-click for colors & options"

        self.hover_started.emit(hint_text)

        # Trigger repaint for hover effect
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        """
        Handle hover leave events to remove visual feedback.

        Args:
            event: Hover event
        """
        # Reset cursor
        self.setCursor(Qt.CursorShape.ArrowCursor)

        # Emit hover end signal
        self.hover_ended.emit()

        # Trigger repaint to remove hover effect
        self.update()
        super().hoverLeaveEvent(event)

    def itemChange(self, change, value):
        """
        Handle item changes including position updates.

        Args:
            change: Type of change
            value: New value

        Returns:
            Processed value
        """
        if change == QGraphicsTextItem.GraphicsItemChange.ItemPositionHasChanged:
            # Emit position changed signal
            new_position = QPointF(value)
            self.position_changed.emit(new_position)

            # Trigger scene expansion check if item is in a scene
            if self.scene():
                # Check if scene needs expansion for new position
                item_rect = self.boundingRect().translated(new_position)
                if hasattr(self.scene(), "_check_and_expand_scene"):
                    self.scene()._check_and_expand_scene(item_rect)

            self.logger.debug(f"Note {self._note_id} moved to {new_position}")

        return super().itemChange(change, value)

    def enter_edit_mode(self) -> None:
        """Enter text editing mode."""
        if not self._is_editing:
            self._is_editing = True
            self._original_text = self.toPlainText()

            # Enable text interaction for editing
            self.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)

            # Clear placeholder text if present
            if self.toPlainText() == "Double-click to edit":
                self.setPlainText("")

            # Set cursor to end of text
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)

            # Update appearance
            self.update()

            # Emit signal
            self.editing_started.emit()

            self.logger.debug(f"Note {self._note_id} entered edit mode")

    def exit_edit_mode(self) -> None:
        """Exit text editing mode and save content."""
        if self._is_editing:
            self._is_editing = False

            # Disable text interaction to allow dragging
            self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)

            # Handle empty text
            current_text = self.toPlainText().strip()
            if not current_text:
                self.setPlainText("Double-click to edit")

            # Update geometry after text change
            self._update_geometry()

            # Update appearance
            self.update()

            # Emit signals if content changed
            if current_text != self._original_text:
                self.content_changed.emit(current_text)

            self.editing_finished.emit()

            self.logger.debug(f"Note {self._note_id} exited edit mode")

    def _on_text_changed(self) -> None:
        """Handle text content changes during editing."""
        if self._is_editing:
            # Update geometry to accommodate new text
            self._update_geometry()

            # Emit content changed signal
            current_text = self.toPlainText()
            self.content_changed.emit(current_text)

    def set_style(self, style_dict: dict[str, Any]) -> None:
        """
        Apply custom styling to the note.

        Args:
            style_dict: Dictionary containing style properties
        """
        # Update style properties
        for key, value in style_dict.items():
            if key in self._style:
                self._style[key] = value

        # Apply text styling
        self._apply_text_styling()

        # Update geometry and appearance
        self._update_geometry()
        self.update()

        # Emit style changed signal
        self.style_changed.emit(self._style.copy())

        self.logger.debug(f"Applied style to note {self._note_id}: {style_dict}")

    def get_style(self) -> dict[str, Any]:
        """
        Get current note styling.

        Returns:
            Dictionary containing current style properties
        """
        return self._style.copy()

    def set_text(self, text: str) -> None:
        """
        Set the note text content.

        Args:
            text: New text content
        """
        self.setPlainText(text)
        self._update_geometry()
        self.update()

        # Emit content changed signal
        self.content_changed.emit(text)

    def get_text(self) -> str:
        """
        Get the current note text content.

        Returns:
            Current text content
        """
        text = self.toPlainText()
        return text if text != "Double-click to edit" else ""

    def get_connection_points(self) -> list[QPointF]:
        """
        Return points where connections can attach to this note.

        Returns:
            List of QPointF representing connection attachment points
        """
        rect = self.boundingRect()

        # Return points at the center of each edge
        points = [
            QPointF(rect.center().x(), rect.top()),  # Top center
            QPointF(rect.right(), rect.center().y()),  # Right center
            QPointF(rect.center().x(), rect.bottom()),  # Bottom center
            QPointF(rect.left(), rect.center().y()),  # Left center
        ]

        # Convert to scene coordinates
        scene_points = [self.mapToScene(point) for point in points]

        return scene_points

    def get_note_id(self) -> int:
        """
        Get the unique identifier for this note.

        Returns:
            Unique note ID
        """
        return self._note_id

    def is_editing(self) -> bool:
        """
        Check if the note is currently in edit mode.

        Returns:
            True if note is being edited, False otherwise
        """
        return self._is_editing

    def get_note_data(self) -> dict[str, Any]:
        """
        Get complete note data for serialization.

        Returns:
            Dictionary containing all note data
        """
        position = self.pos()

        return {
            "id": self._note_id,
            "text": self.get_text(),
            "position": (position.x(), position.y()),
            "style": self._style.copy(),
            "bounds": {
                "width": self.boundingRect().width(),
                "height": self.boundingRect().height(),
            },
        }

    def set_note_data(self, data: dict[str, Any]) -> None:
        """
        Restore note from serialized data.

        Args:
            data: Dictionary containing note data
        """
        # Set position
        if "position" in data:
            pos_x, pos_y = data["position"]
            self.setPos(QPointF(pos_x, pos_y))

        # Set text
        if "text" in data:
            self.set_text(data["text"])

        # Set style
        if "style" in data:
            self.set_style(data["style"])

        # Update note ID if provided
        if "id" in data:
            self._note_id = data["id"]

        self.logger.debug(f"Restored note {self._note_id} from data")
