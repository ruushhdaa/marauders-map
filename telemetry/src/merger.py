import pandas as pd
import logging
import os
from src.config import Config
from src.logger import setup_logging

setup_logging()
logger = logging.getLogger('TelemetryMerger')

def clean_dataframe(df: pd.DataFrame, df_name: str) -> pd.DataFrame:
    """
    Cleans the dataframe by handling missing timestamps, duplicate records,
    and sorting by timestamp.
    """
    initial_len = len(df)
    
    # 1. Parse timestamps
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')
    
    # 2. Drop missing timestamps
    df.dropna(subset=['timestamp'], inplace=True)
    if len(df) < initial_len:
        logger.info(f"{df_name}: Dropped {initial_len - len(df)} rows with missing/invalid timestamps.")
        
    # 3. Sort chronologically
    df.sort_values(by='timestamp', inplace=True)
    
    # 4. Drop duplicates for the same (timestamp, node)
    initial_len = len(df)
    df.drop_duplicates(subset=['timestamp', 'node'], keep='last', inplace=True)
    if len(df) < initial_len:
        logger.info(f"{df_name}: Dropped {initial_len - len(df)} duplicate records.")
        
    return df

def merge_telemetry():
    """
    Merges SNMP network metrics and BGP events into a unified dataframe.
    """
    snmp_file = Config.OUTPUT_FILE
    bgp_file = Config.BGP_OUTPUT_FILE
    unified_file = Config.UNIFIED_OUTPUT_FILE

    if not os.path.exists(snmp_file):
        logger.error(f"SNMP file not found at {snmp_file}. Cannot merge.")
        return
        
    if not os.path.exists(bgp_file):
        logger.error(f"BGP file not found at {bgp_file}. Cannot merge.")
        return

    logger.info("Loading datasets...")
    df_snmp = pd.read_csv(snmp_file)
    df_bgp = pd.read_csv(bgp_file)

    logger.info("Cleaning and preparing datasets...")
    df_snmp = clean_dataframe(df_snmp, "SNMP")
    df_bgp = clean_dataframe(df_bgp, "BGP")
    
    if df_snmp.empty or df_bgp.empty:
        logger.warning("One of the datasets is empty after cleaning. Aborting merge.")
        return

    # Pandas merge_asof requires both DataFrames to be sorted by the 'on' key.
    # It joins the closest timestamp from the right dataframe (BGP) to the left (SNMP),
    # looking backwards in time (direction='backward').
    logger.info("Performing merge_asof with 5-minute tolerance...")
    
    # Explicitly define tolerance
    tolerance = pd.Timedelta('5min')
    
    df_unified = pd.merge_asof(
        left=df_snmp,
        right=df_bgp,
        on='timestamp',
        by='node',
        tolerance=tolerance,
        direction='backward',
        suffixes=('_snmp', '_bgp')
    )

    # Export
    os.makedirs(os.path.dirname(unified_file), exist_ok=True)
    
    # Optional: format timestamp back to ISO
    df_unified['timestamp'] = df_unified['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S.%f')
    
    df_unified.to_csv(unified_file, index=False)
    logger.info(f"Successfully unified {len(df_unified)} records.")
    logger.info(f"Saved to: {unified_file}")

if __name__ == '__main__':
    merge_telemetry()
