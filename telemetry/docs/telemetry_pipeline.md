# Telemetry Pipeline Architecture

The Marauder's Map Pipeline leverages a sequential, state-machine driven architecture. Each record flows through highly decoupled stages. 

## The Orchestration Flow

1. **Collector**  
   Ingests data from the dynamically injected `DataSource`. It acts as a generator, yielding records sequentially without holding the entire dataset in memory, natively supporting live, infinite streams.
   
2. **Cleaner & Validator**  
   Scrub incoming records to prevent downstream poison. 
   - Strict adherence to defined bounding limits configured in `src/config.py`.
   - Records attempting to push negative latency, impossible percentages (>100% bandwidth utilization), or invalid timestamps are explicitly dropped and safely written out to `logs/pipeline.log`.

3. **Normalizer**  
   Ensures raw data is scaled to boundaries expected by future ML algorithms. By default, it allows values to pass through cleanly, but stands as the entry point for custom scalers (e.g. MinMax).

4. **Feature Engineer (Plugin Architecture)**  
   The most complex node in the pipeline. It maintains a stateful 5-record chronological queue per network node. It sequences records through an array of Extractor Plugins:
   - **`MovingAverageExtractor`**: Emits real-time smoothed curves to ignore temporary spikes.
   - **`TrendExtractor`**: Instantly calculates the mathematical delta between immediate stats and the historical norm, detecting gradual degradation.
   - **`ScoreExtractor`**: A heuristic rule engine that converts massive stat-blocks into an easily understandable `health_score` and `risk_score`.
   - **`AnomalyExtractor`**: Final hard-threshold labeling targeting Binary Classification models.

5. **Exporters**  
   Final processing output. Standard metrics write iteratively to `network_timeseries.csv` while discrete events write to `bgp_events.csv`.

## Offline Batch Merge
Because standard metrics (SNMP) trigger on a chron scheduler and discrete logs (BGP) trigger asynchronously upon state changes, they rarely align on the exact millisecond. 
`src/merger.py` solves this using a **nearest-neighbor backward-looking join** (`pandas.merge_asof`). It accepts a 5-minute tolerance window, intelligently assigning the latest BGP event to the closest SNMP poll without duplicating records or dropping baseline statistics.
