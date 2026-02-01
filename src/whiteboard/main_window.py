"""
Main window for the Digital Whiteboard application.
"""

from PyQt6.QtWidgets import (
    QMainWindow,
    QToolBar,
    QStatusBar,
    QFileDialog,
    QMessageBox,
    QApplication,
    QLabel,
    QGraphicsView,
    QWidget,
    QHBoxLayout,
    QPushButton,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPointF
from PyQt6.QtGui import QAction, QKeySequence, QFont
from pathlib import Path

from .goto_dialog import GoToDialog
from .utils.logging_config import get_logger
from .canvas import WhiteboardScene, WhiteboardCanvas
from .session_manager import SessionManager, SessionError
from .state_manager import AppStateManager
from .navigation_panel import NavigationPanel


class PositionIndicator(QWidget):
    """A widget that displays the current view center coordinates with a center button."""

    center_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the position indicator UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Position label
        self._position_label = QLabel("Position: (0, 0)")
        self._position_label.setStyleSheet("""
            QLabel {
                background-color: rgba(240, 240, 240, 0.8);
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 2px 6px;
                font-family: monospace;
                font-size: 11px;
            }
        """)
        self._position_label.setMinimumWidth(140)

        # Center button
        self._center_button = QPushButton("⌖")
        self._center_button.setToolTip("Center on Content")
        self._center_button.setFixedSize(20, 20)
        self._center_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(220, 220, 220, 0.9);
                border: 1px solid #aaa;
                border-radius: 3px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(200, 200, 200, 0.9);
            }
            QPushButton:pressed {
                background-color: rgba(180, 180, 180, 0.9);
            }
        """)
        self._center_button.clicked.connect(self.center_requested.emit)

        layout.addWidget(self._position_label)
        layout.addWidget(self._center_button)

    def update_position(self, center_point):
        """Update the position display."""
        pos_text = f"Position: ({center_point.x():.0f}, {center_point.y():.0f})"
        self._position_label.setText(pos_text)

    def get_position_text(self):
        """Get the current position text."""
        return self._position_label.text()


class ZoomIndicator(QWidget):
    """
    Enhanced zoom indicator widget for the status bar.

    Displays current zoom percentage with interactive controls.
    """

    # Signals
    zoom_reset_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self._current_zoom = 100.0
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the zoom indicator UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        # Zoom percentage label
        self._zoom_label = QLabel("100%")
        self._zoom_label.setMinimumWidth(50)
        self._zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Reset button (small)
        self._reset_btn = QPushButton("⌂")
        self._reset_btn.setMaximumSize(20, 20)
        self._reset_btn.setToolTip("Reset zoom to 100%")
        self._reset_btn.clicked.connect(self.zoom_reset_requested.emit)

        # Style the components
        self._apply_styles()

        layout.addWidget(self._zoom_label)
        layout.addWidget(self._reset_btn)

        self.logger.debug("ZoomIndicator widget initialized")

    def _apply_styles(self) -> None:
        """Apply consistent styling to the zoom indicator."""
        # Main widget style
        self.setStyleSheet("""
            ZoomIndicator {
                background-color: rgba(245, 245, 245, 0.9);
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 1px;
            }
        """)

        # Label style
        label_font = QFont("monospace", 10)
        label_font.setBold(True)
        self._zoom_label.setFont(label_font)
        self._zoom_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                color: #333;
                padding: 2px 4px;
            }
        """)

        # Button style
        self._reset_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(200, 200, 200, 0.8);
                border: 1px solid #bbb;
                border-radius: 2px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(180, 180, 180, 0.9);
            }
            QPushButton:pressed {
                background-color: rgba(160, 160, 160, 1.0);
            }
        """)

    def update_zoom(self, zoom_factor: float) -> None:
        """
        Update the zoom display.

        Args:
            zoom_factor: Current zoom factor (e.g., 1.0 for 100%)
        """
        try:
            self._current_zoom = zoom_factor * 100

            # Format zoom with appropriate precision
            if self._current_zoom >= 100:
                zoom_text = f"{self._current_zoom:.0f}%"
            else:
                zoom_text = f"{self._current_zoom:.1f}%"

            self._zoom_label.setText(zoom_text)

            # Update tooltip with more info
            self.setToolTip(f"Current zoom: {zoom_text}\nClick ⌂ to reset to 100%")

            self.logger.debug(f"ZoomIndicator updated to {zoom_text}")

        except Exception as e:
            self.logger.error(f"Error updating zoom indicator: {e}")

    def get_current_zoom(self) -> float:
        """Get the current zoom percentage."""
        return self._current_zoom


class MainWindow(QMainWindow):
    """
    Main application window containing all UI elements.

    Provides the primary interface with menu bar, toolbar, and canvas area.
    Handles window management including fullscreen mode.
    """

    # Signals
    fullscreen_toggled = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.logger = get_logger(__name__)
        self._is_fullscreen = False
        self._current_file_path = None  # Track current file for save operations

        # Initialize canvas components
        self._scene = WhiteboardScene()
        self._canvas = WhiteboardCanvas(self._scene)

        # Initialize navigation panel
        self._navigation_panel = NavigationPanel(self._scene)

        # Initialize session manager
        self._session_manager = SessionManager()
        self._setup_session_connections()

        # Initialize state manager
        self._state_manager = AppStateManager()

        # Initialize auto-save functionality
        self._auto_save_timer = QTimer()
        self._auto_save_timer.timeout.connect(self._auto_save)
        self._auto_save_interval = 30000  # 30 seconds in milliseconds
        self._auto_save_enabled = True
        self._scene_modified = False

        # Initialize UI components
        self._setup_window()
        self._setup_central_widget()
        self._setup_navigation_panel()
        self._setup_menu_bar()
        self._setup_toolbar()
        self._setup_status_bar()
        self._setup_canvas_connections()
        self._setup_navigation_connections()

        # Load last document if available
        self._load_last_document()

        self.logger.info("MainWindow initialized successfully")

    def _setup_window(self) -> None:
        """Configure main window properties."""
        self.setWindowTitle("Digital Whiteboard")
        self.setMinimumSize(800, 600)
        self.resize(1200, 800)

        # Center window on screen
        screen = QApplication.primaryScreen().geometry()
        window_geometry = self.geometry()
        x = (screen.width() - window_geometry.width()) // 2
        y = (screen.height() - window_geometry.height()) // 2
        self.move(x, y)

    def _setup_central_widget(self) -> None:
        """Set up the central widget area."""
        # Set canvas as central widget
        self.setCentralWidget(self._canvas)

    def _setup_menu_bar(self) -> None:
        """Create and configure the menu bar."""
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("&File")

        # New action
        new_action = QAction("&New", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.setStatusTip("Create a new whiteboard")
        new_action.triggered.connect(self._on_new)
        file_menu.addAction(new_action)

        # Open action
        open_action = QAction("&Open...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.setStatusTip("Open an existing whiteboard")
        open_action.triggered.connect(self._on_open)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        # Load action
        load_action = QAction("&Open...", self)
        load_action.setShortcut(QKeySequence.StandardKey.Open)
        load_action.setStatusTip("Open a whiteboard file")
        load_action.triggered.connect(self._on_load)
        file_menu.addAction(load_action)

        file_menu.addSeparator()

        # Save action
        save_action = QAction("&Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.setStatusTip("Save the current whiteboard")
        save_action.triggered.connect(self._on_save)
        file_menu.addAction(save_action)

        # Save As action
        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.setStatusTip("Save the whiteboard with a new name")
        save_as_action.triggered.connect(self._on_save_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        # Exit action
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.setStatusTip("Exit the application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit Menu
        edit_menu = menubar.addMenu("&Edit")

        # Undo action
        undo_action = QAction("&Undo", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.setStatusTip("Undo the last action")
        undo_action.triggered.connect(self._on_undo)
        undo_action.setEnabled(False)
        edit_menu.addAction(undo_action)
        self._undo_action = undo_action

        # Redo action
        redo_action = QAction("&Redo", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.setStatusTip("Redo the last undone action")
        redo_action.triggered.connect(self._on_redo)
        redo_action.setEnabled(False)
        edit_menu.addAction(redo_action)
        self._redo_action = redo_action

        edit_menu.addSeparator()

        # Cut action
        cut_action = QAction("Cu&t", self)
        cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        cut_action.setStatusTip("Cut selected items")
        cut_action.triggered.connect(self._on_cut)
        edit_menu.addAction(cut_action)

        # Copy action
        copy_action = QAction("&Copy", self)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.setStatusTip("Copy selected items")
        copy_action.triggered.connect(self._on_copy)
        edit_menu.addAction(copy_action)

        # Paste action
        paste_action = QAction("&Paste", self)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        paste_action.setStatusTip("Paste items from clipboard")
        paste_action.triggered.connect(self._on_paste)
        edit_menu.addAction(paste_action)

        edit_menu.addSeparator()

        # Select All action
        select_all_action = QAction("Select &All", self)
        select_all_action.setShortcut(QKeySequence.StandardKey.SelectAll)
        select_all_action.setStatusTip("Select all items")
        select_all_action.triggered.connect(self._on_select_all)
        edit_menu.addAction(select_all_action)

        # View Menu
        view_menu = menubar.addMenu("&View")

        # Zoom In action
        zoom_in_action = QAction("Zoom &In", self)
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.setStatusTip("Zoom in on the canvas")
        zoom_in_action.triggered.connect(self._on_zoom_in)
        view_menu.addAction(zoom_in_action)

        # Zoom Out action
        zoom_out_action = QAction("Zoom &Out", self)
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out_action.setStatusTip("Zoom out on the canvas")
        zoom_out_action.triggered.connect(self._on_zoom_out)
        view_menu.addAction(zoom_out_action)

        # Actual Size action
        actual_size_action = QAction("&Actual Size", self)
        actual_size_action.setShortcut(QKeySequence("Ctrl+0"))
        actual_size_action.setStatusTip("Reset zoom to actual size")
        actual_size_action.triggered.connect(self._on_actual_size)
        view_menu.addAction(actual_size_action)

        # Fit to Window action
        fit_window_action = QAction("&Fit to Window", self)
        fit_window_action.setShortcut(QKeySequence("Ctrl+9"))
        fit_window_action.setStatusTip("Fit content to window")
        fit_window_action.triggered.connect(self._on_fit_window)
        view_menu.addAction(fit_window_action)

        view_menu.addSeparator()

        # Center on Content action
        center_content_action = QAction("&Center on Content", self)
        center_content_action.setShortcut(QKeySequence("Ctrl+H"))
        center_content_action.setStatusTip("Center view on all content")
        center_content_action.triggered.connect(self._on_center_content)
        view_menu.addAction(center_content_action)

        view_menu.addSeparator()

        # Navigation submenu
        navigation_menu = view_menu.addMenu("&Navigation")

        # Pan navigation info action
        pan_info_action = QAction("Pan Navigation Help", self)
        pan_info_action.setStatusTip("Show pan navigation shortcuts")
        pan_info_action.triggered.connect(self._show_pan_help)
        navigation_menu.addAction(pan_info_action)

        navigation_menu.addSeparator()

        # GoTo coordinates action
        goto_action = QAction("&Go To Coordinates...", self)
        goto_action.setShortcut(QKeySequence("Ctrl+G"))
        goto_action.setStatusTip("Navigate to specific coordinates")
        goto_action.triggered.connect(self._on_goto_coordinates)
        navigation_menu.addAction(goto_action)

        navigation_menu.addSeparator()

        # Pan shortcuts (for display only - actual handling is in keyPressEvent)
        pan_left_action = QAction("Pan Left", self)
        pan_left_action.setShortcut(QKeySequence("Left"))
        pan_left_action.setStatusTip("Pan view to the left")
        pan_left_action.setEnabled(False)  # Display only
        navigation_menu.addAction(pan_left_action)

        pan_right_action = QAction("Pan Right", self)
        pan_right_action.setShortcut(QKeySequence("Right"))
        pan_right_action.setStatusTip("Pan view to the right")
        pan_right_action.setEnabled(False)  # Display only
        navigation_menu.addAction(pan_right_action)

        pan_up_action = QAction("Pan Up", self)
        pan_up_action.setShortcut(QKeySequence("Up"))
        pan_up_action.setStatusTip("Pan view upward")
        pan_up_action.setEnabled(False)  # Display only
        navigation_menu.addAction(pan_up_action)

        pan_down_action = QAction("Pan Down", self)
        pan_down_action.setShortcut(QKeySequence("Down"))
        pan_down_action.setStatusTip("Pan view downward")
        pan_down_action.setEnabled(False)  # Display only
        navigation_menu.addAction(pan_down_action)

        navigation_menu.addSeparator()

        space_pan_action = QAction("Space + Drag to Pan", self)
        space_pan_action.setShortcut(QKeySequence("Space"))
        space_pan_action.setStatusTip("Hold Space and drag to pan the view")
        space_pan_action.setEnabled(False)  # Display only
        navigation_menu.addAction(space_pan_action)

        view_menu.addSeparator()

        # Navigation Panel toggle action
        navigation_panel_action = QAction("&Navigation Panel", self)
        navigation_panel_action.setShortcut(QKeySequence("Ctrl+Shift+N"))
        navigation_panel_action.setStatusTip("Toggle navigation panel visibility")
        navigation_panel_action.setCheckable(True)
        navigation_panel_action.setChecked(True)  # Initially visible
        navigation_panel_action.triggered.connect(self._toggle_navigation_panel)
        view_menu.addAction(navigation_panel_action)

        # Store reference to navigation panel action for updates
        self._navigation_panel_action = navigation_panel_action

        view_menu.addSeparator()

        # Fullscreen action
        fullscreen_action = QAction("&Fullscreen", self)
        fullscreen_action.setShortcut(QKeySequence("F11"))
        fullscreen_action.setStatusTip("Toggle fullscreen mode")
        fullscreen_action.setCheckable(True)
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fullscreen_action)

        # Store reference to fullscreen action for updates
        self._fullscreen_action = fullscreen_action

    def _setup_toolbar(self) -> None:
        """Create and configure the toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # New button
        new_action = QAction("New", self)
        new_action.setStatusTip("Create a new whiteboard")
        new_action.triggered.connect(self._on_new)
        toolbar.addAction(new_action)

        # Load button
        load_action = QAction("Open", self)
        load_action.setStatusTip("Open a whiteboard file")
        load_action.triggered.connect(self._on_load)
        toolbar.addAction(load_action)

        # Save button
        save_action = QAction("Save", self)
        save_action.setStatusTip("Save the current whiteboard")
        save_action.triggered.connect(self._on_save)
        toolbar.addAction(save_action)

        toolbar.addSeparator()

        # Undo button
        undo_action = QAction("Undo", self)
        undo_action.setStatusTip("Undo the last action")
        undo_action.triggered.connect(self._on_undo)
        toolbar.addAction(undo_action)

        # Redo button
        redo_action = QAction("Redo", self)
        redo_action.setStatusTip("Redo the last undone action")
        redo_action.triggered.connect(self._on_redo)
        toolbar.addAction(redo_action)

        toolbar.addSeparator()

        # Zoom controls
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.setStatusTip("Zoom in on the canvas")
        zoom_in_action.triggered.connect(self._on_zoom_in)
        toolbar.addAction(zoom_in_action)

        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.setStatusTip("Zoom out on the canvas")
        zoom_out_action.triggered.connect(self._on_zoom_out)
        toolbar.addAction(zoom_out_action)

    def _setup_status_bar(self) -> None:
        """Create and configure the status bar with enhanced zoom and position display."""
        status_bar = QStatusBar()
        status_bar.showMessage("Ready • Double-click empty area to create note")
        self.setStatusBar(status_bar)

        # Add persistent zoom and position indicators on the right side
        self._zoom_indicator = ZoomIndicator()
        self._position_indicator = PositionIndicator()

        # Connect widget signals
        self._zoom_indicator.zoom_reset_requested.connect(self._on_reset_zoom)
        self._position_indicator.center_requested.connect(self._on_center_content)

        # Add widgets to status bar (position first, then zoom indicator)
        status_bar.addPermanentWidget(self._position_indicator)
        status_bar.addPermanentWidget(self._zoom_indicator)

        # Initialize displays with actual values
        try:
            current_zoom = self._canvas.get_zoom_factor()
            center_point = self._canvas.get_center_point()
            self._zoom_indicator.update_zoom(current_zoom)
            self._position_indicator.update_position(center_point)
            self.logger.debug(
                f"Enhanced status bar initialized with zoom={current_zoom * 100:.1f}% and center=({center_point.x():.1f}, {center_point.y():.1f})"
            )
        except Exception as e:
            self.logger.error(
                f"Failed to initialize enhanced status bar indicators: {e}"
            )

    def _update_position_display(self, center_point) -> None:
        """Update position display with enhanced formatting."""
        if (
            hasattr(self, "_position_indicator")
            and self._position_indicator is not None
        ):
            self._position_indicator.update_position(center_point)
            self.logger.debug(
                f"Position display updated to ({center_point.x():.0f}, {center_point.y():.0f})"
            )

    def _setup_session_connections(self) -> None:
        """Set up session manager signal connections."""
        self._session_manager.session_saved.connect(self._on_session_saved)
        self._session_manager.session_loaded.connect(self._on_session_loaded)
        self._session_manager.session_error.connect(self._on_session_error)

    def _setup_canvas_connections(self) -> None:
        """Set up signal connections between canvas and main window."""
        # Connect canvas zoom changes to status bar updates
        self._canvas.zoom_changed.connect(self._on_zoom_changed)
        self._canvas.pan_changed.connect(self._on_pan_changed)
        # Connect undo/redo enablement
        try:
            stack = self._canvas.get_command_stack()
            stack.can_undo_changed.connect(
                lambda enabled: self._undo_action.setEnabled(enabled)
            )
            stack.can_redo_changed.connect(
                lambda enabled: self._redo_action.setEnabled(enabled)
            )
        except Exception as e:
            self.logger.debug(f"Failed to bind undo/redo actions to stack: {e}")
        # Connect note creation signals
        self._canvas.note_created.connect(self._on_note_created)
        # Connect note hover signals for user hints
        self._canvas.note_hover_hint.connect(self._on_note_hover_hint)
        self._canvas.note_hover_ended.connect(self._on_note_hover_ended)
        # Connect scene modification signals for auto-save
        self._scene.changed.connect(self._on_scene_changed)

    def _on_zoom_changed(self, zoom_factor: float) -> None:
        """Handle zoom level changes with enhanced status bar updates."""
        # Update the zoom indicator widget
        self._zoom_indicator.update_zoom(zoom_factor)

        # Also refresh position to reflect any center shift on zoom
        try:
            center_point = self._canvas.get_center_point()
            self._update_position_display(center_point)
        except Exception as e:
            self.logger.error(f"Failed to update position on zoom change: {e}")

        zoom_percent = zoom_factor * 100
        self.logger.debug(f"Zoom changed to {zoom_percent:.1f}%")

    def _on_goto_coordinates(self) -> None:
        """Handle Go To Coordinates action."""
        try:
            # Get current center point
            center_point = self._canvas.get_center_point()
            current_x = center_point.x()
            current_y = center_point.y()

            # Show the GoTo dialog
            result = GoToDialog.show_goto_dialog(current_x, current_y, self)
            if result is not None:
                target_x, target_y = result
                self.logger.info(f"Navigating to coordinates: ({target_x}, {target_y})")

                # Navigate to the specified coordinates
                self._canvas.center_on_point(target_x, target_y)

                # Update status bar
                self.statusBar().showMessage(
                    f"Navigated to ({target_x:.1f}, {target_y:.1f})", 3000
                )

        except Exception as e:
            self.logger.error(f"Error in GoTo Coordinates: {e}")
            self.statusBar().showMessage("Error navigating to coordinates", 3000)

    def _on_reset_zoom(self) -> None:
        """Handle zoom reset request from the zoom indicator."""
        try:
            # Reset zoom to 100% (factor 1.0)
            self._canvas.reset_zoom()
            self.logger.debug("Zoom reset to 100% from status bar indicator")
        except Exception as e:
            self.logger.error(f"Error resetting zoom from status bar: {e}")

    def _on_pan_changed(self, center_point) -> None:
        """Handle pan position changes with enhanced status bar updates."""
        self._update_position_display(center_point)
        self.logger.debug(
            f"Pan changed, center at ({center_point.x():.0f}, {center_point.y():.0f})"
        )

    def _on_note_created(self, note) -> None:
        """Handle note creation events."""
        self.statusBar().showMessage("Note created - Double-click to edit", 3000)
        self.logger.debug(f"Note created at position {note.pos()}")

    def _on_note_hover_hint(self, hint_text: str) -> None:
        """Handle note hover hint events."""
        self.statusBar().showMessage(hint_text)

    def _on_note_hover_ended(self) -> None:
        """Handle note hover end events."""
        # Return to the default hint message; zoom/position are persistent labels now
        self.statusBar().showMessage("Double-click empty area to create note")

    def toggle_fullscreen(self) -> None:
        """
        Toggle fullscreen mode.

        Requirement 6.1: Hide window decorations and maximize canvas area
        Requirement 6.2: Provide clear method to exit fullscreen
        Requirement 6.3: Preserve all canvas content during mode changes
        """
        try:
            if self._is_fullscreen:
                self.showNormal()
                self._is_fullscreen = False
                self.logger.info("Exited fullscreen mode")
            else:
                self.showFullScreen()
                self._is_fullscreen = True
                self.logger.info("Entered fullscreen mode")

            # Update action state
            self._fullscreen_action.setChecked(self._is_fullscreen)

            # Emit signal for other components
            self.fullscreen_toggled.emit(self._is_fullscreen)

        except Exception as e:
            self.logger.error(f"Failed to toggle fullscreen: {e}")
            self._show_error(
                "Fullscreen Error", f"Could not toggle fullscreen mode: {e}"
            )

    def _toggle_navigation_panel(self) -> None:
        """Toggle navigation panel visibility."""
        try:
            if self._navigation_panel.isVisible():
                self._navigation_panel.hide()
                self.logger.info("Navigation panel hidden")
            else:
                self._navigation_panel.show()
                self.logger.info("Navigation panel shown")

            # Update action state
            self._navigation_panel_action.setChecked(self._navigation_panel.isVisible())

        except Exception as e:
            self.logger.error(f"Failed to toggle navigation panel: {e}")
            self._show_error(
                "Navigation Panel Error", f"Could not toggle navigation panel: {e}"
            )

    def keyPressEvent(self, event):
        """Handle key press events."""
        key = event.key()
        modifiers = event.modifiers()

        # F11 for fullscreen toggle
        if key == Qt.Key.Key_F11:
            self.toggle_fullscreen()
            return

        # Handle arrow keys for pan navigation
        if key in [Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down]:
            # Forward arrow keys to canvas for pan navigation
            self._canvas.keyPressEvent(event)
            return

        # Handle space key for pan mode activation
        if key == Qt.Key.Key_Space and not modifiers:
            # Enable space+drag pan mode in canvas
            self._canvas.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.logger.debug("Space key pressed - pan mode activated")
            return

        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        """Handle key release events."""
        key = event.key()

        # Handle space key release to exit pan mode
        if key == Qt.Key.Key_Space:
            # Restore normal drag mode
            self._canvas.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            self.logger.debug("Space key released - pan mode deactivated")
            return

        super().keyReleaseEvent(event)

    def closeEvent(self, event):
        """Handle window close event."""
        try:
            # Save current file path as last document if there is one
            if self._current_file_path:
                self._state_manager.set_last_document_path(str(self._current_file_path))

            # TODO: Check for unsaved changes in later tasks
            self.logger.info("Application closing")
            event.accept()
        except Exception as e:
            self.logger.error(f"Error during application close: {e}")
            event.accept()  # Close anyway to prevent hanging

    def _show_error(self, title: str, message: str) -> None:
        """Show error message to user."""
        QMessageBox.critical(self, title, message)

    def _show_info(self, title: str, message: str) -> None:
        """Show information message to user."""
        QMessageBox.information(self, title, message)

    # Placeholder methods for menu actions (to be implemented in later tasks)
    def _on_new(self) -> None:
        """Handle New action."""
        self.logger.info("New action triggered")

        # Clear current scene
        self._scene.clear()

        # Reset current file path
        self._current_file_path = None

        # Update window title
        self.setWindowTitle("Digital Whiteboard - New")

        # Reset scene modified flag and stop auto-save
        self._scene_modified = False
        if hasattr(self, "_auto_save_timer") and self._auto_save_timer.isActive():
            self._auto_save_timer.stop()

        self.logger.info("New whiteboard created successfully")

    def _on_open(self) -> None:
        """Handle Open action."""
        self.logger.info("Open action triggered")
        # TODO: Implement in later tasks

    def _on_load(self) -> None:
        """Handle Load/Open action."""
        self.logger.info("Load action triggered")

        # Show file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Whiteboard",
            str(Path.home()),
            f"Whiteboard Files (*{SessionManager.FILE_EXTENSION});;All Files (*)",
        )

        if file_path:
            self._load_document(Path(file_path))

    def _load_document(self, file_path: Path) -> bool:
        """
        Load a document from the given path.

        Args:
            file_path: Path to the whiteboard file

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            # Load session data
            session_data = self._session_manager.load_session_from_file(file_path)

            # Clear current scene
            self._scene.clear()

            # Deserialize and populate scene
            self._session_manager.deserialize_scene_data(
                session_data, self._scene, self._canvas
            )

            # Update current file path
            self._current_file_path = file_path

            # Save to state manager as last document
            self._state_manager.set_last_document_path(str(file_path))

            # Update window title
            self.setWindowTitle(f"Digital Whiteboard - {file_path.name}")

            # Reset scene modified flag and start auto-save
            self._scene_modified = False
            if self._auto_save_enabled:
                self.start_auto_save()

            self.logger.info(f"Successfully loaded whiteboard from: {file_path}")
            return True

        except SessionError as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load whiteboard:\n{e}")
            self.logger.error(f"Failed to load whiteboard: {e}")
            return False
        except Exception as e:
            QMessageBox.critical(
                self, "Load Error", f"Unexpected error while loading:\n{e}"
            )
            self.logger.error(f"Unexpected error while loading: {e}")
            return False

    def _on_save(self) -> None:
        """Handle Save action."""
        self.logger.info("Save action triggered")

        if self._current_file_path:
            # Save to current file
            self._save_to_file(self._current_file_path)
        else:
            # No current file, show Save As dialog
            self._on_save_as()

    def _on_save_as(self) -> None:
        """Handle Save As action."""
        self.logger.info("Save As action triggered")

        # Show file dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Whiteboard",
            str(Path.home() / f"untitled{SessionManager.FILE_EXTENSION}"),
            f"Whiteboard Files (*{SessionManager.FILE_EXTENSION});;All Files (*)",
        )

        if file_path:
            self._save_to_file(Path(file_path))

    def _save_to_file(self, file_path: Path) -> None:
        """Save the current whiteboard to a file."""
        try:
            # Serialize scene data
            session_data = self._session_manager.serialize_scene_data(
                self._scene, self._canvas
            )

            # Save to file
            self._session_manager.save_session_to_file(session_data, file_path)

            # Update current file path
            self._current_file_path = file_path

            # Save to state manager as last document
            self._state_manager.set_last_document_path(str(file_path))

            # Update window title
            self.setWindowTitle(f"Digital Whiteboard - {file_path.name}")

            # Reset scene modified flag and start auto-save
            self._scene_modified = False
            if self._auto_save_enabled:
                self.start_auto_save()

            self.logger.info(f"Successfully saved whiteboard to: {file_path}")

        except SessionError as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save whiteboard:\n{e}")
            self.logger.error(f"Failed to save whiteboard: {e}")
        except Exception as e:
            QMessageBox.critical(
                self, "Save Error", f"Unexpected error while saving:\n{e}"
            )
            self.logger.error(f"Unexpected error while saving: {e}")

    def _on_session_saved(self, file_path: str) -> None:
        """Handle session saved signal."""
        self.statusBar().showMessage(f"Saved: {Path(file_path).name}", 3000)

    def _on_session_loaded(self, file_path: str) -> None:
        """Handle session loaded signal."""
        self.statusBar().showMessage(f"Loaded: {Path(file_path).name}", 3000)

    def _on_session_error(self, error_message: str) -> None:
        """Handle session error signal."""
        self.statusBar().showMessage(f"Error: {error_message}", 5000)

    def _on_undo(self) -> None:
        """Handle Undo action."""
        self.logger.info("Undo action triggered")
        try:
            self._canvas.undo()
            self.statusBar().showMessage("Undid last action", 2000)
        except Exception as e:
            self.logger.error(f"Undo failed: {e}")

    def _on_redo(self) -> None:
        """Handle Redo action."""
        self.logger.info("Redo action triggered")
        try:
            self._canvas.redo()
            self.statusBar().showMessage("Redid last action", 2000)
        except Exception as e:
            self.logger.error(f"Redo failed: {e}")

    def _on_cut(self) -> None:
        """Handle Cut action."""
        self.logger.info("Cut action triggered")
        # TODO: Implement in later tasks

    def _on_copy(self) -> None:
        """Handle Copy action."""
        self.logger.info("Copy action triggered")
        # TODO: Implement in later tasks

    def _on_paste(self) -> None:
        """Handle Paste action."""
        self.logger.info("Paste action triggered")
        # TODO: Implement in later tasks

    def _on_select_all(self) -> None:
        """Handle Select All action."""
        self.logger.info("Select All action triggered")
        # TODO: Implement in later tasks

    def _on_zoom_in(self) -> None:
        """Handle Zoom In action."""
        self.logger.info("Zoom In action triggered")
        self._canvas.zoom_in()

    def _on_zoom_out(self) -> None:
        """Handle Zoom Out action."""
        self.logger.info("Zoom Out action triggered")
        self._canvas.zoom_out()

    def _on_actual_size(self) -> None:
        """Handle Actual Size action."""
        self.logger.info("Actual Size action triggered")
        self._canvas.reset_zoom()

    def _on_fit_window(self) -> None:
        """Handle Fit to Window action."""
        self.logger.info("Fit to Window action triggered")
        self._canvas.fit_content_in_view()

    def _on_center_content(self) -> None:
        """Handle Center on Content action."""
        self.logger.info("Center on Content action triggered")
        self._canvas.center_on_content()

    def _show_pan_help(self) -> None:
        """Show pan navigation help dialog."""
        help_text = """Pan Navigation Shortcuts:

