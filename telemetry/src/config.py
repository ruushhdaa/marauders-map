import os

class Config:
    """
    Configuration settings for the telemetry pipeline.
    """
    
    # Source Configuration ('synthetic', 'snmp', or 'bgp')
    # Can be overridden via environment variables
    # Default input URI for auto-detection
    INPUT_URI = os.getenv('INPUT_URI', '')
    DATA_SOURCE_TYPE = os.getenv('DATA_SOURCE_TYPE', 'synthetic')
    
    # Paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    PROCESSED_DIR = os.path.join(DATA_DIR, 'processed')
    OUTPUT_FILE = os.path.join(PROCESSED_DIR, 'network_timeseries.csv')
    
    # Source Specific Settings
    SNMP_ENDPOINT = os.getenv('SNMP_ENDPOINT', 'udp://127.0.0.1:161')
    SNMP_INPUT_FILE = os.getenv('SNMP_INPUT_FILE', os.path.join(DATA_DIR, 'raw', 'dummy_snmp.csv'))
    SNMP_INPUT_FORMAT = os.getenv('SNMP_INPUT_FORMAT', 'csv')
    
    BGP_INPUT_FILE = os.getenv('BGP_INPUT_FILE', os.path.join(DATA_DIR, 'raw', 'dummy_bgp.log'))
    BGP_INPUT_FORMAT = os.getenv('BGP_INPUT_FORMAT', 'log')
    BGP_OUTPUT_FILE = os.path.join(PROCESSED_DIR, 'bgp_events.csv')
    
    UNIFIED_OUTPUT_FILE = os.path.join(PROCESSED_DIR, 'unified_telemetry.csv')
    
    ML_DIR = os.path.join(DATA_DIR, 'ml')
    
    # -----------------------------------------------------
    # Pipeline Settings
    # -----------------------------------------------------
    PIPELINE_MODE = os.getenv('PIPELINE_MODE', 'streaming') # streaming or batch
    SYNTHETIC_SITES = os.getenv('SYNTHETIC_SITES', 'branch1,hub,datacenter').split(',')
    
    # -----------------------------------------------------
    # Validation & Extraction Thresholds
    # -----------------------------------------------------
    THRESHOLD_LATENCY_MAX = float(os.getenv('THRESHOLD_LATENCY_MAX', 10000.0)) # ms
    THRESHOLD_PACKET_LOSS_MAX = float(os.getenv('THRESHOLD_PACKET_LOSS_MAX', 100.0)) # %
    THRESHOLD_BANDWIDTH_MAX = float(os.getenv('THRESHOLD_BANDWIDTH_MAX', 100.0)) # %
    THRESHOLD_CPU_MAX = float(os.getenv('THRESHOLD_CPU_MAX', 100.0)) # %
    
    # Health Scoring Defaults
    HEALTH_PENALTY_BGP_DOWN = float(os.getenv('HEALTH_PENALTY_BGP_DOWN', 50.0))
    HEALTH_PENALTY_LATENCY_HIGH = float(os.getenv('HEALTH_PENALTY_LATENCY_HIGH', 10.0))
    LATENCY_HIGH_MARK = float(os.getenv('LATENCY_HIGH_MARK', 100.0))
    
    # Risk Scoring Defaults
    RISK_PENALTY_LATENCY_TREND = float(os.getenv('RISK_PENALTY_LATENCY_TREND', 20.0))
    RISK_PENALTY_LOSS_TREND = float(os.getenv('RISK_PENALTY_LOSS_TREND', 30.0))
    RISK_PENALTY_LOW_HEALTH = float(os.getenv('RISK_PENALTY_LOW_HEALTH', 50.0))
    TREND_LATENCY_HIGH_MARK = float(os.getenv('TREND_LATENCY_HIGH_MARK', 20.0))
    TREND_LOSS_HIGH_MARK = float(os.getenv('TREND_LOSS_HIGH_MARK', 5.0))
    
    # Anomaly Definition Defaults
    ANOMALY_LATENCY_THRESHOLD = float(os.getenv('ANOMALY_LATENCY_THRESHOLD', 100.0))
    ANOMALY_PACKET_LOSS_THRESHOLD = float(os.getenv('ANOMALY_PACKET_LOSS_THRESHOLD', 5.0))
    
    # -----------------------------------------------------
    # Future API Settings
    # -----------------------------------------------------
    API_URL = os.getenv('API_URL', 'https://api.example.com/telemetry')
    API_AUTH_TOKEN = os.getenv('API_AUTH_TOKEN', '')
    API_TIMEOUT = int(os.getenv('API_TIMEOUT', 30))
    API_RETRY_ATTEMPTS = int(os.getenv('API_RETRY_ATTEMPTS', 3))
