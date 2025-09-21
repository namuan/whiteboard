"""
Session manager for the Digital Whiteboard application.

This module contains the SessionManager class which handles session persistence,
data serialization, and file operations for saving and loading whiteboard sessions.
"""

import json
from pathlib import Path
from typing import Any
from datetime import datetime

from PyQt6.QtCore import QObject, pyqtSignal, QPointF, QRectF
from PyQt6.QtWidgets import QGraphicsScene
from PyQt6.QtGui import QColor

from .utils.logging_config import get_logger
from .utils.config_paths import get_app_data_dir, ensure_app_directories
from .utils.exceptions import WhiteboardError
from .note_item import NoteItem
from .connection_item import ConnectionItem


class SessionError(WhiteboardError):
    """Exception raised for session-related errors."""

    pass


class SessionManager(QObject):
    """
    Manages session persistence and file operations for the whiteboard.

    Provides functionality for:
    - Data serialization for notes, connections, and groups
    - JSON-based file format for session storage
    - Data validation and error handling for file operations
    - Session metadata management

    Requirements addressed:
    - 7.1: Data serialization for notes, connections, and groups
    - 8.1: JSON-based file format for session storage
    - 8.3: Data validation and error handling for file operations
    """

    # Signals
    session_saved = pyqtSignal(str)  # file_path
    session_loaded = pyqtSignal(str)  # file_path
    session_error = pyqtSignal(str)  # error_message

    # File format version for compatibility
    FILE_FORMAT_VERSION = "1.0"

    def __init__(self, parent=None):
        """
        Initialize the session manager.

        Args:
            parent: Parent QObject (optional)
        """
        super().__init__(parent)
        self.logger = get_logger(__name__)

        # Setup storage paths
        self._setup_storage_paths()

        self.logger.info("SessionManager initialized successfully")

    def _setup_storage_paths(self) -> None:
        """Setup storage directory paths."""
        try:
            self._data_dir = get_app_data_dir()
            self._sessions_dir = self._data_dir / "sessions"
            ensure_app_directories()

            # Ensure sessions directory exists
            self._sessions_dir.mkdir(parents=True, exist_ok=True)

            self.logger.debug(f"Sessions directory: {self._sessions_dir}")

        except Exception as e:
            self.logger.error(f"Failed to setup storage paths: {e}")
            raise SessionError(f"Failed to setup storage paths: {e}")

    def serialize_scene_data(
        self, scene: QGraphicsScene, canvas=None
    ) -> dict[str, Any]:
        """
        Serialize scene data including notes, connections, and canvas state.

        Args:
            scene: QGraphicsScene to serialize
            canvas: WhiteboardCanvas for getting view state (optional)

        Returns:
            Dictionary containing serialized scene data

        Raises:
            SessionError: If serialization fails
        """
        try:
            self.logger.debug("Starting scene data serialization")

            # Get all items from the scene
            items = scene.items()

            # Separate items by type
            notes = [item for item in items if isinstance(item, NoteItem)]
            connections = [item for item in items if isinstance(item, ConnectionItem)]

            # Serialize notes
            serialized_notes = []
            for note in notes:
                note_data = self._serialize_note(note)
                serialized_notes.append(note_data)

            # Serialize connections
            serialized_connections = []
            for connection in connections:
                connection_data = self._serialize_connection(connection)
                serialized_connections.append(connection_data)

            # Get scene bounds
            scene_rect = scene.sceneRect()

            # Get canvas state if available
            canvas_state = {}
            if canvas:
                center_point = canvas.get_center_point()
                canvas_state = {
                    "zoom_factor": canvas.get_zoom_factor(),
                    "center_x": center_point.x(),
                    "center_y": center_point.y(),
                }

            # Create session data structure
            session_data = {
                "version": self.FILE_FORMAT_VERSION,
                "created_at": datetime.now().isoformat(),
                "scene": {
                    "rect": {
                        "x": scene_rect.x(),
                        "y": scene_rect.y(),
                        "width": scene_rect.width(),
                        "height": scene_rect.height(),
                    }
                },
                "canvas_state": canvas_state,
                "notes": serialized_notes,
                "connections": serialized_connections,
                "groups": [],  # TODO: Implement groups serialization when groups are added
                "metadata": {
                    "note_count": len(serialized_notes),
                    "connection_count": len(serialized_connections),
                    "group_count": 0,
                },
            }

            self.logger.info(
                f"Serialized {len(serialized_notes)} notes and {len(serialized_connections)} connections"
            )
            return session_data

        except Exception as e:
            self.logger.error(f"Failed to serialize scene data: {e}")
            raise SessionError(f"Failed to serialize scene data: {e}")

    def _serialize_note(self, note: NoteItem) -> dict[str, Any]:
        """
        Serialize a single note item.

        Args:
            note: NoteItem to serialize

        Returns:
            Dictionary containing serialized note data
        """
        try:
            # Get note position
            pos = note.pos()

            # Get note text
            text = note.get_text()

            # Get note style properties and serialize QColor objects
            style = note.get_style()
            serialized_style = self._serialize_style(style)

            note_data = {
                "id": note.get_note_id(),
                "text": text,
                "position": {"x": pos.x(), "y": pos.y()},
                "style": serialized_style,
            }

            return note_data

        except Exception as e:
            self.logger.error(f"Failed to serialize note: {e}")
            raise SessionError(f"Failed to serialize note: {e}")

    def _serialize_connection(self, connection: ConnectionItem) -> dict[str, Any]:
        """
        Serialize a single connection item.

        Args:
            connection: ConnectionItem to serialize

        Returns:
            Dictionary containing serialized connection data
        """
        try:
            connection_data = connection.get_connection_data()
            # Serialize any QColor objects in the connection style
            if "style" in connection_data:
                connection_data["style"] = self._serialize_style(
                    connection_data["style"]
                )
            return connection_data

        except Exception as e:
            self.logger.error(f"Failed to serialize connection: {e}")
            raise SessionError(f"Failed to serialize connection: {e}")

    def _serialize_style(self, style: dict[str, Any]) -> dict[str, Any]:
        """Convert QColor objects and Qt enums to serializable values for JSON serialization."""

        serialized = {}
        for key, value in style.items():
            if isinstance(value, QColor):
                serialized[key] = value.name()  # Convert to hex string
            elif hasattr(value, "value") and hasattr(value, "name"):
                # Handle Qt enums (like PenStyle)
                serialized[key] = value.value
            else:
                serialized[key] = value
        return serialized

    def _deserialize_style(self, style_data: dict[str, Any]) -> dict[str, Any]:
        """Convert JSON data back to style dict with QColor objects and Qt enums."""
        from PyQt6.QtCore import Qt

        deserialized = {}
        for key, value in style_data.items():
            if key.endswith("_color") and isinstance(value, str):
                deserialized[key] = QColor(value)  # Convert from hex string
            elif key == "line_style" and isinstance(value, int):
                # Convert integer back to PenStyle enum
                deserialized[key] = Qt.PenStyle(value)
            else:
                deserialized[key] = value
        return deserialized

    def deserialize_scene_data(
        self, session_data: dict[str, Any], scene: QGraphicsScene, canvas=None
    ) -> None:
        """
        Deserialize session data and populate the scene.

        Args:
            session_data: Dictionary containing serialized session data
            scene: QGraphicsScene to populate
            canvas: WhiteboardCanvas for restoring view state (optional)

        Raises:
            SessionError: If deserialization fails
        """
        try:
            self.logger.debug("Starting scene data deserialization")

            # Validate session data format
            self._validate_session_data(session_data)

            # Clear existing scene content
            scene.clear()

            # Restore scene bounds
            scene_data = session_data.get("scene", {})
            scene_rect_data = scene_data.get("rect", {})
            if scene_rect_data:
                scene_rect = QRectF(
                    scene_rect_data.get("x", 0),
                    scene_rect_data.get("y", 0),
                    scene_rect_data.get("width", 10000),
                    scene_rect_data.get("height", 10000),
                )
                scene.setSceneRect(scene_rect)

            # Restore canvas state if available
            canvas_state = session_data.get("canvas_state", {})
            if canvas and canvas_state:
                # Restore zoom
                zoom_factor = canvas_state.get("zoom_factor", 1.0)
                canvas.set_zoom(zoom_factor)

                # Restore pan position
                center_x = canvas_state.get("center_x", 0.0)
                center_y = canvas_state.get("center_y", 0.0)
                canvas.centerOn(center_x, center_y)

                self.logger.debug(
                    f"Restored canvas state: zoom={zoom_factor:.2f}, center=({center_x:.1f}, {center_y:.1f})"
                )

            # Create mapping for note IDs to recreated notes
            note_id_map = {}

            # Deserialize notes first
            notes_data = session_data.get("notes", [])
            for note_data in notes_data:
                note = self._deserialize_note(note_data)
                scene.addItem(note)
                note_id_map[note.get_note_id()] = note

            # Deserialize connections
            connections_data = session_data.get("connections", [])
            for connection_data in connections_data:
                try:
                    connection = self._deserialize_connection(
                        connection_data, note_id_map
                    )
                    if connection:  # Only add if both notes exist
                        scene.addItem(connection)
                except Exception as e:
                    self.logger.error(f"Failed to deserialize connection: {e}")
                    continue

            # TODO: Deserialize groups when groups are implemented

            self.logger.info(
                f"Deserialized {len(notes_data)} notes and {len(connections_data)} connections"
            )

        except Exception as e:
            self.logger.error(f"Failed to deserialize scene data: {e}")
            raise SessionError(f"Failed to deserialize scene data: {e}")

    def _deserialize_note(self, note_data: dict[str, Any]) -> NoteItem:
        """
        Deserialize a single note item.

        Args:
            note_data: Dictionary containing serialized note data

        Returns:
            Recreated NoteItem
        """
        try:
            # Extract position
            position_data = note_data.get("position", {"x": 0, "y": 0})
            position = QPointF(position_data["x"], position_data["y"])

            # Create note with text and position
            text = note_data.get("text", "")
            note = NoteItem(text, position)

            # Apply style if present
            if "style" in note_data:
                deserialized_style = self._deserialize_style(note_data["style"])
                note.set_style(deserialized_style)

            # Set note ID if present
            if "id" in note_data:
                note._note_id = note_data["id"]

            return note

        except Exception as e:
            self.logger.error(f"Failed to deserialize note: {e}")
            # Return a default note if deserialization fails
            return NoteItem("Error loading note", QPointF(0, 0))

    def _deserialize_connection(
        self, connection_data: dict[str, Any], note_id_map: dict[int, NoteItem]
    ) -> ConnectionItem | None:
        """
        Deserialize a single connection item.

        Args:
            connection_data: Dictionary containing serialized connection data
            note_id_map: Mapping of note IDs to recreated NoteItem objects

        Returns:
            Recreated ConnectionItem or None if referenced notes don't exist
        """
        try:
            # Get referenced notes
            start_note_id = connection_data.get("start_note_id")
            end_note_id = connection_data.get("end_note_id")

            if start_note_id is None or end_note_id is None:
                self.logger.warning("Connection missing note references, skipping")
                return None

            start_note = note_id_map.get(start_note_id)
            end_note = note_id_map.get(end_note_id)

            if start_note is None or end_note is None:
                self.logger.warning(
                    "Connection references non-existent notes, skipping"
                )
                return None

            # Create new connection
            connection = ConnectionItem(start_note, end_note)

            # Restore style
            style_data = connection_data.get("style", {})
            if style_data:
                deserialized_style = self._deserialize_style(style_data)
                connection.set_style(deserialized_style)

            # Restore other properties
            connection.setZValue(connection_data.get("z_value", 0))
            connection.setVisible(connection_data.get("visible", True))
            connection.setEnabled(connection_data.get("enabled", True))

            return connection

        except Exception as e:
            self.logger.error(f"Failed to deserialize connection: {e}")
            raise SessionError(f"Failed to deserialize connection: {e}")

    def _validate_session_data(self, session_data: dict[str, Any]) -> None:
        """
        Validate session data format and structure.

        Args:
            session_data: Dictionary containing session data to validate

        Raises:
            SessionError: If validation fails
        """
        try:
            # Check required top-level keys
            required_keys = ["version", "notes", "connections"]
            for key in required_keys:
                if key not in session_data:
                    raise SessionError(f"Missing required key: {key}")

            # Check version compatibility
            version = session_data.get("version")
            if version != self.FILE_FORMAT_VERSION:
                self.logger.warning(
                    f"File format version mismatch: {version} vs {self.FILE_FORMAT_VERSION}"
                )
                # For now, continue with loading - in future versions, implement migration

            # Validate notes structure
            notes = session_data.get("notes", [])
            if not isinstance(notes, list):
                raise SessionError("Notes data must be a list")

            # Validate connections structure
            connections = session_data.get("connections", [])
            if not isinstance(connections, list):
                raise SessionError("Connections data must be a list")

            self.logger.debug("Session data validation passed")

        except Exception as e:
            self.logger.error(f"Session data validation failed: {e}")
            raise SessionError(f"Session data validation failed: {e}")

    def save_session_to_file(
        self, session_data: dict[str, Any], file_path: Path
    ) -> None:
        """
        Save session data to a JSON file.

        Args:
            session_data: Dictionary containing session data
            file_path: Path to save the session file

        Raises:
            SessionError: If saving fails
        """
        try:
            self.logger.debug(f"Saving session to file: {file_path}")

            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write JSON data to file
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Session saved successfully to: {file_path}")
            self.session_saved.emit(str(file_path))

        except Exception as e:
            error_msg = f"Failed to save session to file: {e}"
            self.logger.error(error_msg)
            self.session_error.emit(error_msg)
            raise SessionError(error_msg)

    def load_session_from_file(self, file_path: Path) -> dict[str, Any]:
        """
        Load session data from a JSON file.

        Args:
            file_path: Path to the session file

        Returns:
            Dictionary containing loaded session data

        Raises:
            SessionError: If loading fails
        """
        try:
            self.logger.debug(f"Loading session from file: {file_path}")

            # Check if file exists
            if not file_path.exists():
                raise SessionError(f"Session file does not exist: {file_path}")

            # Read JSON data from file
            with open(file_path, encoding="utf-8") as f:
                session_data = json.load(f)

            # Validate loaded data
            self._validate_session_data(session_data)

            self.logger.info(f"Session loaded successfully from: {file_path}")
            self.session_loaded.emit(str(file_path))

            return session_data

        except Exception as e:
            error_msg = f"Failed to load session from file: {e}"
            self.logger.error(error_msg)
            self.session_error.emit(error_msg)
            raise SessionError(error_msg)

    def get_default_session_path(self, session_name: str) -> Path:
        """
        Get the default path for a session file.

        Args:
            session_name: Name of the session (without extension)

        Returns:
            Path to the session file
        """
        # Ensure session name has .json extension
        if not session_name.endswith(".json"):
            session_name += ".json"

        return self._sessions_dir / session_name

    def list_saved_sessions(self) -> list[tuple[str, Path, datetime]]:
        """
        List all saved session files.

        Returns:
            List of tuples containing (session_name, file_path, modified_time)
        """
        try:
            sessions = []

            if self._sessions_dir.exists():
                for file_path in self._sessions_dir.glob("*.json"):
                    try:
                        # Get file modification time
                        modified_time = datetime.fromtimestamp(
                            file_path.stat().st_mtime
                        )
                        session_name = file_path.stem
                        sessions.append((session_name, file_path, modified_time))
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to get info for session file {file_path}: {e}"
                        )

            # Sort by modification time (newest first)
            sessions.sort(key=lambda x: x[2], reverse=True)

            return sessions

        except Exception as e:
            self.logger.error(f"Failed to list saved sessions: {e}")
            return []
