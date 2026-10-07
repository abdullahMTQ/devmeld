from todo_adapter import load_todos, save_todos


class TodoManager:
    def get_todos(self) -> list:
        return load_todos()

    def add_todo(self, content: str) -> dict:
        content = content.strip()
        if not content:
            return {"success": False, "error": "Note cannot be empty."}
        todos = load_todos()
        todo_ids = [
            todo.get("id")
            for todo in todos
            if isinstance(todo, dict) and isinstance(todo.get("id"), int)
        ]
        todos.append({"id": max(todo_ids, default=0) + 1, "content": content})
        if save_todos(todos):
            return {"success": True}
        return {"success": False, "error": "Failed to save."}

    def delete_todo(self, todo_id: int) -> dict:
        todos = load_todos()
        filtered = [
            todo
            for todo in todos
            if not isinstance(todo, dict) or todo.get("id") != todo_id
        ]
        if len(filtered) == len(todos):
            return {"success": False, "error": "Note not found."}
        if save_todos(filtered):
            return {"success": True}
        return {"success": False, "error": "Failed to save."}
