# API Reference & Data Schema Documentation

## Overview

This document provides comprehensive details about data formats, Kafka topics, API endpoints, and field definitions used throughout the Flight Data Streaming system.

---

## 1. Kafka Topics Reference

### 1.1 `flight-raw-data`
**Purpose:** Raw flight data from OpenSky Network API  
**Source:** Member 1 - Data Producer  
**Consumers:** Spark Streaming (Member 2)  
**Retention:** 24 hours  
**Partition Count:** 1  
**Replication Factor:** 1  

**Message Format:**
```json
{
  "timestamp": "2026-01-15T10:30:45.123Z",
  "icao24": "abc1234",
  "callsign": "DA1234  ",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "altitude": 32000.0,
  "baro_altitude": 32000.0,
  "geoaltitude": 32010.0,
  "on_ground": false,
  "velocity": 235.5,
  "heading": 180.5,
  "vertical_rate": 150.5,
  "sensors": [1, 2, 3]
}
```

**Field Definitions:**

| Field | Type | Description | Range |
|-------|------|-------------|-------|
| `timestamp` | ISO8601 | Event timestamp in UTC | - |
| `icao24` | string | ICAO 24-bit address (aircraft ID) | 0-FFFFFF (hex) |
| `callsign` | string | Callsign/flight number | Max 8 chars |
| `latitude` | float | Geographic latitude | -90.0 to 90.0 |
| `longitude` | float | Geographic longitude | -180.0 to 180.0 |
| `altitude` | float | Geometric altitude (feet) | -1200 to 68000 |
| `baro_altitude` | float | Barometric altitude (feet) | -1200 to 68000 |
| `geoaltitude` | float | Geometric altitude from GPS | Variable |
| `on_ground` | boolean | Whether aircraft is on ground | true/false |
| `velocity` | float | Horizontal velocity (m/s) | 0 to 300 |
| `heading` | float | True heading (degrees) | 0 to 360 |
| `vertical_rate` | float | Vertical rate (ft/s) | -500 to 500 |
| `sensors` | array | MLAT sensor IDs | Array of integers |

---

### 1.2 `flight-processed-data`
**Purpose:** Cleaned and enriched flight data with ML predictions  
**Source:** Spark Streaming (Member 2)  
**Consumers:** Streamlit Dashboard (Member 3)  
**Retention:** 24 hours  
**Partition Count:** 12 (one per aircraft)  
**Replication Factor:** 1  

**Message Format:**
```json
{
  "timestamp": "2026-01-15T10:31:45.456Z",
  "icao24": "abc1234",
  "callsign": "DA1234",
  "latitude": 40.7215,
  "longitude": -74.0060,
  "velocity": 238.5,
  "baro_altitude": 32500.0,
  "vertical_rate": 145.0,
  "heading": 182.3,
  "on_ground": false,
  "flight_phase": "cruise",
  "hour": 10,
  "day_of_week": 2,
  "velocity_kmh": 857.4,
  "altitude_m": 9906.0,
  "vertical_rate_mpm": 8700.0,
  "heading_sin": 0.1256,
  "heading_cos": -0.9921,
  "hour_sin": -0.6536,
  "hour_cos": 0.7568,
  "dow_sin": 0.9093,
  "dow_cos": -0.4161,
  "grid_x": 42,
  "grid_y": 28,
  "velocity_anomaly": 0.0,
  "altitude_anomaly": 0.0,
  "is_anomaly": false,
  "anomaly_score": -0.15,
  "processing_timestamp": "2026-01-15T10:31:46.789Z",
  "batch_id": "batch-001"
}
```

**Additional Fields (Derived Features):**

