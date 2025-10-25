"""
Image-related commands for undo/redo support.
"""

from __future__ import annotations

from typing import Any
from PyQt6.QtCore import QPointF
from ..utils.logging_config import get_logger
from .base import Command, point_to_tuple
from ..image_item import ImageItem
# Avoid importing canvas/scene to prevent circulars
# from ..canvas import WhiteboardCanvas, WhiteboardScene


class AddImageCommand(Command):
    def __init__(
        self,
        scene: Any,
        canvas: Any,
        image_path: str,
        position: QPointF,
        description: str = "Add image",
    ) -> None:
        super().__init__(description=description)
        self._logger = get_logger(__name__)
        self._scene = scene
        self._canvas = canvas
        self._image_path = image_path
        self._position = QPointF(position)
        self._image: ImageItem | None = None
        self.payload = {
            "image_path": image_path,
            "position": point_to_tuple(self._position),
        }

    def execute(self) -> None:
        try:
            image_item = ImageItem(image_path=self._image_path, position=self._position)
            self._scene.addItem(image_item)
            self._image = image_item
            self._logger.info(f"Image added via command: {self._image_path}")
        except Exception as e:
            self._logger.error(f"Failed to add image via command: {e}")

    def undo(self) -> None:
        try:
            if self._image:
                # Delete connections first
                try:
                    self._canvas.delete_connections_for_item(self._image)
                except Exception:
                    pass
                if self._image.scene():
                    self._image.scene().removeItem(self._image)
                self._logger.info("AddImageCommand undone: image removed")
        except Exception as e:
            self._logger.error(f"Failed to undo image add: {e}")

    def redo(self) -> None:
        self.execute()
