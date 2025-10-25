"""
Connection-related commands for undo/redo support.
"""

from __future__ import annotations

from typing import Any
from ..utils.logging_config import get_logger
from .base import Command

# Avoid importing canvas/scene to prevent circulars
# from ..canvas import WhiteboardCanvas, WhiteboardScene
from ..connection_item import ConnectionItem


class CreateConnectionCommand(Command):
    def __init__(
        self,
        scene: Any,
        canvas: Any,
        start_item: Any,
        end_item: Any,
        description: str = "Create connection",
    ) -> None:
        super().__init__(description=description)
        self._logger = get_logger(__name__)
        self._scene = scene
        self._canvas = canvas
        self._start_item = start_item
        self._end_item = end_item
        self._connection: ConnectionItem | None = None
        self.payload = {
            "start_id": self._endpoint_id(self._start_item),
            "end_id": self._endpoint_id(self._end_item),
        }

    def _endpoint_id(self, obj: Any) -> str:
        if hasattr(obj, "get_note_id"):
            return f"note_{obj.get_note_id()}"
        if hasattr(obj, "get_image_id"):
            return f"image_{obj.get_image_id()}"
        return f"item_{id(obj)}"

    def execute(self) -> None:
        try:
            conn = self._canvas._create_connection(self._start_item, self._end_item)
            self._connection = conn
            self._logger.info("Connection created via command")
        except Exception as e:
            self._logger.error(f"Failed to create connection via command: {e}")

    def undo(self) -> None:
        try:
            if self._connection:
                self._canvas.delete_connection(self._connection)
                self._logger.info("CreateConnectionCommand undone: connection removed")
        except Exception as e:
            self._logger.error(f"Failed to undo connection creation: {e}")

    def redo(self) -> None:
        self.execute()