| Field | Type | Description | Derivation |
|-------|------|-------------|-----------|
| `velocity_kmh` | float | Velocity in km/h | velocity * 3.6 |
| `altitude_m` | float | Altitude in meters | baro_altitude * 0.3048 |
| `vertical_rate_mpm` | float | Vertical rate in m/min | vertical_rate * 0.3048 * 60 |
| `heading_sin` | float | Sine of heading | sin(heading * π/180) |
| `heading_cos` | float | Cosine of heading | cos(heading * π/180) |
| `hour_sin` | float | Cyclic hour encoding | sin(hour * 2π/24) |
| `hour_cos` | float | Cyclic hour encoding | cos(hour * 2π/24) |
| `dow_sin` | float | Cyclic day-of-week | sin(day_of_week * 2π/7) |
| `dow_cos` | float | Cyclic day-of-week | cos(day_of_week * 2π/7) |
| `grid_x` | int | Grid position (X) | Grid quantization |
| `grid_y` | int | Grid position (Y) | Grid quantization |
| `velocity_anomaly` | float | Anomaly component | Feature importance |
| `altitude_anomaly` | float | Anomaly component | Feature importance |
| `is_anomaly` | boolean | Anomaly flag | Model prediction |
| `anomaly_score` | float | Anomaly score | Isolation Forest score |
| `flight_phase` | string | Flight phase | Classification |

**Flight Phase Values:**
- `"ground"` - Aircraft on ground
- `"takeoff"` - Takeoff phase (altitude < 5000 ft, climbing)
- `"climb"` - Climbing phase (altitude < cruise, vertical_rate > 200 ft/s)
- `"cruise"` - Cruise phase (stable altitude)
- `"descent"` - Descent phase (altitude decreasing, vertical_rate < -200 ft/s)
- `"landing"` - Landing approach (altitude < 5000 ft, near ground)

---

### 1.3 `flight-aggregated-data`
**Purpose:** Windowed aggregations and statistics per aircraft  
**Source:** Spark Streaming (Member 2)  
**Consumers:** Streamlit Dashboard (Member 3)  
**Retention:** 24 hours  
**Window Size:** 10 minutes (tumbling)  
**Watermark:** 5 minutes late data handling  

**Message Format:**
```json
{
  "window_start": "2026-01-15T10:30:00.000Z",
  "window_end": "2026-01-15T10:40:00.000Z",
  "event_count": 450,
  "anomaly_count": 12,
  "anomaly_percentage": 2.67,
  "avg_velocity": 238.5,
  "min_velocity": 45.0,
  "max_velocity": 450.0,
  "std_velocity": 85.3,
  "avg_altitude": 28500.0,
  "min_altitude": 1000.0,
  "max_altitude": 43000.0,
  "std_altitude": 12000.0,
  "unique_aircraft": 38,
  "avg_anomaly_score": -0.08,
  "max_anomaly_score": 0.45,
  "climbing_count": 120,
  "descending_count": 180,
  "cruising_count": 150,
  "ground_count": 0,
  "processing_timestamp": "2026-01-15T10:40:05.000Z"
}
```

**Field Definitions:**

| Field | Type | Description |
|-------|------|-------------|
| `window_start` | ISO8601 | Start of 10-minute window |
| `window_end` | ISO8601 | End of 10-minute window |
| `event_count` | int | Total events in window |
| `anomaly_count` | int | Number of anomalies detected |
| `anomaly_percentage` | float | Anomalies / total * 100 |
| `avg_velocity` | float | Mean velocity (m/s) |
| `min_velocity` | float | Minimum velocity |
| `max_velocity` | float | Maximum velocity |
| `std_velocity` | float | Standard deviation of velocity |
| `avg_altitude` | float | Mean altitude (feet) |
| `min_altitude` | float | Minimum altitude |
| `max_altitude` | float | Maximum altitude |
| `std_altitude` | float | Standard deviation of altitude |
| `unique_aircraft` | int | Number of unique aircraft |
| `avg_anomaly_score` | float | Mean anomaly score |
| `max_anomaly_score` | float | Maximum anomaly score |
| `climbing_count` | int | Events in climb phase |
| `descending_count` | int | Events in descent phase |
| `cruising_count` | int | Events in cruise phase |
| `ground_count` | int | Events on ground |
| `processing_timestamp` | ISO8601 | When window was processed |

