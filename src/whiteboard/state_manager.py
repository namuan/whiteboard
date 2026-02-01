"""
Application state manager for the Digital Whiteboard application.

This module provides the AppStateManager class which handles application-level
state persistence, such as the last opened document path.

State is stored in the OS-recommended location:
- Windows: %APPDATA%/DigitalWhiteboard/app_state.json
- macOS: ~/Library/Application Support/DigitalWhiteboard/app_state.json
- Linux: ~/.config/DigitalWhiteboard/app_state.json
"""

import json

from PyQt6.QtCore import QObject, pyqtSignal

from .utils.logging_config import get_logger
from .utils.config_paths import get_app_state_file_path, ensure_app_directories


class StateError(Exception):
    """Exception raised for state-related errors."""

    pass


class AppStateManager(QObject):
    """
    Manages application state persistence.

    Provides functionality for:
    - Storing and retrieving the last opened document path
    - Persisting application state across sessions
    - Handling state file creation and updates

    The state file is stored in the OS-recommended configuration directory,
    ensuring proper integration with the host operating system.
    """

    # Signals for state changes
    last_document_changed = pyqtSignal(str)  # file_path
    state_loaded = pyqtSignal()  # Emitted when state is loaded

    # Default state values
    DEFAULT_STATE = {
        "version": "1.0",
        "last_document_path": None,
        "window_geometry": None,
        "window_state": None,
    }

    def __init__(self, parent=None):
        """
        Initialize the application state manager.

        Args:
            parent: Parent QObject (optional)
        """
        super().__init__(parent)
        self.logger = get_logger(__name__)

        # Ensure configuration directory exists
        ensure_app_directories()

        # Get the state file path
        self._state_file_path = get_app_state_file_path()

        # Current state data
        self._state = self.DEFAULT_STATE.copy()

        # Load existing state
        self._load_state()

        self.logger.info("AppStateManager initialized successfully")

    def _load_state(self) -> None:
        """Load state from the state file if it exists."""
        try:
            if self._state_file_path.exists():
                with open(self._state_file_path, encoding="utf-8") as f:
                    loaded_state = json.load(f)

                # Merge loaded state with defaults
                self._state = {**self.DEFAULT_STATE, **loaded_state}

                self.logger.info(f"State loaded from: {self._state_file_path}")
                self.state_loaded.emit()
            else:
                self.logger.debug("No existing state file found, using defaults")

        except json.JSONDecodeError as e:
            self.logger.warning(f"Invalid state file format: {e}, using defaults")
            self._state = self.DEFAULT_STATE.copy()
        except Exception as e:
            self.logger.warning(f"Failed to load state: {e}, using defaults")
            self._state = self.DEFAULT_STATE.copy()

    def _save_state(self) -> None:
        """Save current state to the state file."""
        try:
            # Ensure parent directory exists
            self._state_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write state to file
            with open(self._state_file_path, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2, ensure_ascii=False)

            self.logger.debug(f"State saved to: {self._state_file_path}")

        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
            raise StateError(f"Failed to save state: {e}")

    def get_last_document_path(self) -> str | None:
        """
        Get the path to the last opened document.

        Returns:
            Path string to the last document, or None if no document has been opened
        """
        return self._state.get("last_document_path")

    def set_last_document_path(self, file_path: str) -> None:
        """
        Set the path to the last opened document.

        Args:
            file_path: Path string to the last document
        """
        old_path = self._state.get("last_document_path")
        self._state["last_document_path"] = file_path

        if old_path != file_path:
            self._save_state()
            self.last_document_changed.emit(file_path)
            self.logger.info(f"Last document updated to: {file_path}")

    def get_window_geometry(self) -> list | None:
        """
        Get the saved window geometry.

        Returns:
            List representing window geometry [x, y, width, height], or None
        """
        return self._state.get("window_geometry")

    def set_window_geometry(self, geometry: list) -> None:
        """
        Set the window geometry.

        Args:
            geometry: List [x, y, width, height] representing window geometry
        """
        self._state["window_geometry"] = geometry
        self._save_state()
        self.logger.debug("Window geometry saved")

    def get_window_state(self) -> bytes | None:
        """
        Get the saved window state (maximized, fullscreen, etc.).

        Returns:
            QByteArray bytes representing window state, or None
        """
        return self._state.get("window_state")

    def set_window_state(self, state: bytes) -> None:
        """
        Set the window state.

        Args:
            state: QByteArray bytes representing window state
        """
        self._state["window_state"] = state
        self._save_state()
        self.logger.debug("Window state saved")

    def clear_last_document(self) -> None:
        """Clear the last document path."""
        self.set_last_document_path(None)

    def get_state(self) -> dict:
        """
        Get the complete state dictionary.

        Returns:
            Copy of the current state dictionary
        """
        return self._state.copy()

    def reset_state(self) -> None:
        """Reset state to defaults and save."""
        self._state = self.DEFAULT_STATE.copy()
        self._save_state()
        self.logger.info("State reset to defaults")
