"""
Image embedding tests for SessionManager.

Focus on verifying that images are serialized with base64 data and restored
from embedded data when loading.
"""

import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF

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
        # Create a temporary image file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
            tf.write(b"\x89PNG\r\n\x1a\n" + b"dummy-png-data")
            image_path = tf.name

        try:
            # Create ImageItem with path
            item = ImageItem(image_path=image_path, position=QPointF(10, 20))

            # Serialize
            data = self.session_manager._serialize_image(item)

            # Assertions
            self.assertIsNotNone(data)
            self.assertEqual(data["position"], {"x": 10.0, "y": 20.0})
            self.assertIn("image_base64", data)
            self.assertTrue(data["metadata"]["has_base64"])  # Embedded data present
            self.assertEqual(data["original_filename"], Path(image_path).name)
            self.assertIsInstance(data["file_size"], int)
        finally:
            Path(image_path).unlink(missing_ok=True)

    def test_deserialize_image_from_base64(self):
        # Prepare dummy base64 data
        import base64

        raw = b"\x89PNG\r\n\x1a\n" + b"dummy-png-data"
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
            "image_path": "",  # Ensures we use base64 path
            "image_base64": b64,
            "original_filename": "embedded.png",
            "file_size": len(raw),
        }

        # Patch Path.home to redirect temp_images folder to a temp dir
        with tempfile.TemporaryDirectory() as tmp_home:
            with patch(
                "src.whiteboard.session_manager.Path.home", return_value=Path(tmp_home)
            ):
                item = self.session_manager._deserialize_image(image_data)

                # Assertions
                self.assertIsNotNone(item)
                self.assertIsInstance(item, ImageItem)
                self.assertEqual(item.pos(), QPointF(5, 6))
                # The image path should be under the patched home temp_images folder
                self.assertTrue(Path(item.get_image_path()).exists())
                self.assertIn("embedded.png", Path(item.get_image_path()).name)
