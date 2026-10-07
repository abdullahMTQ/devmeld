from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication, QGridLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from impobj_utils import get_impobj_path
from pfp_manager import PFPManager


class PFPSelectorScreen(QWidget):
    pfp_selected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Window)
        self.setWindowTitle("Choose your Profile Picture")
        self._setup_ui()

    def show(self):
        super().show()
        self.raise_()
        self.activateWindow()
        self._center_on_screen()

    def _center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geometry = screen.geometry()
        self.move(
            (geometry.width() - self.width()) // 2,
            (geometry.height() - self.height()) // 2,
        )

    def _setup_ui(self):
        self.setStyleSheet("QWidget { background-color: #000000; color: #ffffff; }")
        layout = QVBoxLayout(self)
        title = QLabel("Select a new profile picture")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(15)

        avatar_dir = get_impobj_path() / "avatars"
        row = col = 0
        for number in range(1, 51):
            path = avatar_dir / f"{number}.png"
            if not path.exists():
                continue
            button = QPushButton()
            button.setFixedSize(100, 100)
            button.setStyleSheet(
                "QPushButton { border-radius: 50px; border: 3px solid #333; }"
                "QPushButton:hover { border: 3px solid #00aeff; }"
            )
            pixmap = PFPManager.get_pfp_pixmap("@avatar", number, 94)
            button.setIcon(QIcon(pixmap))
            button.setIconSize(pixmap.size())
            button.clicked.connect(lambda checked=False, selected=number: self._on_select(selected))
            grid.addWidget(button, row, col)
            col += 1
            if col == 4:
                col = 0
                row += 1

        scroll.setWidget(container)
        layout.addWidget(scroll)
        cancel = QPushButton("Cancel")
        cancel.setFixedSize(150, 40)
        cancel.setStyleSheet(
            "QPushButton { background: transparent; color: #888; border: none; font-size: 14px; }"
        )
        cancel.clicked.connect(self.close)
        layout.addWidget(cancel, alignment=Qt.AlignmentFlag.AlignCenter)

    def _on_select(self, pfp_number: int):
        self.pfp_selected.emit(pfp_number)
        self.close()
