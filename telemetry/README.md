# The Marauder's Map - Telemetry Pipeline

**The Marauder's Map** is an enterprise-grade Network Telemetry and Machine Learning data ingestion pipeline developed for the ISRO BAH 2026 project. It establishes a resilient, heavily decoupled architecture designed to ingest, clean, normalize, and engineer complex real-time network metrics for downstream AI analysis.

## Core Capabilities
- **Modular Data Ingestion**: Seamlessly supports Synthetic streams, SNMP (CSV/JSON), BGP Logs, and Live APIs through a Dependency Injected Adapter pattern.
- **Intelligent Auto-Detection**: Uses Strategy pattern to natively sniff inputs and dynamically instantiate the correct data pipeline on the fly.
- **Stateful Feature Engineering**: Maintains real-time rolling history (window-based) per node to calculate moving averages, temporal worsening trends, and heuristic anomaly labeling.
- **Comprehensive Extensibility**: Built natively with SOLID principles. Future engineers simply subclass `DataSource` to inject new protocols (e.g., GNS3) without ever touching core pipeline logic.

## Documentation Index
Comprehensive documentation is available in the `docs/` directory:
- [Telemetry Pipeline Architecture](docs/telemetry_pipeline.md) - Deep dive into the pipeline orchestration, validation rules, and feature extraction plugins.
- [Integration Guide](docs/integration_guide.md) - Manual for future teammates on how to construct and register custom DataSources (e.g., GNS3, Live APIs).
- [Data Dictionary](docs/data_dictionary.md) - Exact schema map of the generated Machine Learning datasets.

## Project Structure
```
telemetry/
│
├── data/                       # Local data storage
│   ├── raw/                    # Raw telemetry inputs
│   ├── processed/              # Normalized, pre-merge datasets
│   └── ml/                     # Versioned, ML-ready outputs (CSV & JSON)
│
├── docs/                       # Project Documentation
│
├── logs/                       # Automated pipeline event logging
│
├── src/                        # Source Code
│   ├── core/                   # Interfaces and Dependency Injection registry
│   ├── pipeline/               # Orchestration stages (Collector, Validator, Normalizer, FeatureEngineer)
│   └── sources/                # Source Adapters (Synthetic, SNMP, BGP)
│
├── src/config.py               # Single Source of Truth for environment configuration
├── src/main.py                 # Primary streaming orchestrator
├── src/merger.py               # Asynchronous log unification engine
└── src/ml_exporter.py          # Final dataset compilation and versioning
```

## Quick Start
The pipeline is entirely environment-driven. No source code modifications are necessary to configure execution.

**1. Run Auto-Detection on a specific file:**
```powershell
$env:DATA_SOURCE_TYPE="auto"
$env:INPUT_URI="test.csv"
python src/main.py
```

**2. Generate ML Dataset:**
```powershell
# Merges asynchronous event sources (SNMP + BGP)
python src/merger.py 

# Extracts exactly the required ML schema and versions the output
python src/ml_exporter.py 
```
