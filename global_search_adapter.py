import os
from pathlib import Path

from impobj_utils import logger


class GlobalSearchAdapter:
    MAX_FILE_SIZE = 1024 * 1024
    MAX_RESULTS = 50
    TEXT_EXTENSIONS = {
        ".py",
        ".js",
        ".ts",
        ".txt",
        ".md",
        ".json",
        ".html",
        ".css",
        ".cpp",
        ".c",
        ".h",
        ".java",
    }
    IGNORED_DIRS = {".git", ".venv", "__pycache__"}

    def search_project(self, root_path: str, query: str) -> list:
        if not query.strip():
            return []

        root = Path(root_path)
        if not root.is_dir():
            logger.warning("Global search root is not a directory: %s", root)
            return []

        results = []
        query_lower = query.casefold()

        def log_walk_error(error: OSError):
            logger.warning("Global search scan failed for %s: %s", root, error)

        try:
            for directory, subdirectories, filenames in os.walk(
                root, onerror=log_walk_error
            ):
                subdirectories[:] = [
                    name
                    for name in subdirectories
                    if name not in self.IGNORED_DIRS
                ]
                for filename in filenames:
                    file_path = Path(directory) / filename
                    try:
                        if file_path.suffix.casefold() not in self.TEXT_EXTENSIONS:
                            continue
                        if file_path.stat().st_size > self.MAX_FILE_SIZE:
                            continue
                    except OSError as error:
                        logger.warning(
                            "Could not inspect search path %s: %s", file_path, error
                        )
                        continue

                    relative_path = str(file_path.relative_to(root))
                    if query_lower in file_path.name.casefold():
                        results.append(
                            {
                                "type": "file",
                                "path": relative_path,
                                "line": 0,
                                "content": file_path.name,
                            }
                        )
                        if len(results) >= self.MAX_RESULTS:
                            return results

                    try:
                        with file_path.open(
                            "r", encoding="utf-8", errors="ignore"
                        ) as file:
                            for line_number, line in enumerate(file, 1):
                                if query_lower in line.casefold():
                                    results.append(
                                        {
                                            "type": "code",
                                            "path": relative_path,
                                            "line": line_number,
                                            "content": line.strip()[:100],
                                        }
                                    )
                                    if len(results) >= self.MAX_RESULTS:
                                        return results
                    except OSError as error:
                        logger.warning(
                            "Could not read search file %s: %s", file_path, error
                        )
        except OSError as error:
            logger.warning("Global search scan failed for %s: %s", root, error)
        return results
