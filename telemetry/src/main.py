import signal
import sys
import logging

from src.config import Config
from src.core.interfaces import DataSource
from src.pipeline.collector import Collector
from src.sources.synthetic import SyntheticSource
from src.sources.snmp import SNMPSource
from src.sources.bgp import BGPSource
from src.sources.influxdb import InfluxDBSource
from src.logger import setup_logging

# Import Pipeline Stages
from src.pipeline.cleaner import Cleaner
from src.pipeline.validator import Validator
from src.pipeline.normalizer import Normalizer
from src.pipeline.feature_engineer import FeatureEngineer
from src.pipeline.dataset_generator import DatasetGenerator, BGPDatasetGenerator
from src.pipeline.exporter import Exporter, BGPExporter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('TelemetryPipeline')

from src.core.integration import DataSourceRegistry

def main():
    setup_logging()
    logger.info("pipeline start")
    logger.info("Starting The Marauder's Map Telemetry Pipeline")
    
    # Dependency Injection: Inject the correct DataSource via Registry
    source = DataSourceRegistry.get_source()
    logger.info("collector start")
    collector = Collector(source)
    
    is_bgp = isinstance(source, BGPSource)
    
    if is_bgp:
        # BGP pipeline
        dataset_generator = BGPDatasetGenerator()
        exporter = BGPExporter(output_path=Config.BGP_OUTPUT_FILE)
        logger.info(f"BGP Pipeline writing to {Config.BGP_OUTPUT_FILE}")
    else:
        # Standard Network metrics pipeline
        cleaner = Cleaner()
        validator = Validator()
        normalizer = Normalizer()
        feature_engineer = FeatureEngineer()
        dataset_generator = DatasetGenerator()
        exporter = Exporter(output_path=Config.OUTPUT_FILE)
        logger.info(f"Standard Pipeline writing to {Config.OUTPUT_FILE}")
        
    logger.info("Press Ctrl+C to stop.")

    try:
        # Stream processing
        for raw_data in collector.stream():
            data = raw_data
            if not is_bgp:
                # Pass data through the standard pipeline stages
                data = cleaner.process(data)
                data = validator.process(data)
                data = normalizer.process(data)
                data = feature_engineer.process(data)
            
            record = dataset_generator.process(data)
            if record:
                exporter.process(record)
                logger.info(f"Processed record for node: {record.node}")

    except KeyboardInterrupt:
        logger.info("\nPipeline stopped by user.")
    finally:
        exporter.close()
        logger.info("Pipeline shutdown complete.")

if __name__ == '__main__':
    main()
