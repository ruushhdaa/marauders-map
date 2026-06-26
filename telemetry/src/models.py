from dataclasses import dataclass
from typing import Optional

@dataclass
class TelemetryRecord:
    """
    Standard schema for the telemetry pipeline output.
    """
    timestamp: str
    node: str
    latency: float
    jitter: float
    packet_loss: float
    bandwidth: float
    cpu: float
    bgp_status: int
    moving_average_latency: Optional[float] = None
    moving_average_bandwidth: Optional[float] = None
    moving_average_cpu: Optional[float] = None
    packet_loss_trend: Optional[float] = None
    latency_trend: Optional[float] = None
    bandwidth_trend: Optional[float] = None
    health_score: Optional[float] = None
    risk_score: Optional[float] = None
    anomaly: Optional[int] = None

@dataclass
class BGPRecord:
    """
    Standard schema for the BGP telemetry output.
    """
    timestamp: str
    node: str
    bgp_status: int
    neighbor: str
    event: str
    severity: str

