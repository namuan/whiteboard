"""
Navigation panel for the Digital Whiteboard application.

This module provides navigation aids including minimap, zoom controls,
and position indicators to enhance user experience with large canvases.
"""

from PyQt6.QtWidgets import (
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QGroupBox,
    QGraphicsView,
    QGraphicsScene,
)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF, QTimer
from PyQt6.QtGui import QPainter, QBrush, QPen, QColor

from .utils.logging_config import get_logger


class MinimapWidget(QGraphicsView):
    """
    Minimap widget showing overview of the entire canvas.

    Provides a bird's-eye view of the whiteboard with current viewport indicator
    and click-to-navigate functionality.
    """

    # Signals
    navigate_to_position = pyqtSignal(QPointF)

    def __init__(self, main_scene, parent=None):
        """
        Initialize the minimap widget.

        Args:
            main_scene: The main whiteboard scene to display
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.logger = get_logger(__name__)

        self.logger.debug(
            f"Initializing MinimapWidget with scene: {type(main_scene).__name__}"
        )

        # Store reference to main scene
        self._main_scene = main_scene
        if not main_scene:
            self.logger.warning("MinimapWidget initialized with None scene")
        else:
            scene_rect = main_scene.sceneRect()
            self.logger.debug(f"Main scene rect: {scene_rect}")

        # Create minimap scene
        self._minimap_scene = QGraphicsScene(self)
        self.setScene(self._minimap_scene)
        self.logger.debug("Minimap scene created and set")

        # Performance optimization settings
        self._item_count_threshold = 100
        self._min_item_size = 5.0
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._perform_update)
        self._cached_items = {}
        self.logger.debug(
            f"Performance settings: threshold={self._item_count_threshold}, min_size={self._min_item_size}"
        )

        # Viewport indicator
        self._viewport_indicator = None
        self._viewport_rect = None  # Current viewport rectangle
        self._viewport_item = None  # Viewport indicator item
        self._main_canvas = None  # Will be set by parent
        self.logger.debug("Viewport indicator initialized as None")

        # Configure view settings for performance
        self.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        self.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate
        )
        self.setOptimizationFlags(
            QGraphicsView.OptimizationFlag.DontSavePainterState
            | QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing
        )

        # Set minimum size for tests
        self.setMinimumSize(150, 150)

        self.logger.debug("View optimization flags set")

        self.logger.info("MinimapWidget initialized with performance optimizations")

    def set_main_canvas(self, canvas) -> None:
        """Set reference to main canvas for viewport calculations."""
        self._main_canvas = canvas
        self.logger.debug(f"Main canvas reference set: {type(canvas).__name__}")

    def schedule_update(self) -> None:
        """Schedule a minimap update with debouncing."""
        if not self._update_timer.isActive():
            self.logger.debug("Scheduling minimap update - timer was inactive")
            self._update_timer.start(100)  # 100ms debounce
        else:
            self.logger.debug("Minimap update already scheduled, extending timer")
            self._update_timer.start(100)  # Reset timer

    def _perform_update(self) -> None:
        """Perform the actual minimap update."""
        self.logger.debug("Performing scheduled minimap update")
        try:
            self.update_content()
            self.logger.debug("Scheduled minimap update completed successfully")
        except Exception as e:
            self.logger.error(f"Error during scheduled minimap update: {e}")

    def update_viewport_indicator(self, viewport_rect: QRectF) -> None:
        """Update the viewport indicator rectangle."""
        try:
            self.logger.debug(f"Updating viewport indicator with rect: {viewport_rect}")

            # Store the viewport rect
            self._viewport_rect = viewport_rect

            # Remove existing indicator
            if self._viewport_indicator:
                self.logger.debug("Removing existing viewport indicator")
                self._minimap_scene.removeItem(self._viewport_indicator)

            # Create new indicator
            pen = QPen(QColor(255, 0, 0), 2)
            brush = QBrush(QColor(255, 0, 0, 50))
            self._viewport_indicator = self._minimap_scene.addRect(
                viewport_rect, pen, brush
            )
            self._viewport_indicator.setZValue(1000)  # Set to expected test value

            # Store reference to viewport item
            self._viewport_item = self._viewport_indicator

            self.logger.debug(f"Updated viewport indicator: {viewport_rect}")

        except Exception as e:
            self.logger.error(f"Error updating viewport indicator: {e}")

    def update_content(self, force_full_update: bool = False) -> None:
        """Update minimap content with performance optimizations."""
        if not self._main_scene:
            self.logger.warning("Cannot update minimap content: no main scene")
            return

        try:
            self.logger.debug(
                f"Starting minimap content update (force_full={force_full_update})"
            )

            # Clear existing content if forced or if cache is invalid
            if force_full_update or len(self._cached_items) == 0:
                self.logger.debug("Clearing minimap scene for full update")
                self._minimap_scene.clear()
                self._cached_items.clear()
                self._viewport_indicator = None

            # Get main scene items and bounds
            main_items = self._main_scene.items()
            main_scene_rect = self._main_scene.sceneRect()
            item_count = len(main_items)

            self.logger.debug(
                f"Main scene has {item_count} items, scene rect: {main_scene_rect}"
            )

            # Determine if we should use level-of-detail rendering
            use_lod = item_count > self._item_count_threshold
            if use_lod:
                self.logger.debug(
                    f"Using LOD rendering due to high item count: {item_count}"
                )

            # Set minimap scene rect to match main scene
            self._minimap_scene.setSceneRect(main_scene_rect)

            # Add items with performance optimizations
            items_added = self._add_items_with_lod(main_items, use_lod)

            self.logger.debug(
                f"Full minimap update: {items_added}/{item_count} items rendered (LOD: {use_lod})"
            )

            # Fit content in view
            self._fit_content_optimized(main_scene_rect)
            self.logger.debug("Minimap content fitted to view")

        except Exception as e:
            self.logger.error(f"Error updating minimap content: {e}")

    def _add_items_with_lod(self, main_items: list, use_lod: bool) -> int:
        """Add items to minimap with level-of-detail optimization."""
        self.logger.debug(f"Adding {len(main_items)} items to minimap (LOD: {use_lod})")
        items_added = 0
        items_skipped = 0

        for item in main_items:
            if use_lod and items_added > self._item_count_threshold * 2:
                # Skip items beyond threshold for very large scenes
                items_skipped += 1
                continue

            if self._add_minimap_item_optimized(item, use_lod):
                items_added += 1
            else:
                items_skipped += 1

        self.logger.debug(
            f"Items processed: {items_added} added, {items_skipped} skipped"
        )
        return items_added

    def _fit_content_optimized(self, main_scene_rect: QRectF) -> None:
        """Fit content in view with performance optimizations."""
        try:
            self.logger.debug("Fitting minimap content to view")

            # Get content bounds for better fitting
            content_bounds = self._minimap_scene.itemsBoundingRect()
            if not content_bounds.isEmpty():
                self.logger.debug(f"Content bounds: {content_bounds}")
                # Add some padding around content
                padding = max(content_bounds.width(), content_bounds.height()) * 0.1
                content_bounds.adjust(-padding, -padding, padding, padding)

                # Fit content in view with aspect ratio preserved
                self.fitInView(content_bounds, Qt.AspectRatioMode.KeepAspectRatio)
                self.logger.debug(f"Fitted content with padding: {content_bounds}")
            else:
                # If no content, fit the scene rect
                self.logger.debug(
                    f"No content bounds, fitting scene rect: {main_scene_rect}"
                )
                self.fitInView(main_scene_rect, Qt.AspectRatioMode.KeepAspectRatio)
        except Exception as e:
            self.logger.debug(f"Error fitting minimap content: {e}")

    def _add_minimap_item_optimized(self, item, use_lod: bool = False) -> bool:
        """
        Add a simplified representation of an item to the minimap with performance optimizations.

        Args:
            item: The item to add to the minimap
            use_lod: Whether to use level-of-detail rendering

        Returns:
            bool: True if item was added, False if skipped
        """
        try:
            # Get item bounds and position
            bounds = item.boundingRect()
            pos = item.pos()
            item_type = type(item).__name__

            # Skip items that are too small to be meaningful in minimap
            if not self._is_item_size_valid(bounds, use_lod):
                self.logger.debug(f"Skipping {item_type} - too small: {bounds}")
                return False

            # Check if item is cached and still valid
            if self._try_use_cached_item(item, bounds, pos):
                self.logger.debug(f"Using cached representation for {item_type}")
                return True

            # Create simplified representation based on item type
            minimap_item = self._create_minimap_representation(
                item, bounds, pos, use_lod
            )

            # Cache the representation for future use
            if minimap_item:
                self._cache_minimap_item(item, bounds, pos, minimap_item)
                self.logger.debug(f"Added {item_type} to minimap at {pos}")
                return True
            else:
                self.logger.debug(
                    f"Failed to create minimap representation for {item_type}"
                )

        except Exception as e:
            self.logger.debug(f"Could not add item to minimap: {e}")

        return False

    def _is_item_size_valid(self, bounds: QRectF, use_lod: bool) -> bool:
        """Check if item size is valid for minimap rendering."""
        min_size = self._min_item_size if not use_lod else self._min_item_size * 2
        is_valid = bounds.width() >= min_size and bounds.height() >= min_size
        if not is_valid:
            self.logger.debug(
                f"Item size invalid: {bounds.width()}x{bounds.height()} < {min_size}"
            )
        return is_valid

    def _try_use_cached_item(self, item, bounds: QRectF, pos: QPointF) -> bool:
        """Try to use cached minimap item if available and valid."""
        item_id = id(item)
        if item_id in self._cached_items:
            cached_item = self._cached_items[item_id]
            cached_bounds = cached_item.get("bounds")
            cached_pos = cached_item.get("pos")

            self.logger.debug(
                f"Checking cache for item {item_id}: cached_pos={cached_pos}, current_pos={pos}"
            )

            if cached_bounds == bounds and cached_pos == pos:
                # Reuse cached representation
                minimap_item = cached_item["minimap_item"]
                if minimap_item.scene() != self._minimap_scene:
                    self._minimap_scene.addItem(minimap_item)
                    self.logger.debug(f"Restored cached item {item_id} to scene")
                return True
            else:
                self.logger.debug(
                    f"Cache invalid for item {item_id} - bounds or position changed"
                )
                # Remove invalid cache entry
                minimap_item = cached_item["minimap_item"]
                if minimap_item.scene() == self._minimap_scene:
                    self._minimap_scene.removeItem(minimap_item)
                del self._cached_items[item_id]
                return False
        return False
        return False

    def _create_minimap_representation(
        self, item, bounds: QRectF, pos: QPointF, use_lod: bool
    ):
        """Create a minimap representation for the given item."""
        item_type = type(item).__name__
        self.logger.debug(f"Creating minimap representation for {item_type}")

        if hasattr(item, "get_text"):  # Note item
            return self._create_note_representation(bounds, pos, use_lod)
        elif hasattr(item, "line"):  # Connection item
            return self._create_connection_representation(item, pos, use_lod)
        else:
            self.logger.debug(
                f"Creating generic representation for unknown item type: {item_type}"
            )
            return self._create_generic_representation(bounds, pos, use_lod)

    def _create_note_representation(self, bounds: QRectF, pos: QPointF, use_lod: bool):
        """Create a note representation for the minimap."""
        self.logger.debug(f"Creating note representation at {pos} with bounds {bounds}")

        if use_lod:
            pen = QPen(QColor(100, 100, 100), 0.3)
            brush = QBrush(QColor(255, 255, 200, 150))
        else:
            pen = QPen(QColor(80, 80, 80), 0.5)
            brush = QBrush(QColor(255, 255, 180, 200))

        minimap_item = self._minimap_scene.addRect(bounds, pen, brush)
        minimap_item.setPos(pos)
        minimap_item.setZValue(10)  # Notes above connections
        return minimap_item

    def _create_connection_representation(self, item, pos: QPointF, use_lod: bool):
        """Create a connection representation for the minimap."""
        self.logger.debug(f"Creating connection representation at {pos}")

        if use_lod:
            pen = QPen(QColor(120, 120, 120, 100), 0.3)
        else:
            pen = QPen(QColor(120, 120, 120, 150), 0.5)

        line = item.line()
        minimap_item = self._minimap_scene.addLine(line, pen)
        minimap_item.setPos(pos)
        minimap_item.setZValue(5)  # Connections below notes
        return minimap_item

    def _create_generic_representation(
        self, bounds: QRectF, pos: QPointF, use_lod: bool
    ):
        """Create a generic representation for the minimap."""
        self.logger.debug(
            f"Creating generic representation at {pos} with bounds {bounds}"
        )

        if use_lod:
            pen = QPen(QColor(120, 120, 120), 0.3)
            brush = QBrush(QColor(200, 200, 200, 80))
        else:
            pen = QPen(QColor(100, 100, 100), 0.5)
            brush = QBrush(QColor(200, 200, 200, 100))

        minimap_item = self._minimap_scene.addRect(bounds, pen, brush)
        minimap_item.setPos(pos)
        minimap_item.setZValue(1)
        return minimap_item

    def _cache_minimap_item(self, item, bounds: QRectF, pos: QPointF, minimap_item):
        """Cache the minimap item for future use."""
        item_id = id(item)
        self._cached_items[item_id] = {
            "bounds": bounds,
            "pos": pos,
            "minimap_item": minimap_item,
        }
        self.logger.debug(f"Cached minimap item {item_id}")

    def _add_minimap_item(self, item) -> None:
        """
        Add a simplified representation of an item to the minimap.

        This method is kept for backward compatibility and delegates to the optimized version.

        Args:
            item: The item to add to the minimap
        """
        self.logger.debug(f"Legacy add_minimap_item called for {type(item).__name__}")
        self._add_minimap_item_optimized(item, use_lod=False)

    def _update_minimap_content(self) -> None:
        """Update minimap content - alias for update_content method."""
        self.logger.debug(
            "_update_minimap_content called - delegating to update_content"
        )
        self.update_content()

    def _perform_full_minimap_update(
        self, scene_rect: QRectF, items: list, use_lod: bool = False
    ) -> None:
        """
        Perform a full minimap update with the given scene rect and items.

        Args:
            scene_rect: The scene rectangle to use
            items: List of items to add to minimap
            use_lod: Whether to use level-of-detail rendering
        """
        self.logger.debug(
            f"Performing full minimap update with {len(items)} items (LOD: {use_lod})"
        )

        try:
            # Clear existing content
            self._minimap_scene.clear()
            self._cached_items.clear()
            self._viewport_indicator = None
            self._viewport_item = None

            # Set scene rect
            self._minimap_scene.setSceneRect(scene_rect)

            # Add items with LOD
            items_added = self._add_items_with_lod(items, use_lod)

            # Fit content
            self._fit_content_optimized(scene_rect)

            self.logger.debug(
                f"Full minimap update completed: {items_added}/{len(items)} items rendered"
            )

        except Exception as e:
            self.logger.error(f"Error in _perform_full_minimap_update: {e}")

    def mousePressEvent(self, event) -> None:
        """Handle mouse press events for navigation."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Convert click position to scene coordinates
            scene_pos = self.mapToScene(event.pos())
            widget_pos = event.pos()

            self.logger.debug(
                f"Navigation click at widget pos: {widget_pos}, scene pos: {scene_pos}"
            )

            # Emit navigation signal to center main canvas on clicked position
            self.navigate_to_position.emit(scene_pos)

            self.logger.debug(f"Navigation click at scene position: {scene_pos}")
        else:
            self.logger.debug(f"Mouse press with button: {event.button()}")

        super().mousePressEvent(event)


