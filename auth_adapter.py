"""Firebase authentication implementation placeholder."""


class FirebaseAuthAdapter:
    def __init__(self, credentials_path=None):
        self.credentials_path = credentials_path

    def sign_in(self, email: str, password: str):
        raise NotImplementedError("Firebase authentication is not configured")
