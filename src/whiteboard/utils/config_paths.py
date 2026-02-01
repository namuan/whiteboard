"""
Configuration path utilities for the Digital Whiteboard application.

This module provides cross-platform configuration directory paths following
OS-specific conventions for storing application data and configuration files.
"""

import os
import sys
from pathlib import Path


def get_app_config_dir() -> Path:
    """
    Get the application configuration directory following OS conventions.

    Returns:
        Path to the application configuration directory

    OS-specific locations:
    - Windows: %APPDATA%/DigitalWhiteboard
    - macOS: ~/Library/Application Support/DigitalWhiteboard
    - Linux: ~/.config/DigitalWhiteboard
    """
    app_name = "DigitalWhiteboard"

    if sys.platform == "win32":
        # Windows: Use APPDATA
        base_dir = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base_dir / app_name

    elif sys.platform == "darwin":
        # macOS: Use Application Support
        return Path.home() / "Library" / "Application Support" / app_name

    else:
        # Linux and other Unix-like systems: Use XDG Base Directory
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config_home:
            base_dir = Path(xdg_config_home)
        else:
            base_dir = Path.home() / ".config"
        return base_dir / app_name


def get_app_data_dir() -> Path:
    """
    Get the application data directory following OS conventions.

    Returns:
        Path to the application data directory

    OS-specific locations:
    - Windows: %LOCALAPPDATA%/DigitalWhiteboard
    - macOS: ~/Library/Application Support/DigitalWhiteboard
    - Linux: ~/.local/share/DigitalWhiteboard
    """
    app_name = "DigitalWhiteboard"

    if sys.platform == "win32":
        # Windows: Use LOCALAPPDATA for data files
        base_dir = Path(
            os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
        )
        return base_dir / app_name

    elif sys.platform == "darwin":
        # macOS: Use Application Support (same as config)
        return Path.home() / "Library" / "Application Support" / app_name

    else:
        # Linux and other Unix-like systems: Use XDG Base Directory
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            base_dir = Path(xdg_data_home)
        else:
            base_dir = Path.home() / ".local" / "share"
        return base_dir / app_name


def get_app_cache_dir() -> Path:
    """
    Get the application cache directory following OS conventions.

    Returns:
        Path to the application cache directory

    OS-specific locations:
    - Windows: %LOCALAPPDATA%/DigitalWhiteboard/Cache
    - macOS: ~/Library/Caches/DigitalWhiteboard
    - Linux: ~/.cache/DigitalWhiteboard
    """
    app_name = "DigitalWhiteboard"

    if sys.platform == "win32":
        # Windows: Use LOCALAPPDATA/Cache
        base_dir = Path(
            os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
        )
        return base_dir / app_name / "Cache"

    elif sys.platform == "darwin":
        # macOS: Use Caches directory
        return Path.home() / "Library" / "Caches" / app_name

    else:
        # Linux and other Unix-like systems: Use XDG Base Directory
        xdg_cache_home = os.environ.get("XDG_CACHE_HOME")
        if xdg_cache_home:
            base_dir = Path(xdg_cache_home)
        else:
            base_dir = Path.home() / ".cache"
        return base_dir / app_name


def get_app_log_dir() -> Path:
    """
    Get the application log directory following OS conventions.

    Returns:
        Path to the application log directory

    OS-specific locations:
    - Windows: %LOCALAPPDATA%/DigitalWhiteboard/Logs
    - macOS: ~/Library/Logs/DigitalWhiteboard
    - Linux: ~/.local/share/DigitalWhiteboard/logs (or XDG_DATA_HOME)
    """
    app_name = "DigitalWhiteboard"

    if sys.platform == "win32":
        # Windows: Use LOCALAPPDATA/Logs
        base_dir = Path(
            os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
        )
        return base_dir / app_name / "Logs"

    elif sys.platform == "darwin":
        # macOS: Use dedicated Logs directory
        return Path.home() / "Library" / "Logs" / app_name

    else:
        # Linux: Use data directory with logs subdirectory
        return get_app_data_dir() / "logs"


def ensure_app_directories() -> None:
    """
    Ensure all application directories exist.

    Creates the configuration, data, cache, and log directories if they don't exist.
    """
    directories = [
        get_app_config_dir(),
        get_app_data_dir(),
        get_app_cache_dir(),
        get_app_log_dir(),
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def get_styles_file_path() -> Path:
    """
    Get the path to the styles configuration file.

    Returns:
        Path to styles.json file in the config directory
    """
    return get_app_config_dir() / "styles.json"


def get_app_settings_file_path() -> Path:
    """
    Get the path to the main application settings file.

    Returns:
        Path to settings.json file in the config directory
    """
    return get_app_config_dir() / "settings.json"


def get_recent_files_path() -> Path:
    """
    Get the path to the recent files list.

    Returns:
        Path to recent_files.json in the config directory
    """
    return get_app_config_dir() / "recent_files.json"


def get_app_state_file_path() -> Path:
    """
    Get the path to the application state file.

    The state file stores application-level state such as the last opened document.
    This follows OS-specific conventions for storing application data.

    Returns:
        Path to app_state.json in the config directory
    """
    return get_app_config_dir() / "app_state.json"


def get_platform_info() -> dict:
    """
    Get information about the current platform and configuration paths.

    Returns:
        Dictionary with platform and path information
    """
    return {
        "platform": sys.platform,
        "config_dir": str(get_app_config_dir()),
        "data_dir": str(get_app_data_dir()),
        "cache_dir": str(get_app_cache_dir()),
        "log_dir": str(get_app_log_dir()),
        "styles_file": str(get_styles_file_path()),
        "settings_file": str(get_app_settings_file_path()),
        "state_file": str(get_app_state_file_path()),
    }
