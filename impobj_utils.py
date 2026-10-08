import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("devmeld")


def get_resource_path(relative_path: str) -> Path:
    """Get an absolute resource path in development and PyInstaller builds."""
    try:
        base_path = Path(sys._MEIPASS)
    except Exception:
        base_path = Path(__file__).parent
    return base_path / relative_path


def get_impobj_path() -> Path:
    try:
        if getattr(sys, "frozen", False):
            base_path = Path(sys.executable).parent
        else:
            base_path = Path(__file__).parent
        impobj_path = base_path / "IMPOBJ"
        impobj_path.mkdir(exist_ok=True)
        return impobj_path
    except Exception as error:
        logger.error("Failed to resolve IMPOBJ path: %s", error)
        return Path.cwd() / "IMPOBJ"
