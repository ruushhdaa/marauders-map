import os
import csv
from typing import Any, List
from src.models import TelemetryRecord, BGPRecord
from src.core.interfaces import PipelineStep

class Exporter(PipelineStep):
    """
    Exports structured records to a CSV file.
    Can be easily modified to support JSON output.
    """
    def __init__(self, output_path: str):
        self.output_path = output_path
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        self.file = open(self.output_path, 'a', newline='')
        self.writer = csv.writer(self.file)
        
        # Write header if file is empty
        if os.path.getsize(self.output_path) == 0:
            self.writer.writerow([
                'timestamp', 'node', 'latency', 'jitter', 'packet_loss', 
                'bandwidth', 'cpu', 'bgp_status', 'moving_average_latency',
                'moving_average_bandwidth', 'moving_average_cpu',
                'packet_loss_trend', 'latency_trend', 'bandwidth_trend',
                'health_score', 'risk_score', 'anomaly'
            ])
            self.file.flush()

    def process(self, data: TelemetryRecord) -> TelemetryRecord:
        if data is None:
            return None
            
        self.writer.writerow([
            data.timestamp,
            data.node,
            data.latency,
            data.jitter,
            data.packet_loss,
            data.bandwidth,
            data.cpu,
            data.bgp_status,
            data.moving_average_latency,
            data.moving_average_bandwidth,
            data.moving_average_cpu,
            data.packet_loss_trend,
            data.latency_trend,
            data.bandwidth_trend,
            data.health_score,
            data.risk_score,
            data.anomaly
        ])
        self.file.flush()
        return data

    def close(self):
        self.file.close()

class BGPExporter(PipelineStep):
    """
    Exports structured BGP records to a CSV file.
    """
    def __init__(self, output_path: str):
        self.output_path = output_path
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        self.file = open(self.output_path, 'a', newline='')
        self.writer = csv.writer(self.file)
        
        # Write header if file is empty
        if os.path.getsize(self.output_path) == 0:
            self.writer.writerow([
                'timestamp', 'node', 'bgp_status', 'neighbor', 'event', 'severity'
            ])
            self.file.flush()

    def process(self, data: BGPRecord) -> BGPRecord:
        if data is None:
            return None
            
        self.writer.writerow([
            data.timestamp,
            data.node,
            data.bgp_status,
            data.neighbor,
            data.event,
            data.severity
        ])
        self.file.flush()
        return data

    def close(self):
        self.file.close()

