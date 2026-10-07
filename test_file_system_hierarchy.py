import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from file_system_service import FileSystemService


class FileSystemHierarchyTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.service = FileSystemService()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_rename_copy_move_and_delete(self):
        destination = self.root / "destination"
        destination.mkdir()

        self.assertTrue(self.service.create_file(str(self.root), "start.py")["success"])
        self.assertFalse(self.service.create_file(str(self.root), "start.py")["success"])
        self.assertTrue(self.service.create_folder(str(self.root), "assets")["success"])
        self.assertTrue(
            self.service.rename_item(str(self.root / "start.py"), "main.py")["success"]
        )
        self.assertTrue(
            self.service.copy_item(str(self.root / "main.py"), str(destination))["success"]
        )
        self.assertTrue(
            self.service.move_item(str(self.root / "assets"), str(destination))["success"]
        )
        self.assertTrue(self.service.delete_item(str(destination / "main.py"))["success"])
        self.assertTrue(self.service.delete_item(str(destination / "assets"))["success"])
        self.assertFalse((destination / "main.py").exists())

    def test_rejects_invalid_names(self):
        self.assertFalse(self.service.create_file(str(self.root), "../outside.py")["success"])
        self.assertFalse(self.service.create_folder(str(self.root), "..")["success"])
        self.assertFalse(self.service.rename_item(str(self.root), "bad/name")["success"])

    def test_open_terminal_uses_project_as_working_directory(self):
        with patch("file_system_adapter.subprocess.Popen") as popen:
            result = self.service.open_terminal(str(self.root))
        self.assertTrue(result["success"])
        self.assertEqual(popen.call_args.kwargs["cwd"], str(self.root))


if __name__ == "__main__":
    unittest.main()
