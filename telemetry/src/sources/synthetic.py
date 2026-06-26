import time
import random
from datetime import datetime
from typing import Any, Dict, Iterator, List
from src.core.interfaces import DataSource
from src.core.integration import DataSourceRegistry

@DataSourceRegistry.register('synthetic')
class SyntheticSource(DataSource):
    """
    Generates synthetic telemetry data for testing.
    """
    
    @classmethod
    def can_handle(cls, source_uri: str) -> bool:
        return source_uri.lower() == 'synthetic'

    def __init__(self, sites: List[str] = None):
        self.sites = sites or ['branch1', 'hub', 'datacenter']
        self.bgp_status = {site: 1 for site in self.sites}

    def _generate_telemetry_for_site(self, site: str) -> Dict[str, Any]:
        """Generates realistic telemetry for a single site."""
        latency = random.uniform(10.0, 50.0)
        jitter = random.uniform(1.0, 5.0)
        packet_loss = random.uniform(0.0, 0.5)
        bandwidth_utilization = random.uniform(20.0, 80.0)
        cpu_utilization = random.uniform(10.0, 60.0)
        
        # Introduce anomalies
        anomaly_chance = random.random()
        
        if anomaly_chance < 0.05:
            anomaly_type = random.choice(['latency_spike', 'packet_loss_spike', 'bgp_down'])
            if anomaly_type == 'latency_spike':
                latency = random.uniform(150.0, 500.0)
            elif anomaly_type == 'packet_loss_spike':
                packet_loss = random.uniform(10.0, 50.0)
            elif anomaly_type == 'bgp_down':
                self.bgp_status[site] = 0
                
        # BGP Recovery mechanism
        if self.bgp_status[site] == 0 and random.random() < 0.20:
            self.bgp_status[site] = 1

        return {
            'timestamp': datetime.now().isoformat(),
            'node': site,
            'latency': round(latency, 2),
            'jitter': round(jitter, 2),
            'packet_loss': round(packet_loss, 2),
            'bandwidth': round(bandwidth_utilization, 2),
            'cpu': round(cpu_utilization, 2),
            'bgp_status': self.bgp_status[site]
        }

    def fetch_data(self) -> Iterator[Dict[str, Any]]:
        """
        Yields an infinite stream of synthetic telemetry records.
        """
        while True:
            for site in self.sites:
                yield self._generate_telemetry_for_site(site)
            # Sleep briefly to simulate real-time generation rate
            time.sleep(1)
