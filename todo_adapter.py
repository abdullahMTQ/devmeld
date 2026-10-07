import json
from pathlib import Path

from impobj_utils import get_impobj_path, logger

TODO_DIR_NAME = "TODO_list"
TODO_FILE_NAME = "todos.json"


def _get_todo_file() -> Path:
    todo_dir = get_impobj_path() / TODO_DIR_NAME
    todo_dir.mkdir(parents=True, exist_ok=True)
    return todo_dir / TODO_FILE_NAME


def load_todos() -> list:
    try:
        file_path = _get_todo_file()
        if not file_path.exists():
            return []
        with file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, list):
            return data
        logger.error("TODO file must contain a JSON list: %s", file_path)
        return []
    except (OSError, ValueError) as error:
        logger.error("Failed to load TODOs: %s", error)
        return []


def save_todos(todos: list) -> bool:
    try:
        file_path = _get_todo_file()
        with file_path.open("w", encoding="utf-8") as file:
            json.dump(todos, file, indent=2)
        return True
    except (OSError, TypeError, ValueError) as error:
        logger.error("Failed to save TODOs: %s", error)
        return False
