"""
Tests for auto-save functionality in MainWindow.
"""

import pytest
from unittest.mock import patch
from pathlib import Path
from PyQt6.QtCore import QTimer

from whiteboard.main_window import MainWindow
from whiteboard.session_manager import SessionError


class TestAutoSave:
    """Test auto-save functionality."""

    @pytest.fixture
    def main_window(self, qtbot):
        """Create a MainWindow instance for testing."""
        window = MainWindow()
        qtbot.addWidget(window)
        return window

    def test_auto_save_initialization(self, main_window):
        """Test that auto-save is properly initialized."""
        assert hasattr(main_window, "_auto_save_timer")
        assert isinstance(main_window._auto_save_timer, QTimer)
        assert main_window._auto_save_interval == 30000  # 30 seconds
        assert main_window._auto_save_enabled is True
        # Note: _scene_modified might be True due to scene initialization signals

    def test_scene_change_triggers_auto_save_timer(self, main_window):
        """Test that scene changes trigger the auto-save timer."""
        # Set up a current file path
        main_window._current_file_path = Path("/test/file.json")

        # Mock the timer
        with patch.object(main_window._auto_save_timer, "start") as mock_start:
            # Trigger scene change
            main_window._on_scene_changed()

            # Verify timer was started
            mock_start.assert_called_once_with(30000)
            assert main_window._scene_modified is True

    def test_scene_change_without_file_path(self, main_window):
        """Test that scene changes without file path don't start timer."""
        main_window._current_file_path = None

        with patch.object(main_window._auto_save_timer, "start") as mock_start:
            main_window._on_scene_changed()

            mock_start.assert_not_called()
            assert main_window._scene_modified is True

    def test_scene_change_when_auto_save_disabled(self, main_window):
        """Test that scene changes when auto-save is disabled don't start timer."""
        main_window._current_file_path = Path("/test/file.json")
        main_window._auto_save_enabled = False

        with patch.object(main_window._auto_save_timer, "start") as mock_start:
            main_window._on_scene_changed()

            mock_start.assert_not_called()
            assert main_window._scene_modified is True

    def test_auto_save_success(self, main_window):
        """Test successful auto-save."""
        main_window._scene_modified = True
        main_window._current_file_path = Path("/test/path.wb")
        main_window._auto_save_enabled = True

        with patch.object(
            main_window._session_manager, "serialize_scene_data"
        ) as mock_serialize, patch.object(
            main_window._session_manager, "save_session_to_file"
        ) as mock_save, patch("PyQt6.QtCore.QTimer.singleShot") as mock_single_shot:
            mock_serialize.return_value = {"test": "data"}

            # Call auto-save which should schedule background save
            main_window._auto_save()

            # Verify QTimer.singleShot was called
            mock_single_shot.assert_called_once_with(0, main_window._perform_auto_save)

            # Now call the actual background save method
            main_window._perform_auto_save()

            mock_serialize.assert_called_once_with(
                main_window._scene, main_window._canvas
            )
            mock_save.assert_called_once_with({"test": "data"}, Path("/test/path.wb"))
            assert not main_window._scene_modified

    def test_auto_save_timer_debouncing(self, main_window):
        """Test that auto-save timer properly debounces multiple scene changes."""
        main_window._current_file_path = Path("/test/file.json")
        main_window._auto_save_enabled = True

        with patch.object(main_window._auto_save_timer, "start") as mock_start:
            # Trigger multiple scene changes rapidly
            main_window._on_scene_changed()
            main_window._on_scene_changed()
            main_window._on_scene_changed()

            # Timer should be restarted for each change (debouncing)
            assert mock_start.call_count == 3
            # Each call should use the same interval
            for call in mock_start.call_args_list:
                assert call[0][0] == main_window._auto_save_interval

    def test_auto_save_timer_timeout_triggers_save(self, main_window):
        """Test that timer timeout triggers auto-save."""
        main_window._scene_modified = True
        main_window._current_file_path = Path("/test/file.json")
        main_window._auto_save_enabled = True

        with patch("PyQt6.QtCore.QTimer.singleShot") as mock_single_shot:
            # Simulate timer timeout by calling the connected slot
            main_window._auto_save()

            # Verify background save was scheduled
            mock_single_shot.assert_called_once_with(0, main_window._perform_auto_save)

    def test_auto_save_error_recovery_session_error(self, main_window):
        """Test error recovery when SessionError occurs during auto-save."""
        main_window._scene_modified = True
        main_window._current_file_path = Path("/test/file.json")

        with patch.object(
            main_window._session_manager, "serialize_scene_data"
        ) as mock_serialize, patch.object(
            main_window, "statusBar"
        ) as mock_status_bar, patch.object(
            main_window.logger, "warning"
        ) as mock_log_warning:
            mock_serialize.side_effect = SessionError("Serialization failed")

            # Should not raise exception
            main_window._perform_auto_save()

            # Verify error handling
            mock_log_warning.assert_called_once_with(
                "Auto-save failed: Serialization failed"
            )
            mock_status_bar.return_value.showMessage.assert_any_call(
                "Auto-save failed: Serialization failed", 5000
            )

            # Scene should remain modified for retry
            assert main_window._scene_modified

    def test_auto_save_error_recovery_unexpected_error(self, main_window):
        """Test error recovery when unexpected error occurs during auto-save."""
        main_window._scene_modified = True
        main_window._current_file_path = Path("/test/file.json")

        with patch.object(
            main_window._session_manager, "serialize_scene_data"
        ) as mock_serialize, patch.object(
            main_window, "statusBar"
        ) as mock_status_bar, patch.object(
            main_window.logger, "error"
        ) as mock_log_error:
            mock_serialize.side_effect = Exception("Unexpected error")

            # Should not raise exception
            main_window._perform_auto_save()

            # Verify error handling
            mock_log_error.assert_called_once_with(
                "Unexpected error during auto-save: Unexpected error"
            )
            mock_status_bar.return_value.showMessage.assert_any_call(
                "Auto-save failed: Unexpected error", 5000
            )

            # Scene should remain modified for retry
            assert main_window._scene_modified

    def test_auto_save_retry_after_error(self, main_window):
        """Test that auto-save can retry after an error."""
        main_window._scene_modified = True
        main_window._current_file_path = Path("/test/file.json")

        with patch.object(
            main_window._session_manager, "serialize_scene_data"
        ) as mock_serialize, patch.object(
            main_window._session_manager, "save_session_to_file"
        ) as mock_save:
            # First call fails
            mock_serialize.side_effect = [
                SessionError("First failure"),
                {"test": "data"},
            ]

            # First attempt fails
            main_window._perform_auto_save()
            assert main_window._scene_modified  # Should remain modified

            # Second attempt succeeds
            main_window._perform_auto_save()
            assert not main_window._scene_modified  # Should be cleared

            # Verify both attempts were made
            assert mock_serialize.call_count == 2
            mock_save.assert_called_once_with({"test": "data"}, Path("/test/file.json"))

    def test_auto_save_timing_interval_changes(self, main_window):
        """Test that auto-save timing responds to interval changes."""
        main_window._current_file_path = Path("/test/file.json")

        with patch.object(main_window._auto_save_timer, "start") as mock_start:
            # Set initial interval
            main_window.set_auto_save_interval(15000)  # 15 seconds

            # Trigger scene change
            main_window._on_scene_changed()
            mock_start.assert_called_with(15000)

            # Change interval
            main_window.set_auto_save_interval(45000)  # 45 seconds

            # Trigger another scene change
            main_window._on_scene_changed()
            mock_start.assert_called_with(45000)

    def test_auto_save_disabled_prevents_timer_start(self, main_window):
        """Test that disabling auto-save prevents timer from starting."""
        main_window._current_file_path = Path("/test/file.json")
        main_window._auto_save_enabled = False

        with patch.object(main_window._auto_save_timer, "start") as mock_start:
            main_window._on_scene_changed()
            mock_start.assert_not_called()

    def test_auto_save_multiple_rapid_changes_performance(self, main_window):
        """Test that multiple rapid scene changes don't cause performance issues."""
        main_window._current_file_path = Path("/test/file.json")
        main_window._auto_save_enabled = True

        with patch.object(main_window._auto_save_timer, "start") as mock_start:
            # Simulate 10 rapid scene changes
            for _ in range(10):
                main_window._on_scene_changed()

            # Timer should be restarted for each change
            assert mock_start.call_count == 10
            # Each call should use the same interval
            for call in mock_start.call_args_list:
                assert call[0][0] == main_window._auto_save_interval

            # Scene should be marked as modified
            assert main_window._scene_modified

    def test_auto_save_no_modification(self, main_window):
        """Test auto-save when scene is not modified."""
        main_window._scene_modified = False
        main_window._current_file_path = Path("/test/file.json")
        main_window._auto_save_enabled = True

        with patch("PyQt6.QtCore.QTimer.singleShot") as mock_single_shot:
            main_window._auto_save()
            mock_single_shot.assert_not_called()

    def test_auto_save_no_file_path(self, main_window):
        """Test auto-save when no file path is set."""
        main_window._scene_modified = True
        main_window._current_file_path = None
        main_window._auto_save_enabled = True

        with patch("PyQt6.QtCore.QTimer.singleShot") as mock_single_shot:
            main_window._auto_save()
            mock_single_shot.assert_not_called()

    def test_auto_save_session_error(self, main_window):
        """Test auto-save handling of SessionError."""
        main_window._scene_modified = True
        main_window._current_file_path = Path("/test/file.json")
        main_window._auto_save_enabled = True

        with patch.object(
            main_window._session_manager, "serialize_scene_data"
        ) as mock_serialize, patch.object(main_window, "statusBar") as mock_status_bar:
            mock_serialize.side_effect = SessionError("Test error")

            # Should not raise exception
            main_window._perform_auto_save()

            # Scene should still be marked as modified
            assert main_window._scene_modified

            # Verify error status message
            mock_status_bar.return_value.showMessage.assert_any_call(
                "Auto-saving...", 0
            )
            mock_status_bar.return_value.showMessage.assert_any_call(
                "Auto-save failed: Test error", 5000
            )

    def test_auto_save_unexpected_error(self, main_window):
        """Test auto-save handling of unexpected errors."""
        main_window._scene_modified = True
        main_window._current_file_path = Path("/test/file.json")
        main_window._auto_save_enabled = True

        with patch.object(
            main_window._session_manager, "serialize_scene_data"
        ) as mock_serialize, patch.object(main_window, "statusBar") as mock_status_bar:
            mock_serialize.side_effect = Exception("Unexpected error")

            # Should not raise exception
            main_window._perform_auto_save()

            # Scene should still be marked as modified
            assert main_window._scene_modified

            # Verify error status message
            mock_status_bar.return_value.showMessage.assert_any_call(
                "Auto-saving...", 0
            )
            mock_status_bar.return_value.showMessage.assert_any_call(
                "Auto-save failed: Unexpected error", 5000
            )

    def test_start_auto_save(self, main_window):
        """Test starting auto-save functionality."""
        main_window._auto_save_enabled = False

        main_window.start_auto_save()

        assert main_window._auto_save_enabled is True

    def test_stop_auto_save(self, main_window):
        """Test stopping auto-save functionality."""
        with patch.object(main_window._auto_save_timer, "stop") as mock_stop:
            main_window.stop_auto_save()

            assert main_window._auto_save_enabled is False
            mock_stop.assert_called_once()

    def test_set_auto_save_interval(self, main_window):
        """Test setting auto-save interval."""
        new_interval = 60000  # 1 minute

        main_window.set_auto_save_interval(new_interval)

        assert main_window._auto_save_interval == new_interval

    def test_set_auto_save_interval_with_active_timer(self, main_window):
        """Test setting auto-save interval when timer is active."""
        new_interval = 60000  # 1 minute

        with patch.object(
            main_window._auto_save_timer, "isActive", return_value=True
        ), patch.object(main_window._auto_save_timer, "start") as mock_start:
            main_window.set_auto_save_interval(new_interval)

            assert main_window._auto_save_interval == new_interval
            mock_start.assert_called_once_with(new_interval)

    def test_set_auto_save_interval_with_inactive_timer(self, main_window):
        """Test setting auto-save interval when timer is inactive."""
        new_interval = 60000  # 1 minute

        with patch.object(
            main_window._auto_save_timer, "isActive", return_value=False
        ), patch.object(main_window._auto_save_timer, "start") as mock_start:
            main_window.set_auto_save_interval(new_interval)

            assert main_window._auto_save_interval == new_interval
            mock_start.assert_not_called()

    def test_save_resets_scene_modified_flag(self, main_window):
        """Test that saving resets the scene modified flag."""
        main_window._scene_modified = True
        main_window._current_file_path = Path("/test/file.json")

        with patch.object(
            main_window._session_manager, "serialize_scene_data"
        ) as mock_serialize, patch.object(
            main_window._session_manager, "save_session_to_file"
        ):
            mock_serialize.return_value = {"notes": [], "connections": []}
            main_window._save_to_file(Path("/test/file.json"))

            assert not main_window._scene_modified

    def test_load_resets_scene_modified_flag(self, main_window):
        """Test that loading resets the scene modified flag."""
        main_window._scene_modified = True

        with patch.object(
            main_window._session_manager, "load_session_from_file"
        ) as mock_load, patch.object(
            main_window._session_manager, "deserialize_scene_data"
        ), patch(
            "PyQt6.QtWidgets.QFileDialog.getOpenFileName",
            return_value=("/test/file.json", ""),
        ):
            mock_load.return_value = {"notes": [], "connections": []}
            main_window._on_load()

            assert not main_window._scene_modified
