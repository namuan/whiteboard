"""
Custom exceptions for the Digital Whiteboard application.
"""


class WhiteboardError(Exception):
    """Base exception for whiteboard application."""

    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class FileOperationError(WhiteboardError):
    """Errors related to file I/O operations."""

    pass


class RenderingError(WhiteboardError):
    """Errors related to graphics rendering."""

    pass


class ValidationError(WhiteboardError):
    """Errors related to data validation."""

    pass


class ConfigurationError(WhiteboardError):
    """Errors related to application configuration."""

    pass