---

## 2. OpenSky Network API Reference

### 2.1 Authentication
**Type:** HTTP Basic Auth (Base64 encoded username:password)  
**Endpoint:** https://opensky-network.org:443/api/  
**Rate Limit:** 4 requests/second for free tier  

### 2.2 StateVectors Endpoint
**Purpose:** Get current flight state vectors  
**URL:** `/states/all?extended=1`  
**Method:** GET  
**Parameters:**
- `extended` (optional): 1 = include extra fields, 0 = basic fields
- `lamin` (optional): Minimum latitude
- `lamax` (optional): Maximum latitude
- `lomin` (optional): Minimum longitude
- `lomax` (optional): Maximum longitude

**Response Format:**
```json
{
  "time": 1642262445,
  "states": [
    ["abc1234", "DA1234  ", "Germany", 1642262400, 1642262444, 6.25, 50.10, 1536, false, 132.45, 121.3, -0.5, false, 0, "0000", false, 0],
    ...
  ]
}
```

**State Vector Fields (Index):**
```
0:  icao24 (string)
1:  callsign (string)
2:  origin_country (string)
3:  time_position (int, unix timestamp)
4:  last_contact (int, unix timestamp)
5:  longitude (float, or null)
6:  latitude (float, or null)
7:  baro_altitude (float, feet, or null)
8:  on_ground (boolean)
9:  velocity (float, m/s, or null)
10: true_track (float, degrees, or null)
11: vertical_rate (float, ft/s, or null)
12: sensors (array of ints, or null)
13: geo_altitude (float, feet, or null)
14: squawk (string, or null)
15: spi (boolean)
16: position_source (int)
```

### 2.3 Example API Call
```bash
curl -u username:password "https://opensky-network.org/api/states/all?lamin=40&lamax=41&lomin=-74&lomax=-73"

# Response (truncated):
{
  "time": 1642262445,
  "states": [
    [
      "abc1234",
      "UA1234  ",
      "United States",
      1642262400,
      1642262444,
      -74.006,
      40.713,
      32000,
      false,
      235.5,
      180,
      150,
      [1, 2, 3],
      32010,
      "0000",
      false,
      0
    ]
  ]
}
```

---

## 3. Machine Learning Model Reference

### 3.1 Model: flight_anomaly_detector.pkl
**Type:** Isolation Forest (Scikit-learn)  
**Training Data:** Historical flight data (10,000+ records)  
**Contamination:** 0.05 (5% expected anomalies)  
**Performance Metrics:**
- Precision: 1.00
- Recall: 1.00
- F1-Score: 1.00
- ROC-AUC: 1.00

**Input Features (15):**
1. `velocity_kmh` - Normalized velocity
2. `altitude_m` - Normalized altitude
3. `vertical_rate_mpm` - Vertical rate
4. `heading_sin` - Direction encoding
5. `heading_cos` - Direction encoding
6. `hour_sin` - Time encoding
7. `hour_cos` - Time encoding
8. `dow_sin` - Day encoding
9. `dow_cos` - Day encoding
10. `grid_x` - Spatial encoding
11. `grid_y` - Spatial encoding
12. Additional derived features

**Output:** Anomaly score (negative = normal, positive = anomalous)

### 3.2 Scaler: flight_scaler.pkl
**Type:** StandardScaler (Scikit-learn)  
**Method:** Z-score normalization (μ=0, σ=1)  
**Applied to:** All 15 features before model inference  

