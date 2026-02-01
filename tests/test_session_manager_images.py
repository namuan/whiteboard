"""
Image embedding tests for SessionManager.

Focus on verifying that images are serialized with base64 data and restored
from embedded data when loading - no external temp files.
"""

import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPixmap, QColor

from src.whiteboard.session_manager import SessionManager
from src.whiteboard.image_item import ImageItem


class TestSessionManagerImages(unittest.TestCase):
    @classmethod
    @patch("src.whiteboard.utils.config_paths.get_app_data_dir")
    @patch("src.whiteboard.utils.config_paths.ensure_app_directories")
    @patch("pathlib.Path.mkdir")
    def setUpClass(cls, mock_mkdir, mock_ensure_dirs, mock_data_dir):
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()

        # Use a temporary directory as app data dir
        cls._tmpdir = tempfile.TemporaryDirectory()
        mock_data_dir.return_value = Path(cls._tmpdir.name)
        mock_ensure_dirs.return_value = None
        mock_mkdir.return_value = None

        cls.session_manager = SessionManager()

    @classmethod
    def tearDownClass(cls):
        cls._tmpdir.cleanup()

    def test_serialize_image_embeds_base64(self):
        """Test that images are serialized with embedded base64 data."""
        # Create a real pixmap (not just dummy bytes)
        pixmap = QPixmap(100, 50)
        pixmap.fill(QColor(255, 0, 0))  # Red image

        # Create ImageItem with the pixmap
        item = ImageItem("", QPointF(10, 20))

        # Manually set the pixmap from our test pixmap
        item._original_pixmap = pixmap
        item._scale_image()

        # Serialize
        data = self.session_manager._serialize_image(item)

        # Assertions
        self.assertIsNotNone(data)
        self.assertEqual(data["position"], {"x": 10.0, "y": 20.0})
        self.assertIn("image_base64", data)
        self.assertTrue(data["metadata"]["has_base64"])  # Embedded data present
        self.assertEqual(
            data["original_filename"], "image.png"
        )  # Default since no path
        self.assertIsInstance(data["file_size"], int)
        self.assertGreater(data["file_size"], 0)  # Should have actual data

    def test_deserialize_image_from_base64(self):
        """Test that images are restored from embedded base64 data without temp files."""
        import base64

        # Create a real pixmap and encode it
        original_pixmap = QPixmap(100, 50)
        original_pixmap.fill(QColor(0, 255, 0))  # Green image

        # Save to bytes to get valid PNG data
        from PyQt6.QtCore import QBuffer, QIODevice

        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        original_pixmap.save(buffer, "PNG")
        raw = bytes(buffer.data())

        b64 = base64.b64encode(raw).decode("utf-8")

        image_id = 9999
        image_data = {
            "id": image_id,
            "position": {"x": 5, "y": 6},
            "style": {},
            "rotation": 0,
            "z_value": 0,
            "visible": True,
            "enabled": True,
            "image_path": "",  # No original path
            "image_base64": b64,
            "original_filename": "embedded.png",
            "file_size": len(raw),
        }

        # Deserialize - should load from embedded data, no temp files
        item = self.session_manager._deserialize_image(image_data)

        # Assertions
        self.assertIsNotNone(item)
        self.assertIsInstance(item, ImageItem)
        self.assertEqual(item.pos(), QPointF(5, 6))

        # Image should be fully embedded - path should be empty
        self.assertEqual(item.get_image_path(), "")

        # Verify the pixmap was loaded (not null) - dimensions are scaled by style
        self.assertFalse(item.pixmap().isNull())
        self.assertGreater(item.pixmap().width(), 0)
        self.assertGreater(item.pixmap().height(), 0)


if __name__ == "__main__":
    unittest.main()