🔹 Arrow Keys: Pan in the corresponding direction
   • ← Left Arrow: Pan left
   • → Right Arrow: Pan right
   • ↑ Up Arrow: Pan up
   • ↓ Down Arrow: Pan down

🔹 Space + Drag: Hold Space key and drag with mouse to pan freely

🔹 Middle Mouse Button: Click and drag to pan

🔹 Shift + Left Click: Alternative pan mode

🔹 Ctrl+H: Center view on all content

These shortcuts work when the canvas has focus."""

        QMessageBox.information(self, "Pan Navigation Help", help_text)
        self.logger.debug("Pan navigation help dialog shown")

    def _on_scene_changed(self) -> None:
        """Handle scene modification for auto-save tracking."""
        self._scene_modified = True
        if self._auto_save_enabled and self._current_file_path:
            # Start or restart the auto-save timer
            self._auto_save_timer.start(self._auto_save_interval)
            self.logger.debug("Scene modified, auto-save timer started")

    def _auto_save(self) -> None:
        """Perform auto-save if scene has been modified."""
        if not self._scene_modified or not self._current_file_path:
            return

        # Use QTimer.singleShot for background saving to prevent UI blocking
        QTimer.singleShot(0, self._perform_auto_save)

    def _perform_auto_save(self) -> None:
        """Perform the actual auto-save operation in the background."""
        try:
            self.logger.info(f"Auto-saving to {self._current_file_path}")
            # Show auto-save in progress indicator
            self.statusBar().showMessage("Auto-saving...", 0)

            # Serialize scene data
            session_data = self._session_manager.serialize_scene_data(
                self._scene, self._canvas
            )
            # Save to file
            self._session_manager.save_session_to_file(
                session_data, self._current_file_path
            )

            # Reset modified flag
            self._scene_modified = False

            # Update status message
            self.statusBar().showMessage("Auto-saved successfully", 2000)
            self.logger.info("Auto-save completed successfully")
        except SessionError as e:
            self.logger.warning(f"Auto-save failed: {e}")
            self.statusBar().showMessage(f"Auto-save failed: {e}", 5000)
        except Exception as e:
            self.logger.error(f"Unexpected error during auto-save: {e}")
            self.statusBar().showMessage(f"Auto-save failed: {e}", 5000)

    def start_auto_save(self) -> None:
        """Start the auto-save timer if enabled."""
        self._auto_save_enabled = True
        if self._auto_save_enabled and self._current_file_path:
            self._auto_save_timer.start(self._auto_save_interval)
            self.logger.info(
                f"Auto-save started with interval {self._auto_save_interval} ms"
            )

    def stop_auto_save(self) -> None:
        """Stop the auto-save timer."""
        self._auto_save_enabled = False
        self._auto_save_timer.stop()
        self.logger.info("Auto-save stopped")

    def set_auto_save_interval(self, interval_ms: int) -> None:
        """Set the auto-save interval in milliseconds."""
        self._auto_save_interval = interval_ms
        # If timer is currently active, restart it with new interval
        if self._auto_save_timer.isActive():
            self._auto_save_timer.start(interval_ms)
        self.logger.info(f"Auto-save interval set to {interval_ms} ms")

    def _setup_navigation_panel(self) -> None:
        """Set up the navigation panel as a dockable widget."""
        try:
            # Add navigation panel as dockable widget
            self.addDockWidget(
                Qt.DockWidgetArea.RightDockWidgetArea, self._navigation_panel
            )

            # Initially show the navigation panel
            self._navigation_panel.show()

            self.logger.info("Navigation panel setup completed")
        except Exception as e:
            self.logger.error(f"Error setting up navigation panel: {e}")

    def _setup_navigation_connections(self) -> None:
        """Set up connections between navigation panel and canvas."""
        try:
            # Connect navigation panel signals to canvas methods
            self._navigation_panel.zoom_changed.connect(
                self._on_navigation_zoom_changed
            )
            self._navigation_panel.navigate_to_position.connect(
                self._on_navigate_to_position
            )
            self._navigation_panel.fit_to_window_requested.connect(self._on_fit_window)
            self._navigation_panel.center_on_content_requested.connect(
                self._on_center_content
            )

            # Connect canvas signals to navigation panel updates
            if hasattr(self._canvas, "zoom_changed"):
                self._canvas.zoom_changed.connect(
                    self._navigation_panel.update_zoom_display
                )
            if hasattr(self._canvas, "pan_changed"):
                self._canvas.pan_changed.connect(
                    self._navigation_panel.update_viewport_indicator
                )
            if hasattr(self._canvas, "viewport_changed"):
                self._canvas.viewport_changed.connect(
                    self._navigation_panel.update_viewport_indicator
                )

            # Connect scene changes to minimap updates
            self._scene.changed.connect(self._navigation_panel.schedule_minimap_update)

            self.logger.info("Navigation panel connections setup completed")
        except Exception as e:
            self.logger.error(f"Error setting up navigation connections: {e}")

    def _load_last_document(self) -> None:
        """
        Load the last document if available.

        This is called during application startup to restore the last document
        the user was working on.
        """
        last_doc_path = self._state_manager.get_last_document_path()

        if last_doc_path:
            file_path = Path(last_doc_path)
            if file_path.exists():
                self.logger.info(f"Loading last document: {file_path}")
                self._load_document(file_path)
            else:
                self.logger.info(
                    f"Last document not found, starting with new whiteboard: {file_path}"
                )
        else:
            self.logger.debug("No last document found, starting with new whiteboard")

    def _on_navigation_zoom_changed(self, zoom_level: float) -> None:
        """Handle zoom changes from navigation panel."""
        try:
            # Convert percentage to scale factor
            scale_factor = zoom_level / 100.0

            # Apply zoom to canvas
            if hasattr(self._canvas, "set_zoom_level"):
                self._canvas.set_zoom_level(scale_factor)
            else:
                # Fallback to transform-based zoom
                self._canvas.resetTransform()
                self._canvas.scale(scale_factor, scale_factor)

            self.logger.debug(f"Navigation zoom changed to {zoom_level}%")
        except Exception as e:
            self.logger.error(f"Error handling navigation zoom change: {e}")

    def _on_navigate_to_position(self, position: QPointF) -> None:
        """Handle navigation to specific position from minimap."""
        try:
            # Center the canvas view on the specified position
            self._canvas.centerOn(position)

            self.logger.debug(f"Navigated to position: {position}")
        except Exception as e:
            self.logger.error(f"Error navigating to position: {e}")
