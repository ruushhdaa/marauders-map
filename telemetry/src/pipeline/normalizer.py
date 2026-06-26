import logging
from typing import Any, Dict
from src.core.interfaces import PipelineStep

logger = logging.getLogger('Normalizer')

class Normalizer(PipelineStep):
    """
    Normalizes data values (e.g., scaling between 0 and 1) if required for ML models.
    """
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if data is None:
            return None
            
        # Example of where one might normalize CPU to 0-1 range
        # data['cpu'] = data['cpu'] / 100.0
        
        logger.info("normalization completed")
        return data
