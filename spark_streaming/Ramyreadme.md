# Member 2: Stream Processing & Machine Learning
**Author:** Ramy Lazghab
**Role:** Stream Processing & ML Engineer  
**Branch:** `ramy-stream-processing`

---

## 🎯 Overview

I built a **real-time flight data processing pipeline** using Apache Spark Structured Streaming. The pipeline consumes flight tracking data from Member 1's Kafka producer, cleans and enriches it, applies machine learning-based anomaly detection, and produces aggregated insights for Member 3's dashboard.

---

## 📋 What I Built

### Task 2.1: Kafka Stream Integration
**Objective:** Connect Spark to Kafka and establish streaming pipeline

**Implementation:**
- Created Spark Structured Streaming application reading from `flight-raw-data` topic
- Parsed Member 1's flight JSON schema (17 fields including icao24, velocity, altitude, position)
- Established 4 output streams:
  - `flight-processed-data` - Event-level data with ML predictions
  - `flight-aggregated-data` - 10-minute windowed metrics per aircraft
  - `flight-invalid-spark` - Invalid/rejected records
  - Console output - Real-time monitoring

**Key Files:**
- `spark_streaming/config.py` - Configuration for Kafka, Spark, checkpointing
- `spark_streaming/stream_processor.py` - Main pipeline orchestration

---

### Task 2.2: Data Cleaning & Feature Engineering
**Objective:** Validate, clean, and enrich flight data

**Data Validation:**
- Coordinate bounds checking (latitude: -90 to 90, longitude: -180 to 180)
- Physical limits validation:
  - Altitude: -1000m to 50,000m
  - Velocity: 0 to 1000 m/s
  - Heading: 0 to 360 degrees
- Null value handling with safe defaults
- Deduplication on (icao24, time_position)

**Feature Engineering:**
I added 15+ derived features to enrich the raw flight data:

**Speed Conversions:**
- `velocity_kmh` - Velocity in km/h (velocity × 3.6)
- `velocity_knots` - Velocity in knots (velocity × 1.94384)
- `mach_number` - Speed relative to sound (for future use)

**Altitude Conversions:**
- `altitude_feet` - Altitude in feet (altitude × 3.28084)
- `flight_level` - FL designation (altitude_feet / 100)

**Flight Phase Detection:**
- `flight_phase` - Categorized as:
  - `ground` - on_ground = true
  - `takeoff_landing` - altitude < 1000m
  - `climbing` - vertical_rate > 5 m/s
  - `descending` - vertical_rate < -5 m/s
  - `cruise` - stable altitude

**Time Features:**
- `hour` - Hour of day (0-23)
- `day_of_week` - Day of week (1-7)
- `is_weekend` - Boolean weekend indicator
- `hour_sin`, `hour_cos` - Cyclic encoding of time
- `dow_sin`, `dow_cos` - Cyclic encoding of day

**Spatial Features:**
- `heading_sin`, `heading_cos` - Cyclic encoding of direction

**Why These Features?**
- Speed/altitude conversions: Make data interpretable for aviation domain
- Flight phase: Critical for understanding aircraft behavior
- Cyclic encoding: Prevents ML model from treating 23:59 and 00:01 as far apart
- Time features: Capture daily/weekly patterns in flight behavior

**Key Files:**
- `spark_streaming/transformations.py` - All cleaning and feature engineering logic

---

### Task 2.3: Machine Learning & Aggregations
**Objective:** Apply ML for anomaly detection and create time-windowed analytics

#### 🤖 ML Model: Isolation Forest

**Why Isolation Forest?**
I chose Isolation Forest because:
1. **Unsupervised:** No labeled anomaly data required
2. **Efficient:** Fast inference on streaming data
3. **Proven:** Industry standard for anomaly detection in time-series
4. **Explainable:** Provides anomaly scores (0-1) not just binary yes/no

**Model Training:**
- **Training Data:** 10,000 synthetic flight records
  - 99% normal flights (cruise ~250 m/s, altitude ~11,000m)
  - 1% anomalous flights (supersonic speeds, extreme altitudes, rapid descents)
- **Features Used (5):**
  1. `velocity` - Aircraft speed (m/s)
  2. `baro_altitude` - Barometric altitude (meters)
  3. `vertical_rate` - Climb/descent rate (m/s)
  4. `hour` - Time of day (0-23)
  5. `day_of_week` - Day of week (1-7)
