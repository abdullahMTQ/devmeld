from PySide6.QtCore import QThread, Signal

from auth_service import AuthService


class AuthWorker(QThread):
    finished_signal = Signal(dict)

    def __init__(self, task_type: str, email: str, password: str, username: str = ""):
        super().__init__()
        self.task_type = task_type
        self.email = email
        self.password = password
        self.username = username
        self.service = AuthService()

    def run(self):
        try:
            if self.task_type == "signup":
                result = self.service.sign_up(self.email, self.password, self.username)
            elif self.task_type == "signin":
                result = self.service.sign_in(self.email, self.password)
            else:
                result = {"success": False, "error": "Unknown authentication task."}
        except Exception as error:
            result = {"success": False, "error": f"System error: {error}"}
        self.finished_signal.emit(result)
