"""
Unit tests for the SessionManager class.

Tests cover session persistence, data serialization/deserialization,
file operations, and error handling with extensive use of mocks.
"""

import unittest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QGraphicsScene
from PyQt6.QtCore import QPointF, QRectF

from src.whiteboard.session_manager import SessionManager, SessionError
from src.whiteboard.note_item import NoteItem
from src.whiteboard.connection_item import ConnectionItem


class TestSessionManager(unittest.TestCase):
    """Test cases for SessionManager functionality."""

    @classmethod
    @patch("src.whiteboard.utils.config_paths.get_app_data_dir")
    @patch("src.whiteboard.utils.config_paths.ensure_app_directories")
    @patch("pathlib.Path.mkdir")
    def setUpClass(cls, mock_mkdir, mock_ensure_dirs, mock_data_dir):
        """Set up test class with mocked paths."""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()

        mock_data_dir.return_value = Path("/mock/data/dir")
        mock_ensure_dirs.return_value = None
        mock_mkdir.return_value = None
        cls.session_manager = SessionManager()

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Session manager is already created in setUpClass
        pass

        # Create mock scene and items
        self.mock_scene = Mock(spec=QGraphicsScene)
        self.mock_scene.sceneRect.return_value = QRectF(0, 0, 1000, 1000)

        # Create mock notes
        self.mock_note1 = Mock(spec=NoteItem)
        self.mock_note1.pos.return_value = QPointF(100, 200)
        self.mock_note1.get_text.return_value = "Test Note 1"
        self.mock_note1.get_note_id.return_value = 1001
        self.mock_note1.get_style.return_value = {
            "background_color": "#FFFF99",
            "border_color": "#000000",
            "text_color": "#000000",
        }

        self.mock_note2 = Mock(spec=NoteItem)
        self.mock_note2.pos.return_value = QPointF(300, 400)
        self.mock_note2.get_text.return_value = "Test Note 2"
        self.mock_note2.get_note_id.return_value = 1002
        self.mock_note2.get_style.return_value = {
            "background_color": "#99CCFF",
            "border_color": "#000000",
            "text_color": "#000000",
        }

        # Create mock connection
        self.mock_connection = Mock(spec=ConnectionItem)
        self.mock_connection.get_connection_data.return_value = {
            "id": 2001,
            "start_note_id": 1001,
            "end_note_id": 1002,
            "style": {
                "line_color": "#000000",
                "line_width": 2,
                "arrow_style": "filled",
            },
            "start_point": {"x": 100.0, "y": 200.0},
            "end_point": {"x": 300.0, "y": 400.0},
        }

    def test_session_manager_initialization(self):
        """Test SessionManager initialization."""
        # Verify initialization
        self.assertIsInstance(self.session_manager, SessionManager)
        self.assertEqual(self.session_manager.FILE_FORMAT_VERSION, "1.0")
        self.assertEqual(self.session_manager.FILE_EXTENSION, ".whiteboard")

        # Verify logger is set up
        self.assertIsNotNone(self.session_manager.logger)

    @patch("src.whiteboard.session_manager.get_app_data_dir")
    @patch("src.whiteboard.session_manager.ensure_app_directories")
    def test_setup_storage_paths_success(self, mock_ensure_dirs, mock_data_dir):
        """Test successful storage path setup."""
        mock_data_dir.return_value = Path("/test/data")

        with patch.object(Path, "mkdir") as mock_mkdir:
            SessionManager()

            mock_ensure_dirs.assert_called_once()
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch("src.whiteboard.session_manager.get_app_data_dir")
    def test_setup_storage_paths_failure(self, mock_data_dir):
        """Test storage path setup failure."""
        mock_data_dir.side_effect = Exception("Path setup failed")

        with self.assertRaises(SessionError) as context:
            SessionManager()

        self.assertIn("Failed to setup storage paths", str(context.exception))

    def test_serialize_scene_data_success(self):
        """Test successful scene data serialization."""
        # Setup mock scene items
        self.mock_scene.items.return_value = [
            self.mock_note1,
            self.mock_note2,
            self.mock_connection,
        ]

        result = self.session_manager.serialize_scene_data(self.mock_scene)

        # Verify result structure
        self.assertIn("version", result)
        self.assertIn("created_at", result)
        self.assertIn("scene", result)
        self.assertIn("notes", result)
        self.assertIn("connections", result)
        self.assertIn("groups", result)
        self.assertIn("metadata", result)

        # Verify version
        self.assertEqual(result["version"], "1.0")

        # Verify scene data
        scene_data = result["scene"]
        self.assertIn("rect", scene_data)

        # Verify notes data
        notes_data = result["notes"]
        self.assertEqual(len(notes_data), 2)

        note1_data = notes_data[0]
        self.assertEqual(note1_data["id"], 1001)
        self.assertEqual(note1_data["text"], "Test Note 1")
        self.assertEqual(note1_data["position"]["x"], 100)
        self.assertEqual(note1_data["position"]["y"], 200)

        # Verify connections data
        connections_data = result["connections"]
        self.assertEqual(len(connections_data), 1)

        connection_data = connections_data[0]
        self.assertEqual(connection_data["id"], 2001)
        self.assertEqual(connection_data["start_note_id"], 1001)
        self.assertEqual(connection_data["end_note_id"], 1002)

        # Verify metadata
        metadata = result["metadata"]
        self.assertEqual(metadata["note_count"], 2)
        self.assertEqual(metadata["connection_count"], 1)
        self.assertEqual(metadata["group_count"], 0)

    def test_serialize_scene_data_failure(self):
        """Test scene data serialization failure."""
        # Setup mock scene to raise exception
        self.mock_scene.items.side_effect = Exception("Scene access failed")

        with self.assertRaises(SessionError) as context:
            self.session_manager.serialize_scene_data(self.mock_scene)

        self.assertIn("Failed to serialize scene data", str(context.exception))

    def test_serialize_note(self):
        """Test note serialization."""
        # Create mock note
        mock_note = Mock(spec=NoteItem)
        mock_note.get_note_id.return_value = 123
        mock_note.get_text.return_value = "Test note"
        mock_note.pos.return_value = QPointF(10, 20)
        mock_note.get_style.return_value = {"font_size": 12}

        # Serialize note
        result = self.session_manager._serialize_note(mock_note)

        # Verify result
        expected = {
            "id": 123,
            "text": "Test note",
            "position": {"x": 10, "y": 20},
            "style": {"font_size": 12},
        }
        self.assertEqual(result, expected)

    def test_serialize_note_failure(self):
        """Test note serialization failure."""
        # Setup mock note to raise exception
        self.mock_note1.pos.side_effect = Exception("Position access failed")

        with self.assertRaises(SessionError) as context:
            self.session_manager._serialize_note(self.mock_note1)

        self.assertIn("Failed to serialize note", str(context.exception))

    def test_serialize_connection(self):
        """Test connection serialization."""
        # Create mock connection
        mock_connection = Mock(spec=ConnectionItem)
        mock_connection.get_connection_data.return_value = {
            "id": 456,
            "start_note_id": 123,
            "end_note_id": 789,
            "style": {"line_width": 2},
            "start_point": (0, 0),
            "end_point": (100, 100),
        }

        # Serialize connection
        result = self.session_manager._serialize_connection(mock_connection)

        # Verify result
        expected = {
            "id": 456,
            "start_note_id": 123,
            "end_note_id": 789,
            "style": {"line_width": 2},
            "start_point": (0, 0),
            "end_point": (100, 100),
        }
        self.assertEqual(result, expected)

    def test_serialize_connection_failure(self):
        """Test connection serialization failure."""
        # Create mock connection that raises exception
        mock_connection = Mock(spec=ConnectionItem)
        mock_connection.get_connection_data.side_effect = Exception("Connection error")

        # Test serialization failure
        with self.assertRaises(SessionError) as context:
            self.session_manager._serialize_connection(mock_connection)

        self.assertIn("Failed to serialize connection", str(context.exception))

    def test_validate_session_data_success(self):
        """Test successful session data validation."""
        valid_data = {"version": "1.0", "notes": [], "connections": [], "groups": []}

        # Should not raise exception
        self.session_manager._validate_session_data(valid_data)

    def test_validate_session_data_missing_keys(self):
        """Test session data validation with missing keys."""
        invalid_data = {
            "version": "1.0",
            "notes": [],
            # Missing "connections" key
        }

        with self.assertRaises(SessionError) as context:
            self.session_manager._validate_session_data(invalid_data)

        self.assertIn("Missing required key: connections", str(context.exception))

    def test_validate_session_data_invalid_structure(self):
        """Test session data validation with invalid structure."""
        invalid_data = {
            "version": "1.0",
            "notes": "not a list",  # Should be a list
            "connections": [],
        }

        with self.assertRaises(SessionError) as context:
            self.session_manager._validate_session_data(invalid_data)

        self.assertIn("Notes data must be a list", str(context.exception))

    def test_validate_session_data_version_mismatch(self):
        """Test session data validation with version mismatch."""
        data_with_old_version = {"version": "0.9", "notes": [], "connections": []}

        # Should not raise exception but log warning
        with patch.object(self.session_manager.logger, "warning") as mock_warning:
            self.session_manager._validate_session_data(data_with_old_version)
            mock_warning.assert_called_once()

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    @patch("pathlib.Path.mkdir")
    def test_save_session_to_file_success(self, mock_mkdir, mock_json_dump, mock_file):
        """Test successful session save to file."""
        test_data = {"version": "1.0", "notes": [], "connections": []}
        test_path = Path("/test/session.json")

        self.session_manager.save_session_to_file(test_data, test_path)

        # Verify file operations
        mock_file.assert_called_once_with(test_path, "w", encoding="utf-8")
        mock_json_dump.assert_called_once_with(
            test_data, mock_file.return_value, indent=2, ensure_ascii=False
        )
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch("builtins.open", side_effect=IOError("Write failed"))
    @patch("pathlib.Path.mkdir")
    def test_save_session_to_file_failure(self, mock_mkdir, mock_file):
        """Test session save to file failure."""
        test_data = {"version": "1.0", "notes": [], "connections": []}
        test_path = Path("/test/session.json")

        with self.assertRaises(SessionError) as context:
            self.session_manager.save_session_to_file(test_data, test_path)

        self.assertIn("Failed to save session to file", str(context.exception))

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"version": "1.0", "notes": [], "connections": []}',
    )
    @patch("json.load")
    @patch("pathlib.Path.exists")
    def test_load_session_from_file_success(
        self, mock_exists, mock_json_load, mock_file
    ):
        """Test successful session load from file."""
        test_data = {"version": "1.0", "notes": [], "connections": []}
        mock_json_load.return_value = test_data
        mock_exists.return_value = True
        test_path = Path("/test/session.json")

        result = self.session_manager.load_session_from_file(test_path)

        # Verify file operations
        mock_file.assert_called_once_with(test_path, encoding="utf-8")
        mock_json_load.assert_called_once()
        self.assertEqual(result, test_data)

    @patch("pathlib.Path.exists")
    def test_load_session_from_file_not_exists(self, mock_exists):
        """Test session load from non-existent file."""
        mock_exists.return_value = False
        test_path = Path("/test/nonexistent.json")

        with self.assertRaises(SessionError) as context:
            self.session_manager.load_session_from_file(test_path)

        self.assertIn("Session file does not exist", str(context.exception))

    @patch("builtins.open", side_effect=IOError("Read failed"))
    @patch("pathlib.Path.exists")
    def test_load_session_from_file_failure(self, mock_exists, mock_file):
        """Test session load from file failure."""
        mock_exists.return_value = True
        test_path = Path("/test/session.json")

        with self.assertRaises(SessionError) as context:
            self.session_manager.load_session_from_file(test_path)

        self.assertIn("Failed to load session from file", str(context.exception))

    def test_deserialize_note(self):
        """Test note deserialization."""
        note_data = {
            "id": 123,
            "text": "Test note",
            "position": {"x": 10, "y": 20},
            "style": {"font_size": 12},
        }

        with patch("src.whiteboard.session_manager.NoteItem") as mock_note_class:
            mock_note = Mock(spec=NoteItem)
            mock_note_class.return_value = mock_note

            result = self.session_manager._deserialize_note(note_data)

            # Verify note creation
            mock_note_class.assert_called_once_with("Test note", QPointF(10, 20))
            mock_note.set_style.assert_called_once_with({"font_size": 12})
            self.assertEqual(mock_note._note_id, 123)
            self.assertEqual(result, mock_note)

    def test_deserialize_connection(self):
        """Test connection deserialization."""
        # Create mock notes
        mock_note1 = Mock(spec=NoteItem)
        mock_note2 = Mock(spec=NoteItem)
        note_id_map = {123: mock_note1, 456: mock_note2}

        connection_data = {
            "id": 789,
            "start_note_id": 123,
            "end_note_id": 456,
            "style": {"line_width": 2},
        }

        with patch(
            "src.whiteboard.session_manager.ConnectionItem"
        ) as mock_connection_class:
            mock_connection = Mock(spec=ConnectionItem)
            mock_connection_class.return_value = mock_connection

            result = self.session_manager._deserialize_connection(
                connection_data, note_id_map
            )

            # Verify connection creation
            mock_connection_class.assert_called_once_with(mock_note1, mock_note2)
            mock_connection.set_style.assert_called_once_with({"line_width": 2})
            self.assertEqual(result, mock_connection)

    def test_deserialize_connection_missing_notes(self):
        """Test connection deserialization with missing referenced notes."""
        note_id_map = {}  # Empty mapping

        connection_data = {
            "id": 2001,
            "type": "connection",
            "start_note_id": 1001,
            "end_note_id": 1002,
            "style": {"line_color": "#000000"},
        }

        result = self.session_manager._deserialize_connection(
            connection_data, note_id_map
        )

        # Should return None when referenced notes don't exist
        self.assertIsNone(result)

    def test_get_default_session_path(self):
        """Test getting default session path."""
        # Get the expected extension from session manager
        expected_extension = self.session_manager.FILE_EXTENSION

        # Test with extension (should keep the provided extension)
        path1 = self.session_manager.get_default_session_path(
            f"test{expected_extension}"
        )
        self.assertTrue(str(path1).endswith(f"test{expected_extension}"))

        # Test without extension (should add the extension)
        path2 = self.session_manager.get_default_session_path("test")
        self.assertTrue(str(path2).endswith(f"test{expected_extension}"))

    @patch("pathlib.Path.glob")
    @patch("pathlib.Path.exists")
    def test_list_saved_sessions_success(self, mock_exists, mock_glob):
        """Test successful listing of saved sessions."""
        mock_exists.return_value = True

        # Create mock file paths
        mock_file1 = Mock()
        mock_file1.stem = "session1"
        mock_file1.stat.return_value.st_mtime = 1640995200  # 2022-01-01

        mock_file2 = Mock()
        mock_file2.stem = "session2"
        mock_file2.stat.return_value.st_mtime = 1641081600  # 2022-01-02

        mock_glob.return_value = [mock_file1, mock_file2]

        result = self.session_manager.list_saved_sessions()

        # Verify results (should be sorted by modification time, newest first)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0][0], "session2")  # Newer file first
        self.assertEqual(result[1][0], "session1")

    @patch("pathlib.Path.exists")
    def test_list_saved_sessions_no_directory(self, mock_exists):
        """Test listing saved sessions when directory doesn't exist."""
        mock_exists.return_value = False

        result = self.session_manager.list_saved_sessions()

        # Should return empty list
        self.assertEqual(result, [])

    def test_deserialize_scene_data_success(self):
        """Test successful scene data deserialization."""
        # Create test session data
        session_data = {
            "version": "1.0",
            "scene": {"rect": {"x": 0, "y": 0, "width": 1000, "height": 1000}},
            "notes": [
                {
                    "id": 1001,
                    "type": "note",
                    "position": {"x": 100, "y": 200},
                    "content": {"text": "Test Note", "html": "<p>Test Note</p>"},
                    "style": {"background_color": "#FFFF99"},
                    "z_value": 1.0,
                    "visible": True,
                    "enabled": True,
                }
            ],
            "connections": [
                {
                    "id": 2001,
                    "type": "connection",
                    "start_note_id": 1001,
                    "end_note_id": 1002,
                    "style": {"line_color": "#000000"},
                    "z_value": 0.5,
                    "visible": True,
                    "enabled": True,
                }
            ],
            "groups": [],
        }

        mock_scene = Mock()

        with (
            patch.object(
                self.session_manager, "_deserialize_note"
            ) as mock_deserialize_note,
            patch.object(
                self.session_manager, "_deserialize_connection"
            ) as mock_deserialize_connection,
        ):
            mock_note = Mock()
            mock_deserialize_note.return_value = mock_note
            mock_deserialize_connection.return_value = None  # No connection created

            self.session_manager.deserialize_scene_data(session_data, mock_scene)

        # Verify scene operations
        mock_scene.clear.assert_called_once()
        mock_scene.setSceneRect.assert_called_once()
        mock_scene.addItem.assert_called_once_with(mock_note)

        # Verify deserialization calls
        mock_deserialize_note.assert_called_once()
        mock_deserialize_connection.assert_called_once()

    def test_deserialize_scene_data_validation_failure(self):
        """Test scene data deserialization with validation failure."""
        invalid_session_data = {
            "version": "1.0"
            # Missing required keys
        }

        mock_scene = Mock()

        with self.assertRaises(SessionError):
            self.session_manager.deserialize_scene_data(
                invalid_session_data, mock_scene
            )

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    @patch("json.load")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    def test_complete_save_load_workflow(
        self, mock_mkdir, mock_exists, mock_json_load, mock_json_dump, mock_file
    ):
        """Test complete save/load workflow with canvas state."""
        # Setup mock canvas
        mock_canvas = Mock()
        mock_canvas.get_zoom_factor.return_value = 1.5
        mock_canvas.get_center_point.return_value = QPointF(500, 300)

        # Setup mock scene with items
        mock_scene = Mock(spec=QGraphicsScene)
        mock_scene.sceneRect.return_value = QRectF(0, 0, 1000, 1000)

        # Create mock note
        mock_note = Mock(spec=NoteItem)
        mock_note.pos.return_value = QPointF(100, 200)
        mock_note.get_text.return_value = "Test Note"
        mock_note.get_style.return_value = {
            "background_color": "#ffff99",
            "text_color": "#000000",
            "border_color": "#cccccc",
            "font_family": "Arial",
            "font_size": 12,
        }
        mock_note.zValue.return_value = 1.0
        mock_note.isVisible.return_value = True
        mock_note.isEnabled.return_value = True

        # Setup scene items
        mock_scene.items.return_value = [mock_note]

        # Test serialization
        session_data = self.session_manager.serialize_scene_data(
            mock_scene, mock_canvas
        )

        # Verify canvas state is included
        self.assertIn("canvas_state", session_data)
        self.assertEqual(session_data["canvas_state"]["zoom_factor"], 1.5)
        self.assertEqual(session_data["canvas_state"]["center_x"], 500)
        self.assertEqual(session_data["canvas_state"]["center_y"], 300)

        # Test save to file
        test_path = Path("/test/session.json")
        self.session_manager.save_session_to_file(session_data, test_path)

        # Verify file operations
        mock_file.assert_called_with(test_path, "w", encoding="utf-8")
        mock_json_dump.assert_called_once()

        # Test load from file
        mock_exists.return_value = True
        mock_json_load.return_value = session_data

        loaded_data = self.session_manager.load_session_from_file(test_path)

        # Verify loaded data matches original
        self.assertEqual(loaded_data, session_data)

        # Test deserialization with canvas restoration
        new_mock_scene = Mock(spec=QGraphicsScene)
        new_mock_canvas = Mock()

        with patch.object(
            self.session_manager, "_deserialize_note"
        ) as mock_deserialize_note:
            mock_deserialize_note.return_value = mock_note

            self.session_manager.deserialize_scene_data(
                loaded_data, new_mock_scene, new_mock_canvas
            )

            # Verify canvas state restoration
            new_mock_canvas.set_zoom.assert_called_once_with(1.5)
            new_mock_canvas.centerOn.assert_called_once_with(500, 300)

            # Verify scene operations
            new_mock_scene.clear.assert_called_once()
            new_mock_scene.setSceneRect.assert_called_once()
            new_mock_scene.addItem.assert_called_once_with(mock_note)

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    @patch("json.load")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    def test_save_load_workflow_without_canvas(
        self, mock_mkdir, mock_exists, mock_json_load, mock_json_dump, mock_file
    ):
        """Test save/load workflow without canvas state (backward compatibility)."""
        # Setup mock scene without canvas
        mock_scene = Mock(spec=QGraphicsScene)
        mock_scene.sceneRect.return_value = QRectF(0, 0, 1000, 1000)
        mock_scene.items.return_value = []

        # Test serialization without canvas
        session_data = self.session_manager.serialize_scene_data(mock_scene)

        # Verify canvas state is empty but still present
        self.assertIn("canvas_state", session_data)
        self.assertEqual(session_data["canvas_state"], {})

        # Test save to file
        test_path = Path("/test/session.json")
        self.session_manager.save_session_to_file(session_data, test_path)

        # Test load from file
        mock_exists.return_value = True
        mock_json_load.return_value = session_data

        loaded_data = self.session_manager.load_session_from_file(test_path)

        # Test deserialization without canvas
        new_mock_scene = Mock(spec=QGraphicsScene)

        self.session_manager.deserialize_scene_data(loaded_data, new_mock_scene)

        # Verify scene operations
        new_mock_scene.clear.assert_called_once()
        new_mock_scene.setSceneRect.assert_called_once()

    @patch("builtins.open", side_effect=IOError("File write error"))
    def test_save_workflow_file_error(self, mock_file):
        """Test save workflow with file I/O error."""
        session_data = {"version": "1.0", "notes": [], "connections": []}
        test_path = Path("/test/session.json")

        with self.assertRaises(SessionError) as context:
            self.session_manager.save_session_to_file(session_data, test_path)

        self.assertIn("Failed to save session", str(context.exception))

    @patch("pathlib.Path.exists", return_value=True)
    @patch("builtins.open", side_effect=IOError("File read error"))
    def test_load_workflow_file_error(self, mock_file, mock_exists):
        """Test load workflow with file I/O error."""
        test_path = Path("/test/session.json")

        with self.assertRaises(SessionError) as context:
            self.session_manager.load_session_from_file(test_path)

        self.assertIn("Failed to load session", str(context.exception))


if __name__ == "__main__":
    unittest.main()
