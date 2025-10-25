"""
Undo/Redo stack for the Digital Whiteboard application.

Provides a QObject-backed stack with signals for UI enablement.
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from ..utils.logging_config import get_logger
from .base import Command


class UndoRedoStack(QObject):
    """Manage command history and provide undo/redo operations."""

    stack_changed = pyqtSignal()
    can_undo_changed = pyqtSignal(bool)
    can_redo_changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self._logger = get_logger(__name__)
        self._undo_stack: list[Command] = []
        self._redo_stack: list[Command] = []

    def push_and_execute(self, command: Command) -> None:
        try:
            self._logger.debug(
                f"Executing command: {type(command).__name__} - {command.description}"
            )
            command.execute()
            self._undo_stack.append(command)
            self._redo_stack.clear()
            self._emit_signals()
            self._logger.info(f"Command executed and pushed: {type(command).__name__}")
        except Exception as e:
            self._logger.error(
                f"Failed to execute command {type(command).__name__}: {e}"
            )

    def undo(self) -> None:
        if not self._undo_stack:
            self._logger.debug("Undo requested but stack is empty")
            return
        try:
            cmd = self._undo_stack.pop()
            self._logger.debug(
                f"Undoing command: {type(cmd).__name__} - {cmd.description}"
            )
            cmd.undo()
            self._redo_stack.append(cmd)
            self._emit_signals()
            self._logger.info(f"Undo completed: {type(cmd).__name__}")
        except Exception as e:
            self._logger.error(f"Failed to undo command: {e}")

    def redo(self) -> None:
        if not self._redo_stack:
            self._logger.debug("Redo requested but stack is empty")
            return
        try:
            cmd = self._redo_stack.pop()
            self._logger.debug(
                f"Redoing command: {type(cmd).__name__} - {cmd.description}"
            )
            cmd.redo()
            self._undo_stack.append(cmd)
            self._emit_signals()
            self._logger.info(f"Redo completed: {type(cmd).__name__}")
        except Exception as e:
            self._logger.error(f"Failed to redo command: {e}")

    def clear(self) -> None:
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._emit_signals()
        self._logger.debug("Undo/Redo stack cleared")

    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def _emit_signals(self) -> None:
        self.stack_changed.emit()
        self.can_undo_changed.emit(self.can_undo())
        self.can_redo_changed.emit(self.can_redo())
