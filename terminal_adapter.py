import platform
import shutil
import subprocess
from pathlib import Path

from impobj_utils import logger


class TerminalAdapter:
    TIMEOUT_SECONDS = 15

    @staticmethod
    def _decode_output(value) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return str(value)

    def execute_command(self, command: str, cwd: str) -> dict:
        """Run a command in the project's native shell with a strict timeout."""
        directory = Path(cwd)
        if not command.strip():
            return {"success": False, "output": "Enter a command."}
        if not directory.is_dir():
            return {"success": False, "output": "Working directory does not exist."}

        system = platform.system()
        if system == "Windows":
            executable = shutil.which("powershell.exe") or shutil.which("powershell")
            if not executable:
                return {"success": False, "output": "PowerShell was not found."}
            args = [executable, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command]
        elif system == "Darwin":
            args = ["/bin/zsh", "-lc", command]
        else:
            args = ["/bin/bash", "-lc", command]

        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(directory),
                timeout=self.TIMEOUT_SECONDS,
                check=False,
            )
            output = result.stdout
            if result.stderr:
                output += ("\n" if output else "") + result.stderr
            return {
                "success": result.returncode == 0,
                "output": output.strip(),
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired as error:
            output = self._decode_output(error.stdout)
            stderr = self._decode_output(error.stderr)
            if stderr:
                output += ("\n" if output else "") + stderr
            output += ("\n" if output else "") + (
                f"Error: Command timed out ({self.TIMEOUT_SECONDS}s limit)."
            )
            return {"success": False, "output": output, "timed_out": True}
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            logger.error("Terminal execution error: %s", error)
            return {"success": False, "output": f"Error: {error}"}
