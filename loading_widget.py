import math

from PySide6.QtCore import QEvent, QPointF, QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget


class LoadingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.sides = 3
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._next_shape)
        self.timer.start(100)
        self.setFixedSize(100, 100)
        self.setStyleSheet("background-color: rgba(15, 15, 15, 230); border-radius: 15px; border: 1px solid #333;")
        if parent is not None:
            parent.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.parent() and event.type() == QEvent.Type.Resize:
            self._center_on_parent()
        return super().eventFilter(obj, event)

    def showEvent(self, event):
        super().showEvent(event)
        self._center_on_parent()
        self.raise_()

    def _center_on_parent(self):
        if self.parent() is not None:
            self.move(self.parent().rect().center() - self.rect().center())

    def _next_shape(self):
        self.sides += 1
        if self.sides > 8:
            self.sides = 3
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#00aeff"), 3))
        center = self.rect().center()
        radius = 35
        points = [
            QPointF(
                center.x() + radius * math.cos(2 * math.pi * index / self.sides - math.pi / 2),
                center.y() + radius * math.sin(2 * math.pi * index / self.sides - math.pi / 2),
            )
            for index in range(self.sides)
        ]
        painter.drawPolygon(QPolygonF(points))
        painter.end()
