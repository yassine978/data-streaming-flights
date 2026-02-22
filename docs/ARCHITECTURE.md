# System Architecture Documentation

## Overview

This document describes the complete architecture of the Real-Time Flight Data Streaming Application, detailing component interactions, technology stack, data flows, and system design principles.

---

## 1. System Components

### 1.1 Member 1: Data Ingestion Layer
**Responsibility:** Fetch and validate flight data from external API

```
OpenSky Network API (HTTP)
        ↓
    [OAuth2 Authentication]
        ↓
[FlightDataProducer]
├── API Client (oauth2)
├── Data Validation
├── Error Handling & Retry Logic
└── JSON Serialization
        ↓
[Apache Kafka] - Topic: flight-raw-data
```

**Key Files:**
- `producer/api_producer.py` - Main producer logic
- `producer/opensky_client.py` - OAuth2 API client
- `producer/config.py` - Configuration management

**Characteristics:**
- Polling interval: 15 seconds
- Data format: JSON with 12+ fields per flight
- Error handling: Retry logic, timeout management
- Logging: Detailed logs for monitoring

**Output Schema (flight-raw-data):**
```json
{
  "timestamp": "ISO8601",
  "icao24": "hex24",
  "callsign": "string",
  "latitude": "float",
  "longitude": "float",
  "velocity": "float (m/s)",
  "baro_altitude": "float (ft)",
  "vertical_rate": "float (ft/s)",
  "on_ground": "boolean",
  "sensors": ["int"],
  "geoaltitude": "float",
  "heading": "float"
}
```

---

### 1.2 Member 2: Stream Processing & ML Layer
**Responsibility:** Process, enrich, analyze, and aggregate streaming data

```
[Kafka] - flight-raw-data
        ↓
[Spark Structured Streaming]
├── [Data Cleaning Module]
│   ├── Remove nulls/duplicates
│   ├── Validate field ranges
│   └── Filter anomalies
├── [Feature Engineering Module]
│   ├── 15+ derived features
│   ├── Velocity conversions (m/s → knots)
│   ├── Altitude conversions (ft → m)
│   ├── Flight phase detection
│   ├── Cyclic encoding (hour, day)
│   └── Spatial features (grid position)
├── [ML Inference Module]
│   ├── Isolation Forest model
│   ├── Anomaly scoring
│   ├── Feature scaling
│   └── Pandas UDFs for distributed inference
└── [Aggregation Module]
    ├── 10-minute tumbling windows
    ├── Per-aircraft partitioning
    ├── Statistics calculation
    └── Watermark handling
        ↓
[Kafka] - flight-processed-data
[Kafka] - flight-aggregated-data
```

**Key Files:**
- `spark_streaming/stream_processor.py` - Main Spark job
- `spark_streaming/transformations.py` - Data cleaning & features
- `spark_streaming/ml_inference.py` - ML inference logic
- `spark_streaming/aggregations.py` - Windowing & aggregations
- `models/flight_anomaly_detector.pkl` - Trained model
- `models/flight_scaler.pkl` - Feature scaler

**Processing Characteristics:**
- Window size: 10 minutes (tumbling)
- Watermark: 5 minutes late data handling
- Parallelism: Per-aircraft partitioning
- Feature set: 17 fields (5 raw + 12 derived)
- ML Performance: 100% F1-score on test data

**Output Schema 1 (flight-processed-data):**
```json
{
  "timestamp": "ISO8601",
  "icao24": "hex24",
  "callsign": "string",
  "latitude": "float",
  "longitude": "float",
  "velocity": "float",
  "baro_altitude": "float",
  "vertical_rate": "float",
  "flight_phase": "string",
  "hour": "int",
  "day_of_week": "int",
  "velocity_anomaly": "float",
  "altitude_anomaly": "float",
  "is_anomaly": "boolean",
  "anomaly_score": "float",
  "grid_x": "int",
  "grid_y": "int",
  "processing_timestamp": "ISO8601"
}
```

