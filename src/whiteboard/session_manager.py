"""
Session manager for the Digital Whiteboard application.

This module contains the SessionManager class which handles session persistence,
data serialization, and file operations for saving and loading whiteboard sessions.
"""

import json
import base64
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
from .image_item import ImageItem


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

    # File format version for session files
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

            # Serialize all scene items
            serialized_notes, serialized_connections, serialized_images = (
                self._serialize_scene_items(scene)
            )

            # Get scene and canvas state
            scene_rect = scene.sceneRect()
            canvas_state = self._get_canvas_state(canvas)

            # Create session data structure
            session_data = self._create_session_data_structure(
                serialized_notes,
                serialized_connections,
                serialized_images,
                scene_rect,
                canvas_state,
            )

            self.logger.info(
                f"Serialized {len(serialized_notes)} notes, "
                f"{len(serialized_connections)} connections, "
                f"{len(serialized_images)} images"
            )
            return session_data

        except Exception as e:
            # Align error message with test expectations while preserving context in logs
            self.logger.error(f"Scene serialization failed: {e}")
            raise SessionError("Failed to serialize scene data")

    def _serialize_scene_items(self, scene: QGraphicsScene) -> tuple[list, list, list]:
        """Serialize all items in the scene by type."""
        notes, connections, images = self._separate_items_by_type(scene.items())
        return self._serialize_items_by_type(notes, connections, images)

    def _separate_items_by_type(self, items) -> tuple[list, list, list]:
        """Separate scene items by their type."""
        notes = [item for item in items if isinstance(item, NoteItem)]
        connections = [item for item in items if isinstance(item, ConnectionItem)]
        images = [item for item in items if isinstance(item, ImageItem)]
        return notes, connections, images

    def _serialize_items_by_type(
        self, notes: list, connections: list, images: list
    ) -> tuple[list, list, list]:
        """Serialize items of each type."""
        serialized_notes = [self._serialize_note(note) for note in notes]
        serialized_connections = [
            self._serialize_connection(conn) for conn in connections
        ]
        serialized_images = [
            image_data
            for image in images
            if (image_data := self._serialize_image(image)) is not None
        ]
        return serialized_notes, serialized_connections, serialized_images

    def _get_canvas_state(self, canvas) -> dict[str, Any]:
        """Get canvas state if available."""
        if not canvas:
            return {}

        center_point = canvas.get_center_point()
        return {
            "zoom_factor": canvas.get_zoom_factor(),
            "center_x": center_point.x(),
            "center_y": center_point.y(),
        }

    def _create_session_data_structure(
        self,
        serialized_notes: list,
        serialized_connections: list,
        serialized_images: list,
        scene_rect,
        canvas_state: dict,
    ) -> dict[str, Any]:
        """Create the main session data structure."""
        return {
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
            "images": serialized_images,
            "groups": [],  # TODO: Implement groups serialization when groups are added
            "metadata": {
                "note_count": len(serialized_notes),
                "connection_count": len(serialized_connections),
                "image_count": len(serialized_images),
                "group_count": 0,
            },
        }

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
            self.logger.debug(
                f"Serializing connection {connection.get_connection_id()} with data keys: {list(connection_data.keys())}"
            )
            # Serialize any QColor objects in the connection style
            if "style" in connection_data:
                connection_data["style"] = self._serialize_style(
                    connection_data["style"]
                )
            self.logger.debug(
                f"Serialized connection endpoints: start_item_id={connection_data.get('start_item_id')}, end_item_id={connection_data.get('end_item_id')}, "
                f"legacy_start_note_id={connection_data.get('start_note_id')}, legacy_end_note_id={connection_data.get('end_note_id')}"
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

    def _apply_connection_properties(
        self, connection: ConnectionItem, connection_data: dict[str, Any]
    ) -> None:
        """Apply style and flags to a deserialized connection."""
        style_data = connection_data.get("style")
        if style_data:
            connection.set_style(self._deserialize_style(style_data))

        z_value = connection_data.get("z_value")
        if z_value is not None:
            connection.setZValue(z_value)

        visible = connection_data.get("visible")
        if visible is not None:
            connection.setVisible(visible)

        enabled = connection_data.get("enabled")
        if enabled is not None:
            connection.setEnabled(enabled)

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

            # Restore scene and canvas state
            self._restore_scene_state(session_data, scene, canvas)

            # Deserialize all items
            notes_count, connections_count, images_count = (
                self._deserialize_scene_items(session_data, scene)
            )

            self.logger.info(
                f"Deserialized {notes_count} notes, {connections_count} connections, "
                f"and {images_count} images"
            )

        except Exception as e:
            self.logger.error(f"Scene deserialization failed: {e}")
            raise SessionError(f"Scene deserialization failed: {e}")

    def _restore_scene_state(
        self, session_data: dict[str, Any], scene: QGraphicsScene, canvas
    ) -> None:
        """Restore scene bounds and canvas state."""
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
            zoom_factor = canvas_state.get("zoom_factor", 1.0)
            canvas.set_zoom(zoom_factor)

            center_x = canvas_state.get("center_x", 0.0)
            center_y = canvas_state.get("center_y", 0.0)
            canvas.centerOn(center_x, center_y)

            self.logger.debug(
                f"Restored canvas state: zoom={zoom_factor:.2f}, "
                f"center=({center_x:.1f}, {center_y:.1f})"
            )

    def _deserialize_scene_items(
        self, session_data: dict[str, Any], scene: QGraphicsScene
    ) -> tuple[int, int, int]:
        """Deserialize all scene items and return counts."""
        # Create mapping for note IDs to recreated notes
        note_id_map = {}
        image_id_map = {}

        # Deserialize notes first
        notes_data = session_data.get("notes", [])
        for note_data in notes_data:
            note = self._deserialize_note(note_data)
            scene.addItem(note)
            note_id_map[note.get_note_id()] = note
        self.logger.debug(f"Recreated {len(note_id_map)} notes for deserialization")

        # Deserialize images next so connections can resolve them
        images_data = session_data.get("images", [])
        images_added = 0
        for image_data in images_data:
            try:
                image = self._deserialize_image(image_data)
                if image:
                    scene.addItem(image)
                    image_id_map[image.get_image_id()] = image
                    images_added += 1
            except Exception as e:
                self.logger.error(f"Failed to deserialize image: {e}")
        self.logger.debug(
            f"Recreated {images_added} images; available image IDs: {list(image_id_map.keys())}"
        )

        # Deserialize connections last, when all endpoints exist
        connections_data = session_data.get("connections", [])
        connections_added = 0
        for connection_data in connections_data:
            try:
                connection = self._deserialize_connection(
                    connection_data, note_id_map, image_id_map
                )
                if connection is not None:
                    scene.addItem(connection)
                    connections_added += 1
            except Exception as e:
                self.logger.error(f"Failed to deserialize connection: {e}")

        return len(notes_data), connections_added, images_added

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
        self,
        connection_data: dict[str, Any],
        note_id_map: dict[int, NoteItem],
        image_id_map: dict[int, ImageItem] | None = None,
    ) -> ConnectionItem | None:
        """
        Deserialize a single connection item.
        """
        try:
            start_item, end_item = self._resolve_connection_endpoints(
                connection_data, note_id_map, image_id_map
            )
            if start_item is None or end_item is None:
                self.logger.warning(
                    "Skipping connection: unresolved endpoints. "
                    f"start_item_id={connection_data.get('start_item_id')}, end_item_id={connection_data.get('end_item_id')}, "
                    f"legacy_start_note_id={connection_data.get('start_note_id')}, "
                    f"legacy_end_note_id={connection_data.get('end_note_id')}"
                )
                return None

            connection = ConnectionItem(start_item, end_item)
            self._apply_connection_properties(connection, connection_data)

            self.logger.debug(
                f"Deserialized connection: start={self._endpoint_id_str(start_item)}, end={self._endpoint_id_str(end_item)}"
            )
            return connection

        except Exception as e:
            self.logger.error(f"Failed to deserialize connection: {e}")
            raise SessionError(f"Failed to deserialize connection: {e}")

    def _resolve_connection_endpoints(
        self,
        connection_data: dict[str, Any],
        note_id_map: dict[int, NoteItem],
        image_id_map: dict[int, ImageItem] | None = None,
    ) -> tuple[Any | None, Any | None]:
        """Resolve start and end endpoints for a connection, supporting legacy fallbacks."""
        start_item_id = connection_data.get("start_item_id")
        end_item_id = connection_data.get("end_item_id")

        start_item = self._resolve_connection_endpoint(
            start_item_id, note_id_map, image_id_map
        )
        end_item = self._resolve_connection_endpoint(
            end_item_id, note_id_map, image_id_map
        )

        if start_item is None and isinstance(connection_data.get("start_note_id"), int):
            start_item = note_id_map.get(connection_data["start_note_id"])  # legacy
        if end_item is None and isinstance(connection_data.get("end_note_id"), int):
            end_item = note_id_map.get(connection_data["end_note_id"])  # legacy

        return start_item, end_item

    def _resolve_connection_endpoint(
        self,
        item_id: Any,
        note_id_map: dict[int, NoteItem],
        image_id_map: dict[int, ImageItem] | None = None,
    ) -> Any | None:
        """Resolve a connection endpoint by generic item identifier."""
        if not isinstance(item_id, str):
            return None
        # coalesce optional maps
        image_map = image_id_map or {}
        if item_id.startswith("note_"):
            try:
                note_id = int(item_id.split("_", 1)[1])
                return note_id_map.get(note_id)
            except Exception:
                return None
        if item_id.startswith("image_"):
            try:
                image_id = int(item_id.split("_", 1)[1])
                return image_map.get(image_id)
            except Exception:
                return None
        return None

    def _endpoint_id_str(self, obj: Any) -> str:
        """Return a stable identifier string for logging endpoints."""
        try:
            if hasattr(obj, "get_note_id"):
                return f"note_{obj.get_note_id()}"
            if hasattr(obj, "get_image_id"):
                return f"image_{obj.get_image_id()}"
            return f"item_{id(obj)}"
        except Exception:
            return f"item_{id(obj)}"

    def _validate_session_data(self, session_data: dict[str, Any]) -> None:
        """
        Validate session data structure and format.

        Args:
            session_data: Dictionary containing session data to validate

        Raises:
            SessionError: If validation fails
        """
        try:
            self._validate_required_keys(session_data)
            self._validate_version_compatibility(session_data)
            self._validate_data_structures(session_data)
            self.logger.debug("Session data validation passed")

        except Exception as e:
            self.logger.error(f"Session data validation failed: {e}")
            raise SessionError(f"Session data validation failed: {e}")

    def _validate_required_keys(self, session_data: dict[str, Any]) -> None:
        """Validate required top-level keys."""
        required_keys = ["version", "notes", "connections"]
        for key in required_keys:
            if key not in session_data:
                raise SessionError(f"Missing required key: {key}")

    def _validate_version_compatibility(self, session_data: dict[str, Any]) -> None:
        """Check version compatibility."""
        version = session_data.get("version")
        if version != self.FILE_FORMAT_VERSION:
            self.logger.warning(
                f"File format version mismatch: {version} vs {self.FILE_FORMAT_VERSION}"
            )
            # For now, continue with loading - in future versions, implement migration

    def _validate_data_structures(self, session_data: dict[str, Any]) -> None:
        """Validate data structure types and content."""
        # Validate notes structure
        notes = session_data.get("notes", [])
        if not isinstance(notes, list):
            raise SessionError("Notes data must be a list")

        # Validate connections structure
        connections = session_data.get("connections", [])
        if not isinstance(connections, list):
            raise SessionError("Connections data must be a list")

        # Validate images structure (optional for backward compatibility)
        images = session_data.get("images", [])
        if not isinstance(images, list):
            raise SessionError("Images data must be a list")

        self._validate_image_data(images)

    def _validate_image_data(self, images: list) -> None:
        """Validate individual image data structures."""
        for i, image_data in enumerate(images):
            if not isinstance(image_data, dict):
                raise SessionError(f"Image {i} data must be a dictionary")

            # Check for required image fields
            required_image_fields = ["id", "position"]
            for field in required_image_fields:
                if field not in image_data:
                    self.logger.warning(f"Image {i} missing field: {field}")

            # Validate base64 data if present
            if "image_base64" in image_data:
                try:
                    base64.b64decode(image_data["image_base64"], validate=True)
                except Exception as e:
                    self.logger.warning(f"Image {i} has invalid base64 data: {e}")

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
            self.logger.error(f"Failed to list sessions: {e}")
            raise SessionError(f"Failed to list sessions: {e}")

    def _serialize_image(self, image: ImageItem) -> dict[str, Any] | None:
        """
        Serialize a single image item with base64 encoding.

        Args:
            image: ImageItem to serialize

        Returns:
            Dictionary containing serialized image data or None if serialization fails
        """
        try:
            # Get image position
            pos = image.pos()

            # Get image data
            image_data = image.get_image_data()
            image_path = image.get_image_path()

            # Encode image file as base64 if path exists
            image_base64 = None
            original_filename = None
            file_size = None

            if image_path and Path(image_path).exists():
                try:
                    with open(image_path, "rb") as f:
                        image_bytes = f.read()
                        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                        original_filename = Path(image_path).name
                        file_size = len(image_bytes)

                    self.logger.debug(
                        f"Encoded image {image_path} as base64 ({file_size} bytes)"
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to encode image {image_path}: {e}")
                    # Continue without base64 data, just store the path

            # Get image style properties and serialize QColor objects
            style = image_data.get("style", {})
            serialized_style = self._serialize_style(style)

            serialized_image = {
                "id": image.get_image_id(),
                "position": {"x": pos.x(), "y": pos.y()},
                "style": serialized_style,
                "rotation": image_data.get("rotation", 0),
                "z_value": image.zValue(),
                "visible": image.isVisible(),
                "enabled": image.isEnabled(),
                "image_path": image_path,  # Keep original path for reference
                "image_base64": image_base64,  # Base64 encoded image data
                "original_filename": original_filename,
                "file_size": file_size,
                "metadata": {
                    "serialized_at": datetime.now().isoformat(),
                    "has_base64": image_base64 is not None,
                },
            }

            return serialized_image

        except Exception as e:
            self.logger.error(f"Failed to serialize image: {e}")
            # Return None to skip this image rather than failing the entire serialization
            return None

    def _deserialize_image(self, image_data: dict[str, Any]) -> ImageItem | None:
        """
        Deserialize a single image item from base64 or file path.

        Args:
            image_data: Dictionary containing serialized image data

        Returns:
            ImageItem instance or None if deserialization fails
        """
        try:
            # Get position data
            position_data = image_data.get("position", {})
            position = QPointF(position_data.get("x", 0), position_data.get("y", 0))

            # Try to restore image from base64 first, then fall back to file path
            image_path = ""

            if image_data.get("image_base64"):
                try:
                    # Decode base64 image data
                    image_bytes = base64.b64decode(image_data["image_base64"])

                    # Create temporary file for the image
                    original_filename = image_data.get("original_filename", "image.png")
                    temp_dir = Path.home() / ".whiteboard" / "temp_images"
                    temp_dir.mkdir(parents=True, exist_ok=True)

                    # Use image ID to create unique filename
                    image_id = image_data.get("id", "unknown")
                    temp_filename = f"{image_id}_{original_filename}"
                    temp_path = temp_dir / temp_filename

                    # Write decoded image to temporary file
                    with open(temp_path, "wb") as f:
                        f.write(image_bytes)

                    image_path = str(temp_path)
                    self.logger.debug(f"Restored image from base64 to {image_path}")

                except Exception as e:
                    self.logger.warning(f"Failed to decode base64 image: {e}")
                    # Fall back to original path if available
                    image_path = image_data.get("image_path", "")
            else:
                # Use original file path
                image_path = image_data.get("image_path", "")

                # Validate that the file still exists
                if image_path and not Path(image_path).exists():
                    self.logger.warning(f"Image file not found: {image_path}")
                    # Continue anyway - ImageItem will handle missing files gracefully

            # Create new image item
            image = ImageItem(image_path, position)

            # Restore style
            style_data = image_data.get("style", {})
            if style_data:
                deserialized_style = self._deserialize_style(style_data)
                image.update_style(deserialized_style)

            # Restore other properties
            image.setZValue(image_data.get("z_value", 0))
            image.setVisible(image_data.get("visible", True))
            image.setEnabled(image_data.get("enabled", True))

            # Restore rotation if present
            rotation = image_data.get("rotation", 0)
            if rotation != 0:
                image._rotation = rotation
                image._apply_transform()

            # Update image ID if provided
            if "id" in image_data:
                image._image_id = image_data["id"]

            self.logger.debug(f"Deserialized ImageItem {image.get_image_id()}")
            return image

        except Exception as e:
            self.logger.error(f"Failed to deserialize image: {e}")
            # Return None to skip this image rather than failing the entire deserialization
            return None
