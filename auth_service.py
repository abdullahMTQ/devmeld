"""High-level authentication intent layer."""

from auth_manager import AuthManager


class AuthService:
    def __init__(self):
        self.manager = AuthManager()

    def sign_up(self, email: str, password: str, username: str) -> dict:
        return self.manager.execute_sign_up(email, password, username)

    def sign_in(self, email: str, password: str) -> dict:
        return self.manager.execute_sign_in(email, password)

    def delete_account(self, uid: str, token: str, username: str) -> dict:
        return self.manager.delete_account(uid, token, username)
