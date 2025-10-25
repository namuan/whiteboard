"""
Delete-related commands for undo/redo support.

Provides DeleteItemsCommand that can remove notes, images, and connections
and restore them on undo using serialized state.
"""

from __future__ import annotations

from typing import Any
from PyQt6.QtCore import QPointF

from ..utils.logging_config import get_logger
from .base import Command
from ..note_item import NoteItem
from ..image_item import ImageItem
from ..connection_item import ConnectionItem
from ..canvas import WhiteboardCanvas, WhiteboardScene


class DeleteItemsCommand(Command):
    def __init__(
        self,
        scene: WhiteboardScene,
        canvas: WhiteboardCanvas,
        items: list[Any],
        description: str = "Delete items",
    ) -> None:
        super().__init__(description=description)
        self._logger = get_logger(__name__)
        self._scene = scene
        self._canvas = canvas
        self._items = list(items)
        # Serialized state for undo
        self._notes_data: list[dict[str, Any]] = []
        self._images_data: list[dict[str, Any]] = []
        self._connections_data: list[dict[str, Any]] = []

    def _serialize_items(self) -> None:
        self._notes_data.clear()
        self._images_data.clear()
        self._connections_data.clear()
        for it in self._items:
            if isinstance(it, NoteItem):
                self._notes_data.append(it.get_note_data())
            elif isinstance(it, ImageItem):
                data = it.get_image_data()
                pos = it.pos()
                data["position"] = (pos.x(), pos.y())
                data["image_path"] = it.get_image_path()
                self._images_data.append(data)
            elif isinstance(it, ConnectionItem):
                self._connections_data.append(it.get_connection_data())

        self.payload = {
            "notes": self._notes_data,
            "images": self._images_data,
            "connections": self._connections_data,
        }
        self._logger.debug(
            f"DeleteItemsCommand payload: notes={len(self._notes_data)}, images={len(self._images_data)}, connections={len(self._connections_data)}"
        )

    def _delete_connections_first(self) -> None:
        """Delete connection items first to avoid dangling references."""
        for conn in list(self._connections_data):
            for item in list(self._items):
                try:
                    if isinstance(
                        item, ConnectionItem
                    ) and item.get_connection_id() == conn.get("id"):
                        item.delete_connection()
                        self._items.remove(item)
                except Exception as e:
                    self._logger.error(f"Failed deleting connection: {e}")

    def _delete_remaining_items(self) -> None:
        """Delete notes and images in a simplified loop."""
        for item in list(self._items):
            try:
                if isinstance(item, NoteItem):
                    if hasattr(item, "_delete_note"):
                        item._delete_note()
                    else:
                        self._canvas.delete_connections_for_item(item)
                        if item.scene():
                            item.scene().removeItem(item)
                elif isinstance(item, ImageItem):
                    if hasattr(item, "_delete_image"):
                        item._delete_image()
                    else:
                        self._canvas.delete_connections_for_item(item)
                        if item.scene():
                            item.scene().removeItem(item)
            except Exception as e:
                self._logger.error(f"Failed deleting item: {e}")

    def execute(self) -> None:
        # Serialize current state then delete
        self._serialize_items()
        self._delete_connections_first()
        self._delete_remaining_items()
        self._logger.info("Deleted items via command")

    def _restore_notes(self, id_map: dict[int, Any]) -> None:
        for note_data in self._notes_data:
            try:
                pos_x, pos_y = note_data.get("position", (0, 0))
                note = NoteItem(note_data.get("text", ""), QPointF(pos_x, pos_y))
                style = note_data.get("style")
                if style:
                    note.set_style(style)
                if "id" in note_data:
                    note._note_id = int(note_data["id"])  # restore id
                self._scene.addItem(note)
                try:
                    self._canvas._connect_note_signals(note)
                except Exception:
                    pass
                id_map[note._note_id] = note
            except Exception as e:
                self._logger.error(f"Failed to restore note: {e}")

    def _restore_images(self, id_map: dict[int, Any]) -> None:
        for image_data in self._images_data:
            try:
                pos_data = image_data.get("position", (0, 0))
                image = ImageItem(
                    image_data.get("image_path", ""), QPointF(pos_data[0], pos_data[1])
                )
                style = image_data.get("style")
                if style:
                    image.update_style(style)
                if "id" in image_data:
                    image._image_id = int(image_data["id"])  # restore id
                self._scene.addItem(image)
                id_map[image._image_id] = image
            except Exception as e:
                self._logger.error(f"Failed to restore image: {e}")

    def _resolve_endpoint(self, id_map: dict[int, Any], item_id: Any) -> Any | None:
        """Resolve endpoint from serialized generic ID."""
        if not isinstance(item_id, str):
            return None
        try:
            if item_id.startswith("note_"):
                return id_map.get(int(item_id.split("_", 1)[1]))
            if item_id.startswith("image_"):
                return id_map.get(int(item_id.split("_", 1)[1]))
        except Exception:
            return None
        return None

    def _restore_connections(self, id_map: dict[int, Any]) -> None:
        for conn_data in self._connections_data:
            try:
                start_item = self._resolve_endpoint(
                    id_map, conn_data.get("start_item_id")
                )
                end_item = self._resolve_endpoint(id_map, conn_data.get("end_item_id"))
                if not start_item or not end_item:
                    self._logger.warning(
                        "Skipping connection restore: endpoints not found"
                    )
                    continue
                connection = ConnectionItem(start_item, end_item)
                style = conn_data.get("style")
                if style:
                    connection.set_style(style)
                self._scene.addItem(connection)
            except Exception as e:
                self._logger.error(f"Failed to restore connection: {e}")

    def undo(self) -> None:
        id_map: dict[int, Any] = {}
        self._restore_notes(id_map)
        self._restore_images(id_map)
        self._restore_connections(id_map)
        self._logger.info("Undo delete: items restored")

    def redo(self) -> None:
        self.execute()
