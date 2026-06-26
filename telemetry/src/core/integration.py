import logging
from typing import Dict, Type, Any
from src.core.interfaces import DataSource
from src.config import Config

logger = logging.getLogger('IntegrationLayer')

class DataSourceRegistry:
    """
    Registry for Dependency Injection of DataSources.
    Automatically detects and instantiates the correct source adapter.
    """
    _registry: Dict[str, Type[DataSource]] = {}

    @classmethod
    def register(cls, name: str):
        """Decorator to register a new DataSource adapter."""
        def wrapper(source_cls: Type[DataSource]):
            cls._registry[name.lower()] = source_cls
            return source_cls
        return wrapper

    @classmethod
    def get_source(cls) -> DataSource:
        """
        Detects and instantiates the correct DataSource based on Configuration.
        If DATA_SOURCE_TYPE is 'auto', it delegates detection to the adapters.
        """
        source_type = Config.DATA_SOURCE_TYPE.lower()

        if source_type == 'auto':
            logger.info(f"Auto-detecting telemetry source from INPUT_URI: {Config.INPUT_URI}")
            detected_type = None
            for name, source_cls in cls._registry.items():
                if hasattr(source_cls, 'can_handle') and source_cls.can_handle(Config.INPUT_URI):
                    detected_type = name
                    break
            if detected_type:
                logger.info(f"Auto-detected source type: {detected_type}")
                source_type = detected_type
            else:
                logger.warning("Auto-detection failed. Falling back to synthetic.")
                source_type = 'synthetic'

        if source_type not in cls._registry:
            logger.error(f"Source type '{source_type}' not found in registry. Falling back to synthetic.")
            source_type = 'synthetic'

        source_cls = cls._registry[source_type]
        
        # Instantiate with appropriate kwargs based on type
        # This keeps the adapters decoupled from the central config parsing
        if source_type == 'synthetic':
            logger.info("Injecting Synthetic Data Source.")
            return source_cls(sites=Config.SYNTHETIC_SITES)
        elif source_type == 'snmp':
            logger.info(f"Injecting SNMP Data Source from {Config.SNMP_INPUT_FILE} ({Config.SNMP_INPUT_FORMAT})")
            return source_cls(file_path=Config.SNMP_INPUT_FILE, format=Config.SNMP_INPUT_FORMAT)
        elif source_type == 'bgp':
            logger.info(f"Injecting BGP Log Source from {Config.BGP_INPUT_FILE} ({Config.BGP_INPUT_FORMAT})")
            return source_cls(file_path=Config.BGP_INPUT_FILE, format=Config.BGP_INPUT_FORMAT)
        else:
            # Future custom sources can initialize cleanly here or via a more generic init
            logger.info(f"Injecting Custom Source: {source_type}")
            return source_cls()
