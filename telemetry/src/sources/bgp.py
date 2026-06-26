import csv
import json
import logging
import time
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator
from datetime import datetime
import dateutil.parser

from src.core.interfaces import DataSource
from src.core.integration import DataSourceRegistry

logger = logging.getLogger('BGPSource')

class BGPReader(ABC):
    """Abstract Base Class for reading raw BGP data from different formats."""
    @abstractmethod
    def read(self) -> Iterator[Dict[str, Any]]:
        pass

class CSV_BGPReader(BGPReader):
    """Reads BGP data from a CSV file."""
    def __init__(self, file_path: str):
        self.file_path = file_path

    def read(self) -> Iterator[Dict[str, Any]]:
        try:
            with open(self.file_path, mode='r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    yield row
                    time.sleep(0.5)
        except FileNotFoundError:
            logger.error(f"CSV file not found: {self.file_path}")

class JSON_BGPReader(BGPReader):
    """Reads BGP data from a JSON file."""
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
                    time.sleep(0.5)
        except FileNotFoundError:
            logger.error(f"JSON file not found: {self.file_path}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON format in file: {self.file_path}")

class TextLog_BGPReader(BGPReader):
    """
    Reads and parses BGP syslog files using regex.
    Expected log format:
    TIMESTAMP node=NODE neighbor=NEIGHBOR event=EVENT severity=SEVERITY bgp_status=STATUS
    Example:
    2026-06-25T12:00:00Z node=router1 neighbor=10.0.0.1 event=BGP-5-ADJCHANGE severity=warning bgp_status=0
    """
    def __init__(self, file_path: str):
        self.file_path = file_path
        # Regex to capture timestamp and key=value pairs
        self.log_pattern = re.compile(
            r'^(?P<timestamp>\S+)\s+'
            r'node=(?P<node>\S+)\s+'
            r'neighbor=(?P<neighbor>\S+)\s+'
            r'event=(?P<event>\S+)\s+'
            r'severity=(?P<severity>\S+)\s+'
            r'bgp_status=(?P<bgp_status>\d+)'
        )

    def read(self) -> Iterator[Dict[str, Any]]:
        try:
            with open(self.file_path, mode='r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    match = self.log_pattern.search(line)
                    if match:
                        yield match.groupdict()
                    else:
                        logger.warning(f"Could not parse log line: {line}")
                    
                    time.sleep(0.5)
        except FileNotFoundError:
            logger.error(f"Log file not found: {self.file_path}")

@DataSourceRegistry.register('bgp')
class BGPSource(DataSource):
    """
    Ingests BGP events using an adapter, validates it, and normalizes it
    to the internal dictionary format matching the BGPRecord schema.
    """

    @classmethod
    def can_handle(cls, source_uri: str) -> bool:
        if 'bgp' in source_uri.lower():
            return True
        if source_uri.endswith('.log'):
            return True
        return False

    def __init__(self, file_path: str, format: str = 'text'):
        self.file_path = file_path
        self.format = format.lower()
        
        if self.format == 'csv':
            self.reader = CSV_BGPReader(file_path)
        elif self.format == 'json':
            self.reader = JSON_BGPReader(file_path)
        elif self.format == 'text' or self.format == 'log':
            self.reader = TextLog_BGPReader(file_path)
        else:
            raise ValueError(f"Unsupported format: {self.format}")

    def _validate_and_normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates timestamps, missing fields, and normalizes types.
        """
        try:
            expected_keys = ['timestamp', 'node', 'bgp_status', 'neighbor', 'event', 'severity']
            if not all(k in raw_data for k in expected_keys):
                logger.warning(f"Dropping BGP record: Missing fields. Raw: {raw_data}")
                return None
                
            if any(str(raw_data[k]).strip() == '' for k in expected_keys):
                logger.warning(f"Dropping BGP record: Empty values. Raw: {raw_data}")
                return None

            try:
                parsed_time = dateutil.parser.isoparse(str(raw_data['timestamp']))
                timestamp = parsed_time.isoformat()
            except ValueError:
                logger.warning(f"validation errors: Invalid timestamp format '{raw_data['timestamp']}'")
                return None

            bgp_status = int(raw_data['bgp_status'])
            if bgp_status not in (0, 1):
                logger.warning(f"validation errors: BGP status must be 0 or 1. Raw: {raw_data}")
                return None

            return {
                'timestamp': timestamp,
                'node': str(raw_data['node']),
                'bgp_status': bgp_status,
                'neighbor': str(raw_data['neighbor']),
                'event': str(raw_data['event']),
                'severity': str(raw_data['severity'])
            }

        except (ValueError, TypeError) as e:
            logger.warning(f"validation errors: Type conversion error - {e}. Raw: {raw_data}")
            return None

    def fetch_data(self) -> Iterator[Dict[str, Any]]:
        """Yields clean, standardized BGP records."""
        logger.info("BGP records loaded")
        for raw_record in self.reader.read():
            clean_record = self._validate_and_normalize(raw_record)
            if clean_record is not None:
                yield clean_record