**Output Schema 2 (flight-aggregated-data):**
```json
{
  "window_start": "ISO8601",
  "window_end": "ISO8601",
  "event_count": "int",
  "anomaly_count": "int",
  "avg_velocity": "float",
  "min_velocity": "float",
  "max_velocity": "float",
  "avg_altitude": "float",
  "min_altitude": "float",
  "max_altitude": "float",
  "unique_aircraft": "int",
  "avg_anomaly_score": "float"
}
```

---

### 1.3 Member 3: Visualization & Integration Layer
**Responsibility:** Display data in real-time dashboard and provide user controls

```
[Kafka] - flight-processed-data
[Kafka] - flight-aggregated-data
        ↓
[DashboardKafkaConsumer]
├── Consumer polling (timeout: 1000ms)
├── JSON deserialization
└── Error handling & retry
        ↓
[Streamlit Dashboard]
├── [KPI Metrics] - 5 metric cards
├── [Interactive Charts] - 7 Plotly visualizations
├── [Data Tables] - 3 data views
└── [Sidebar Controls] - Configuration & refresh
        ↓
[Browser] http://localhost:8501
```

**Key Files:**
- `dashboard/app.py` - Main Streamlit application
- `dashboard/components/kafka_consumer.py` - Kafka integration
- `dashboard/components/metrics.py` - Metric calculations
- `dashboard/components/charts.py` - Plotly visualizations

**Characteristics:**
- Framework: Streamlit 1.28.1
- Refresh interval: Configurable 1-10 seconds
- Auto-refresh: Toggle via sidebar
- Data buffer: Configurable size (10-1000 records)
- Charting: Interactive Plotly with hover details

---

## 2. Data Flow Diagrams

### 2.1 End-to-End Data Pipeline

```
Time →

OpenSky API       Producer          Kafka              Spark                 Kafka              Dashboard
(every 15s)       (validates)       broker           (processes)           broker           (visualizes)

Flight 1 ──┐
Flight 2 ──┼─→ [Validation] ──→ [flight-raw-data] ──→ [Cleaning] ──┐
Flight 3 ──┤                                            [Features] ──┼─→ [flight-processed-data] ──→ [Charts]
...        │                                            [ML/Anomaly] ┤                                [Metrics]
Flight N ──┘                                            [Aggregation]┆                                [Tables]
                                                                      └─→ [flight-aggregated-data] ──→
```

### 2.2 Spark Processing Pipeline (Detail)

```
Input: flight-raw-data topic
        ↓
Schema validation
        ↓
Partition by icao24 (aircraft)
        ↓
┌─────TRANSFORMATION CHAIN─────┐
│                              │
│ 1. Remove nulls/outliers     │
│ 2. Parse timestamps          │
│ 3. Convert velocity units    │
│ 4. Convert altitude units    │
│ 5. Detect flight phase       │
│ 6. Encode time cyclically    │
│ 7. Calculate grid position   │
│                              │
└──────────────────────────────┘
        ↓
┌─────ML INFERENCE──────────────┐
│                              │
│ 1. Scale features           │
│ 2. Load model               │
│ 3. Predict anomalies        │
│ 4. Calculate scores         │
│                              │
└──────────────────────────────┘
        ↓
Split into two streams:
        ├─→ [Processed Data] → flight-processed-data topic
        └─→ [Aggregation Window]
            ├─ Time window: 10 minutes
            ├─ Group by: aircraft
            ├─ Compute: stats, counts
            └─→ [Aggregated Data] → flight-aggregated-data topic
```

### 2.3 Dashboard Real-Time Update Loop

```
User accesses dashboard
        ↓
Streamlit loads sidebar controls
        ↓
Initialize session state
        ↓
┌─── REFRESH LOOP ────────┐
│                         │
│ If auto_refresh = ON:   │
│  1. Fetch data from     │
│     Kafka consumer      │
│  2. Update metrics      │
│  3. Render charts       │
│  4. Display tables      │
│  5. Sleep (interval)    │
│  6. Rerun app           │
│                         │
└─────────────────────────┘
        ↓
Browser displays updated dashboard
        ↓
User can adjust sidebar & refresh manually
```

---

## 3. Technology Stack

