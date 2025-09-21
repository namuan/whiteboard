"""
Tests for the logging configuration.
"""

import logging
import tempfile
from pathlib import Path

from src.whiteboard.utils.logging_config import setup_logging, get_logger


def test_setup_logging():
    """Test that logging is set up correctly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        log_file = Path(temp_dir) / "test.log"

        # Set up logging
        setup_logging(log_level="DEBUG", log_file=str(log_file))

        # Test that logger works
        logger = get_logger("test_logger")
        logger.info("Test message")

        # Check that log file was created and contains message
        assert log_file.exists()
        log_content = log_file.read_text()
        assert "Test message" in log_content


def test_get_logger():
    """Test that get_logger returns a proper logger instance."""
    logger = get_logger("test_module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_module"


def test_logging_levels():
    """Test that different logging levels work correctly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        log_file = Path(temp_dir) / "test_levels.log"

        # Set up logging with INFO level
        setup_logging(log_level="INFO", log_file=str(log_file))

        logger = get_logger("test_levels")
        logger.debug("Debug message")  # Should not appear
        logger.info("Info message")  # Should appear
        logger.warning("Warning message")  # Should appear

        log_content = log_file.read_text()
        assert "Debug message" not in log_content
        assert "Info message" in log_content
        assert "Warning message" in log_content
