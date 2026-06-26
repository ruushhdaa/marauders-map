from abc import ABC, abstractmethod
from typing import Any, Dict, List, Iterator

class DataSource(ABC):
    """
    Abstract Base Class for Telemetry Data Sources.
    """
    
    @abstractmethod
    def fetch_data(self) -> Iterator[Dict[str, Any]]:
        """
        Yields standard dictionary representation of raw network logs.
        """
        pass

    @classmethod
    def can_handle(cls, source_uri: str) -> bool:
        """
        Determines if the specific DataSource can handle the given input URI.
        Defaults to False unless overridden by specific adapters.
        """
        return False

class PipelineStep(ABC):
    """
    Abstract Base Class for Pipeline Stages.
    """
    
    @abstractmethod
    def process(self, data: Any) -> Any:
        """
        Process the data and return the transformed data.
        """
        pass
