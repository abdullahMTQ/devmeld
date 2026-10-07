import logging
import platform
import uuid

logger = logging.getLogger("devmeld")


class HardwareIdAdapter:
    def get_machine_id(self) -> str:
        try:
            return f"{uuid.getnode()}-{platform.node()}"
        except Exception as error:
            logger.error("Failed to get HW ID: %s", error)
            return "unknown_hw_id"
