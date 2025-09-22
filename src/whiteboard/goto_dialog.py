"""
GoTo dialog for the Digital Whiteboard application.

This module contains the GoToDialog class which provides an interface
for quick navigation to specific coordinates on the whiteboard.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QDoubleValidator
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QDialogButtonBox,
    QGroupBox,
    QWidget,
)

from .utils.logging_config import get_logger


class GoToDialog(QDialog):
    """Dialog for navigating to specific coordinates."""

    goto_requested = pyqtSignal(float, float)

    def __init__(
        self,
        current_x: float = 0.0,
        current_y: float = 0.0,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self._current_x = current_x
        self._current_y = current_y
        self._setup_ui()
        self._populate_current_position()

    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Go To Coordinates")
        self.setModal(True)
        self.setFixedSize(350, 200)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Coordinates group
        coords_group = QGroupBox("Target Coordinates")
        coords_layout = QGridLayout(coords_group)

        # X coordinate
        coords_layout.addWidget(QLabel("X:"), 0, 0)
        self._x_input = QLineEdit()
        self._x_input.setValidator(QDoubleValidator(-999999.0, 999999.0, 2))
        self._x_input.setPlaceholderText("Enter X coordinate")
        coords_layout.addWidget(self._x_input, 0, 1)

        # Y coordinate
        coords_layout.addWidget(QLabel("Y:"), 1, 0)
        self._y_input = QLineEdit()
        self._y_input.setValidator(QDoubleValidator(-999999.0, 999999.0, 2))
        self._y_input.setPlaceholderText("Enter Y coordinate")
        coords_layout.addWidget(self._y_input, 1, 1)

        layout.addWidget(coords_group)

        # Current position info
        current_group = QGroupBox("Current Position")
        current_layout = QVBoxLayout(current_group)
        self._current_label = QLabel()
        self._current_label.setStyleSheet("color: #666; font-style: italic;")
        current_layout.addWidget(self._current_label)
        layout.addWidget(current_group)

        # Quick navigation buttons
        quick_group = QGroupBox("Quick Navigation")
        quick_layout = QHBoxLayout(quick_group)

        origin_btn = QPushButton("Origin (0, 0)")
        origin_btn.clicked.connect(lambda: self._set_coordinates(0.0, 0.0))
        quick_layout.addWidget(origin_btn)

        current_btn = QPushButton("Current Position")
        current_btn.clicked.connect(self._use_current_position)
        quick_layout.addWidget(current_btn)

        layout.addWidget(quick_group)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._handle_goto)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Set focus to X input
        self._x_input.setFocus()

        self.logger.debug("GoToDialog UI setup completed")

    def _populate_current_position(self):
        """Populate the current position display."""
        self._current_label.setText(
            f"Currently at: ({self._current_x:.1f}, {self._current_y:.1f})"
        )

    def _set_coordinates(self, x: float, y: float):
        """Set the coordinate input fields."""
        self._x_input.setText(str(x))
        self._y_input.setText(str(y))

    def _use_current_position(self):
        """Set inputs to current position."""
        self._set_coordinates(self._current_x, self._current_y)

    def _handle_goto(self):
        """Handle the Go To button click."""
        try:
            x_text = self._x_input.text().strip()
            y_text = self._y_input.text().strip()

            if not x_text or not y_text:
                self.logger.warning("Empty coordinate fields")
                return

            x = float(x_text)
            y = float(y_text)

            self.logger.info(f"GoTo requested: ({x}, {y})")
            self.goto_requested.emit(x, y)
            self.accept()

        except ValueError as e:
            self.logger.error(f"Invalid coordinate values: {e}")

    @staticmethod
    def show_goto_dialog(
        current_x: float = 0.0, current_y: float = 0.0, parent: QWidget | None = None
    ) -> tuple[float, float] | None:
        """
        Static method to show the GoTo dialog.

        Args:
            current_x: Current X coordinate
            current_y: Current Y coordinate
            parent: Parent widget

        Returns:
            Tuple of (x, y) coordinates if accepted, None if cancelled
        """
        dialog = GoToDialog(current_x, current_y, parent)
        result_coords = None

        def on_goto_requested(x: float, y: float):
            nonlocal result_coords
            result_coords = (x, y)

        dialog.goto_requested.connect(on_goto_requested)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            return result_coords
        return None
