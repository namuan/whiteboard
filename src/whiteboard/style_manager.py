"""
Style manager for the Digital Whiteboard application.

This module contains the StyleManager class which handles default styles,
style templates, and style copying functionality for notes.
"""

import json
from typing import Any
from PyQt6.QtGui import QColor
from PyQt6.QtCore import QObject, pyqtSignal

from .utils.logging_config import get_logger
from .utils.config_paths import get_styles_file_path, ensure_app_directories


class StyleManager(QObject):
    """
    Manages note styles, templates, and default settings.

    Provides functionality for:
    - Default style management
    - Style template creation and application
    - Style copying between notes
    - Style persistence and loading

    Requirements addressed:
    - 4.3: Default style settings for new notes
    - 4.4: Style template system for consistent note appearance
    """

    # Signals
    default_style_changed = pyqtSignal(dict)
    template_added = pyqtSignal(str, dict)
    template_removed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.logger = get_logger(__name__)

        # Initialize default styles and templates
        self._default_style = self._get_builtin_default_style()
        self._style_templates = self._get_builtin_templates()

        # Setup storage paths
        self._setup_storage_paths()

        # Load user customizations
        self._load_user_styles()

        self.logger.debug("StyleManager initialized")

    def _get_builtin_default_style(self) -> dict[str, Any]:
        """Get the built-in default style."""
        return {
            "background_color": QColor(255, 255, 200),  # Light yellow
            "border_color": QColor(200, 200, 150),  # Darker yellow
            "text_color": QColor(0, 0, 0),  # Black text
            "border_width": 2,
            "corner_radius": 8,
            "padding": 10,
            "font_family": "Arial",
            "font_size": 12,
            "font_bold": False,
            "font_italic": False,
            "min_width": 100,
            "min_height": 60,
        }

    def _get_builtin_templates(self) -> dict[str, dict[str, Any]]:
        """Get built-in style templates."""
        return {
            "Default": self._get_builtin_default_style(),
            "Sticky Note": {
                "background_color": QColor(255, 255, 200),
                "border_color": QColor(200, 200, 150),
                "text_color": QColor(0, 0, 0),
                "border_width": 1,
                "corner_radius": 4,
                "padding": 8,
                "font_family": "Arial",
                "font_size": 11,
                "font_bold": False,
                "font_italic": False,
                "min_width": 80,
                "min_height": 50,
            },
            "Important": {
                "background_color": QColor(255, 200, 200),
                "border_color": QColor(200, 100, 100),
                "text_color": QColor(100, 0, 0),
                "border_width": 3,
                "corner_radius": 8,
                "padding": 12,
                "font_family": "Arial",
                "font_size": 14,
                "font_bold": True,
                "font_italic": False,
                "min_width": 120,
                "min_height": 70,
            },
            "Idea": {
                "background_color": QColor(200, 220, 255),
                "border_color": QColor(150, 180, 220),
                "text_color": QColor(0, 50, 100),
                "border_width": 2,
                "corner_radius": 12,
                "padding": 10,
                "font_family": "Arial",
                "font_size": 12,
                "font_bold": False,
                "font_italic": True,
                "min_width": 100,
                "min_height": 60,
            },
            "Action Item": {
                "background_color": QColor(200, 255, 200),
                "border_color": QColor(150, 200, 150),
                "text_color": QColor(0, 100, 0),
                "border_width": 2,
                "corner_radius": 6,
                "padding": 10,
                "font_family": "Arial",
                "font_size": 12,
                "font_bold": True,
                "font_italic": False,
                "min_width": 110,
                "min_height": 65,
            },
            "Question": {
                "background_color": QColor(255, 220, 200),
                "border_color": QColor(220, 180, 150),
                "text_color": QColor(100, 50, 0),
                "border_width": 2,
                "corner_radius": 10,
                "padding": 10,
                "font_family": "Arial",
                "font_size": 12,
                "font_bold": False,
                "font_italic": False,
                "min_width": 100,
                "min_height": 60,
            },
            "Title": {
                "background_color": QColor(240, 240, 240),
                "border_color": QColor(180, 180, 180),
                "text_color": QColor(50, 50, 50),
                "border_width": 3,
                "corner_radius": 8,
                "padding": 15,
                "font_family": "Arial",
                "font_size": 16,
                "font_bold": True,
                "font_italic": False,
                "min_width": 150,
                "min_height": 80,
            },
        }

    def _setup_storage_paths(self):
        """Setup storage paths for user styles."""
        # Use OS-specific configuration directory
        self._styles_file = get_styles_file_path()
        self._config_dir = self._styles_file.parent

        # Ensure config directory exists
        ensure_app_directories()

    def _load_user_styles(self):
        """Load user customizations from file."""
        if not self._styles_file.exists():
            self.logger.debug("No user styles file found, using defaults")
            return

        try:
            with open(self._styles_file) as f:
                data = json.load(f)

            # Load default style if customized
            if "default_style" in data:
                custom_default = self._deserialize_style(data["default_style"])
                # Merge with built-in default to ensure all properties are present
                self._default_style.update(custom_default)
                self.logger.debug("Loaded custom default style")

            # Load custom templates
            if "templates" in data:
                for name, style_data in data["templates"].items():
                    if name not in self._style_templates:  # Don't override built-ins
                        self._style_templates[name] = self._deserialize_style(
                            style_data
                        )
                        self.logger.debug(f"Loaded custom template: {name}")

        except Exception as e:
            self.logger.error(f"Failed to load user styles: {e}")

    def _save_user_styles(self):
        """Save user customizations to file."""
        try:
            # Prepare data for serialization
            data = {
                "default_style": self._serialize_style(self._default_style),
                "templates": {},
            }

            # Save custom templates (exclude built-ins)
            builtin_names = set(self._get_builtin_templates().keys())
            for name, style in self._style_templates.items():
                if name not in builtin_names:
                    data["templates"][name] = self._serialize_style(style)

            # Write to file
            with open(self._styles_file, "w") as f:
                json.dump(data, f, indent=2)

            self.logger.debug("Saved user styles to file")

        except Exception as e:
            self.logger.error(f"Failed to save user styles: {e}")

    def _serialize_style(self, style: dict[str, Any]) -> dict[str, Any]:
        """Convert style dict to JSON-serializable format."""
        serialized = {}
        for key, value in style.items():
            if isinstance(value, QColor):
                serialized[key] = value.name()  # Convert to hex string
            else:
                serialized[key] = value
        return serialized

    def _deserialize_style(self, style_data: dict[str, Any]) -> dict[str, Any]:
        """Convert JSON data back to style dict with QColor objects."""
        deserialized = {}
        for key, value in style_data.items():
            if key.endswith("_color") and isinstance(value, str):
                deserialized[key] = QColor(value)  # Convert from hex string
            else:
                deserialized[key] = value
        return deserialized

    def get_default_style(self) -> dict[str, Any]:
        """
        Get the current default style for new notes.

        Returns:
            Dictionary containing default style properties
        """
        return self._default_style.copy()

    def set_default_style(self, style: dict[str, Any]) -> None:
        """
        Set the default style for new notes.

        Args:
            style: Dictionary containing style properties
        """
        # Merge with existing default to ensure all properties are present
        updated_style = self._default_style.copy()
        updated_style.update(style)
        self._default_style = updated_style

        self._save_user_styles()

        # Emit signal safely
        try:
            self.default_style_changed.emit(self._default_style.copy())
        except RuntimeError:
            # Object may have been deleted, ignore signal emission
            pass

        self.logger.debug("Default style updated")

    def get_template_names(self) -> list[str]:
        """
        Get list of available template names.

        Returns:
            List of template names
        """
        return list(self._style_templates.keys())

    def get_template_style(self, template_name: str) -> dict[str, Any] | None:
        """
        Get style for a specific template.

        Args:
            template_name: Name of the template

        Returns:
            Style dictionary if template exists, None otherwise
        """
        if template_name in self._style_templates:
            return self._style_templates[template_name].copy()
        return None

    def add_template(self, name: str, style: dict[str, Any]) -> bool:
        """
        Add a new style template.

        Args:
            name: Name for the template
            style: Style dictionary

        Returns:
            True if template was added, False if name already exists
        """
        if name in self._style_templates:
            return False

        self._style_templates[name] = style.copy()
        self._save_user_styles()

        # Emit signal safely
        try:
            self.template_added.emit(name, style.copy())
        except RuntimeError:
            # Object may have been deleted, ignore signal emission
            pass

        self.logger.debug(f"Added template: {name}")
        return True

    def update_template(self, name: str, style: dict[str, Any]) -> bool:
        """
        Update an existing template.

        Args:
            name: Name of the template
            style: New style dictionary

        Returns:
            True if template was updated, False if template doesn't exist
        """
        if name not in self._style_templates:
            return False

        # Don't allow updating built-in templates
        if name in self._get_builtin_templates():
            return False

        self._style_templates[name] = style.copy()
        self._save_user_styles()
        self.logger.debug(f"Updated template: {name}")
        return True

    def remove_template(self, name: str) -> bool:
        """
        Remove a template.

        Args:
            name: Name of the template to remove

        Returns:
            True if template was removed, False if template doesn't exist or is built-in
        """
        if name not in self._style_templates:
            return False

        # Don't allow removing built-in templates
        if name in self._get_builtin_templates():
            return False

        del self._style_templates[name]
        self._save_user_styles()

        # Emit signal safely
        try:
            self.template_removed.emit(name)
        except RuntimeError:
            # Object may have been deleted, ignore signal emission
            pass

        self.logger.debug(f"Removed template: {name}")
        return True

    def copy_style_from_note(self, source_note) -> dict[str, Any]:
        """
        Copy style from a note.

        Args:
            source_note: Note item to copy style from

        Returns:
            Copied style dictionary
        """
        if hasattr(source_note, "get_style"):
            style = source_note.get_style()
            self.logger.debug(
                f"Copied style from note {getattr(source_note, '_note_id', 'unknown')}"
            )
            return style
        return self.get_default_style()

    def apply_style_to_note(self, target_note, style: dict[str, Any]) -> None:
        """
        Apply style to a note.

        Args:
            target_note: Note item to apply style to
            style: Style dictionary to apply
        """
        if hasattr(target_note, "set_style"):
            target_note.set_style(style)
            self.logger.debug(
                f"Applied style to note {getattr(target_note, '_note_id', 'unknown')}"
            )

    def apply_template_to_note(self, target_note, template_name: str) -> bool:
        """
        Apply a template style to a note.

        Args:
            target_note: Note item to apply template to
            template_name: Name of the template to apply

        Returns:
            True if template was applied, False if template doesn't exist
        """
        template_style = self.get_template_style(template_name)
        if template_style is None:
            return False

        self.apply_style_to_note(target_note, template_style)
        self.logger.debug(f"Applied template '{template_name}' to note")
        return True

    def create_template_from_note(self, source_note, template_name: str) -> bool:
        """
        Create a new template from a note's current style.

        Args:
            source_note: Note item to copy style from
            template_name: Name for the new template

        Returns:
            True if template was created, False if name already exists
        """
        style = self.copy_style_from_note(source_note)
        return self.add_template(template_name, style)

    def get_style_summary(self, style: dict[str, Any]) -> str:
        """
        Get a human-readable summary of a style.

        Args:
            style: Style dictionary

        Returns:
            String summary of the style
        """
        bg_color = style.get("background_color", QColor())
        text_color = style.get("text_color", QColor())
        font_family = style.get("font_family", "Unknown")
        font_size = style.get("font_size", 0)

        return f"{font_family} {font_size}pt, {bg_color.name()}/{text_color.name()}"

    def is_builtin_template(self, template_name: str) -> bool:
        """
        Check if a template is built-in (cannot be modified/deleted).

        Args:
            template_name: Name of the template

        Returns:
            True if template is built-in, False otherwise
        """
        return template_name in self._get_builtin_templates()


# Global style manager instance
_style_manager = None


def get_style_manager() -> StyleManager:
    """
    Get the global style manager instance.

    Returns:
        StyleManager instance
    """
    global _style_manager
    if _style_manager is None:
        _style_manager = StyleManager()
    return _style_manager
