from todo_manager import TodoManager


class TodoService:
    def __init__(self):
        self.manager = TodoManager()

    def get_todos(self) -> list:
        return self.manager.get_todos()

    def add_todo(self, content: str) -> dict:
        return self.manager.add_todo(content)

    def delete_todo(self, todo_id: int) -> dict:
        return self.manager.delete_todo(todo_id)
