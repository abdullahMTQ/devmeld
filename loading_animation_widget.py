import random

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QWidget


class LoadingAnimationWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.shapes = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_shapes)
        self.success_message = ""
        self.error_message = ""
        self.state = "loading"

    def start_loading(self):
        self.state = "loading"
        self.success_message = ""
        self.error_message = ""
        width = max(1, self.width())
        height = max(1, self.height())
        self.shapes = [
            {
                "type": random.choice(["rect", "circle"]),
                "x": random.randint(0, width),
                "y": random.randint(0, height),
                "size": random.randint(20, 60),
                "dx": random.uniform(-2, 2),
                "dy": random.uniform(-2, 2),
                "color": QColor(random.randint(0, 255), random.randint(100, 200), 255, 150),
            }
            for _ in range(15)
        ]
        self.timer.start(16)
        self.show()
        self.raise_()

    def show_success(self, username: str):
        self.state = "success"
        self.success_message = f"welcome {username}!"
        self.timer.stop()
        self.update()

    def show_error(self, error_msg: str):
        self.state = "error"
        self.error_message = error_msg
        self.timer.stop()
        self.update()

    def update_shapes(self):
        for shape in self.shapes:
            shape["x"] += shape["dx"]
            shape["y"] += shape["dy"]
            if shape["x"] <= 0 or shape["x"] + shape["size"] >= self.width():
                shape["dx"] *= -1
            if shape["y"] <= 0 or shape["y"] + shape["size"] >= self.height():
                shape["dy"] *= -1
            shape["size"] = max(10, min(80, shape["size"] + random.uniform(-1, 1)))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.state == "loading":
            for shape in self.shapes:
                painter.setBrush(shape["color"])
                painter.setPen(Qt.PenStyle.NoPen)
                if shape["type"] == "rect":
                    painter.drawRoundedRect(
                        shape["x"], shape["y"], shape["size"], shape["size"], 10, 10
                    )
                else:
                    painter.drawEllipse(
                        shape["x"], shape["y"], shape["size"], shape["size"]
                    )
        elif self.state == "success":
            painter.fillRect(self.rect(), QColor(0, 0, 0, 200))
            painter.setPen(QColor(0, 255, 100))
            painter.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.success_message)
        elif self.state == "error":
            painter.fillRect(self.rect(), QColor(0, 0, 0, 200))
