# Integration Guide for Telemetry Modules

This pipeline is built upon the **Dependency Injection** and **Strategy** design patterns. This means that expanding the pipeline to consume data from new proprietary sources (such as a live GNS3 Network Simulation API or new CSV/JSON schemas) requires exactly **zero** modifications to the core orchestrator.

## How to add a new Data Adapter

Follow these 4 simple steps to integrate your module.

### 1. Create a Source Adapter File
Navigate to `src/sources/` and create a new Python file for your system (e.g. `gns3.py`).

### 2. Implement the `DataSource` Interface
Your class must inherit from `src.core.interfaces.DataSource`. It enforces three required methods:
- `connect()`: Establish connection (open file, authenticate with API).
- `fetch_data()`: Yield your raw records.
- `disconnect()`: Teardown and clean up resources safely.

### 3. Register your Module
Import the `DataSourceRegistry` and attach the `@DataSourceRegistry.register` decorator to your class. 

### 4. Build the Auto-Detect Strategy (Optional but Recommended)
Implement the `@classmethod can_handle(cls, source_uri)` function. The registry will pass the active environment's `INPUT_URI` through this method. If your class recognizes the formatting (e.g. "it contains `.gns3`"), simply return `True` to seize control of the pipeline.

### Example Boilerplate
```python
import logging
from typing import Iterator, Dict, Any
from src.core.interfaces import DataSource
from src.core.integration import DataSourceRegistry

logger = logging.getLogger('GNS3Adapter')

@DataSourceRegistry.register('gns3_simulation')
class GNS3Source(DataSource):
    """
    Adapter for connecting directly to live GNS3 instances via API.
    """
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.client = None

    @classmethod
    def can_handle(cls, source_uri: str) -> bool:
        """Auto-detection strategy"""
        return "gns3" in source_uri.lower()

    def connect(self) -> None:
        logger.info(f"Connecting to GNS3 API at {self.endpoint}")
        # self.client = RESTClient(self.endpoint)

    def fetch_data(self) -> Iterator[Dict[str, Any]]:
        # for raw_record in self.client.stream():
        #     # Format the record to match the required schema here
        #     yield clean_record
        pass

    def disconnect(self) -> None:
        if self.client:
            # self.client.close()
            pass
```

## Running the Integration
Simply spin up the environment with your newly formatted URI and ensure `DATA_SOURCE_TYPE="auto"`. 
The `DataSourceRegistry` will detect your class, construct it, and intelligently inject it directly into the `Collector` pipeline automatically.

```powershell
$env:DATA_SOURCE_TYPE="auto"
$env:INPUT_URI="http://192.168.1.100:3080/gns3/telemetry"
python src/main.py
```