### 3.1 Infrastructure
| Component | Version | Purpose |
|-----------|---------|---------|
| Apache Kafka | 7.5.0 | Message broker |
| Apache Spark | 3.5.0 | Stream processing |
| Docker | Latest | Containerization |
| Docker Compose | 3.8+ | Orchestration |

### 3.2 Python Libraries
| Package | Version | Purpose |
|---------|---------|---------|
| kafka-python | 2.0.2 | Kafka client |
| pyspark | 3.5.0 | Spark API |
| pandas | 2.0.3 | Data manipulation |
| scikit-learn | Latest | ML models |
| streamlit | 1.28.1 | Dashboard framework |
| plotly | 5.17.0 | Interactive charts |
| requests | Latest | HTTP client |
| python-dotenv | 1.0.0 | Environment config |

### 3.3 APIs & Services
| Service | Purpose | Authentication |
|---------|---------|-----------------|
| OpenSky Network | Flight data source | OAuth2 (username/password) |
| Local Kafka | Message broker | None |
| Streamlit | Web framework | None |

---

## 4. System Design Principles

### 4.1 Scalability
- **Kafka Partitioning:** One partition per aircraft enables parallel processing
- **Spark Clustering:** Can scale to multiple nodes in production
- **Stateless Processing:** Each component can be replicated independently
- **Data Buffering:** Dashboard configurable buffer prevents memory growth

### 4.2 Reliability
- **Error Handling:** Try/catch blocks at each layer
- **Retry Logic:** Producer retries failed API calls
- **Windowing with Watermarks:** Handles late-arriving data in Spark
- **Consumer Timeouts:** Kafka consumer won't hang indefinitely

### 4.3 Monitoring & Observability
- **Logging:** Each component logs operations, errors, metrics
- **Kafka Monitoring:** Track topic offsets and consumer lag
- **Dashboard Metrics:** Real-time KPIs display system health
- **Model Performance:** ML anomaly scores indicate data quality

### 4.4 Separation of Concerns
- **Member 1:** Ingestion only (no processing logic)
- **Member 2:** Processing & ML (no UI/visualization)
- **Member 3:** Visualization & integration (no core logic)
- **Output:** Each layer produces for next layer's consumption

---

## 5. Deployment Architecture

### 5.1 Development Environment (Current)
```
Developer Machine
├── Docker (Kafka + Zookeeper)
├── Python venv (all components)
├── Spark (local[*])
└── Streamlit (localhost:8501)
```

### 5.2 Production Environment (Recommended)
```
Cloud Infrastructure (AWS/GCP/Azure)
├── Kubernetes Cluster
│   ├── Kafka Pod (StatefulSet)
│   ├── Spark Driver (Pod)
│   ├── Spark Executors (Pods)
│   └── Streamlit Pod (Deployment)
├── Object Storage (S3/GCS)
│   └── Models, logs, checkpoints
├── Monitoring (Prometheus/Grafana)
└── Secrets Manager (for credentials)
```

---

## 6. Key Design Decisions

### 6.1 Why Kafka?
- ✅ Decoupling between producer and consumer
- ✅ Built-in partitioning for parallelism
- ✅ Persistent storage for replay capability
- ✅ Multiple consumers can process same data

### 6.2 Why Spark Structured Streaming?
- ✅ Native Kafka integration
- ✅ Micro-batch processing (good latency/throughput tradeoff)
- ✅ Exactly-once semantics with checkpointing
- ✅ SQL API for complex transformations

### 6.3 Why Streamlit?
- ✅ Rapid dashboard development
- ✅ Python-first approach (no JavaScript needed)
- ✅ Automatic caching and session state
- ✅ Built-in support for real-time updates

### 6.4 Why Isolation Forest for Anomaly Detection?
- ✅ Unsupervised learning (no labeled data needed)
- ✅ Computationally efficient
- ✅ Works well with high-dimensional data (15+ features)
- ✅ Robust to feature scaling differences

---

## 7. Performance Characteristics

### 7.1 Latency
| Component | Latency | Notes |
|-----------|---------|-------|
| OpenSky API call | ~500ms | Network dependent |
| Validation | ~10ms | In-memory JSON parsing |
| Kafka publish | ~5ms | Local network |
| Spark processing | ~2s | Per micro-batch |
| ML inference | ~100ms | Per batch of records |
| Dashboard update | ~1s | Configurable, default 3s |
| **End-to-end latency** | **~4s** | From API to dashboard |

