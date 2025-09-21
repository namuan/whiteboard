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
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QKeySequence
from pathlib import Path

from .utils.logging_config import get_logger
from .canvas import WhiteboardScene, WhiteboardCanvas
from .session_manager import SessionManager, SessionError


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

        # Initialize session manager
        self._session_manager = SessionManager()
        self._setup_session_connections()

        # Initialize auto-save functionality
        self._auto_save_timer = QTimer()
        self._auto_save_timer.timeout.connect(self._auto_save)
        self._auto_save_interval = 30000  # 30 seconds in milliseconds
        self._auto_save_enabled = True
        self._scene_modified = False

        # Initialize UI components
        self._setup_window()
        self._setup_central_widget()
        self._setup_menu_bar()
        self._setup_toolbar()
        self._setup_status_bar()
        self._setup_canvas_connections()

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
        edit_menu.addAction(undo_action)

        # Redo action
        redo_action = QAction("&Redo", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.setStatusTip("Redo the last undone action")
        redo_action.triggered.connect(self._on_redo)
        edit_menu.addAction(redo_action)

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
        """Create and configure the status bar."""
        status_bar = QStatusBar()
        status_bar.showMessage("Ready • Double-click empty area to create note")
        self.setStatusBar(status_bar)

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

        # Connect note creation signals
        self._canvas.note_created.connect(self._on_note_created)

        # Connect note hover signals for user hints
        self._canvas.note_hover_hint.connect(self._on_note_hover_hint)
        self._canvas.note_hover_ended.connect(self._on_note_hover_ended)

        # Connect scene modification signals for auto-save
        self._scene.changed.connect(self._on_scene_changed)

    def _on_zoom_changed(self, zoom_factor: float) -> None:
        """Handle zoom level changes."""
        zoom_percent = int(zoom_factor * 100)
        self.statusBar().showMessage(f"Zoom: {zoom_percent}%")
        self.logger.debug(f"Zoom changed to {zoom_percent}%")

    def _on_pan_changed(self, center_point) -> None:
        """Handle pan position changes."""
        # Update status bar with position info if needed
        pass

    def _on_note_created(self, note) -> None:
        """Handle note creation events."""
        self.statusBar().showMessage("Note created - Double-click to edit", 3000)
        self.logger.debug(f"Note created at position {note.pos()}")

    def _on_note_hover_hint(self, hint_text: str) -> None:
        """Handle note hover hint events."""
        self.statusBar().showMessage(hint_text)

    def _on_note_hover_ended(self) -> None:
        """Handle note hover end events."""
        # Show default zoom info or ready message
        zoom_percent = int(self._canvas.get_zoom_factor() * 100)
        self.statusBar().showMessage(
            f"Zoom: {zoom_percent}% • Double-click empty area to create note"
        )

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

    def keyPressEvent(self, event):
        """Handle key press events."""
        # F11 for fullscreen toggle
        if event.key() == Qt.Key.Key_F11:
            self.toggle_fullscreen()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """Handle window close event."""
        try:
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
            "Whiteboard Files (*.json);;All Files (*)",
        )

        if file_path:
            try:
                # Load session data
                session_data = self._session_manager.load_session_from_file(
                    Path(file_path)
                )

                # Clear current scene
                self._scene.clear()

                # Deserialize and populate scene
                self._session_manager.deserialize_scene_data(
                    session_data, self._scene, self._canvas
                )

                # Update current file path
                self._current_file_path = Path(file_path)

                # Update window title
                self.setWindowTitle(
                    f"Digital Whiteboard - {self._current_file_path.name}"
                )

                # Reset scene modified flag and start auto-save
                self._scene_modified = False
                if self._auto_save_enabled:
                    self.start_auto_save()

                self.logger.info(f"Successfully loaded whiteboard from: {file_path}")

            except SessionError as e:
                QMessageBox.critical(
                    self, "Load Error", f"Failed to load whiteboard:\n{e}"
                )
                self.logger.error(f"Failed to load whiteboard: {e}")
            except Exception as e:
                QMessageBox.critical(
                    self, "Load Error", f"Unexpected error while loading:\n{e}"
                )
                self.logger.error(f"Unexpected error while loading: {e}")

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
            str(Path.home() / "untitled.json"),
            "Whiteboard Files (*.json);;All Files (*)",
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
        # TODO: Implement in later tasks

    def _on_redo(self) -> None:
        """Handle Redo action."""
        self.logger.info("Redo action triggered")
        # TODO: Implement in later tasks

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
            self._scene_modified = False
            self._auto_save_timer.stop()

            # Show success indicator
            self.statusBar().showMessage("Auto-saved successfully", 2000)
            self.logger.debug("Auto-save completed successfully")
        except SessionError as e:
            self.logger.warning(f"Auto-save failed: {e}")
            # Show error notification to user
            self.statusBar().showMessage(f"Auto-save failed: {e}", 5000)
        except Exception as e:
            self.logger.error(f"Unexpected error during auto-save: {e}")
            # Show generic error notification
            self.statusBar().showMessage("Auto-save failed: Unexpected error", 5000)

    def start_auto_save(self) -> None:
        """Enable auto-save functionality."""
        self._auto_save_enabled = True
        self.logger.info("Auto-save enabled")

    def stop_auto_save(self) -> None:
        """Disable auto-save functionality."""
        self._auto_save_enabled = False
        self._auto_save_timer.stop()
        self.logger.info("Auto-save disabled")

    def set_auto_save_interval(self, interval_ms: int) -> None:
        """Set the auto-save interval in milliseconds."""
        self._auto_save_interval = interval_ms
        self.logger.info(f"Auto-save interval set to {interval_ms}ms")

        # Restart timer with new interval if it's running
        if self._auto_save_timer.isActive():
            self._auto_save_timer.start(self._auto_save_interval)