- **Preprocessing:** StandardScaler normalization
- **Model Parameters:**
  - n_estimators: 200
  - contamination: 0.01 (1% expected anomalies)
  - random_state: 42

**Model Performance:**
- Test accuracy: 100% on synthetic data
- Anomaly detection rate: 1.0%
- Files saved:
  - `models/flight_anomaly_detector.pkl` (2.7 MB)
  - `models/flight_scaler.pkl`
  - `models/flight_features.json`

**ML Outputs Added to Each Flight Record:**
- `ml_anomaly_score` (0-1) - Higher = more anomalous
- `ml_is_anomaly` (boolean) - Binary classification
- `ml_anomaly_reason` (string) - Explanation:
  - `"normal"` - Expected flight behavior
  - `"extreme_speed"` - Velocity > 800 m/s
  - `"suspiciously_slow"` - Velocity < 50 m/s at altitude
  - `"extreme_altitude"` - Above 14,000m
  - `"dangerously_low"` - Below 500m while fast
  - `"extreme_climb_descent"` - |vertical_rate| > 20 m/s

**Implementation Details:**
- Used **Pandas UDFs** for vectorized ML inference (10-100x faster than row-by-row)
- Singleton pattern for model loading (load once per executor)
- Graceful fallback when model unavailable (safe defaults)
- Error handling in all UDF functions

#### 📊 Windowed Aggregations

**10-Minute Tumbling Windows Per Aircraft:**

I created time-based analytics grouping flights by aircraft (icao24) in 10-minute buckets:

**Velocity Metrics:**
- `avg_velocity`, `max_velocity`, `min_velocity`
- `velocity_variance` - Flight stability indicator
- `velocity_range` - Max - min speed in window

**Altitude Metrics:**
- `avg_altitude`, `max_altitude`, `min_altitude`
- `altitude_variance` - Altitude stability
- `altitude_change` - Total altitude gain/loss

**Flight Behavior:**
- `flight_events` - Number of data points in window
- `anomaly_count` - Total anomalies detected
- `anomaly_rate` - Percentage of anomalous records
- `flight_behavior` - Categorical classification:
  - `"stationary"` - On ground entire window
  - `"takeoff"` - Started on ground
  - `"landing"` - Ended on ground
  - `"stable_cruise"` - Low altitude variance (<100m)
  - `"maneuvering"` - Significant altitude changes

**Position Tracking:**
- `start_latitude`, `start_longitude` - Window entry point
- `end_latitude`, `end_longitude` - Window exit point
- Enables Member 3 to draw flight paths

**Why 10 Minutes?**
- Balances real-time responsiveness with statistical significance
- Typical commercial flight changes phases every 5-15 minutes
- Reduces data volume for dashboard (vs. second-by-second)

**Key Files:**
- `spark_streaming/ml_inference.py` - ML model loading and Pandas UDFs
- `spark_streaming/aggregations.py` - Windowing logic
- `models/train_model.py` - Model training script

---

## 🏗️ Architecture

```
Member 1's Kafka Producer
         ↓
    flight-raw-data topic
         ↓
┌────────────────────────────┐
│   stream_processor.py      │
│                            │
│  1. Parse JSON             │ ← Task 2.1
│  2. Clean & Validate       │ ← Task 2.2
│  3. Feature Engineering    │ ← Task 2.2
│  4. ML Anomaly Detection   │ ← Task 2.3
│  5. Windowed Aggregations  │ ← Task 2.3
└────────────────────────────┘
         ↓
    ┌────┴────┐
    ↓         ↓
flight-processed-data  flight-aggregated-data
    (events)              (10-min windows)
         ↓                      ↓
    Member 3's Dashboard
```

---

## 📦 Deliverables

### Folder Structure
```
data-streaming-flights/
├── spark_streaming/
│   ├── config.py              # Kafka/Spark configuration
│   ├── stream_processor.py    # Main pipeline (Tasks 2.1+2.2+2.3)
│   ├── transformations.py     # Data cleaning (Task 2.2)
│   ├── aggregations.py        # Windowing logic (Task 2.3)
│   ├── ml_inference.py        # ML predictions (Task 2.3)
│   ├── create_topics.py       # Kafka topic setup
│   ├── requirements.txt       # Python dependencies
│   └── __init__.py
├── models/
│   ├── train_model.py         # ML training script
│   ├── flight_anomaly_detector.pkl   # Trained model
│   ├── flight_scaler.pkl             # Feature scaler
│   └── flight_features.json          # Feature list
├── tests/
│   └── test_spark.py          # Unit tests
└── README_MEMBER2.md          # This file
```

