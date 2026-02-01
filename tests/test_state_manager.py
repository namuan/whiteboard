"""
Tests for the state_manager module.
"""

from unittest.mock import patch

import pytest

from src.whiteboard.state_manager import AppStateManager


class TestAppStateManager:
    """Tests for AppStateManager class."""

    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """Create a temporary config directory for testing."""
        config_dir = tmp_path / "test_config"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    @pytest.fixture
    def mock_config_dir(self, temp_config_dir):
        """Mock the config directory path."""
        with patch("src.whiteboard.state_manager.get_app_state_file_path") as mock_path:
            state_file = temp_config_dir / "app_state.json"
            mock_path.return_value = state_file
            yield {"config_dir": temp_config_dir, "state_file": state_file}

    def test_default_state(self, mock_config_dir):
        """Test that default state is correctly initialized."""
        manager = AppStateManager()

        assert manager.get_last_document_path() is None
        assert manager.get_window_geometry() is None
        assert manager.get_window_state() is None

    def test_set_and_get_last_document_path(self, mock_config_dir):
        """Test setting and getting last document path."""
        manager = AppStateManager()

        test_path = "/path/to/document.whiteboard"
        manager.set_last_document_path(test_path)

        assert manager.get_last_document_path() == test_path

    def test_state_persistence(self, mock_config_dir):
        """Test that state is persisted to file."""
        test_path = "/path/to/test.whiteboard"

        # Create first manager and set state
        manager1 = AppStateManager()
        manager1.set_last_document_path(test_path)

        # Create second manager and verify state is loaded
        manager2 = AppStateManager()
        assert manager2.get_last_document_path() == test_path

    def test_clear_last_document(self, mock_config_dir):
        """Test clearing last document path."""
        manager = AppStateManager()

        manager.set_last_document_path("/path/to/doc.whiteboard")
        assert manager.get_last_document_path() is not None

        manager.clear_last_document()
        assert manager.get_last_document_path() is None

    def test_window_geometry(self, mock_config_dir):
        """Test setting and getting window geometry."""
        manager = AppStateManager()

        geometry = [100, 200, 800, 600]
        manager.set_window_geometry(geometry)

        assert manager.get_window_geometry() == geometry

    def test_get_state(self, mock_config_dir):
        """Test getting complete state dictionary."""
        manager = AppStateManager()

        manager.set_last_document_path("/path/to/doc.whiteboard")
        manager.set_window_geometry([100, 200, 800, 600])

        state = manager.get_state()

        assert state["last_document_path"] == "/path/to/doc.whiteboard"
        assert state["window_geometry"] == [100, 200, 800, 600]
        assert state["version"] == "1.0"

    def test_reset_state(self, mock_config_dir):
        """Test resetting state to defaults."""
        manager = AppStateManager()

        manager.set_last_document_path("/path/to/doc.whiteboard")
        manager.set_window_geometry([100, 200, 800, 600])

        manager.reset_state()

        state = manager.get_state()
        assert state["last_document_path"] is None
        assert state["window_geometry"] is None

    def test_last_document_changed_signal(self, mock_config_dir):
        """Test that last_document_changed signal is emitted."""
        manager = AppStateManager()

        with patch.object(manager, "last_document_changed") as mock_signal:
            manager.set_last_document_path("/path/to/doc.whiteboard")
            mock_signal.emit.assert_called_once_with("/path/to/doc.whiteboard")

    def test_invalid_state_file(self, mock_config_dir):
        """Test handling of invalid state file."""
        # Write invalid JSON to state file
        state_file = mock_config_dir["state_file"]
        with open(state_file, "w") as f:
            f.write("invalid json {")

        # Should not raise exception, should use defaults
        manager = AppStateManager()
        assert manager.get_last_document_path() is None

    def test_missing_state_file(self, mock_config_dir):
        """Test behavior when state file doesn't exist."""
        state_file = mock_config_dir["state_file"]
        if state_file.exists():
            state_file.unlink()

        # Should not raise exception
        manager = AppStateManager()
        assert manager.get_last_document_path() is None


class TestGetAppStateFilePath:
    """Tests for get_app_state_file_path function."""

    def test_returns_json_file(self):
        """Test that the function returns a path ending with app_state.json."""
        from src.whiteboard.utils.config_paths import get_app_state_file_path

        path = get_app_state_file_path()
        assert path.name == "app_state.json"
        assert path.suffix == ".json"