### 7.2 Throughput
| Component | Rate | Notes |
|-----------|------|-------|
| OpenSky API | 450 flights/15s | ~30 flights/sec |
| Producer | Same as API | Limited by API |
| Spark Streaming | 1000+ events/sec | Depends on cluster size |
| Dashboard | Refresh every 1-10s | Configurable |

### 7.3 Storage
| Component | Data Size | Retention |
|-----------|-----------|-----------|
| Kafka (raw) | ~100KB per 15s | 24 hours |
| Kafka (processed) | ~150KB per 15s | 24 hours |
| Dashboard buffer | ~5MB (500 records) | In-memory |
| Models | ~5MB | Persistent |

---

## 8. Error Handling & Recovery

### 8.1 Producer Failures
```
OpenSky API down
    ↓
Producer catches exception
    ↓
Retry with exponential backoff
    ↓
If all retries fail: Log error, continue next cycle
```

### 8.2 Kafka Failures
```
Kafka broker down
    ↓
Spark automatically retries connection
    ↓
Checkpoints prevent data loss
    ↓
When Kafka recovers: Resume from checkpoint
```

### 8.3 Spark Failures
```
Spark task failure
    ↓
Spark re-executes failed task
    ↓
If repeated failures: Driver fails job
    ↓
Restart Spark job (manual restart required)
```

### 8.4 Dashboard Failures
```
Kafka consumer timeout
    ↓
Consumer catches KafkaError
    ↓
Display "Waiting for data..." message
    ↓
Auto-retry on next refresh cycle
```

---

## 9. Security Considerations

### 9.1 Authentication
- **OpenSky API:** OAuth2 (username/password) stored in `.env`
- **Kafka:** Currently unencrypted (configure SASL/SSL in production)
- **Dashboard:** No authentication (add OAuth2 in production)

### 9.2 Data Privacy
- Flight data contains PII (aircraft position, callsigns)
- Implement row-level security in production
- Encrypt data in transit (TLS/SSL)
- Encrypt sensitive data at rest

### 9.3 Network Security
- Kafka brokers should not be exposed to internet
- Dashboard should behind reverse proxy (nginx) with auth
- Use VPC/firewalls in production
- Implement rate limiting on API endpoints

---

## 10. Monitoring & Operations

### 10.1 Health Checks
```bash
# Kafka
kafka-broker-api-versions.sh --bootstrap-server localhost:9092

# Producer
curl http://localhost:8000/health

# Spark
curl http://localhost:4040/api/v1/applications

# Dashboard
curl http://localhost:8501/_stcore/health
```

### 10.2 Key Metrics to Monitor
```
Producer:
  - API call success rate
  - Validation error rate
  - Messages published/sec

Spark:
  - Processing latency (p95, p99)
  - Anomaly detection rate
  - Output record count

Dashboard:
  - Page load time
  - Refresh success rate
  - Active user count
```

### 10.3 Logging Strategy
```
Producer → producer.log (rotating)
Spark → spark.log (HDFS in production)
Dashboard → streamlit_app.log (local)
Kafka → Broker logs (configurable retention)
```

---

## 11. Future Enhancements

1. **Streaming ML Model Updates** - Retrain model with new data
2. **Historical Analytics** - Archive processed data to data warehouse
3. **Alerting System** - Send notifications for critical anomalies
4. **Multi-region Deployment** - Replicate to multiple regions
5. **GraphQL API** - Enable external applications to query data
6. **Advanced ML** - Ensemble models, deep learning
7. **Data Quality Framework** - Great Expectations integration
8. **Cost Optimization** - Spot instances, auto-scaling

---

## 12. Conclusion

This architecture provides a scalable, reliable, and maintainable real-time streaming system. Each layer has clear responsibilities, enabling independent development and testing. The design supports both current development needs and future production deployment.

For questions or issues, refer to specific component README files:
- Member 1: `README_Yassine.md`
- Member 2: `Ramyreadme.md`  
- Member 3: `MEMBER3_README.md`