class NavigationPanel(QDockWidget):
    """
    Navigation panel providing minimap and navigation controls.

    A dockable widget that contains minimap functionality and various
    navigation aids for enhanced canvas navigation experience.
    """

    # Signals
    zoom_changed = pyqtSignal(float)
    navigate_to_position = pyqtSignal(QPointF)
    fit_to_window_requested = pyqtSignal()
    center_on_content_requested = pyqtSignal()

    def __init__(self, main_scene, parent=None):
        """
        Initialize the navigation panel.

        Args:
            main_scene: The main whiteboard scene
            parent: Parent widget (optional)
        """
        super().__init__("Navigation", parent)
        self.logger = get_logger(__name__)

        self.logger.debug(
            f"Initializing NavigationPanel with scene: {type(main_scene).__name__}"
        )

        # Store reference to main scene
        self._main_scene = main_scene
        if not main_scene:
            self.logger.warning("NavigationPanel initialized with None scene")

        # Create main widget and layout
        self._main_widget = QWidget()
        self.setWidget(self._main_widget)
        self.logger.debug("Main widget created and set")

        # Setup UI components
        self._setup_ui()

        # Configure dock widget properties
        self._setup_dock_properties()

        self.logger.info("NavigationPanel initialized")

    def _setup_ui(self) -> None:
        """Set up the user interface components."""
        self.logger.debug("Setting up NavigationPanel UI components")

        layout = QVBoxLayout(self._main_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Minimap section
        self.logger.debug("Setting up minimap section")
        self._setup_minimap_section(layout)

        # Zoom controls section
        self.logger.debug("Setting up zoom controls section")
        self._setup_zoom_section(layout)

        # Navigation buttons section
        self.logger.debug("Setting up navigation buttons section")
        self._setup_navigation_section(layout)

        # Add stretch to push everything to top
        layout.addStretch()

        self.logger.debug("NavigationPanel UI setup completed")

    def _setup_minimap_section(self, parent_layout) -> None:
        """Set up the minimap section."""
        self.logger.debug("Creating minimap section")

        # Minimap group box
        minimap_group = QGroupBox("Minimap")
        minimap_layout = QVBoxLayout(minimap_group)

        # Create minimap widget
        self._minimap = MinimapWidget(self._main_scene)
        self._minimap.navigate_to_position.connect(self.navigate_to_position.emit)
        self.logger.debug("Minimap widget created and connected")

        minimap_layout.addWidget(self._minimap)
        parent_layout.addWidget(minimap_group)

        self.logger.debug("Minimap section setup completed")

    def _setup_zoom_section(self, parent_layout) -> None:
        """Set up the zoom controls section."""
        self.logger.debug("Creating zoom controls section")

        # Zoom group box
        zoom_group = QGroupBox("Zoom")
        zoom_layout = QVBoxLayout(zoom_group)

        # Zoom level display
        zoom_info_layout = QHBoxLayout()
        zoom_info_layout.addWidget(QLabel("Level:"))

        self._zoom_spinbox = QSpinBox()
        self._zoom_spinbox.setRange(10, 1000)
        self._zoom_spinbox.setValue(100)
        self._zoom_spinbox.setSuffix("%")
        self._zoom_spinbox.valueChanged.connect(self._on_zoom_spinbox_changed)
        zoom_info_layout.addWidget(self._zoom_spinbox)
        self.logger.debug("Zoom spinbox created with range 10-1000%, default 100%")

        zoom_layout.addLayout(zoom_info_layout)

        # Zoom slider
        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setRange(10, 1000)
        self._zoom_slider.setValue(100)
        self._zoom_slider.valueChanged.connect(self._on_zoom_slider_changed)
        zoom_layout.addWidget(self._zoom_slider)
        self.logger.debug("Zoom slider created with range 10-1000%, default 100%")

        # Zoom buttons
        zoom_buttons_layout = QHBoxLayout()

        zoom_in_btn = QPushButton("Zoom In")
        zoom_in_btn.clicked.connect(self._on_zoom_in)
        zoom_buttons_layout.addWidget(zoom_in_btn)

        zoom_out_btn = QPushButton("Zoom Out")
        zoom_out_btn.clicked.connect(self._on_zoom_out)
        zoom_buttons_layout.addWidget(zoom_out_btn)

        zoom_layout.addLayout(zoom_buttons_layout)
        self.logger.debug("Zoom in/out buttons created")

        # Reset zoom button
        reset_zoom_btn = QPushButton("Reset (100%)")
        reset_zoom_btn.clicked.connect(self._on_reset_zoom)
        zoom_layout.addWidget(reset_zoom_btn)
        self.logger.debug("Reset zoom button created")

        parent_layout.addWidget(zoom_group)

        self.logger.debug("Zoom controls section setup completed")

    def _setup_navigation_section(self, parent_layout) -> None:
        """Set up the navigation buttons section."""
        self.logger.debug("Creating navigation buttons section")

        # Navigation group box
        nav_group = QGroupBox("Quick Navigation")
        nav_layout = QVBoxLayout(nav_group)

        # Fit to window button
        fit_window_btn = QPushButton("Fit to Window")
        fit_window_btn.clicked.connect(self.fit_to_window_requested.emit)
        nav_layout.addWidget(fit_window_btn)
        self.logger.debug("Fit to window button created")

        # Center on content button
        center_content_btn = QPushButton("Center on Content")
        center_content_btn.clicked.connect(self.center_on_content_requested.emit)
        nav_layout.addWidget(center_content_btn)
        self.logger.debug("Center on content button created")

        parent_layout.addWidget(nav_group)

        self.logger.debug("Navigation buttons section setup completed")

    def _setup_dock_properties(self) -> None:
        """Configure dock widget properties."""
        self.logger.debug("Configuring dock widget properties")

        # Set allowed dock areas
        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.logger.debug("Allowed dock areas set to left and right")

        # Set features
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.logger.debug("Dock features set: movable, floatable, closable")

        # Set size constraints
        self.setMinimumWidth(200)
        self.setMaximumWidth(400)
        self.logger.debug("Size constraints set: min width 200px, max width 400px")

    def update_zoom_display(self, zoom_level: float) -> None:
        """
        Update the zoom level display.

        Args:
            zoom_level: Current zoom level as percentage (e.g., 100.0 for 100%)
        """
        try:
            self.logger.debug(f"Updating zoom display to {zoom_level}%")

            # Block signals to prevent recursion
            self._zoom_spinbox.blockSignals(True)
            self._zoom_slider.blockSignals(True)

            # Update displays
            zoom_percent = int(zoom_level)
            self._zoom_spinbox.setValue(zoom_percent)
            self._zoom_slider.setValue(zoom_percent)

            self.logger.debug(
                f"Zoom display updated: spinbox={zoom_percent}%, slider={zoom_percent}%"
            )

            # Unblock signals
            self._zoom_spinbox.blockSignals(False)
            self._zoom_slider.blockSignals(False)

        except Exception as e:
            self.logger.error(f"Error updating zoom display: {e}")

    def update_viewport_indicator(self, viewport_rect_or_center) -> None:
        """
        Update the minimap viewport indicator.

        Args:
            viewport_rect_or_center: Either a QRectF viewport rectangle or QPointF center point
        """
        try:
            if isinstance(viewport_rect_or_center, QRectF):
                # Called from viewport_changed signal
                self.logger.debug(
                    f"Updating viewport indicator with rect: {viewport_rect_or_center}"
                )
                self._minimap.update_viewport_indicator(viewport_rect_or_center)
            elif isinstance(viewport_rect_or_center, QPointF):
                # Called from pan_changed signal - need to calculate viewport rect
                self.logger.debug(
                    f"Updating viewport indicator with center point: {viewport_rect_or_center}"
                )

                # Get current view size from the minimap's main canvas reference
                if (
                    hasattr(self._minimap, "_main_canvas")
                    and self._minimap._main_canvas
                ):
                    view_rect = self._minimap._main_canvas.mapToScene(
                        self._minimap._main_canvas.rect()
                    ).boundingRect()
                    # Center the view rect on the new center point
                    center = viewport_rect_or_center
                    view_rect.moveCenter(center)
                    self._minimap.update_viewport_indicator(view_rect)
                    self.logger.debug(
                        f"Calculated viewport rect from canvas: {view_rect}"
                    )
                else:
                    # Fallback: create a reasonable viewport rect around the center
                    center = viewport_rect_or_center
                    size = 800  # Default viewport size
                    viewport_rect = QRectF(
                        center.x() - size / 2, center.y() - size / 2, size, size
                    )
                    self._minimap.update_viewport_indicator(viewport_rect)
                    self.logger.debug(f"Using fallback viewport rect: {viewport_rect}")
            else:
                self.logger.warning(
                    f"Invalid viewport indicator type: {type(viewport_rect_or_center)}"
                )
        except Exception as e:
            self.logger.error(f"Error updating viewport indicator: {e}")

    def schedule_minimap_update(self) -> None:
        """Schedule a minimap content update."""
        self.logger.debug("NavigationPanel.schedule_minimap_update called")
        self._minimap.schedule_update()

    def _on_zoom_spinbox_changed(self, value: int) -> None:
        """Handle zoom spinbox value changes."""
        self.logger.debug(f"Zoom spinbox changed to {value}%")

        self._zoom_slider.blockSignals(True)
        self._zoom_slider.setValue(value)
        self._zoom_slider.blockSignals(False)

        self.logger.debug(f"Emitting zoom_changed signal with value {value}")
        self.zoom_changed.emit(float(value))

    def _on_zoom_slider_changed(self, value: int) -> None:
        """Handle zoom slider value changes."""
        self.logger.debug(f"Zoom slider changed to {value}%")

        self._zoom_spinbox.blockSignals(True)
        self._zoom_spinbox.setValue(value)
        self._zoom_spinbox.blockSignals(False)

        self.logger.debug(f"Emitting zoom_changed signal with value {value}")
        self.zoom_changed.emit(float(value))

    def _on_zoom_in(self) -> None:
        """Handle zoom in button click."""
        current_zoom = self._zoom_spinbox.value()
        new_zoom = min(1000, current_zoom + 25)
        self.logger.debug(f"Zoom in clicked: {current_zoom}% -> {new_zoom}%")
        self.zoom_changed.emit(float(new_zoom))

    def _on_zoom_out(self) -> None:
        """Handle zoom out button click."""
        current_zoom = self._zoom_spinbox.value()
        new_zoom = max(10, current_zoom - 25)
        self.logger.debug(f"Zoom out clicked: {current_zoom}% -> {new_zoom}%")
        self.zoom_changed.emit(float(new_zoom))

    def _on_reset_zoom(self) -> None:
        """Handle reset zoom button click."""
        self.logger.debug("Reset zoom clicked: setting to 100%")
        self.zoom_changed.emit(100.0)
