import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from terminal_adapter import TerminalAdapter


class TerminalAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cwd = Path(self.temp_dir.name)
        self.adapter = TerminalAdapter()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_executes_command_in_requested_directory(self):
        result = self.adapter.execute_command("pwd", str(self.cwd))
        self.assertTrue(result["success"], result)
        self.assertIn(str(self.cwd), result["output"])

    def test_rejects_empty_command_and_invalid_directory(self):
        self.assertFalse(self.adapter.execute_command(" ", str(self.cwd))["success"])
        missing = self.cwd / "missing"
        self.assertFalse(self.adapter.execute_command("pwd", str(missing))["success"])

    @patch(
        "terminal_adapter.subprocess.run",
        side_effect=subprocess.TimeoutExpired(
            "shell", 15, output=b"partial output", stderr=b"partial error"
        ),
    )
    def test_timeout_returns_partial_output(self, _run):
        result = self.adapter.execute_command("long-running", str(self.cwd))
        self.assertFalse(result["success"])
        self.assertTrue(result["timed_out"])
        self.assertIn("partial output", result["output"])
        self.assertIn("partial error", result["output"])
        self.assertIn("15s limit", result["output"])


if __name__ == "__main__":
    unittest.main()
