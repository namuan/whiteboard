"""
Tests for configuration path utilities.

This module tests the OS-specific configuration directory functionality.
"""

import tempfile
import sys
from pathlib import Path
from unittest.mock import patch

from src.whiteboard.utils.config_paths import (
    get_app_config_dir,
    get_app_data_dir,
    get_app_cache_dir,
    get_app_log_dir,
    get_styles_file_path,
    get_app_settings_file_path,
    get_recent_files_path,
    ensure_app_directories,
    get_platform_info,
)


class TestConfigPaths:
    """Test configuration path utilities."""

    def test_get_app_config_dir_macos(self):
        """Test config directory on macOS."""
        with patch("sys.platform", "darwin"):
            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = Path("/Users/testuser")

                config_dir = get_app_config_dir()
                expected = Path(
                    "/Users/testuser/Library/Application Support/DigitalWhiteboard"
                )
                assert config_dir == expected

    def test_get_app_config_dir_windows(self):
        """Test config directory on Windows."""
        with patch("sys.platform", "win32"):
            with patch.dict(
                "os.environ", {"APPDATA": "C:\\Users\\testuser\\AppData\\Roaming"}
            ):
                config_dir = get_app_config_dir()
                # Check the path components rather than exact string match
                assert "testuser" in str(config_dir)
                assert "AppData" in str(config_dir)
                assert "Roaming" in str(config_dir)
                assert "DigitalWhiteboard" in str(config_dir)

    def test_get_app_config_dir_linux(self):
        """Test config directory on Linux."""
        with patch("sys.platform", "linux"):
            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = Path("/home/testuser")

                config_dir = get_app_config_dir()
                expected = Path("/home/testuser/.config/DigitalWhiteboard")
                assert config_dir == expected

    def test_get_app_config_dir_linux_xdg(self):
        """Test config directory on Linux with XDG_CONFIG_HOME."""
        with patch("sys.platform", "linux"):
            with patch.dict("os.environ", {"XDG_CONFIG_HOME": "/custom/config"}):
                config_dir = get_app_config_dir()
                expected = Path("/custom/config/DigitalWhiteboard")
                assert config_dir == expected

    def test_get_app_data_dir_macos(self):
        """Test data directory on macOS."""
        with patch("sys.platform", "darwin"):
            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = Path("/Users/testuser")

                data_dir = get_app_data_dir()
                expected = Path(
                    "/Users/testuser/Library/Application Support/DigitalWhiteboard"
                )
                assert data_dir == expected

    def test_get_app_data_dir_windows(self):
        """Test data directory on Windows."""
        with patch("sys.platform", "win32"):
            with patch.dict(
                "os.environ", {"LOCALAPPDATA": "C:\\Users\\testuser\\AppData\\Local"}
            ):
                data_dir = get_app_data_dir()
                # Check the path components rather than exact string match
                assert "testuser" in str(data_dir)
                assert "AppData" in str(data_dir)
                assert "Local" in str(data_dir)
                assert "DigitalWhiteboard" in str(data_dir)

    def test_get_app_data_dir_linux(self):
        """Test data directory on Linux."""
        with patch("sys.platform", "linux"):
            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = Path("/home/testuser")

                data_dir = get_app_data_dir()
                expected = Path("/home/testuser/.local/share/DigitalWhiteboard")
                assert data_dir == expected

    def test_get_app_cache_dir_macos(self):
        """Test cache directory on macOS."""
        with patch("sys.platform", "darwin"):
            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = Path("/Users/testuser")

                cache_dir = get_app_cache_dir()
                expected = Path("/Users/testuser/Library/Caches/DigitalWhiteboard")
                assert cache_dir == expected

    def test_get_app_cache_dir_windows(self):
        """Test cache directory on Windows."""
        with patch("sys.platform", "win32"):
            with patch.dict(
                "os.environ", {"LOCALAPPDATA": "C:\\Users\\testuser\\AppData\\Local"}
            ):
                cache_dir = get_app_cache_dir()
                # Check the path components rather than exact string match
                assert "testuser" in str(cache_dir)
                assert "AppData" in str(cache_dir)
                assert "Local" in str(cache_dir)
                assert "DigitalWhiteboard" in str(cache_dir)
                assert "Cache" in str(cache_dir)

    def test_get_app_cache_dir_linux(self):
        """Test cache directory on Linux."""
        with patch("sys.platform", "linux"):
            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = Path("/home/testuser")

                cache_dir = get_app_cache_dir()
                expected = Path("/home/testuser/.cache/DigitalWhiteboard")
                assert cache_dir == expected

    def test_get_app_log_dir_macos(self):
        """Test log directory on macOS."""
        with patch("sys.platform", "darwin"):
            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = Path("/Users/testuser")

                log_dir = get_app_log_dir()
                expected = Path("/Users/testuser/Library/Logs/DigitalWhiteboard")
                assert log_dir == expected

    def test_get_app_log_dir_windows(self):
        """Test log directory on Windows."""
        with patch("sys.platform", "win32"):
            with patch.dict(
                "os.environ", {"LOCALAPPDATA": "C:\\Users\\testuser\\AppData\\Local"}
            ):
                log_dir = get_app_log_dir()
                # Check the path components rather than exact string match
                assert "testuser" in str(log_dir)
                assert "AppData" in str(log_dir)
                assert "Local" in str(log_dir)
                assert "DigitalWhiteboard" in str(log_dir)
                assert "Logs" in str(log_dir)

    def test_get_app_log_dir_linux(self):
        """Test log directory on Linux."""
        with patch("sys.platform", "linux"):
            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = Path("/home/testuser")

                log_dir = get_app_log_dir()
                expected = Path("/home/testuser/.local/share/DigitalWhiteboard/logs")
                assert log_dir == expected

    def test_file_path_functions(self):
        """Test specific file path functions."""
        with patch(
            "src.whiteboard.utils.config_paths.get_app_config_dir"
        ) as mock_config_dir:
            mock_config_dir.return_value = Path("/test/config")

            assert get_styles_file_path() == Path("/test/config/styles.json")
            assert get_app_settings_file_path() == Path("/test/config/settings.json")
            assert get_recent_files_path() == Path("/test/config/recent_files.json")

    def test_ensure_app_directories(self):
        """Test directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            with patch(
                "src.whiteboard.utils.config_paths.get_app_config_dir"
            ) as mock_config:
                with patch(
                    "src.whiteboard.utils.config_paths.get_app_data_dir"
                ) as mock_data:
                    with patch(
                        "src.whiteboard.utils.config_paths.get_app_cache_dir"
                    ) as mock_cache:
                        with patch(
                            "src.whiteboard.utils.config_paths.get_app_log_dir"
                        ) as mock_log:
                            mock_config.return_value = temp_path / "config"
                            mock_data.return_value = temp_path / "data"
                            mock_cache.return_value = temp_path / "cache"
                            mock_log.return_value = temp_path / "logs"

                            ensure_app_directories()

                            assert (temp_path / "config").exists()
                            assert (temp_path / "data").exists()
                            assert (temp_path / "cache").exists()
                            assert (temp_path / "logs").exists()

    def _verify_platform_info_keys(self, info):
        """Helper to verify platform info contains required keys."""
        required_keys = [
            "platform",
            "config_dir",
            "data_dir",
            "cache_dir",
            "log_dir",
            "styles_file",
            "settings_file",
        ]
        for key in required_keys:
            assert key in info

    def _verify_platform_info_values(self, info):
        """Helper to verify platform info values are correct."""
        assert info["platform"] == sys.platform
        assert isinstance(info["config_dir"], str)
        assert isinstance(info["data_dir"], str)

    def test_get_platform_info(self):
        """Test platform information gathering."""
        info = get_platform_info()
        self._verify_platform_info_keys(info)
        self._verify_platform_info_values(info)


class TestRealPlatformPaths:
    """Test paths on the actual current platform."""

    def _get_all_directories(self):
        """Helper to get all directory paths."""
        return {
            "config": get_app_config_dir(),
            "data": get_app_data_dir(),
            "cache": get_app_cache_dir(),
            "log": get_app_log_dir(),
        }

    def _verify_paths_absolute(self, dirs):
        """Helper to verify all paths are absolute."""
        for path in dirs.values():
            assert path.is_absolute()

    def _verify_paths_contain_app_name(self, dirs):
        """Helper to verify paths contain app name."""
        for path in dirs.values():
            assert "DigitalWhiteboard" in str(path)

    def _verify_file_paths(self, config_dir):
        """Helper to verify file paths are correct."""
        files = {
            "styles": get_styles_file_path(),
            "settings": get_app_settings_file_path(),
            "recent": get_recent_files_path(),
        }

        for file_path in files.values():
            assert file_path.parent == config_dir

        assert files["styles"].name == "styles.json"
        assert files["settings"].name == "settings.json"
        assert files["recent"].name == "recent_files.json"

    def test_current_platform_paths(self):
        """Test that paths are generated correctly for current platform."""
        dirs = self._get_all_directories()

        self._verify_paths_absolute(dirs)
        self._verify_paths_contain_app_name(dirs)

        # Paths should be different (except on macOS where config and data are the same)
        if sys.platform != "darwin":
            assert dirs["config"] != dirs["data"]

        self._verify_file_paths(dirs["config"])
