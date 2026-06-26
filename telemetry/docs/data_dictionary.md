# Data Dictionary

This document defines the schema of the final Machine Learning dataset compiled and exported into `data/ml/v1.0/dataset.csv` and `data/ml/v1.0/dataset.json`.

All upstream validation errors, transient records, and intermediate calculations have been purged. This specific schema is guaranteed to be clean, normalized, and model-ready.

| Field | Data Type | Description |
|---|---|---|
| **timestamp** | `datetime64[ns]` | ISO 8601 formatted timestamp of the telemetry event. |
| **node** | `string` | Unique identifier for the network device (e.g., router_1, branch_hub). |
| **latency** | `float64` | Measured round-trip delay in milliseconds. Minimum 0. |
| **jitter** | `float64` | Variation in packet delay in milliseconds. |
| **packet_loss** | `float64` | Percentage of packets lost in transit (0.0 to 100.0). |
| **bandwidth** | `float64` | Current interface bandwidth utilization as a percentage (0.0 to 100.0). |
| **cpu** | `float64` | Current CPU utilization of the device as a percentage (0.0 to 100.0). |
| **bgp_status** | `int64` | Binary status of BGP peering (1 = Established, 0 = Down). Prioritizes actual asynchronous BGP events, falls back to SNMP base metrics. |
| **health_score** | `float64` | Engineered Feature: Heuristic representation of device health (0-100). |
| **risk_score** | `float64` | Engineered Feature: Statistical probability of impending failure based on worsening trends (0-100). |
| **anomaly** | `int64` | Binary Classification Target (1 = Anomaly detected, 0 = Normal operation). Computed based on strict configuration thresholds. |

## Feature Engineering Specifics
The `health_score`, `risk_score`, and `anomaly` fields are not sourced from raw logs. They are actively compiled during the pipeline's execution phase within `src/pipeline/feature_engineer.py` by maintaining a rolling chronological queue and identifying deviation from the moving average. These formulas can be tuned across environments entirely via `src/config.py`.