### Output Schemas

#### Output 1: `flight-processed-data` (Event-Level)
Real-time flight records with ML predictions - **24 fields**

```json
{
  "icao24": "471f37",
  "callsign": "WZZ21GR",
  "origin_country": "Hungary",
  "event_time": "2026-02-20T22:54:06",
  "latitude": 47.5123,
  "longitude": 19.0456,
  "baro_altitude": 10980.42,
  "velocity": 236.29,
  "velocity_kmh": 850.64,
  "velocity_knots": 459.5,
  "altitude_feet": 36024.01,
  "flight_level": 360,
  "heading": 270.0,
  "vertical_rate": -0.5,
  "on_ground": false,
  "flight_phase": "cruise",
  "hour": 22,
  "day_of_week": 3,
  "is_weekend": false,
  "velocity_zscore": 0.0,
  "altitude_zscore": 0.0,
  "is_stat_anomaly": false,
  "ml_anomaly_score": 0.08,
  "ml_is_anomaly": false,
  "ml_anomaly_reason": "normal",
  "data_quality": "valid",
  "processing_timestamp": "2026-02-20T22:54:07Z"
}
```

#### Output 2: `flight-aggregated-data` (10-Min Windows)
Aircraft behavior analytics - **20 fields**

```json
{
  "window_start": "2026-02-20T22:50:00",
  "window_end": "2026-02-20T23:00:00",
  "icao24": "471f37",
  "callsign": "WZZ21GR",
  "origin_country": "Hungary",
  "flight_events": 42,
  "avg_velocity": 236.5,
  "max_velocity": 240.2,
  "min_velocity": 232.1,
  "velocity_variance": 2.3,
  "velocity_range": 8.1,
  "avg_altitude": 10975.0,
  "max_altitude": 10985.0,
  "min_altitude": 10965.0,
  "altitude_variance": 8.5,
  "altitude_change": 20.0,
  "avg_vertical_rate": -0.3,
  "anomaly_count": 0,
  "anomaly_rate": 0.0,
  "flight_behavior": "stable_cruise",
  "start_latitude": 47.51,
  "start_longitude": 19.04,
  "end_latitude": 47.89,
  "end_longitude": 19.23
}
```

---

## 🚀 How to Run

