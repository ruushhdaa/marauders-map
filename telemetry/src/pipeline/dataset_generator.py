from typing import Any, Dict
from src.models import TelemetryRecord, BGPRecord
from src.core.interfaces import PipelineStep

class DatasetGenerator(PipelineStep):
    """
    Converts raw dictionary into the standardized TelemetryRecord model.
    """
    def process(self, data: Dict[str, Any]) -> TelemetryRecord:
        if data is None:
            return None
            
        return TelemetryRecord(
            timestamp=data['timestamp'],
            node=data['node'],
            latency=data['latency'],
            jitter=data['jitter'],
            packet_loss=data['packet_loss'],
            bandwidth=data['bandwidth'],
            cpu=data['cpu'],
            bgp_status=data['bgp_status'],
            moving_average_latency=data.get('moving_average_latency'),
            moving_average_bandwidth=data.get('moving_average_bandwidth'),
            moving_average_cpu=data.get('moving_average_cpu'),
            packet_loss_trend=data.get('packet_loss_trend'),
            latency_trend=data.get('latency_trend'),
            bandwidth_trend=data.get('bandwidth_trend'),
            health_score=data.get('health_score'),
            risk_score=data.get('risk_score'),
            anomaly=data.get('anomaly', 0)
        )

class BGPDatasetGenerator(PipelineStep):
    """
    Converts raw BGP dictionary into the standardized BGPRecord model.
    """
    def process(self, data: Dict[str, Any]) -> BGPRecord:
        if data is None:
            return None
            
        return BGPRecord(
            timestamp=data['timestamp'],
            node=data['node'],
            bgp_status=data['bgp_status'],
            neighbor=data['neighbor'],
            event=data['event'],
            severity=data['severity']
        )

