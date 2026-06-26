import csv
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator
from datetime import datetime
import dateutil.parser

from src.core.interfaces import DataSource
from src.core.integration import DataSourceRegistry

logger = logging.getLogger('SNMPSource')

class SNMPReader(ABC):
    """Abstract Base Class for reading raw SNMP data from different formats."""
    @abstractmethod
    def read(self) -> Iterator[Dict[str, Any]]:
        pass

class CSV_SNMPReader(SNMPReader):
    """Reads SNMP data from a CSV file."""
    def __init__(self, file_path: str):
        self.file_path = file_path

    def read(self) -> Iterator[Dict[str, Any]]:
        try:
            with open(self.file_path, mode='r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    yield row
                    time.sleep(0.5) # Simulate stream
        except FileNotFoundError:
            logger.error(f"CSV file not found: {self.file_path}")

class JSON_SNMPReader(SNMPReader):
    """Reads SNMP data from a JSON file."""
    def __init__(self, file_path: str):
        self.file_path = file_path

    def read(self) -> Iterator[Dict[str, Any]]:
        try:
            with open(self.file_path, mode='r') as f:
                data = json.load(f)
                if not isinstance(data, list):
                    logger.error("JSON data must be a list of records.")
                    return
                for record in data:
                    yield record
                    time.sleep(0.5) # Simulate stream
        except FileNotFoundError:
            logger.error(f"JSON file not found: {self.file_path}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON format in file: {self.file_path}")

@DataSourceRegistry.register('snmp')
class SNMPSource(DataSource):
    @classmethod
    def can_handle(cls, source_uri: str) -> bool:
        if 'snmp' in source_uri.lower():
            return True
        if source_uri.endswith('.csv') and 'bgp' not in source_uri.lower():
            return True
        return False
    """
    Ingests SNMP data using an adapter, validates it, and normalizes it
    to the common internal format.
    """
    
    def __init__(self, file_path: str, format: str = 'csv'):
        self.file_path = file_path
        self.format = format.lower()
        
        if self.format == 'csv':
            self.reader = CSV_SNMPReader(file_path)
        elif self.format == 'json':
            self.reader = JSON_SNMPReader(file_path)
        else:
            raise ValueError(f"Unsupported format: {self.format}")

    def _validate_and_normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Performs strict SNMP-specific validation and type conversion.
        Missing or invalid records are logged and dropped (returns None).
        """
        try:
            # 1. Handle missing values
            expected_keys = ['timestamp', 'node', 'latency', 'jitter', 'packet_loss', 'bandwidth', 'cpu', 'bgp_status']
            if not all(k in raw_data for k in expected_keys):
                logger.warning(f"Dropping record: Missing fields. Raw: {raw_data}")
                return None
                
            # Handle empty strings from CSV
            if any(raw_data[k] == '' for k in expected_keys):
                logger.warning(f"Dropping record: Empty values. Raw: {raw_data}")
                return None

            # 2. Validate timestamp
            try:
                # dateutil parses various ISO formats gracefully
                parsed_time = dateutil.parser.isoparse(str(raw_data['timestamp']))
                timestamp = parsed_time.isoformat()
            except ValueError:
                logger.warning(f"Dropping record: Invalid timestamp format '{raw_data['timestamp']}'")
                return None

            # 3. Type conversions and range validations
            latency = float(raw_data['latency'])
            jitter = float(raw_data['jitter'])
            packet_loss = float(raw_data['packet_loss'])
            bandwidth = float(raw_data['bandwidth'])
            cpu = float(raw_data['cpu'])
            bgp_status = int(raw_data['bgp_status'])

            if latency < 0 or jitter < 0:
                logger.warning(f"validation errors: Latency/Jitter cannot be negative. Raw: {raw_data}")
                return None
            if not (0 <= packet_loss <= 100):
                logger.warning(f"validation errors: Packet loss out of bounds (0-100). Raw: {raw_data}")
                return None
            if not (0 <= bandwidth <= 100):
                logger.warning(f"validation errors: Bandwidth utilization out of bounds (0-100). Raw: {raw_data}")
                return None
            if not (0 <= cpu <= 100):
                logger.warning(f"validation errors: CPU utilization out of bounds (0-100). Raw: {raw_data}")
                return None
            if bgp_status not in (0, 1):
                logger.warning(f"validation errors: BGP status must be 0 or 1. Raw: {raw_data}")
                return None

            return {
                'timestamp': timestamp,
                'node': str(raw_data['node']),
                'latency': latency,
                'jitter': jitter,
                'packet_loss': packet_loss,
                'bandwidth': bandwidth,
                'cpu': cpu,
                'bgp_status': bgp_status
            }

        except (ValueError, TypeError) as e:
            logger.warning(f"Dropping record: Type conversion error - {e}. Raw: {raw_data}")
            return None

    def fetch_data(self) -> Iterator[Dict[str, Any]]:
        """
        Yields clean, standardized records.
        """
        logger.info("SNMP records loaded")
        for raw_record in self.reader.read():
            clean_record = self._validate_and_normalize(raw_record)
            if clean_record is not None:
                yield clean_record