### Prerequisites
- Docker with Kafka + Zookeeper running (Member 1's setup)
- Python 3.8+
- Apache Spark 3.5.0

### Setup

```bash
# 1. Install dependencies (inside Spark Docker container)
docker exec -it spark_flights bash
cd /opt/spark-apps/spark_streaming
pip3 install -r requirements.txt

# 2. Create Kafka output topics (via Docker)
# Exit container first
exit

# In PowerShell
docker exec -it kafka_flights kafka-topics --create --topic flight-processed-data --partitions 3 --replication-factor 1 --bootstrap-server localhost:9092
docker exec -it kafka_flights kafka-topics --create --topic flight-aggregated-data --partitions 3 --replication-factor 1 --bootstrap-server localhost:9092
docker exec -it kafka_flights kafka-topics --create --topic flight-invalid-spark --partitions 1 --replication-factor 1 --bootstrap-server localhost:9092

# 3. Train ML model (inside container)
docker exec -it spark_flights bash
cd /opt/spark-apps/models
python3 train_model.py

# 4. Run pipeline (inside container)
cd /opt/spark-apps
python3 stream_processor.py
```

### Verify Output

```bash
# Check processed flights
docker exec -it kafka_flights kafka-console-consumer \
  --topic flight-processed-data \
  --from-beginning \
  --bootstrap-server localhost:9092 \
  --max-messages 5

# Check aggregated windows
docker exec -it kafka_flights kafka-console-consumer \
  --topic flight-aggregated-data \
  --from-beginning \
  --bootstrap-server localhost:9092 \
  --max-messages 5
```

---

## 🎯 Key Design Decisions

### 1. **Why Run in Docker?**
- **Problem:** Windows PySpark path issues
- **Solution:** Run entire pipeline inside Spark Docker container
- **Benefit:** Consistent environment, no Windows-specific bugs

### 2. **Why Simplified Z-Score?**
- **Challenge:** Spark Streaming doesn't support row-based windows (`.rowsBetween()`)
- **Solution:** Used placeholder z-score columns, relied on ML model
- **Alternative Considered:** Time-windowed statistics (complex, marginal benefit)

### 3. **Why Disable Trend Calculation?**
- **Challenge:** `lag()` function not supported in streaming aggregations
- **Solution:** Removed trend_summary, added placeholder
- **Trade-off:** Lost window-to-window comparison, kept core metrics

### 4. **Why Pandas UDFs?**
- **Alternative:** Regular Python UDFs (row-by-row)
- **Chosen:** Pandas UDFs (vectorized batches)
- **Benefit:** 10-100x faster ML inference

### 5. **Why Absolute Paths for Models?**
- **Problem:** Relative paths failed in Docker
- **Solution:** Hardcoded `/opt/spark-apps/models/`
- **Trade-off:** Less portable, but works reliably

---

## 📊 Pipeline Performance

**Observed Metrics:**
- **Throughput:** 2,000-3,000 flight records per batch
- **Batch Interval:** 10 seconds (configured)
- **Actual Processing:** 12-20 seconds per batch (falling behind due to ML inference)
- **Batches Processed:** 1,279+ batches successfully
- **Uptime:** Stable for 2+ hours continuous operation

**Performance Bottlenecks:**
- ML inference (Pandas UDF) takes 8-10 seconds per batch
- Window aggregations add 2-4 seconds
- **Recommendation:** For production, use stronger hardware or reduce batch frequency

---

## 🔄 Handoff to Member 3

### What Member 3 Gets

**Two Kafka Topics with Rich Data:**

1. **`flight-processed-data`** - Real-time events
   - Use for: Live flight map, alerts, current status
   - Update frequency: Every 10 seconds
   - Contains: ML scores, flight phase, enriched metrics

2. **`flight-aggregated-data`** - 10-min summaries
   - Use for: Trend charts, aircraft performance, historical analysis
   - Update frequency: Every 10 minutes per aircraft
   - Contains: Average speeds, altitude changes, anomaly rates

**Dashboard Suggestions:**

**Map View:**
- Plot `latitude`, `longitude` from processed-data
- Color by `flight_phase` or `ml_anomaly_score`
- Size by `altitude_feet`

**Anomaly Alerts:**
- Filter `ml_is_anomaly = true`
- Display `ml_anomaly_reason`
- Show `icao24`, `callsign` for identification

**Aircraft Performance:**
- Use aggregated-data
- Chart `avg_velocity` over time per aircraft
- Show `flight_behavior` distribution

**Gauges:**
- `ml_anomaly_score` (0-1) → perfect for gauge visualization
- `anomaly_rate` (%) → percentage indicator

---

## 🧪 Testing

```bash
# Run unit tests
cd tests
pytest test_spark.py -v
```

**Test Coverage:**
- Data cleaning validation
- Feature engineering correctness
- Z-score column addition
- Valid/invalid data separation

---

## 📝 Dependencies

```
pyspark==3.5.0
kafka-python==2.0.2
scikit-learn==1.4.0
pandas==2.2.0
numpy==1.26.3
joblib==1.3.2
pyarrow==15.0.0
six==1.16.0
python-dotenv==1.0.0
pytest==8.0.0
```

---

## 🐛 Known Issues & Limitations

1. **Z-Score Detection:** Placeholder only (Spark Streaming limitation)
2. **Trend Calculation:** Disabled (lag() not supported in streaming)
3. **Processing Speed:** Falls behind during high traffic (ML inference bottleneck)
4. **Model Path:** Hardcoded for Docker environment
5. **No Backpressure:** Pipeline processes all incoming data regardless of speed

---

## 🎓 What I Learned

1. **Spark Structured Streaming** has limitations vs batch processing
2. **Pandas UDFs** are essential for performant ML in Spark
3. **Feature engineering** is critical for ML model performance
4. **Docker** solves Windows environment issues elegantly
5. **Isolation Forest** is powerful for unsupervised anomaly detection

---

## 🙏 Acknowledgments

- **Member 1 (Yassine):** Excellent Kafka producer with clean schema
- **OpenSky Network:** Real-time flight data API
- **Apache Spark:** Robust streaming framework
- **scikit-learn:** Reliable ML library

---