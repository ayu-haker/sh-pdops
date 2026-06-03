# SH-PDOPS: Self-Healing + Predictive DevOps System

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SH-PDOPS Core Engine                         │
│                                                                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐      │
│  │ Collector │───▶│ Detector │───▶│ Predictor│───▶│  Healer  │      │
│  │  Layer    │    │  Layer   │    │  Layer   │    │  Layer   │      │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘      │
│       │                │               │               │            │
│       ▼                ▼               ▼               ▼            │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐      │
│  │Simulated │    │Statistical│   │  Failure  │    │  Local   │      │
│  │  Metrics │    │ Anomaly   │   │Predictor  │    │Remediation│     │
│  │          │    │ Detection │   │ (Polyfit) │    │  Engine  │      │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘      │
└─────────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   FastAPI REST   │  │  Streamlit Dash  │  │   ML Models      │
│   (port 8000)    │  │  (port 8501)     │  │  (joblib cache)  │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

## Component Description

### 1. Collector Layer (`src/collector/`)
- **SimulatedCollector**: Generates realistic time-series metrics for 6 microservices
  - CPU, Memory, Disk, Latency, Error Rate, Request Rate
  - Sinusoidal patterns + noise + drift for realistic behavior
  - Fault injection: cpu_spike, memory_leak, latency_burst, error_burst, traffic_surge

### 2. Detector Layer (`src/detector/`)
- **StatisticalDetector**: Z-score based anomaly detection
  - Configurable sensitivity threshold
  - Detects spikes and drops
  - Maintains rolling history for adaptive baselines

### 3. Predictor Layer (`src/predictor/`)
- **FailurePredictor**: Polynomial regression + heuristic failure prediction
  - Multi-degree polynomial curve fitting
  - Confidence-weighted prediction intervals
  - Failure probability scoring based on metric thresholds and trends
  - Time-to-failure estimation

### 4. Healer Layer (`src/healer/`)
- **LocalRemediationEngine**: Playbook-based remediation execution
  - 3 modes: auto, semi_auto, manual
  - Risk-aware action gating (low/medium/high)
  - Concurrent action limiting
  - Rollback support

### 5. ML Models (`src/models/`)
- **MLAnomalyDetector**: Isolation Forest for unsupervised anomaly detection
- **MLFailurePredictor**: Random Forest Classifier for failure prediction
- **ForecastModel**: Polynomial trend forecasting with uncertainty bounds

### 6. API Layer (`src/api/`)
- RESTful endpoints for all system components
- Real-time metrics via WebSocket
- Fault injection controls

## Data Flow

1. Collector generates metrics every N seconds (configurable)
2. Detector analyzes metrics against historical baselines
3. Predictor forecasts future values and computes failure probabilities
4. Healer triggers remediation actions for detected anomalies and high-risk predictions
5. API exposes all data for dashboard and external integration

## Research Use Cases

- **Anomaly Detection**: Compare statistical vs ML-based detection
- **Failure Prediction**: Evaluate polynomial vs ensemble methods
- **Self-Healing**: Measure MTTR with auto vs manual remediation
- **Proactive Scaling**: Predict resource exhaustion before it happens

## Running

```bash
# Install
pip install -r requirements.txt

# API Server
uvicorn src.main:app --reload

# Dashboard (separate terminal)
streamlit run src/dashboard/app.py

# Simulation
python scripts/simulate.py [steps]

# Evaluation
python scripts/evaluate.py [runs] [steps_per_run]
```