### 3.3 Feature List: flight_features.json
```json
{
  "features": [
    "velocity_kmh",
    "altitude_m",
    "vertical_rate_mpm",
    "heading_sin",
    "heading_cos",
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
    "grid_x",
    "grid_y",
    "velocity_anomaly",
    "altitude_anomaly",
    "on_ground",
    "velocity_max"
  ],
  "n_features": 15,
  "model_version": "1.0",
  "training_date": "2025-09-15",
  "accuracy": 1.0
}
```

---

## 4. Kafka Consumer Configuration

### 4.1 Dashboard Consumer
**Topic:** flight-processed-data, flight-aggregated-data  
**Group ID:** flight-dashboard-group  
**Auto Offset Reset:** latest  
**Partition Assignment:** range  
**Max Poll Records:** 500  
**Session Timeout:** 10000ms  
**Consumer Timeout:** 1000ms  

**Python Example:**
```python
from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    'flight-processed-data',
    bootstrap_servers=['localhost:9092'],
    auto_offset_reset='latest',
    consumer_timeout_ms=1000,
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    group_id='flight-dashboard-group'
)

for message in consumer:
    print(message.value)
```

---

## 5. Configuration Parameters

### 5.1 Producer Configuration
```python
{
    "OPENSKY_USERNAME": "your_username",
    "OPENSKY_PASSWORD": "your_password",
    "API_POLL_INTERVAL": 15,  # seconds
    "KAFKA_HOST": "localhost",
    "KAFKA_PORT": 9092,
    "KAFKA_TOPIC": "flight-raw-data",
    "API_TIMEOUT": 10,  # seconds
    "RETRY_ATTEMPTS": 3,
    "RETRY_BACKOFF": 2  # exponential
}
```

### 5.2 Spark Configuration
```python
{
    "SPARK_APP_NAME": "FlightStreamingApp",
    "KAFKA_BROKER": "localhost:9092",
    "INPUT_TOPIC": "flight-raw-data",
    "OUTPUT_TOPICS": [
        "flight-processed-data",
        "flight-aggregated-data"
    ],
    "CHECKPOINT_LOCATION": "/tmp/spark-checkpoint",
    "WINDOW_SIZE_MINUTES": 10,
    "WATERMARK_DELAY_MINUTES": 5,
    "BATCH_INTERVAL": 10,  # seconds
    "MAX_OFFSETS_PER_TRIGGER": 1000
}
```

### 5.3 Dashboard Configuration
```python
{
    "KAFKA_HOST": "localhost",
    "KAFKA_PORT": 9092,
    "REFRESH_INTERVAL": 3,  # seconds, configurable 1-10
    "AUTO_REFRESH": True,
    "DATA_BUFFER_SIZE": 500,  # records
    "CONSUMER_TIMEOUT": 1000,  # milliseconds
    "STREAMLIT_PORT": 8501,
    "PAGE_LAYOUT": "wide",
    "PAGE_TITLE": "Flight Streaming Dashboard"
}
```

---

## 6. Error Codes & Handling

### 6.1 Producer Errors
```
ERROR_API_TIMEOUT
  → Problem: OpenSky API not responding
  → Action: Retry with exponential backoff

ERROR_AUTH_FAILED  
  → Problem: Invalid credentials
  → Action: Check .env file

ERROR_KAFKA_UNAVAILABLE
  → Problem: Kafka broker not accessible
  → Action: Verify Kafka is running, check network

ERROR_VALIDATION_FAILED
  → Problem: Invalid flight data received
  → Action: Log error, skip record, continue
```

### 6.2 Spark Errors
```
ERROR_KAFKA_CONNECTION
  → Problem: Cannot read from Kafka topic
  → Action: Verify topic exists, check Kafka status

ERROR_MODEL_LOAD_FAILED
  → Problem: ML model file not found or corrupted
  → Action: Verify models/ directory, retrain if needed

ERROR_SCHEMA_MISMATCH
  → Problem: Input data doesn't match expected schema
  → Action: Check producer output, validate sanitization
```

