"""
Tests for the MainWindow class.
"""

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt

from src.whiteboard.main_window import MainWindow


@pytest.fixture
def app():
    """Create QApplication instance for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # Don't quit the app as it might be used by other tests


@pytest.fixture
def main_window(app):
    """Create MainWindow instance for testing."""
    window = MainWindow()
    yield window
    window.close()


def test_main_window_initialization(main_window):
    """Test that MainWindow initializes correctly."""
    assert main_window.windowTitle() == "Digital Whiteboard"
    assert main_window.minimumSize().width() == 800
    assert main_window.minimumSize().height() == 600


def test_fullscreen_toggle(main_window):
    """Test fullscreen mode toggle functionality."""
    # Initially not in fullscreen
    assert not main_window._is_fullscreen

    # Toggle to fullscreen
    main_window.toggle_fullscreen()
    assert main_window._is_fullscreen
    assert main_window._fullscreen_action.isChecked()

    # Toggle back to normal
    main_window.toggle_fullscreen()
    assert not main_window._is_fullscreen
    assert not main_window._fullscreen_action.isChecked()


def test_menu_bar_exists(main_window):
    """Test that menu bar is properly set up."""
    menubar = main_window.menuBar()
    assert menubar is not None

    # Check that main menus exist
    menu_titles = [action.text() for action in menubar.actions() if action.menu()]
    assert "&File" in menu_titles
    assert "&Edit" in menu_titles
    assert "&View" in menu_titles


def test_toolbar_exists(main_window):
    """Test that toolbar is properly set up."""
    from PyQt6.QtWidgets import QToolBar

    toolbars = main_window.findChildren(QToolBar)
    assert len(toolbars) > 0


def test_status_bar_exists(main_window):
    """Test that status bar is properly set up."""
    status_bar = main_window.statusBar()
    assert status_bar is not None
    assert "Ready" in status_bar.currentMessage()
    assert "Double-click" in status_bar.currentMessage()


def test_f11_key_toggles_fullscreen(main_window, app):
    """Test that F11 key toggles fullscreen mode."""
    # Initially not in fullscreen
    assert not main_window._is_fullscreen

    # Simulate F11 key press
    QTest.keyPress(main_window, Qt.Key.Key_F11)
    app.processEvents()

    # Should now be in fullscreen
    assert main_window._is_fullscreen
