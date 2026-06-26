import os
import logging
from typing import Any, Dict, Iterator
from influxdb_client import InfluxDBClient
from src.core.interfaces import DataSource
from src.core.integration import DataSourceRegistry
from src.config import Config

logger = logging.getLogger('InfluxDBSource')

@DataSourceRegistry.register('influxdb')
class InfluxDBSource(DataSource):
    """
    Adapter for connecting to InfluxDB to retrieve historical telemetry.
    """
    
    @classmethod
    def can_handle(cls, source_uri: str) -> bool:
        return source_uri.startswith('influxdb://')

    def __init__(self):
        self.url = Config.INFLUXDB_URL
        self.token = Config.INFLUXDB_TOKEN
        self.org = Config.INFLUXDB_ORG
        self.bucket = Config.INFLUXDB_BUCKET
        self.client = None

    def connect(self) -> None:
        logger.info(f"Connecting to InfluxDB at {self.url}")
        self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)

    def fetch_data(self) -> Iterator[Dict[str, Any]]:
        if not self.client:
            self.connect()
            
        query_api = self.client.query_api()
        # Querying the last 48 hours to match the demo generator data
        query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: -48h)
          |> filter(fn: (r) => r["_measurement"] == "{Config.INFLUXDB_MEASUREMENT}")
          |> pivot(rowKey:["_time", "node_id"], columnKey: ["_field"], valueColumn: "_value")
        '''
        
        logger.info("Executing InfluxDB query...")
        try:
            tables = query_api.query(query, org=self.org)
            
            for table in tables:
                for record in table.records:
                    # Map InfluxDB schema to our internal schema
                    yield {
                        'timestamp': record.get_time().isoformat() if record.get_time() else None,
                        'node': record.values.get("node_id"),
                        'latency': float(record.values.get("latency_ms", 0.0)),
                        'jitter': float(record.values.get("jitter_ms", 0.0)),
                        'packet_loss': float(record.values.get("packet_loss", 0.0)),
                        'bandwidth': float(record.values.get("bandwidth_utilization", 0.0)),
                        'cpu': float(record.values.get("cpu_utilization", 0.0)),
                        'bgp_status': 1 # Defaulting to 1 for this data source
                    }
        except Exception as e:
            logger.error(f"Failed to fetch data from InfluxDB: {e}")
        finally:
            self.disconnect()

    def disconnect(self) -> None:
        if self.client:
            self.client.close()
            self.client = None
