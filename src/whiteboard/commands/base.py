"""
Base command definitions for the Digital Whiteboard application.

Defines the core Command interface used to implement undo/redo for user actions.
"""

from __future__ import annotations

from typing import Any
from dataclasses import dataclass, field
from PyQt6.QtCore import QPointF


@dataclass
class Command:
    """Abstract base class for all commands.

    Each command implements execute(), undo(), and redo() and may provide
    a serializable payload that captures the state necessary to reverse the action.
    """

    description: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    def execute(self) -> None:
        raise NotImplementedError

    def undo(self) -> None:
        raise NotImplementedError

    def redo(self) -> None:
        # Default redo is to execute again
        self.execute()

    def serialize(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the command."""
        return {
            "type": type(self).__name__,
            "description": self.description,
            "payload": self.payload,
        }

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> Command:
        """Generic deserializer. Concrete commands should override if needed."""
        cmd = cls(
            description=data.get("description", ""), payload=data.get("payload", {})
        )
        return cmd


# Helper converters kept here to avoid cross-import cycles


def point_to_tuple(p: QPointF) -> tuple[float, float]:
    return (p.x(), p.y())


def tuple_to_point(t: tuple[float, float]) -> QPointF:
    return QPointF(t[0], t[1])
