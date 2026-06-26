from typing import Any, Dict
from src.core.interfaces import PipelineStep

class Cleaner(PipelineStep):
    """
    Cleans incoming telemetry data by standardizing formats.
    """
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not data:
            return None
        
        # Ensure all expected keys are present, dropping if major keys are missing
        expected_keys = ['timestamp', 'node', 'latency', 'jitter', 'packet_loss', 'bandwidth', 'cpu', 'bgp_status']
        if not all(k in data for k in expected_keys):
            return None
            
        return data
