from typing import Any, Dict, List
from src.core.interfaces import PipelineStep, DataSource

class Collector(PipelineStep):
    """
    Coordinates the fetching of data from the source and pushing it down the pipeline.
    """
    def __init__(self, source: DataSource):
        self.source = source

    def process(self, data: Any) -> Any:
        # In this stream-based architecture, the Collector's process method 
        # isn't strictly used as a step. Instead, it yields data from the source.
        pass
        
    def stream(self):
        """Yields raw data directly from the source."""
        yield from self.source.fetch_data()
