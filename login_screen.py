from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from auth_worker import AuthWorker
from loading_animation_widget import LoadingAnimationWidget


class LoginScreen(QWidget):
    login_successful = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.worker = None
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Devmeld - Sign In")
        screen = self.screen()
        if screen is not None:
            self.setGeometry(screen.geometry())
        self.setStyleSheet(
            "QWidget { background-color: #000000; color: #ffffff; "
            "font-family: 'Segoe UI', Arial, sans-serif; }"
        )

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        title_layout = QHBoxLayout()
        title_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label = QLabel("sign in")
        self.title_label.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        title_layout.addWidget(self.title_label)
        self.create_account_label = QLabel("create account")
        self.create_account_label.setStyleSheet(
            "QLabel { color: #00aeff; text-decoration: underline; padding: 10px; }"
        )
        self.create_account_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.create_account_label.mousePressEvent = self._open_signup_screen
        title_layout.addWidget(self.create_account_label)
        layout.addLayout(title_layout)

        self.inputs_container = QWidget()
        inputs_layout = QVBoxLayout(self.inputs_container)
        inputs_layout.setContentsMargins(0, 0, 0, 0)
        inputs_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.email_input = self._create_input("email")
        self.password_input = self._create_input("password", echo_mode=True)
        inputs_layout.addWidget(self.email_input)
        inputs_layout.addWidget(self.password_input)

        self.warning_label = QLabel("")
        self.warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.warning_label.setStyleSheet("QLabel { color: #ff4444; font-size: 14px; }")
        inputs_layout.addWidget(self.warning_label)
        layout.addWidget(self.inputs_container)
        self.inputs_container.adjustSize()

        self.go_btn = QPushButton("lets go")
        self.go_btn.setFixedSize(250, 60)
        self.go_btn.setStyleSheet(
            """
            QPushButton { background-color: #1a1a1a; color: #ffffff; border: 3px solid #ffffff; border-radius: 30px; font-size: 20px; font-weight: bold; }
            QPushButton:hover { background-color: #333333; border: 3px solid #00aeff; color: #00aeff; }
            QPushButton:pressed { background-color: #00aeff; color: #000000; }
            """
        )
        self.go_btn.clicked.connect(self._on_go_clicked)
        layout.addWidget(self.go_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.back_btn = QPushButton("← back to home")
        self.back_btn.setFixedSize(200, 40)
        self.back_btn.setStyleSheet(
            "QPushButton { background-color: transparent; color: #888888; border: none; font-size: 14px; }"
            "QPushButton:hover { color: #00aeff; }"
        )
        self.back_btn.clicked.connect(self.close)
        layout.addWidget(self.back_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.loading_overlay = LoadingAnimationWidget(self)
        self.loading_overlay.resize(self.size())
        self.loading_overlay.hide()
        self._current_anim = None

    def _create_input(self, placeholder: str, echo_mode: bool = False) -> QLineEdit:
        input_field = QLineEdit()
        input_field.setPlaceholderText(placeholder)
        input_field.setFixedSize(400, 60)
        input_field.setStyleSheet(
            "QLineEdit { background-color: #111111; color: #ffffff; border: 3px solid #ffffff; border-radius: 30px; padding: 0 25px; font-size: 18px; }"
            "QLineEdit:focus { border: 3px solid #00aeff; }"
        )
        if echo_mode:
            input_field.setEchoMode(QLineEdit.EchoMode.Password)
        return input_field

    def _open_signup_screen(self, event):
        from signin_screen import SignUpScreen

        self.signup_screen = SignUpScreen(parent=self.parent())
        self.signup_screen.login_successful.connect(self.login_successful.emit)
        self.signup_screen.show()
        self.close()

    def _on_go_clicked(self):
        email = self.email_input.text()
        password = self.password_input.text()
        if not email or not password:
            self.warning_label.setText("All fields are required.")
            return

        self.warning_label.setText("")
        self.go_btn.setEnabled(False)
        slide_target_x = self.width() + 500
        self._slide_widget(
            self.inputs_container,
            target_x=slide_target_x,
            duration=500,
            on_finished=lambda: self._start_loading_overlay(email, password),
        )

    def _slide_widget(self, widget, target_x, duration, on_finished=None):
        """Slide a widget horizontally while preserving its vertical position."""
        animation = QPropertyAnimation(widget, b"pos", self)
        current_pos = widget.pos()
        animation.setDuration(duration)
        animation.setStartValue(current_pos)
        animation.setEndValue(QPoint(target_x, current_pos.y()))
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        if on_finished is not None:
            animation.finished.connect(on_finished)
        self._current_anim = animation
        animation.start()

    def _start_loading_overlay(self, email, password):
        self.loading_overlay.resize(self.size())
        self.loading_overlay.start_loading()
        self.worker = AuthWorker("signin", email, password)
        self.worker.finished_signal.connect(self._on_auth_finished)
        self.worker.start()

    def _on_auth_finished(self, result):
        self.go_btn.setEnabled(True)
        if result["success"]:
            self.loading_overlay.show_success(result["username"])
            QTimer.singleShot(1500, lambda: self._on_success(result))
        else:
            self.loading_overlay.show_error(result.get("error", "Authentication failed."))
            self.inputs_container.move(-500, self.inputs_container.pos().y())
            center_x = (self.width() - self.inputs_container.width()) // 2
            self._slide_widget(self.inputs_container, center_x, 500)
            self.loading_overlay.hide()
            self.warning_label.setText(result.get("error", "Authentication failed."))

    def _on_success(self, user_data):
        from session_service import SessionService

        SessionService().login_user(user_data)
        self.login_successful.emit(user_data)
        self.close()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.loading_overlay.resize(self.size())
