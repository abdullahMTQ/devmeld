from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPixmap

from impobj_utils import get_impobj_path, logger


class PFPManager:
    """Create letter avatars or load numbered avatar images."""

    @staticmethod
    def get_pfp_pixmap(username: str, pfp_number: int, size: int = 60) -> QPixmap:
        if pfp_number == 0:
            return PFPManager._create_letter_avatar(username, size)
        return PFPManager._load_pfp_image(pfp_number, size)

    @staticmethod
    def _create_letter_avatar(username: str, size: int) -> QPixmap:
        logger.info("PFPManager: Creating letter avatar for username: %r", username)
        clean_name = username.replace("@", "").strip()
        logger.info("PFPManager: Cleaned name: %r", clean_name)
        first_letter = clean_name[0].upper() if clean_name else "?"
        logger.info("PFPManager: First letter: %r", first_letter)

        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(0, 174, 255))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, size, size)
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Segoe UI", int(size * 0.5), QFont.Weight.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, first_letter)
        painter.end()
        return pixmap

    @staticmethod
    def _load_pfp_image(pfp_number: int, size: int) -> QPixmap:
        pfp_path = get_impobj_path() / "avatars" / f"{pfp_number}.png"
        if pfp_path.exists():
            return PFPManager._apply_circular_mask(QPixmap(str(pfp_path)), size)
        logger.warning("PFP image not found: %s", pfp_path)
        return PFPManager._create_letter_avatar("@?", size)

    @staticmethod
    def _apply_circular_mask(source_pixmap: QPixmap, size: int) -> QPixmap:
        target = QPixmap(size, size)
        target.fill(Qt.GlobalColor.transparent)

        painter = QPainter(target)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)
        scaled = source_pixmap.scaled(
            size,
            size,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        painter.drawPixmap(0, 0, scaled)
        painter.end()
        return target

    @staticmethod
    def get_default_pfp_number(username: str) -> int:
        return 0
