"""
Note-related commands for undo/redo support.
"""

from __future__ import annotations

from typing import Any
from PyQt6.QtCore import QPointF

from ..utils.logging_config import get_logger
from .base import Command, point_to_tuple
from ..note_item import NoteItem
# Avoid circular import at runtime; use Any for scene/canvas
# from ..canvas import WhiteboardCanvas, WhiteboardScene


class CreateNoteCommand(Command):
    def __init__(
        self,
        scene: Any,
        canvas: Any,
        position: QPointF,
        text: str = "",
        style: dict[str, Any] | None = None,
        description: str = "Create note",
    ) -> None:
        super().__init__(description=description)
        self._logger = get_logger(__name__)
        self._scene = scene
        self._canvas = canvas
        self._position = QPointF(position)
        self._text = text
        self._style = style or {}
        self._note: NoteItem | None = None
        self.payload = {
            "position": point_to_tuple(self._position),
            "text": self._text,
            "style": self._style,
        }

    def execute(self) -> None:
        note = NoteItem(self._text, self._position)
        if self._style:
            note.set_style(self._style)
        self._scene.addItem(note)
        # Connect canvas-level signals for hover etc.
        try:
            self._canvas._connect_note_signals(note)
        except Exception:
            pass
        self._note = note
        self._logger.info(
            f"Note created via command at ({self._position.x():.1f}, {self._position.y():.1f})"
        )

    def undo(self) -> None:
        if not self._note:
            return
        # Delete connections first
        try:
            self._canvas.delete_connections_for_item(self._note)
        except Exception:
            pass
        # Remove from scene
        if self._note.scene():
            self._note.scene().removeItem(self._note)
        self._logger.info("CreateNoteCommand undone: note removed")

    def redo(self) -> None:
        # Re-create note with same payload
        self.execute()


class MoveNoteCommand(Command):
    def __init__(
        self,
        note: NoteItem,
        old_pos: QPointF,
        new_pos: QPointF,
        description: str = "Move note",
    ) -> None:
        super().__init__(description=description)
        self._logger = get_logger(__name__)
        self._note = note
        self._old_pos = QPointF(old_pos)
        self._new_pos = QPointF(new_pos)
        self.payload = {
            "note_id": getattr(note, "_note_id", id(note)),
            "old_pos": point_to_tuple(self._old_pos),
            "new_pos": point_to_tuple(self._new_pos),
        }

    def execute(self) -> None:
        self._note.setPos(self._new_pos)
        self._logger.debug(
            f"MoveNoteCommand execute: ({self._old_pos.x():.1f},{self._old_pos.y():.1f}) -> ({self._new_pos.x():.1f},{self._new_pos.y():.1f})"
        )

    def undo(self) -> None:
        self._note.setPos(self._old_pos)
        self._logger.debug(
            f"MoveNoteCommand undo: revert to ({self._old_pos.x():.1f},{self._old_pos.y():.1f})"
        )


class UpdateNoteTextCommand(Command):
    def __init__(self, note: NoteItem, old_text: str, new_text: str) -> None:
        super().__init__(description="Update note text")
        self._logger = get_logger(__name__)
        self._note = note
        self._old_text = old_text
        self._new_text = new_text
        self.payload = {
            "note_id": getattr(note, "_note_id", id(note)),
            "old_text": old_text,
            "new_text": new_text,
        }

    def execute(self) -> None:
        self._note.set_text(self._new_text)
        self._logger.debug("UpdateNoteTextCommand execute")

    def undo(self) -> None:
        self._note.set_text(self._old_text)
        self._logger.debug("UpdateNoteTextCommand undo")


class UpdateNoteStyleCommand(Command):
    def __init__(
        self, note: NoteItem, old_style: dict[str, Any], new_style: dict[str, Any]
    ) -> None:
        super().__init__(description="Update note style")
        self._logger = get_logger(__name__)
        self._note = note
        self._old_style = old_style.copy()
        self._new_style = new_style.copy()
        self.payload = {
            "note_id": getattr(note, "_note_id", id(note)),
            "old_style": self._old_style,
            "new_style": self._new_style,
        }

    def execute(self) -> None:
        self._note.set_style(self._new_style)
        self._logger.debug("UpdateNoteStyleCommand execute")

    def undo(self) -> None:
        self._note.set_style(self._old_style)
        self._logger.debug("UpdateNoteStyleCommand undo")
