"""
Image item implementation for the Digital Whiteboard application.

This module contains the ImageItem class which represents individual image items
on the whiteboard canvas with drag-and-drop support and interaction capabilities.
"""

from typing import Any
from PyQt6.QtCore import Qt, QPointF, pyqtSignal, QRectF, QObject
from PyQt6.QtGui import (
    QPainter,
    QPen,
    QBrush,
    QColor,
    QPixmap,
    QTransform,
    QKeySequence,
)
from PyQt6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsSceneHoverEvent,
    QGraphicsSceneMouseEvent,
    QMenu,
    QGraphicsSceneContextMenuEvent,
    QStyle,
    QGraphicsScene,
    QStyleOptionGraphicsItem,
    QWidget,
)

from .utils.logging_config import get_logger
from .image_resize_handle import ImageResizeHandle, HandleType


class ImageItemSignals(QObject):
    """Signal emitter for ImageItem."""

    # Signals
    position_changed = pyqtSignal(QPointF)
    style_changed = pyqtSignal(dict)
    hover_started = pyqtSignal(str)  # Emits hint text
    hover_ended = pyqtSignal()


class ImageItem(QGraphicsPixmapItem):
    """
    Individual image item with drag-and-drop support and interaction capabilities.

    A custom QGraphicsPixmapItem that provides image display functionality,
    focus handling for selection, and basic image styling including borders
    and scaling options.

    Requirements addressed:
    - Image display with proper scaling
    - Drag-and-drop support for image files
    - Connection points for linking with other items
    - Position and style change signals
    """

    def __init__(self, image_path: str = "", position: QPointF = QPointF(0, 0)):
        """
        Initialize a new image item.

        Args:
            image_path: Path to the image file
            position: Initial position of the image on the canvas
        """
        super().__init__()
        self.logger = get_logger(__name__)

        # Signal emitter
        self.signals = ImageItemSignals()

        # Image properties
        self._image_id = id(self)  # Unique identifier
        self._image_path = image_path
        self._original_pixmap = None
        self._scale_factor = 1.0
        self._rotation = 0
        self._drag_start_position = QPointF()

        # Resize handles
        self._resize_handles: list[ImageResizeHandle] = []
        self._handles_visible = False
        self._is_resizing = False

        # Default styling
        self._style = {
            "border_width": 2,
            "border_color": QColor(100, 100, 100),
            "background_color": QColor(255, 255, 255, 0),  # Transparent
            "max_width": 400,
            "max_height": 300,
            "maintain_aspect_ratio": True,
            "opacity": 1.0,
        }

        # Setup image
        self._setup_image(image_path, position)

        # Create resize handles
        self._create_resize_handles()

        # Set helpful tooltip
        self.setToolTip(
            "🖼️ Drag to move • Right-click for options • Supports connections"
        )

        self.logger.debug(
            f"Created ImageItem with ID {self._image_id} at position {position}"
        )

    def _setup_image(self, image_path: str, position: QPointF) -> None:
        """
        Configure the image item properties and appearance.

        Args:
            image_path: Path to the image file
            position: Initial position
        """
        # Set position
        self.setPos(position)

        # Configure item properties
        self.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsFocusable, True)
        self.setFlag(
            QGraphicsPixmapItem.GraphicsItemFlag.ItemSendsGeometryChanges, True
        )

        # Enable hover events for visual feedback
        self.setAcceptHoverEvents(True)

        # Load and set image
        if image_path:
            self._load_image(image_path)
        else:
            # Create placeholder pixmap
            placeholder = QPixmap(200, 150)
            placeholder.fill(QColor(240, 240, 240))
            self.setPixmap(placeholder)

        # Apply initial styling
        self._apply_styling()

        self.logger.info(f"Setup ImageItem {self._image_id} with path: {image_path}")

    def _load_image(self, image_path: str) -> None:
        """
        Load image from file path and apply scaling.

        Args:
            image_path: Path to the image file
        """
        try:
            # Load the original pixmap
            self._original_pixmap = QPixmap(image_path)

            if self._original_pixmap.isNull():
                self.logger.error(f"Failed to load image from path: {image_path}")
                # Create error placeholder
                placeholder = QPixmap(200, 150)
                placeholder.fill(QColor(255, 200, 200))
                self._original_pixmap = placeholder
                # Retain the original path so it can be serialized/embedded later
                self._image_path = image_path
                self.logger.warning(
                    "Using placeholder pixmap due to load failure; retaining original path for serialization"
                )
            else:
                self._image_path = image_path
                self.logger.info(f"Successfully loaded image: {image_path}")
                self.logger.debug(
                    f"Original image size: {self._original_pixmap.size()}"
                )

            # Scale the image according to style settings
            self._scale_image()

        except Exception as e:
            self.logger.error(f"Exception loading image {image_path}: {e}")
            # Create error placeholder
            placeholder = QPixmap(200, 150)
            placeholder.fill(QColor(255, 200, 200))
            self._original_pixmap = placeholder
            # Retain the original path so it can be serialized/embedded later
            self._image_path = image_path
            self.logger.warning(
                "Exception during image load; using placeholder and retaining original path for serialization"
            )
            self._scale_image()

    def _scale_image(self) -> None:
        """Scale the image according to current style settings."""
        if not self._original_pixmap:
            return

        max_width = self._style["max_width"]
        max_height = self._style["max_height"]
        maintain_aspect = self._style["maintain_aspect_ratio"]

        # Scale the pixmap
        if maintain_aspect:
            scaled_pixmap = self._original_pixmap.scaled(
                max_width,
                max_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            scaled_pixmap = self._original_pixmap.scaled(
                max_width,
                max_height,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

        self.setPixmap(scaled_pixmap)
        self.logger.debug(f"Scaled image to size: {scaled_pixmap.size()}")

    def _apply_styling(self) -> None:
        """Apply current styling to the image item."""
        # Set opacity
        self.setOpacity(self._style["opacity"])

        # Note: Border and background are handled in paint method
        self.update()

        self.logger.debug(f"Applied style to ImageItem {self._image_id}")

    # New: apply rotation/transform based on current rotation value
    def _apply_transform(self) -> None:
        """Apply current rotation transform to the image item."""
        try:
            # Use built-in rotation to keep it simple and consistent
            self.setRotation(float(self._rotation))
            self.logger.debug(
                f"Applied rotation {self._rotation} to ImageItem {self._image_id}"
            )
        except Exception as e:
            self.logger.warning(
                f"Failed to apply rotation for ImageItem {self._image_id}: {e}"
            )

    # New: update style from dict
    def update_style(self, style_dict: dict[str, Any]) -> None:
        """Update image style and re-apply sizing/styling.

        Args:
            style_dict: Dictionary of style properties to update
        """
        try:
            # Update known style keys only
            for key, value in style_dict.items():
                if key in self._style:
                    self._style[key] = value

            # Recompute scale and styling when dimensions/aspect change
            self._scale_image()
            self._apply_styling()

            # Refresh resize handles positions if visible
            if self._handles_visible:
                self._update_handle_positions()

            # Emit style changed signal
            self.signals.style_changed.emit(self._style.copy())
            self.logger.debug(
                f"Updated style for ImageItem {self._image_id}: {style_dict}"
            )
        except Exception as e:
            self.logger.error(
                f"Failed to update style for ImageItem {self._image_id}: {e}"
            )

    # New: provide path access for session serialization
    def get_image_path(self) -> str:
        """Return the original image file path if available."""
        return self._image_path

    # New: provide image data summary for session serialization
    def get_image_data(self) -> dict[str, Any]:
        """Return serializable image-related data for sessions."""
        try:
            data: dict[str, Any] = {
                "id": self._image_id,
                "rotation": self._rotation,
                "style": self._style.copy(),
                "bounds": {
                    "width": self.boundingRect().width(),
                    "height": self.boundingRect().height(),
                },
            }
            return data
        except Exception as e:
            self.logger.warning(
                f"Failed to build image data for ImageItem {self._image_id}: {e}"
            )
            return {
                "id": self._image_id,
                "rotation": self._rotation,
                "style": self._style.copy(),
            }

    def _create_resize_handles(self) -> None:
        """Create resize handles for the image."""
        # Create handles for all corners and edges
        handle_types = [
            HandleType.TOP_LEFT,
            HandleType.TOP_RIGHT,
            HandleType.BOTTOM_LEFT,
            HandleType.BOTTOM_RIGHT,
            HandleType.TOP,
            HandleType.BOTTOM,
            HandleType.LEFT,
            HandleType.RIGHT,
        ]

        for handle_type in handle_types:
            handle = ImageResizeHandle(handle_type, self)
            handle.set_callbacks(
                resize_started=self._on_resize_started,
                resize_updated=self._on_resize_updated,
                resize_finished=self._on_resize_finished,
            )
            handle.setVisible(False)  # Initially hidden
            # Ensure handles are above the image item in Z-order
            handle.setZValue(self.zValue() + 1)
            self._resize_handles.append(handle)

        self.logger.debug(f"Created {len(self._resize_handles)} resize handles")

    def _update_handle_positions(self) -> None:
        """Update positions of all resize handles."""
        if not self._resize_handles:
            return

        rect = self.boundingRect()
        for handle in self._resize_handles:
            handle.update_position(rect)

    def _show_resize_handles(self) -> None:
        """Show resize handles when image is selected."""
        if self._handles_visible:
            return

        self._handles_visible = True
        self._update_handle_positions()

        for handle in self._resize_handles:
            handle.setVisible(True)

        self.logger.debug("Showed resize handles")

    def _hide_resize_handles(self) -> None:
        """Hide resize handles when image is deselected."""
        if not self._handles_visible:
            return

        self._handles_visible = False

        for handle in self._resize_handles:
            handle.setVisible(False)

        self.logger.debug("Hid resize handles")

    def _on_resize_started(self) -> None:
        """Handle resize operation start."""
        self._is_resizing = True
        self.logger.debug(f"Started image resize for ImageItem {self._image_id}")

        # Emit position changed signal to ensure connections update at resize start
        self.signals.position_changed.emit(self.pos())

    def _on_resize_updated(self, new_rect: QRectF) -> None:
        """Handle resize operation update."""
        # Store the old bounding rect for invalidation
        old_rect = self.boundingRect()

        # Notify Qt that geometry is about to change
        self.prepareGeometryChange()

        # Check if the image is shrinking (important for clearing trailing lines)
        is_shrinking = (
            new_rect.width() < old_rect.width() or new_rect.height() < old_rect.height()
        )

        # Update image size based on new rectangle
        if self._original_pixmap:
            # Calculate new scale factor
            original_size = self._original_pixmap.size()
            scale_x = new_rect.width() / original_size.width()
            scale_y = new_rect.height() / original_size.height()

            # Use uniform scaling if maintaining aspect ratio
            if self._style["maintain_aspect_ratio"]:
                scale = min(scale_x, scale_y)
                self._scale_factor = scale
            else:
                # For non-uniform scaling, we need to transform the pixmap
                self._scale_factor = scale_x  # Use x scale as primary

            # Apply the scaling
            scaled_pixmap = self._original_pixmap.scaled(
                int(original_size.width() * self._scale_factor),
                int(original_size.height() * self._scale_factor),
                Qt.AspectRatioMode.KeepAspectRatio
                if self._style["maintain_aspect_ratio"]
                else Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            self.setPixmap(scaled_pixmap)

            # Update handle positions
            self._update_handle_positions()

            # Emit style changed signal during resize to update connections
            self.signals.style_changed.emit(self._style.copy())

            # Special handling for shrinking images to prevent trailing lines
            if self.scene():
                # Map old and new rects into scene coordinates for proper invalidation
                old_scene_rect = self.mapRectToScene(old_rect)
                new_scene_rect = self.sceneBoundingRect()

                # Add detailed logging
                self.logger.debug(
                    f"Resize update: is_shrinking={is_shrinking}, old_item_rect={old_rect}, new_item_rect={self.boundingRect()}, old_scene_rect={old_scene_rect}, new_scene_rect={new_scene_rect}"
                )

                if is_shrinking:
                    # When shrinking, clear the old larger area using scene coordinates
                    clear_scene_rect = old_scene_rect.adjusted(-20, -20, 20, 20)

                    # Force background and item layer redraw to clear old content
                    self.scene().invalidate(
                        clear_scene_rect, QGraphicsScene.SceneLayer.BackgroundLayer
                    )
                    self.scene().invalidate(
                        clear_scene_rect, QGraphicsScene.SceneLayer.ItemLayer
                    )

                    # Force immediate scene update of the cleared area
                    self.scene().update(clear_scene_rect)

                    # Also force view updates to ensure visual clearing
                    views = self.scene().views()
                    for view in views:
                        view_rect = view.mapFromScene(clear_scene_rect).boundingRect()
                        view.update(view_rect)
                        # Force immediate repaint for shrinking
                        view.repaint(view_rect)

                    self.logger.debug(
                        f"Shrink invalidation applied on scene rect {clear_scene_rect} across {len(views)} views"
                    )
                else:
                    # For growing images, invalidate the union of old and new scene rects
                    combined_scene_rect = old_scene_rect.united(new_scene_rect)
                    self.scene().invalidate(combined_scene_rect)
                    self.scene().update(combined_scene_rect)

                    # Also force view updates for growing
                    views = self.scene().views()
                    for view in views:
                        view_rect = view.mapFromScene(
                            combined_scene_rect
                        ).boundingRect()
                        view.update(view_rect)

                    self.logger.debug(
                        f"Grow invalidation applied on combined scene rect {combined_scene_rect} across {len(views)} views"
                    )

                # Always trigger item update
                self.update()

    def _on_resize_finished(self, final_rect: QRectF) -> None:
        """Handle resize operation completion."""
        self._is_resizing = False

        # Emit style change signal to notify of size change
        self.signals.style_changed.emit(self._style.copy())

        # Force final scene update to ensure clean state
        if self.scene():
            self.scene().invalidate(self.boundingRect())
            self.update()

        self.logger.debug(f"Finished image resize to {final_rect}")

    def paint(
        self,
        painter: QPainter,
        option: "QStyleOptionGraphicsItem",
        widget: "QWidget" = None,
    ) -> None:
        """
        Paint the image item with selection highlighting.

        Args:
            painter: QPainter for drawing
            option: Style options
            widget: Widget being painted on
        """
        # Get bounding rectangle
        rect = self.boundingRect()

        # Setup painter
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Clear the background to prevent trailing artifacts
        if self._is_resizing:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(rect.adjusted(-5, -5, 5, 5), QColor(0, 0, 0, 0))
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_SourceOver
            )

        # Draw selection highlight if selected
        if self.isSelected():
            # Draw selection border
            selection_color = QColor(0, 120, 215)  # Blue selection color
            selection_pen = QPen(selection_color, 3)
            painter.setPen(selection_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect.adjusted(-2, -2, 2, 2))

            # Add subtle glow effect
            glow_color = QColor(selection_color)
            glow_color.setAlpha(50)
            painter.setBrush(QBrush(glow_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(rect.adjusted(-1, -1, 1, 1))

        # Draw hover highlight
        elif option.state & QStyle.StateFlag.State_MouseOver:
            hover_color = QColor(100, 100, 100, 100)
            painter.setBrush(QBrush(hover_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(rect)

        # Draw the actual image
        super().paint(painter, option, widget)

        self.logger.debug(
            f"ImageItem {self._image_id} painted with selection={self.isSelected()}"
        )

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """
        Handle mouse press events for image selection and drag initiation.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if the event was already handled by a child item (like resize handles)
            if event.isAccepted():
                return

            # Handle selection and potential drag start
            self.setSelected(True)
            self._show_resize_handles()

            # Store drag start position for movement
            self._drag_start_position = event.pos()

            # Bring to front when selected
            self._bring_to_front()

            self.logger.debug(f"ImageItem {self._image_id} selected and ready for drag")

        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """
        Handle double-click events to show image properties or open in external viewer.

        Args:
            event: Mouse double-click event
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self.logger.debug(f"ImageItem {self._image_id} double-clicked")
            # TODO: Implement image properties dialog or external viewer
            self.signals.hover_started.emit(
                "💡 Double-click functionality coming soon!"
            )

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
            self.logger.debug(f"ImageItem {self._image_id} mouse released")

        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent) -> None:
        """
        Handle context menu (right-click) events.
        """
        menu = QMenu()

        # Image properties action
        properties_action = menu.addAction("🖼️ Image Properties")
        properties_action.triggered.connect(self._show_image_properties)

        menu.addSeparator()

        # Resize options
        resize_menu = menu.addMenu("📏 Resize")

        # Aspect ratio toggle
        aspect_ratio_action = resize_menu.addAction(
            "🔒 Lock Aspect Ratio"
            if not self._style["maintain_aspect_ratio"]
            else "🔓 Unlock Aspect Ratio"
        )
        aspect_ratio_action.triggered.connect(self._toggle_aspect_ratio)

        # Reset to original size
        reset_size_action = resize_menu.addAction("↩️ Reset to Original Size")
        reset_size_action.triggered.connect(self._reset_to_original_size)

        menu.addSeparator()

        # Rotation actions
        rotate_menu = menu.addMenu("🔄 Rotate")
        rotate_left_action = rotate_menu.addAction("↺ Rotate Left 90°")
        rotate_left_action.triggered.connect(lambda: self._rotate_image(-90))

        rotate_right_action = rotate_menu.addAction("↻ Rotate Right 90°")
        rotate_right_action.triggered.connect(lambda: self._rotate_image(90))

        rotate_180_action = rotate_menu.addAction("↕ Rotate 180°")
        rotate_180_action.triggered.connect(lambda: self._rotate_image(180))

        # Custom rotation action
        custom_rotate_action = rotate_menu.addAction("🎯 Custom Rotation...")
        custom_rotate_action.triggered.connect(self._show_custom_rotation_dialog)

        menu.addSeparator()

        # Opacity controls
        opacity_menu = menu.addMenu("🌫️ Opacity")

        # Opacity presets
        opacity_25_action = opacity_menu.addAction("25%")
        opacity_25_action.triggered.connect(lambda: self._set_opacity(0.25))

        opacity_50_action = opacity_menu.addAction("50%")
        opacity_50_action.triggered.connect(lambda: self._set_opacity(0.5))

        opacity_75_action = opacity_menu.addAction("75%")
        opacity_75_action.triggered.connect(lambda: self._set_opacity(0.75))

        opacity_100_action = opacity_menu.addAction("100%")
        opacity_100_action.triggered.connect(lambda: self._set_opacity(1.0))

        opacity_menu.addSeparator()

        # Custom opacity
        custom_opacity_action = opacity_menu.addAction("🎯 Custom Opacity...")
        custom_opacity_action.triggered.connect(self._show_custom_opacity_dialog)

        menu.addSeparator()

        # Z-order actions
        z_order_menu = menu.addMenu("📚 Layer Order")
        bring_front_action = z_order_menu.addAction("⬆️ Bring to Front")
        bring_front_action.triggered.connect(self._bring_to_front)

        send_back_action = z_order_menu.addAction("⬇️ Send to Back")
        send_back_action.triggered.connect(self._send_to_back)

        menu.addSeparator()

        # Delete action
        delete_action = menu.addAction("🗑️ Delete Image")
        delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        delete_action.triggered.connect(self._delete_image)

        # Show menu at cursor position
        menu.exec(event.screenPos())

        self.logger.debug(f"Context menu shown for ImageItem {self._image_id}")

    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        """
        Handle hover enter events for visual feedback.

        Args:
            event: Hover event
        """
        # Change cursor to indicate the image can be moved
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        # Emit hover signal with helpful hint
        hint_text = (
            "💡 Drag to move • Double-click for properties • Right-click for options"
        )
        self.signals.hover_started.emit(hint_text)

        # Trigger repaint for hover effect
        self.update()
        self.logger.debug(f"ImageItem {self._image_id} hover started")
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
        self.signals.hover_ended.emit()

        # Trigger repaint to remove hover effect
        self.update()
        self.logger.debug(f"ImageItem {self._image_id} hover ended")
        super().hoverLeaveEvent(event)

    def _handle_scene_expansion(self):
        """Handle scene expansion when item moves."""
        if not self.scene():
            return

        if hasattr(self.scene(), "_check_and_expand_scene"):
            self.scene()._check_and_expand_scene(self.sceneBoundingRect())
        else:
            self._manual_scene_expansion()

    def _manual_scene_expansion(self):
        """Fallback manual scene expansion for compatibility."""
        scene_rect = self.scene().sceneRect()
        item_rect = self.sceneBoundingRect()

        # Expansion threshold
        threshold = 1000
        expansion = 5000

        new_scene_rect = scene_rect
        expanded = False

        # Check boundaries and expand if needed
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
                f"Scene expanded to {new_scene_rect} due to ImageItem movement"
            )

    def _handle_position_change(self, new_position):
        """Handle position change logic."""
        # Emit position change signal
        self.signals.position_changed.emit(new_position)

        # Update handle positions when item moves
        self._update_handle_positions()

        # Check if we need to expand the scene
        self._handle_scene_expansion()

        # Force scene update to prevent trailing lines
        if self.scene():
            self.scene().update()

        self.logger.debug(f"ImageItem {self._image_id} moved to {new_position}")

    def _handle_selection_change(self, selected):
        """Handle selection state changes."""
        if selected:  # Selected
            self._show_resize_handles()
        else:  # Deselected
            self._hide_resize_handles()

        self.logger.debug(f"ImageItem {self._image_id} selection changed to {selected}")

    def itemChange(self, change, value):
        """
        Handle item changes including position updates.
        """
        if change == QGraphicsPixmapItem.GraphicsItemChange.ItemPositionHasChanged:
            self._handle_position_change(self.pos())
        elif change == QGraphicsPixmapItem.GraphicsItemChange.ItemSelectedHasChanged:
            self._handle_selection_change(value)

        return super().itemChange(change, value)

    def _show_image_properties(self) -> None:
        """Show image properties dialog."""
        if self.pixmap().isNull():
            self.signals.hover_started.emit("❌ No image loaded")
            return

        pixmap = self.pixmap()
        size = pixmap.size()

        properties_text = (
            f"🖼️ Image Properties:\n"
            f"Size: {size.width()} × {size.height()} pixels\n"
            f"Scale: {self._scale_factor:.0%}\n"
            f"Rotation: {self._rotation}°\n"
            f"Path: {self._image_path or 'Unknown'}"
        )

        self.signals.hover_started.emit(properties_text)
        self.logger.debug(f"ImageItem {self._image_id} properties shown")

    def _rotate_image(self, degrees: int) -> None:
        """
        Rotate the image by the specified degrees.

        Args:
            degrees: Rotation angle in degrees
        """
        self._rotation = (self._rotation + degrees) % 360

        # Apply rotation transform
        transform = QTransform()
        transform.rotate(self._rotation)
        self.setTransform(transform)

        # Emit style changed signal
        self.signals.style_changed.emit(self._style.copy())

        self.signals.hover_started.emit(f"🔄 Rotated to {self._rotation}°")
        self.logger.debug(f"ImageItem {self._image_id} rotated to {self._rotation}°")

    def _bring_to_front(self) -> None:
        """Bring this image to the front (highest z-value)."""
        if self.scene():
            # Find the highest z-value among all items
            max_z = 0
            for item in self.scene().items():
                if item != self:
                    max_z = max(max_z, item.zValue())

            # Set this item's z-value to be higher
            self.setZValue(max_z + 1)

            # Update resize handle Z-order to be above this item
            for handle in self._resize_handles:
                handle.setZValue(self.zValue() + 1)

            self.signals.hover_started.emit("🔝 Brought to front")
            self.logger.debug(
                f"ImageItem {self._image_id} brought to front with z-value {max_z + 1}"
            )

    def _send_to_back(self) -> None:
        """Send this image to the back (lowest z-value)."""
        if self.scene():
            # Find the lowest z-value among all items
            min_z = 0
            for item in self.scene().items():
                if item != self:
                    min_z = min(min_z, item.zValue())

            # Set this item's z-value to be lower
            self.setZValue(min_z - 1)

            self.signals.hover_started.emit("🔻 Sent to back")
            self.logger.debug(
                f"ImageItem {self._image_id} sent to back with z-value {min_z - 1}"
            )

    def _show_move_help(self) -> None:
        """Show help information about moving images."""
        help_text = "💡 To move images: Hover over an image and drag it to a new position. The cursor will change to indicate you can move the image."
        self.signals.hover_started.emit(help_text)
        self.logger.debug(f"ImageItem {self._image_id} move help shown")

    # Context menu action methods
    def _reload_image(self) -> None:
        """Reload the image from its file path."""
        if self._image_path:
            self._load_image(self._image_path)
            self.logger.info(f"Reloaded image for ImageItem {self._image_id}")

    def _toggle_aspect_ratio(self) -> None:
        """Toggle the aspect ratio lock for this image."""
        self._style["maintain_aspect_ratio"] = not self._style["maintain_aspect_ratio"]

        # Update resize handles to reflect the new aspect ratio setting
        self._apply_styling()
        self.signals.style_changed.emit(self._style.copy())

        # Provide user feedback
        status = "locked" if self._style["maintain_aspect_ratio"] else "unlocked"
        self.signals.hover_started.emit(f"🔒 Aspect ratio {status}")
        self.logger.info(f"Aspect ratio {status} for ImageItem {self._image_id}")

    def _reset_to_original_size(self) -> None:
        """Reset image to its original size from the loaded pixmap."""
        if hasattr(self, "_original_pixmap") and not self._original_pixmap.isNull():
            original_size = self._original_pixmap.size()

            # Reset scale factor to 1.0 (original size)
            self._scale_factor = 1.0

            # Update style to match original dimensions
            self._style["max_width"] = original_size.width()
            self._style["max_height"] = original_size.height()

            # Apply the changes
            self._scale_image()
            self._apply_styling()
            self.signals.style_changed.emit(self._style.copy())

            self.signals.hover_started.emit("↩️ Reset to original size")
            self.logger.info(
                f"Reset ImageItem {self._image_id} to original size: {original_size}"
            )
        else:
            self.logger.warning(
                f"Cannot reset ImageItem {self._image_id} - no original pixmap available"
            )

    def _reset_size(self) -> None:
        """Reset image to its original size constraints."""
        self._style["max_width"] = 400
        self._style["max_height"] = 300
        self._scale_image()
        self._apply_styling()
        self.signals.style_changed.emit(self._style.copy())
        self.logger.info(f"Reset size for ImageItem {self._image_id}")

    def _change_border_color(self) -> None:
        """Change the border color of the image."""
        # TODO: Implement color picker dialog
        # For now, cycle through some predefined colors
        colors = [
            QColor(100, 100, 100),  # Gray
            QColor(255, 0, 0),  # Red
            QColor(0, 255, 0),  # Green
            QColor(0, 0, 255),  # Blue
            QColor(255, 255, 0),  # Yellow
        ]

        current_color = self._style["border_color"]
        try:
            current_index = colors.index(current_color)
            new_index = (current_index + 1) % len(colors)
        except ValueError:
            new_index = 0

        self._style["border_color"] = colors[new_index]
        self._apply_styling()
        self.signals.style_changed.emit(self._style.copy())
        self.logger.info(f"Changed border color for ImageItem {self._image_id}")

    def _copy_image_path(self) -> None:
        """Copy the image file path to the system clipboard."""
        from PyQt6.QtWidgets import QApplication

        clipboard = QApplication.clipboard()
        clipboard.setText(self._image_path)

        self.signals.hover_started.emit("📋 Image path copied to clipboard!")
        self.logger.debug(f"Copied path of ImageItem {self._image_id} to clipboard")

    def _delete_image(self) -> None:
        """Delete this image from the scene."""
        from PyQt6.QtWidgets import QMessageBox

        # Get parent window for dialog
        parent = None
        if self.scene() and self.scene().views():
            view = self.scene().views()[0]
            parent = view.window()

        # Confirm deletion
        reply = QMessageBox.question(
            parent,
            "Delete Image",
            "Are you sure you want to delete this image?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Delete connections first
            if hasattr(self.scene(), "delete_connections_for_item"):
                self.scene().delete_connections_for_item(self)

            # Remove from scene
            if self.scene():
                self.scene().removeItem(self)

            self.logger.debug(f"Deleted ImageItem {self._image_id} with confirmation")

    def _set_opacity(self, opacity: float) -> None:
        """Set the opacity of the image."""
        self._style["opacity"] = max(0.0, min(1.0, opacity))
        self.setOpacity(self._style["opacity"])
        self.signals.style_changed.emit(self._style.copy())
        self.signals.hover_started.emit(
            f"🌫️ Opacity set to {int(self._style['opacity'] * 100)}%"
        )
        self.logger.debug(
            f"ImageItem {self._image_id} opacity set to {self._style['opacity']}"
        )

    def get_image_id(self) -> int:
        """
        Get the unique identifier for this image.

        Returns:
            Unique image ID
        """
        return self._image_id

    def get_connection_points(self) -> list[QPointF]:
        """
        Return points where connections can attach to this image.

        Returns:
            List of QPointF representing connection attachment points
        """
        rect = self.boundingRect()

        # Return points at the center of each edge and at corners
        points = [
            QPointF(rect.center().x(), rect.top()),  # Top center
            QPointF(rect.right(), rect.center().y()),  # Right center
            QPointF(rect.center().x(), rect.bottom()),  # Bottom center
            QPointF(rect.left(), rect.center().y()),  # Left center
            QPointF(rect.left(), rect.top()),  # Top-left corner
            QPointF(rect.right(), rect.top()),  # Top-right corner
            QPointF(rect.right(), rect.bottom()),  # Bottom-right corner
            QPointF(rect.left(), rect.bottom()),  # Bottom-left corner
        ]

        # Convert to scene coordinates
        scene_points = [self.mapToScene(point) for point in points]

        self.logger.debug(
            f"Generated {len(scene_points)} connection points for image {self._image_id}"
        )

        return scene_points

    def _show_custom_opacity_dialog(self) -> None:
        """Show dialog for custom opacity adjustment."""
        from PyQt6.QtWidgets import QInputDialog

        # Get parent window for dialog
        parent = None
        if self.scene() and self.scene().views():
            view = self.scene().views()[0]
            parent = view.window()

        current_opacity = int(self._style["opacity"] * 100)
        opacity, ok = QInputDialog.getInt(
            parent,
            "Custom Opacity",
            "Enter opacity percentage (0-100):",
            current_opacity,
            0,
            100,
            1,
        )

        if ok:
            self._set_opacity(opacity / 100.0)

    def _show_custom_rotation_dialog(self) -> None:
        """Show dialog for custom rotation angle."""
        from PyQt6.QtWidgets import QInputDialog

        # Get parent window for dialog
        parent = None
        if self.scene() and self.scene().views():
            view = self.scene().views()[0]
            parent = view.window()

        angle, ok = QInputDialog.getDouble(
            parent,
            "Custom Rotation",
            "Enter rotation angle in degrees:",
            0.0,
            -360.0,
            360.0,
            1,
        )

        if ok:
            self._rotate_image(angle)
            self.signals.hover_started.emit(f"🔄 Rotated by {angle}°")
