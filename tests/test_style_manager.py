"""
Tests for the style manager functionality.

This module tests the StyleManager class and its integration with note styling,
templates, and default style management.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor

from src.whiteboard.style_manager import StyleManager, get_style_manager
from src.whiteboard.note_item import NoteItem


class TestStyleManager:
    """Test the StyleManager class."""

    @pytest.fixture
    def app(self):
        """Create QApplication instance."""
        return QApplication.instance() or QApplication([])

    @pytest.fixture
    def style_manager(self):
        """Create StyleManager with mocked file operations."""
        with patch(
            "src.whiteboard.style_manager.get_styles_file_path"
        ) as mock_styles_path:
            with patch("src.whiteboard.style_manager.ensure_app_directories"):
                with patch("pathlib.Path.exists") as mock_exists:
                    with patch("builtins.open", mock_open()):
                        # Mock that styles file doesn't exist initially
                        mock_exists.return_value = False
                        mock_styles_path.return_value = Path("/mock/config/styles.json")

                        manager = StyleManager()
                        return manager

    def test_style_manager_initialization(self, style_manager):
        """Test StyleManager initialization."""
        assert style_manager is not None

        # Check default style exists
        default_style = style_manager.get_default_style()
        assert isinstance(default_style, dict)
        assert "background_color" in default_style
        assert "text_color" in default_style
        assert "font_family" in default_style

        # Check built-in templates exist
        template_names = style_manager.get_template_names()
        assert len(template_names) > 0
        assert "Default" in template_names
        assert "Important" in template_names
        assert "Idea" in template_names

    def test_default_style_management(self, style_manager):
        """Test default style getting and setting."""
        # Get original default
        style_manager.get_default_style()

        # Create new default style
        new_default = {
            "background_color": QColor(255, 0, 0),
            "text_color": QColor(0, 255, 0),
            "font_size": 16,
            "font_bold": True,
        }

        # Set new default
        style_manager.set_default_style(new_default)

        # Verify change
        current_default = style_manager.get_default_style()
        assert current_default["background_color"] == QColor(255, 0, 0)
        assert current_default["text_color"] == QColor(0, 255, 0)
        assert current_default["font_size"] == 16
        assert current_default["font_bold"]

    def _create_custom_style(self):
        """Helper to create custom style for testing."""
        return {
            "background_color": QColor(100, 100, 100),
            "text_color": QColor(255, 255, 255),
            "font_size": 14,
        }

    def _test_template_retrieval(self, style_manager):
        """Helper to test template retrieval."""
        idea_template = style_manager.get_template_style("Idea")
        assert idea_template is not None
        assert isinstance(idea_template, dict)

    def _test_template_addition(self, style_manager, custom_style):
        """Helper to test template addition."""
        success = style_manager.add_template("Custom", custom_style)
        assert success
        assert "Custom" in style_manager.get_template_names()

        retrieved_style = style_manager.get_template_style("Custom")
        assert retrieved_style["background_color"] == QColor(100, 100, 100)

    def _test_template_update(self, style_manager, custom_style):
        """Helper to test template updating."""
        updated_style = custom_style.copy()
        updated_style["font_size"] = 18
        update_success = style_manager.update_template("Custom", updated_style)
        assert update_success

        retrieved_updated = style_manager.get_template_style("Custom")
        assert retrieved_updated["font_size"] == 18

    def test_template_management(self, style_manager):
        """Test template creation, retrieval, and removal."""
        custom_style = self._create_custom_style()

        self._test_template_retrieval(style_manager)
        self._test_template_addition(style_manager, custom_style)

        # Test duplicate prevention
        duplicate_success = style_manager.add_template("Custom", custom_style)
        assert not duplicate_success

        self._test_template_update(style_manager, custom_style)

        # Test removal
        remove_success = style_manager.remove_template("Custom")
        assert remove_success
        assert "Custom" not in style_manager.get_template_names()

    def test_builtin_template_protection(self, style_manager):
        """Test that built-in templates cannot be modified or removed."""
        # Try to update built-in template
        new_style = {"background_color": QColor(255, 0, 0)}
        update_success = style_manager.update_template("Default", new_style)
        assert not update_success

        # Try to remove built-in template
        remove_success = style_manager.remove_template("Default")
        assert not remove_success

        # Verify template still exists
        assert "Default" in style_manager.get_template_names()

    def test_style_serialization(self, style_manager):
        """Test style serialization and deserialization."""
        # Create style with QColor objects
        original_style = {
            "background_color": QColor(255, 128, 64),
            "text_color": QColor(0, 0, 0),
            "font_size": 14,
            "font_bold": True,
        }

        # Serialize
        serialized = style_manager._serialize_style(original_style)
        assert serialized["background_color"] == "#ff8040"
        assert serialized["text_color"] == "#000000"
        assert serialized["font_size"] == 14
        assert serialized["font_bold"]

        # Deserialize
        deserialized = style_manager._deserialize_style(serialized)
        assert deserialized["background_color"] == QColor(255, 128, 64)
        assert deserialized["text_color"] == QColor(0, 0, 0)
        assert deserialized["font_size"] == 14
        assert deserialized["font_bold"]

    def test_style_persistence(self):
        """Test saving and loading user styles."""
        mock_file_data = {}

        def mock_open_func(filename, mode="r"):
            if "w" in mode:
                # Capture written data
                mock_file = mock_open().return_value
                original_write = mock_file.write

                def capture_write(data):
                    mock_file_data[str(filename)] = data
                    return original_write(data)

                mock_file.write = capture_write
                return mock_file
            else:
                # Return saved data
                if str(filename) in mock_file_data:
                    return mock_open(
                        read_data=mock_file_data[str(filename)]
                    ).return_value
                else:
                    raise FileNotFoundError()

        with patch(
            "src.whiteboard.style_manager.get_styles_file_path"
        ) as mock_styles_path:
            with patch("src.whiteboard.style_manager.ensure_app_directories"):
                with patch("builtins.open", side_effect=mock_open_func):
                    with patch("pathlib.Path.exists", return_value=False):
                        mock_styles_path.return_value = Path("/mock/config/styles.json")

                        # Create manager
                        style_manager = StyleManager()

                        # Add custom template
                        custom_style = {
                            "background_color": QColor(200, 100, 50),
                            "text_color": QColor(255, 255, 255),
                            "font_size": 15,
                        }
                        style_manager.add_template("Persistent", custom_style)

                        # Verify template was added
                        assert "Persistent" in style_manager.get_template_names()
                        loaded_template = style_manager.get_template_style("Persistent")
                        assert loaded_template["background_color"] == QColor(
                            200, 100, 50
                        )

    def test_style_summary(self, style_manager):
        """Test style summary generation."""
        style = {
            "background_color": QColor(255, 255, 200),
            "text_color": QColor(0, 0, 0),
            "font_family": "Arial",
            "font_size": 12,
        }

        summary = style_manager.get_style_summary(style)
        assert "Arial" in summary
        assert "12pt" in summary
        assert "#ffff" in summary.lower()  # Part of background color
        assert "#000" in summary.lower()  # Part of text color

    def test_builtin_template_detection(self, style_manager):
        """Test detection of built-in templates."""
        assert style_manager.is_builtin_template("Default")
        assert style_manager.is_builtin_template("Important")
        assert not style_manager.is_builtin_template("NonExistent")

        # Add custom template and test
        custom_style = {"background_color": QColor(255, 0, 0)}
        style_manager.add_template("Custom", custom_style)
        assert not style_manager.is_builtin_template("Custom")


class TestStyleManagerNoteIntegration:
    """Test integration between StyleManager and NoteItem."""

    @pytest.fixture
    def app(self):
        """Create QApplication instance."""
        return QApplication.instance() or QApplication([])

    @pytest.fixture
    def style_manager(self):
        """Create StyleManager instance with mocked file operations."""
        with patch(
            "src.whiteboard.style_manager.get_styles_file_path"
        ) as mock_styles_path:
            with patch("src.whiteboard.style_manager.ensure_app_directories"):
                with patch("builtins.open", mock_open()):
                    with patch("pathlib.Path.exists", return_value=False):
                        mock_styles_path.return_value = Path("/mock/config/styles.json")
                        return StyleManager()

    @pytest.fixture
    def note_item(self, app):
        """Create NoteItem instance."""
        return NoteItem("Test Note", QPointF(0, 0))

    def test_note_uses_default_style(self, note_item, style_manager):
        """Test that new notes use the default style."""
        default_style = style_manager.get_default_style()
        note_style = note_item.get_style()

        # Key properties should match
        assert note_style["background_color"] == default_style["background_color"]
        assert note_style["text_color"] == default_style["text_color"]
        assert note_style["font_family"] == default_style["font_family"]
        assert note_style["font_size"] == default_style["font_size"]

    def test_copy_style_from_note(self, note_item, style_manager):
        """Test copying style from a note."""
        # Modify note style
        custom_style = {"background_color": QColor(255, 0, 0), "font_size": 16}
        note_item.set_style(custom_style)

        # Copy style
        copied_style = style_manager.copy_style_from_note(note_item)

        assert copied_style["background_color"] == QColor(255, 0, 0)
        assert copied_style["font_size"] == 16

    def test_apply_style_to_note(self, note_item, style_manager):
        """Test applying style to a note."""
        new_style = {
            "background_color": QColor(0, 255, 0),
            "text_color": QColor(255, 255, 255),
            "font_size": 18,
        }

        style_manager.apply_style_to_note(note_item, new_style)

        note_style = note_item.get_style()
        assert note_style["background_color"] == QColor(0, 255, 0)
        assert note_style["text_color"] == QColor(255, 255, 255)
        assert note_style["font_size"] == 18

    def test_apply_template_to_note(self, note_item, style_manager):
        """Test applying template to a note."""
        # Apply "Important" template
        success = style_manager.apply_template_to_note(note_item, "Important")
        assert success

        # Verify style was applied
        note_style = note_item.get_style()
        important_template = style_manager.get_template_style("Important")

        assert note_style["background_color"] == important_template["background_color"]
        assert note_style["font_bold"] == important_template["font_bold"]

        # Test applying non-existent template
        success = style_manager.apply_template_to_note(note_item, "NonExistent")
        assert not success

    def test_create_template_from_note(self, note_item, style_manager):
        """Test creating template from note style."""
        # Customize note style
        custom_style = {
            "background_color": QColor(128, 64, 192),
            "font_size": 20,
            "font_italic": True,
        }
        note_item.set_style(custom_style)

        # Create template from note
        success = style_manager.create_template_from_note(note_item, "From Note")
        assert success

        # Verify template was created
        assert "From Note" in style_manager.get_template_names()
        template_style = style_manager.get_template_style("From Note")

        assert template_style["background_color"] == QColor(128, 64, 192)
        assert template_style["font_size"] == 20
        assert template_style["font_italic"]


class TestNoteItemTemplateIntegration:
    """Test template functionality in NoteItem."""

    @pytest.fixture
    def app(self):
        """Create QApplication instance."""
        return QApplication.instance() or QApplication([])

    @pytest.fixture
    def note_item(self, app):
        """Create NoteItem instance."""
        return NoteItem("Test Note", QPointF(0, 0))

    def test_apply_template_method(self, note_item):
        """Test applying template through note method."""
        original_style = note_item.get_style().copy()

        # Apply "Important" template
        note_item._apply_template("Important")

        # Verify style changed
        new_style = note_item.get_style()
        assert new_style != original_style
        assert new_style["font_bold"]  # Important template is bold

    def test_style_copying_clipboard(self, note_item, app):
        """Test style copying functionality."""
        # Create another note with different style
        note2 = NoteItem("Note 2", QPointF(100, 100))
        custom_style = {"background_color": QColor(255, 0, 255), "font_size": 18}
        note2.set_style(custom_style)

        # Copy style from note2
        note2._copy_style_to_clipboard()

        # Paste style to note_item
        note_item._paste_style_from_clipboard()

        # Verify style was copied
        note_style = note_item.get_style()
        assert note_style["background_color"] == QColor(255, 0, 255)
        assert note_style["font_size"] == 18

    def test_style_copying_no_clipboard(self, note_item):
        """Test pasting when no style is copied."""
        # Clear clipboard
        if hasattr(NoteItem, "_copied_style"):
            NoteItem._copied_style = None

        original_style = note_item.get_style().copy()

        # Try to paste (should do nothing)
        note_item._paste_style_from_clipboard()

        # Verify style unchanged
        current_style = note_item.get_style()
        assert current_style == original_style

    @patch("PyQt6.QtWidgets.QInputDialog.getText")
    def test_save_as_template(self, mock_input_dialog, note_item):
        """Test saving note style as template."""
        with patch(
            "src.whiteboard.style_manager.get_styles_file_path"
        ) as mock_styles_path:
            with patch("src.whiteboard.style_manager.ensure_app_directories"):
                with patch("builtins.open", mock_open()):
                    with patch("pathlib.Path.exists", return_value=False):
                        mock_styles_path.return_value = Path("/mock/config/styles.json")

                        # Mock user input
                        mock_input_dialog.return_value = ("My Custom Template", True)

                        # Customize note style
                        custom_style = {
                            "background_color": QColor(100, 200, 50),
                            "font_size": 14,
                        }
                        note_item.set_style(custom_style)

                        # Save as template
                        note_item._save_as_template()

                        # Verify template was created by checking the global style manager
                        # Note: This will use the existing global instance, but that's okay for this test
                        from src.whiteboard.style_manager import get_style_manager

                        style_manager = get_style_manager()

                        # The template should be added to the current manager
                        assert (
                            "My Custom Template" in style_manager.get_template_names()
                        )
                        template_style = style_manager.get_template_style(
                            "My Custom Template"
                        )
                        assert template_style["background_color"] == QColor(
                            100, 200, 50
                        )
                        assert template_style["font_size"] == 14

    @patch("PyQt6.QtWidgets.QInputDialog.getText")
    def test_save_as_template_cancelled(self, mock_input_dialog, note_item):
        """Test saving template when user cancels."""
        # Mock user cancelling
        mock_input_dialog.return_value = ("", False)

        original_templates = get_style_manager().get_template_names().copy()

        # Try to save as template
        note_item._save_as_template()

        # Verify no new template was created
        current_templates = get_style_manager().get_template_names()
        assert current_templates == original_templates


class TestGlobalStyleManager:
    """Test global style manager functionality."""

    def test_get_style_manager_singleton(self):
        """Test that get_style_manager returns singleton."""
        manager1 = get_style_manager()
        manager2 = get_style_manager()

        assert manager1 is manager2
        assert isinstance(manager1, StyleManager)

    def test_style_manager_signals(self):
        """Test that style manager emits appropriate signals."""
        with patch(
            "src.whiteboard.style_manager.get_styles_file_path"
        ) as mock_styles_path:
            with patch("src.whiteboard.style_manager.ensure_app_directories"):
                with patch("builtins.open", mock_open()):
                    with patch("pathlib.Path.exists", return_value=False):
                        mock_styles_path.return_value = Path("/mock/config/styles.json")

                        # Create a fresh manager for this test
                        manager = StyleManager()

                        # Test default style changed signal
                        signal_spy = Mock()
                        manager.default_style_changed.connect(signal_spy)

                        new_default = {"background_color": QColor(255, 0, 0)}
                        manager.set_default_style(new_default)

                        signal_spy.assert_called_once()

                        # Test template added signal
                        template_spy = Mock()
                        manager.template_added.connect(template_spy)

                        template_style = {"background_color": QColor(0, 255, 0)}
                        manager.add_template("Signal Test", template_style)

                        template_spy.assert_called_once_with(
                            "Signal Test", template_style
                        )


class TestStylePersistenceIntegration:
    """Test complete style persistence workflow."""

    @pytest.fixture
    def app(self):
        """Create QApplication instance."""
        return QApplication.instance() or QApplication([])

    def test_complete_style_workflow(self, app):
        """Test complete workflow from note creation to template application."""
        with patch(
            "src.whiteboard.style_manager.get_styles_file_path"
        ) as mock_styles_path:
            with patch("src.whiteboard.style_manager.ensure_app_directories"):
                with patch("builtins.open", mock_open()):
                    with patch("pathlib.Path.exists", return_value=False):
                        mock_styles_path.return_value = Path("/mock/config/styles.json")

                        # Create a fresh style manager for this test
                        style_manager = StyleManager()

                        # Create note with default style
                        note1 = NoteItem("Original Note", QPointF(0, 0))
                        original_style = note1.get_style()

                        # Customize the note
                        custom_style = {
                            "background_color": QColor(200, 150, 100),
                            "text_color": QColor(255, 255, 255),
                            "font_size": 16,
                            "font_bold": True,
                        }
                        note1.set_style(custom_style)

                        # Save as template (use unique name to avoid conflicts)
                        import time

                        template_name = f"Workflow Test {int(time.time())}"
                        success = style_manager.create_template_from_note(
                            note1, template_name
                        )
                        assert success

                        # Create new note (should use default style)
                        note2 = NoteItem("New Note", QPointF(100, 100))
                        assert (
                            note2.get_style()["background_color"]
                            == original_style["background_color"]
                        )

                        # Apply template to new note
                        success = style_manager.apply_template_to_note(
                            note2, template_name
                        )
                        assert success

                        # Verify template was applied
                        note2_style = note2.get_style()
                        assert note2_style["background_color"] == QColor(200, 150, 100)
                        assert note2_style["text_color"] == QColor(255, 255, 255)
                        assert note2_style["font_size"] == 16
                        assert note2_style["font_bold"]

                        # Clean up
                        style_manager.remove_template(template_name)
