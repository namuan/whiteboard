import sys
import logging
from PyQt6.QtWidgets import QApplication
from .main_window import MainWindow
from .utils.logging_config import setup_logging


def main() -> None:
    """Main application entry point."""
    # Set up logging configuration
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        # Create QApplication instance
        app = QApplication(sys.argv)
        app.setApplicationName("Digital Whiteboard")
        app.setApplicationVersion("0.1.0")
        app.setOrganizationName("Whiteboard")

        # Create and show main window
        main_window = MainWindow()
        main_window.show()

        logger.info("Digital Whiteboard application started successfully")

        # Start the event loop
        sys.exit(app.exec())

    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)
