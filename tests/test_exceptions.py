"""
Tests for custom exceptions.
"""

from src.whiteboard.utils.exceptions import (
    WhiteboardError,
    FileOperationError,
    RenderingError,
    ValidationError,
    ConfigurationError,
)


def test_whiteboard_error():
    """Test base WhiteboardError exception."""
    error = WhiteboardError("Test message", "Test details")
    assert str(error) == "Test message"
    assert error.message == "Test message"
    assert error.details == "Test details"


def test_file_operation_error():
    """Test FileOperationError inherits from WhiteboardError."""
    error = FileOperationError("File error")
    assert isinstance(error, WhiteboardError)
    assert str(error) == "File error"


def test_rendering_error():
    """Test RenderingError inherits from WhiteboardError."""
    error = RenderingError("Rendering error")
    assert isinstance(error, WhiteboardError)
    assert str(error) == "Rendering error"


def test_validation_error():
    """Test ValidationError inherits from WhiteboardError."""
    error = ValidationError("Validation error")
    assert isinstance(error, WhiteboardError)
    assert str(error) == "Validation error"


def test_configuration_error():
    """Test ConfigurationError inherits from WhiteboardError."""
    error = ConfigurationError("Config error")
    assert isinstance(error, WhiteboardError)
    assert str(error) == "Config error"
