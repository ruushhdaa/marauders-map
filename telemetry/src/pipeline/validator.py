import logging
from typing import Any, Dict
from src.core.interfaces import PipelineStep
from src.config import Config

logger = logging.getLogger('Validator')

class Validator(PipelineStep):
    """
    Validates data to ensure constraints are met.
    """
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if data is None:
            return None
            
        try:
            if data.get('latency', -1) < 0 or data.get('latency', 0) > Config.THRESHOLD_LATENCY_MAX:
                logger.warning("validation errors: latency out of bounds")
                return None
            if not (0 <= data.get('packet_loss', -1) <= Config.THRESHOLD_PACKET_LOSS_MAX):
                logger.warning("validation errors: packet_loss out of bounds")
                return None
            if not (0 <= data.get('bandwidth', -1) <= Config.THRESHOLD_BANDWIDTH_MAX):
                logger.warning("validation errors: bandwidth out of bounds")
                return None
            if not (0 <= data.get('cpu', -1) <= Config.THRESHOLD_CPU_MAX):
                logger.warning("validation errors: cpu out of bounds")
                return None
        except (TypeError, ValueError):
            logger.warning("validation errors: type conversion failed")
            return None
            
        return data
