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
    QKeySequence,
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
    QGraphicsScene,
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

    # Class variable for style clipboard
    _copied_style = None

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
        # Track geometry updates to adjust painting behavior and clearing
        self._is_geometry_updating = False

        # Get default styling from style manager
        from .style_manager import get_style_manager

        style_manager = get_style_manager()
        self._style = style_manager.get_default_style()

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
        """Update the note geometry based on content with min/max width constraints."""
        # Snapshot previous bounds for diagnostics and clearing logic
        old_item_rect = self.boundingRect()
        self.logger.debug(
            f"_update_geometry: old_item_size=({old_item_rect.width():.2f}x{old_item_rect.height():.2f})"
        )

        # Flag start of geometry update (affects painting)
        self._is_geometry_updating = True

        try:
            # Notify scene that geometry is about to change
            self.prepareGeometryChange()

            # Determine sizing constraints from style
            padding = self._style["padding"]
            min_width = self._style["min_width"]
            # Provide a sensible default if not present in persisted styles
            max_width = self._style.get("max_width", 320)

            # Temporarily disable wrapping to measure intrinsic width
            self.setTextWidth(-1)
            natural_text_rect = super().boundingRect()
            natural_width = natural_text_rect.width()

            # Compute desired content area width (without padding)
            min_content_width = max(min_width - 2 * padding, 1)
            max_content_width = max(max_width - 2 * padding, min_content_width)
            desired_content_width = natural_width
            if desired_content_width < min_content_width:
                desired_content_width = min_content_width
            if desired_content_width > max_content_width:
                desired_content_width = max_content_width

            # Apply clamped width for wrapping and layout
            self.setTextWidth(desired_content_width)

            # Logging for diagnostics
            new_item_rect = self.boundingRect()
            self.logger.debug(
                f"_update_geometry: natural_width={natural_width:.2f}, "
                f"min_content_width={min_content_width}, max_content_width={max_content_width}, "
                f"applied_content_width={desired_content_width}, padding={padding}, "
                f"min_width={min_width}, max_width={max_width}, "
                f"new_item_size=({new_item_rect.width():.2f}x{new_item_rect.height():.2f})"
            )

            # If attached to a scene, invalidate the appropriate regions to avoid trailing artifacts
            if self.scene() is not None:
                try:
                    # Determine if the note is shrinking in either dimension
                    is_shrinking = (
                        new_item_rect.width() < old_item_rect.width()
                        or new_item_rect.height() < old_item_rect.height()
                    )

                    old_scene_rect = self.mapRectToScene(old_item_rect)
                    new_scene_rect = self.sceneBoundingRect()

                    self.logger.debug(
                        f"_update_geometry: is_shrinking={is_shrinking}, "
                        f"old_item_rect={old_item_rect}, new_item_rect={new_item_rect}, "
                        f"old_scene_rect={old_scene_rect}, new_scene_rect={new_scene_rect}"
                    )

                    if is_shrinking:
                        # When shrinking, clear the old larger area in scene coords
                        clear_scene_rect = old_scene_rect.adjusted(-20, -20, 20, 20)

                        # Invalidate background and item layers to ensure full redraw
                        self.scene().invalidate(
                            clear_scene_rect, QGraphicsScene.SceneLayer.BackgroundLayer
                        )
                        self.scene().invalidate(
                            clear_scene_rect, QGraphicsScene.SceneLayer.ItemLayer
                        )

                        # Force immediate scene update of the cleared area
                        self.scene().update(clear_scene_rect)

                        # Also force view updates/repaints for the affected area
                        for view in self.scene().views():
                            view_rect = view.mapFromScene(
                                clear_scene_rect
                            ).boundingRect()
                            view.update(view_rect)
                            view.repaint(view_rect)

                        self.logger.debug(
                            f"_update_geometry: shrink invalidation applied on {clear_scene_rect} across {len(self.scene().views())} views"
                        )
                    else:
                        # For growth, invalidate the union area to refresh newly exposed region
                        combined_scene_rect = old_scene_rect.united(new_scene_rect)
                        self.scene().invalidate(combined_scene_rect)
                        self.scene().update(combined_scene_rect)

                        for view in self.scene().views():
                            view_rect = view.mapFromScene(
                                combined_scene_rect
                            ).boundingRect()
                            view.update(view_rect)

                        self.logger.debug(
                            f"_update_geometry: grow invalidation applied on {combined_scene_rect} across {len(self.scene().views())} views"
                        )

                    # Always trigger item update
                    self.update()
                except Exception as e:
                    self.logger.exception(
                        f"_update_geometry: scene invalidation failed: {e}"
                    )
        finally:
            # Ensure flag reset even if exceptions occur
            self._is_geometry_updating = False

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

        # Clear the background slightly larger than rect during geometry updates to avoid trails
        if getattr(self, "_is_geometry_updating", False):
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(rect.adjusted(-5, -5, 5, 5), QColor(0, 0, 0, 0))
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_SourceOver
            )

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

        # Add comprehensive style dialog
        style_action = menu.addAction("🎨 Style...")
        style_action.triggered.connect(self._open_style_dialog)

        menu.addSeparator()

        # Add template options
        template_menu = menu.addMenu("📋 Templates")
        self._populate_template_menu(template_menu)

        menu.addSeparator()

        # Add style copying options
        copy_menu = menu.addMenu("📄 Copy Style")
        copy_style_action = copy_menu.addAction("📋 Copy Style from This Note")
        copy_style_action.triggered.connect(self._copy_style_to_clipboard)

        paste_style_action = copy_menu.addAction("📄 Paste Style to This Note")
        paste_style_action.triggered.connect(self._paste_style_from_clipboard)

        menu.addSeparator()

        # Add quick style options
        style_menu = menu.addMenu("🎨 Quick Colors")

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

        # Add copy and delete operations
        operations_menu = menu.addMenu("🔧 Operations")

        # Copy note content
        copy_content_action = operations_menu.addAction("📋 Copy Note Content")
        copy_content_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_content_action.triggered.connect(self._copy_note_content)

        # Delete note
        delete_action = operations_menu.addAction("🗑️ Delete Note")
        delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        # Route to canvas centralized delete flow
        delete_action.triggered.connect(lambda: self._request_centralized_delete())

        menu.addSeparator()

        # Add helpful info
        info_action = menu.addAction("ℹ️ How to move notes")
        info_action.triggered.connect(self._show_move_help)

        # Show menu at cursor position
        menu.exec(event.screenPos())

        # Accept the event to prevent propagation
        event.accept()

    def _show_move_help(self) -> None:
        """Show help information about moving notes."""
        # Emit a longer help message
        help_text = "💡 To move notes: Hover over a note and drag it to a new position. The cursor will change to indicate you can move the note."
        self.hover_started.emit(help_text)

    def _open_style_dialog(self) -> None:
        """Open the comprehensive style dialog."""
        # Import here to avoid circular imports
        from .note_style_dialog import NoteStyleDialog

        # Get the main window as parent (walk up the widget hierarchy)
        parent = None
        if self.scene() and self.scene().views():
            view = self.scene().views()[0]
            parent = view.window()

        # Open style dialog
        new_style = NoteStyleDialog.get_note_style(self._style, parent)
        if new_style:
            self.set_style(new_style)
            self.logger.debug(f"Applied new style from dialog to note {self._note_id}")

    def _populate_template_menu(self, template_menu) -> None:
        """Populate the template menu with available templates."""
        from .style_manager import get_style_manager

        style_manager = get_style_manager()
        template_names = style_manager.get_template_names()

        if not template_names:
            no_templates_action = template_menu.addAction("No templates available")
            no_templates_action.setEnabled(False)
            return

        # Add template actions
        for template_name in template_names:
            template_style = style_manager.get_template_style(template_name)
            if template_style:
                # Create action with template name and style summary
                summary = style_manager.get_style_summary(template_style)
                action_text = f"{template_name}"
                action = template_menu.addAction(action_text)
                action.setToolTip(f"Apply {template_name} template\n{summary}")
                action.triggered.connect(
                    lambda checked, name=template_name: self._apply_template(name)
                )

        template_menu.addSeparator()

        # Add option to save current style as template
        save_template_action = template_menu.addAction("💾 Save as Template...")
        save_template_action.triggered.connect(self._save_as_template)

    def _apply_template(self, template_name: str) -> None:
        """Apply a template to this note."""
        from .style_manager import get_style_manager

        style_manager = get_style_manager()
        if style_manager.apply_template_to_note(self, template_name):
            self.logger.debug(
                f"Applied template '{template_name}' to note {self._note_id}"
            )
        else:
            self.logger.warning(
                f"Failed to apply template '{template_name}' to note {self._note_id}"
            )

    def _save_as_template(self) -> None:
        """Save current note style as a new template."""
        from PyQt6.QtWidgets import QInputDialog
        from .style_manager import get_style_manager

        # Get template name from user
        parent = None
        if self.scene() and self.scene().views():
            view = self.scene().views()[0]
            parent = view.window()

        template_name, ok = QInputDialog.getText(
            parent, "Save as Template", "Enter template name:", text="My Template"
        )

        if ok and template_name.strip():
            style_manager = get_style_manager()
            if style_manager.create_template_from_note(self, template_name.strip()):
                self.hover_started.emit(
                    f"✅ Template '{template_name}' saved successfully"
                )
                self.logger.debug(
                    f"Created template '{template_name}' from note {self._note_id}"
                )
            else:
                self.hover_started.emit(f"❌ Template '{template_name}' already exists")
                self.logger.warning(f"Template '{template_name}' already exists")

    def _copy_style_to_clipboard(self) -> None:
        """Copy this note's style to a global clipboard."""
        from .style_manager import get_style_manager

        style_manager = get_style_manager()

        # Store style in a class variable for simple clipboard functionality
        NoteItem._copied_style = style_manager.copy_style_from_note(self)

        self.hover_started.emit("📋 Style copied! Right-click another note to paste.")
        self.logger.debug(f"Copied style from note {self._note_id}")

    def _paste_style_from_clipboard(self) -> None:
        """Paste style from clipboard to this note."""
        if hasattr(NoteItem, "_copied_style") and NoteItem._copied_style:
            from .style_manager import get_style_manager

            style_manager = get_style_manager()
            style_manager.apply_style_to_note(self, NoteItem._copied_style)

            self.hover_started.emit("📄 Style pasted successfully!")
            self.logger.debug(f"Pasted style to note {self._note_id}")
        else:
            self.hover_started.emit("❌ No style copied yet. Copy a style first.")
            self.logger.debug("No style in clipboard to paste")

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
        try:
            if change == QGraphicsTextItem.GraphicsItemChange.ItemPositionHasChanged:
                self._handle_position_has_changed(QPointF(value))
            elif change == QGraphicsTextItem.GraphicsItemChange.ItemPositionChange:
                self._handle_position_change()
            elif change == QGraphicsTextItem.GraphicsItemChange.ItemSceneHasChanged:
                self._handle_scene_has_changed()
            elif change == QGraphicsTextItem.GraphicsItemChange.ItemSelectedHasChanged:
                self._handle_selection_changed()
        except Exception as e:
            self.logger.exception(f"itemChange: error handling change {change}: {e}")

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

    # NOTE: duplicate set_style/get_style removed to resolve F811 redefinition errors.

    # NOTE: duplicate implementations removed to resolve F811 redefinition errors.
    def _copy_note_content(self) -> None:
        """Copy the note's text content to the system clipboard."""
        from PyQt6.QtWidgets import QApplication

        clipboard = QApplication.clipboard()
        clipboard.setText(self.get_text())

        self.hover_started.emit("📋 Note content copied to clipboard!")
        self.logger.debug(f"Copied content of note {self._note_id} to clipboard")

    def _request_centralized_delete(self) -> None:
        """Ask the canvas to delete this note via centralized confirmation dialog."""
        try:
            if self.scene() and self.scene().views():
                view = self.scene().views()[0]
                canvas = getattr(view, "_canvas", None)
                if canvas and hasattr(canvas, "delete_items_with_confirmation"):
                    canvas.delete_items_with_confirmation([self])
                    return
        except Exception as e:
            self.logger.error(f"Failed to route note deletion to canvas: {e}")
        # Fallback to legacy behavior
        self._delete_note()

    def _delete_note(self) -> None:
        """Delete this note from the scene without prompting (centralized confirmation is handled by Canvas)."""
        # Delete connections first
        if hasattr(self.scene(), "delete_connections_for_note"):
            self.scene().delete_connections_for_note(self)

        # Remove from scene
        if self.scene():
            self.scene().removeItem(self)

        self.logger.debug(f"Deleted note {self._note_id} (no per-item prompt)")

    def _handle_position_has_changed(self, new_position: QPointF) -> None:
        """Handle logic after the position has changed.

        This emits the position_changed signal (used by connections/canvas) and
        triggers a lightweight scene update to avoid visual trails.
        """
        try:
            # Prefer the actual current position to avoid QVariant conversion quirks
            current_pos = self.pos()
            # Fall back to provided value if needed
            if current_pos is None and new_position is not None:
                current_pos = new_position

            # Emit position changed for dependents (e.g., connections)
            self.position_changed.emit(current_pos)

            # Nudge the scene to refresh around the item to prevent artifacts
            if self.scene() is not None:
                try:
                    self.scene().update(self.sceneBoundingRect().adjusted(-2, -2, 2, 2))
                except Exception as e:
                    self.logger.debug(
                        f"_handle_position_has_changed: scene update failed: {e}"
                    )

            # Ensure infinite canvas behavior by expanding scene if needed
            try:
                self._handle_scene_expansion()
            except Exception as e:
                self.logger.debug(
                    f"_handle_position_has_changed: expansion failed: {e}"
                )

            self.logger.debug(
                f"Note {self._note_id} position changed to ({current_pos.x():.2f}, {current_pos.y():.2f})"
            )
        except Exception as e:
            self.logger.exception(f"_handle_position_has_changed: failed: {e}")

    def _handle_position_change(self) -> None:
        """Handle logic while the position is changing (pre-commit)."""
        try:
            # Currently we only log; clamping or constraints can be added here later
            tentative_pos = self.pos()
            self.logger.debug(
                f"Note {self._note_id} position changing (tentative) to ({tentative_pos.x():.2f}, {tentative_pos.y():.2f})"
            )
        except Exception as e:
            self.logger.exception(f"_handle_position_change: failed: {e}")

    def _handle_scene_has_changed(self) -> None:
        """Handle when the note's scene association changes."""
        try:
            scene_info = "attached" if self.scene() is not None else "detached"
            self.logger.debug(f"Note {self._note_id} scene has changed: {scene_info}")

            # When attached to a scene, ensure geometry and visuals are fresh
            if self.scene() is not None:
                try:
                    self._update_geometry()
                    self.update()
                    # Minor refresh around the item
                    self.scene().update(self.sceneBoundingRect().adjusted(-4, -4, 4, 4))
                except Exception as e:
                    self.logger.debug(f"_handle_scene_has_changed: refresh failed: {e}")
        except Exception as e:
            self.logger.exception(f"_handle_scene_has_changed: failed: {e}")

    def _handle_selection_changed(self) -> None:
        """Handle selection state changes for the note."""
        try:
            selected = self.isSelected()

            # Update cursor to give feedback
            if selected:
                # Slightly emphasize selection via immediate repaint
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
            else:
                # Open hand when hoverable but not selected
                self.setCursor(Qt.CursorShape.OpenHandCursor)

            # Trigger repaint to reflect selection highlight in paint()
            self.update()

            self.logger.debug(
                f"Note {self._note_id} selection changed to {'selected' if selected else 'deselected'}"
            )
        except Exception as e:
            self.logger.exception(f"_handle_selection_changed: failed: {e}")

    def _handle_scene_expansion(self) -> None:
        """Ensure the scene expands when the note moves near its edges.

        Uses the scene's built-in expansion routine when available, with a
        backwards-compatible manual fallback mirroring ImageItem behavior.
        """
        if not self.scene():
            return

        try:
            # Prefer central scene expansion utility if present
            if hasattr(self.scene(), "_check_and_expand_scene"):
                self.scene()._check_and_expand_scene(self.sceneBoundingRect())
                return

            # Fallback manual expansion logic
            self._manual_scene_expansion()
        except Exception as e:
            self.logger.debug(f"_handle_scene_expansion: failed: {e}")

    def _manual_scene_expansion(self) -> None:
        """Manual scene expansion logic (compatibility fallback)."""
        try:
            scene_rect = self.scene().sceneRect()
            item_rect = self.sceneBoundingRect()

            # Threshold and expansion values aligned with scene defaults
            threshold = 1000
            expansion = 5000

            new_scene_rect = scene_rect
            expanded = False

            if item_rect.left() < scene_rect.left() + threshold:
                new_scene_rect.setLeft(scene_rect.left() - expansion)
                expanded = True
            if item_rect.right() > scene_rect.right() - threshold:
                new_scene_rect.setRight(scene_rect.right() + expansion)
                expanded = True
            if item_rect.top() < scene_rect.top() + threshold:
                new_scene_rect.setTop(scene_rect.top() - expansion)
                expanded = True
            if item_rect.bottom() > scene_rect.bottom() - threshold:
                new_scene_rect.setBottom(scene_rect.bottom() + expansion)
                expanded = True

            if expanded:
                self.scene().setSceneRect(new_scene_rect)
                self.logger.debug(
                    f"Scene expanded to {new_scene_rect} due to NoteItem movement"
                )
        except Exception as e:
            self.logger.debug(f"_manual_scene_expansion: failed: {e}")

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

    def _copy_note_content(self) -> None:
        """Copy the note's text content to the system clipboard."""
        from PyQt6.QtWidgets import QApplication

        clipboard = QApplication.clipboard()
        clipboard.setText(self.get_text())

        self.hover_started.emit("📋 Note content copied to clipboard!")
        self.logger.debug(f"Copied content of note {self._note_id} to clipboard")

    def _request_centralized_delete(self) -> None:
        """Ask the canvas to delete this note via centralized confirmation dialog."""
        try:
            if self.scene() and self.scene().views():
                view = self.scene().views()[0]
                canvas = getattr(view, "_canvas", None)
                if canvas and hasattr(canvas, "delete_items_with_confirmation"):
                    canvas.delete_items_with_confirmation([self])
                    return
        except Exception as e:
            self.logger.error(f"Failed to route note deletion to canvas: {e}")
        # Fallback to legacy behavior
        self._delete_note()

    def _delete_note(self) -> None:
        """Delete this note from the scene without prompting (centralized confirmation is handled by Canvas)."""
        # Delete connections first
        if hasattr(self.scene(), "delete_connections_for_note"):
            self.scene().delete_connections_for_note(self)

        # Remove from scene
        if self.scene():
            self.scene().removeItem(self)

        self.logger.debug(f"Deleted note {self._note_id} (no per-item prompt)")