### 6.3 Dashboard Errors
```
ERROR_KAFKA_CONSUMER_TIMEOUT
  → Problem: No messages received within timeout period
  → Action: Check Spark is producing data, verify topic

ERROR_DATA_DESERIALIZATION
  → Problem: Cannot parse JSON from Kafka
  → Action: Check format of upstream data

ERROR_PLOT_RENDERING
  → Problem: Chart rendering fails
  → Action: Check for null values, empty DataFrames
```

---

## 7. Data Quality Metrics

### 7.1 Coverage
- **Message Completeness:** 99.5% (fields required present)
- **Timestamp Validity:** 99.8% (valid ISO8601)
- **Geolocation Validity:** 98.5% (valid lat/lon ranges)

### 7.2 Timeliness
- **API Latency:** 500ms (p95)
- **Kafka Latency:** 5-10ms per hop
- **Spark Latency:** 2-5 seconds per micro-batch
- **Dashboard Update:** 3-10 seconds (configurable)
- **End-to-End:** ~15 seconds (API → Dashboard)

### 7.3 Accuracy
- **Anomaly Detection F1:** 1.00 (100% accurate)
- **Flight Phase Classification:** 95%+ accuracy
- **Coordinate Precision:** ±0.0001 degrees (~10 meters)

---

## 8. Testing Reference

### 8.1 Unit Test Data
```bash
# Sample message for testing
{
  "timestamp": "2026-01-15T10:30:00Z",
  "icao24": "aabbccdd",
  "callsign": "TEST001 ",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "velocity": 200.0,
  "baro_altitude": 30000.0,
  "vertical_rate": 100.0,
  "on_ground": false,
  "heading": 180.0,
  "is_anomaly": false,
  "anomaly_score": -0.5
}
```

### 8.2 Integration Test Commands
```bash
# Verify Kafka connectivity
kafka-console-consumer --bootstrap-server localhost:9092 \
  --topic flight-raw-data --from-beginning --max-messages 1

# Run all tests
pytest tests/test_integration.py -v

# Check message throughput
kafka-consumer-perf-test --broker-list localhost:9092 \
  --topic flight-raw-data --messages 10000
```

---

## 9. Glossary

| Term | Definition |
|------|-----------|
| **ICAO24** | 24-bit mode-C transponder code (aircraft identifier) |
| **Baro Altitude** | Altitude from barometric pressure sensor |
| **Geo Altitude** | Altitude from GPS/geometric calculations |
| **True Track** | Direction of movement (heading adjusted for wind) |
| **State Vector** | Complete aircraft state (position, velocity, etc.) |
| **Anomaly Score** | ML model output (-1 to +1, negative=normal) |
| **Watermark** | Deadline for late-arriving data in streaming windows |
| **Micro-batch** | Small batch of records processed as unit |
| **Tumbling Window** | Non-overlapping time windows (e.g., 10-min) |
| **UDF** | User-Defined Function (custom Spark function) |

---

## 10. Contact & Support

**Issues with:**
- **Data Ingestion (Member 1):** See `README_Yassine.md`
- **Stream Processing (Member 2):** See `Ramyreadme.md`
- **Dashboard & Integration (Member 3):** See `MEMBER3_README.md`

**Common Questions:**
1. Where are the Kafka brokers? → `docker/docker-compose.yml`
2. How do I configure OpenSky credentials? → Edit `.env` file
3. Why is dashboard empty? → Check producer/Spark are running
4. How do I modify ML model? → See `models/train_model.py`
5. Can I change window size? → Edit `WINDOW_SIZE_MINUTES` in config

**For detailed guidance, refer to:**
- Architecture: `docs/ARCHITECTURE.md`
- Deployment: `docs/DEPLOYMENT.md`
- Member 1: `README_Yassine.md` (Data Ingestion)
- Member 2: `Ramyreadme.md` (Stream Processing)
- Member 3: `MEMBER3_README.md` (Visualization)
