import pandas as pd
import os
import json
import logging
from src.config import Config
from src.logger import setup_logging

setup_logging()
logger = logging.getLogger('MLExporter')

DATA_DICTIONARY = {
    "timestamp": {"type": "string (ISO 8601)", "description": "The exact time the telemetry was recorded or the event occurred."},
    "node": {"type": "string", "description": "The identifier of the network device (e.g., router, switch, branch)."},
    "latency": {"type": "float", "description": "Network latency measured in milliseconds (ms)."},
    "jitter": {"type": "float", "description": "Variation in latency measured in milliseconds (ms)."},
    "packet_loss": {"type": "float", "description": "Percentage of packets lost during transmission (0-100)."},
    "bandwidth": {"type": "float", "description": "Network bandwidth utilization in Mbps."},
    "cpu": {"type": "float", "description": "Device CPU utilization percentage (0-100)."},
    "bgp_status": {"type": "integer", "description": "Binary indicator of BGP session health (1 = UP, 0 = DOWN)."},
    "health_score": {"type": "float", "description": "Heuristic health score from 0 to 100 based on immediate metric violations."},
    "risk_score": {"type": "float", "description": "Heuristic risk score from 0 to 100 based on worsening moving average trends."},
    "anomaly": {"type": "integer", "description": "Binary label indicating if the record represents a critical anomaly (1 = Anomaly, 0 = Normal)."}
}

def generate_data_dictionary(output_dir: str):
    """Generates a markdown Data Dictionary file."""
    md_content = "# Telemetry ML Dataset - Data Dictionary\n\n"
    md_content += "| Feature | Data Type | Description |\n"
    md_content += "|---------|-----------|-------------|\n"
    
    for feature, meta in DATA_DICTIONARY.items():
        md_content += f"| **{feature}** | `{meta['type']}` | {meta['description']} |\n"
        
    dict_path = os.path.join(output_dir, 'data_dictionary.md')
    with open(dict_path, 'w') as f:
        f.write(md_content)
    logger.info(f"Generated Data Dictionary at: {dict_path}")

def export_dataset(version: str = "v1.0"):
    """
    Reads the unified dataset, rigidly enforces the ML schema,
    resolves BGP logic, and outputs CSV, JSON and Data Dict into a versioned folder.
    """
    unified_file = Config.UNIFIED_OUTPUT_FILE
    if not os.path.exists(unified_file):
        logger.error(f"Unified telemetry file not found at {unified_file}. Run merger.py first.")
        return
        
    logger.info("Loading unified telemetry dataset...")
    df = pd.read_csv(unified_file)
    
    # Resolve BGP Status
    # unified dataframe has 'bgp_status_snmp' and 'bgp_status_bgp'
    # We prioritize the discrete event 'bgp_status_bgp' if available, else fallback to SNMP
    if 'bgp_status_bgp' in df.columns and 'bgp_status_snmp' in df.columns:
        df['bgp_status'] = df['bgp_status_bgp'].combine_first(df['bgp_status_snmp'])
    elif 'bgp_status_snmp' in df.columns:
        df['bgp_status'] = df['bgp_status_snmp']
    else:
        # Fallback if merger didn't run properly
        df['bgp_status'] = 1
        
    # Convert bgp_status back to integer
    df['bgp_status'] = df['bgp_status'].fillna(1).astype(int)
    
    # Filter columns for ML
    ml_columns = [
        'timestamp', 'node', 'latency', 'jitter', 'packet_loss', 
        'bandwidth', 'cpu', 'bgp_status', 'health_score', 'risk_score', 'anomaly'
    ]
    
    # Ensure all required columns exist, fill with defaults if missing
    for col in ml_columns:
        if col not in df.columns:
            logger.warning(f"Column '{col}' missing. Filling with 0.")
            df[col] = 0
            
    df_ml = df[ml_columns].copy()
    
    # Prepare versioned directory
    output_dir = os.path.join(Config.ML_DIR, version)
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Export CSV
    csv_path = os.path.join(output_dir, 'dataset.csv')
    df_ml.to_csv(csv_path, index=False)
    logger.info(f"Exported CSV: {csv_path}")
    
    # 2. Export JSON (records orientation)
    json_path = os.path.join(output_dir, 'dataset.json')
    df_ml.to_json(json_path, orient='records', date_format='iso', indent=4)
    logger.info(f"Exported JSON: {json_path}")
    
    # 3. Generate Data Dictionary
    generate_data_dictionary(output_dir)
    logger.info("dataset exported")

if __name__ == '__main__':
    # Default to v1.0, but could be passed via argparse
    export_dataset(version="v1.0")
