# Data Foundation - Member 1

**Author:** Mohamed Yassine Madhi
**Branch:** `yassine-data-foundation`

---

## What I Built

### 1. API Integration

- **Selected API:** OpenSky Network
- **Reason:** Real-time flight tracking data with OAuth2 authentication, rich numeric data suitable for ML anomaly detection, free tier with 4000 credits/day
- **Update Frequency:** Every 15 seconds
- **Coverage:** Europe bounding box (lat: 35-72, lon: -10 to 40)
- **Authentication:** OAuth2 client credentials flow (tokens expire every 30 minutes)

### 2. Kafka Infrastructure

- **Topics Created:**
  - `flight-raw-data`: Valid flight data from API (3 partitions)
  - `flight-invalid-data`: Invalid/malformed data (1 partition)
- **Docker Setup:** Complete with docker-compose.yml (Zookeeper + Kafka)
- **Message Key:** `icao24` (unique aircraft identifier) for partitioning

### 3. Producer Application

- **Features:**
  - Polls OpenSky API every 15 seconds
  - OAuth2 token auto-refresh (before 30-min expiry)
  - Validates each flight record before sending
  - Routes invalid data to separate topic
  - Comprehensive error handling and retry logic
  - INFO-level logging with timestamps
  - Graceful shutdown on Ctrl+C
  - Statistics tracking (total, valid, invalid, errors)

---

## Project Structure

```
data-streaming-flights/
├── docker/
│   └── docker-compose.yml      # Kafka + Zookeeper setup
├── producer/
│   ├── __init__.py
│   ├── config.py               # Configuration from .env
│   ├── opensky_client.py       # OAuth2 + API fetching
│   ├── kafka_admin.py          # Topic creation
│   ├── api_producer.py         # Main producer application
│   └── requirements.txt        # Python dependencies
├── tests/
│   ├── test_api.py             # Manual API test script
│   └── test_producer.py        # Unit tests (27 tests)
├── data/
│   ├── sample_data.json        # Sample API responses
│   └── DATA_SCHEMA.md          # Complete schema documentation
├── .env                        # Credentials (NOT committed)
├── .env.example                # Template for teammates
└── README_MEMBER1.md           # This file
```

---

## How to Run

### Prerequisites

- Docker Desktop installed and running
- Python 3.9+
- Git

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/yassine978/data-streaming-flights.git
cd data-streaming-flights

# 2. Checkout Member 1 branch
git checkout member1-data-foundation

# 3. Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 4. Install dependencies
cd producer
pip install -r requirements.txt
cd ..

# 5. Configure environment
# Copy .env.example to .env and add your OpenSky credentials
# Get credentials at: https://opensky-network.org/

# 6. Start Kafka
cd docker
docker-compose up -d
cd ..

# Wait 30 seconds for Kafka to start, then verify:
docker ps
# Should see: kafka_flights and zookeeper_flights

# 7. Run the producer
cd producer
python api_producer.py
```

### Verify It's Working

In another terminal:

```powershell
# Windows PowerShell - Consume messages
docker exec -it kafka_flights kafka-console-consumer --bootstrap-server localhost:9092 --topic flight-raw-data --from-beginning --max-messages 5
```

You should see JSON messages like:
```json
{"icao24": "3c675a", "callsign": "DLH123", "origin_country": "Germany", ...}
```

### Stop Everything

```bash
# Stop producer: Ctrl+C in producer terminal

# Stop Kafka
cd docker
docker-compose down
```

---

## Data Schema

See [data/DATA_SCHEMA.md](data/DATA_SCHEMA.md) for complete schema documentation.

**Sample Kafka message:**

```json
{
  "icao24": "3c675a",
  "callsign": "DLH123",
  "origin_country": "Germany",
  "time_position": 1739700000,
  "longitude": 13.405,
  "latitude": 52.52,
  "baro_altitude": 11200.0,
  "on_ground": false,
  "velocity": 245.3,
  "heading": 270.0,
  "vertical_rate": -2.5,
  "geo_altitude": 11100.0,
  "position_source": 0,
  "ingestion_timestamp": "2025-02-16T10:30:05Z",
  "data_valid": true
}
```

---

## Testing

```bash
# Run unit tests (27 tests)
cd data-streaming-flights
pytest tests/test_producer.py -v

# Manual API test (requires valid .env credentials)
python tests/test_api.py
```

### Test Coverage

- Validation logic (valid/invalid data detection)
- Coordinate boundary tests (lat: -90 to 90, lon: -180 to 180)
- Altitude and velocity validation
- State vector parsing
- OAuth2 token handling (mocked)
- Edge cases and boundary conditions

---

## Validation Rules

The producer validates each flight record:

| Field | Rule | Invalid Example |
|-------|------|-----------------|
| `icao24` | Required, non-empty | `null`, `""` |
| `latitude` | -90 to 90 (if present) | `95.0`, `-100.0` |
| `longitude` | -180 to 180 (if present) | `200.0`, `-200.0` |
| `baro_altitude` | -1000 to 50000 meters (if present) | `100000.0` |
| `velocity` | >= 0 (if present) | `-10.0` |
| `heading` | 0 to 360 (if present) | `400.0` |

Invalid records are sent to `flight-invalid-data` topic with `validation_error` field.

---

## Configuration

All configuration is in `.env` file:

```env
# OpenSky API Credentials
OPENSKY_CLIENT_ID=your_client_id
OPENSKY_CLIENT_SECRET=your_client_secret

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC_RAW=flight-raw-data
KAFKA_TOPIC_INVALID=flight-invalid-data

# Producer Settings
POLLING_INTERVAL=15

# Europe Bounding Box
BBOX_LAMIN=35.0
BBOX_LAMAX=72.0
BBOX_LOMIN=-10.0
BBOX_LOMAX=40.0
```

---

## Performance Metrics

- **Throughput:** ~1500-2500 flights per API call (depends on time of day)
- **Polling Interval:** 15 seconds
- **Token Refresh:** Automatic, 5 minutes before expiry
- **Expected Messages:** ~6000-10000 messages/hour

---

## Known Issues & Limitations

1. **API Rate Limits:** 4000 credits/day on free tier. Each call uses credits.
2. **Token Expiry:** Tokens last 30 minutes, auto-refreshed at 25 minutes.
3. **Data Gaps:** Some aircraft may have null fields (callsign, altitude) - these still pass validation if icao24 is present.
4. **Network Timeouts:** 30-second timeout on API calls, with automatic retry.

---

## For Member 2: What You Need to Know

### Kafka Topics

| Topic | Partitions | Content |
|-------|------------|---------|
| `flight-raw-data` | 3 | Valid flight records |
| `flight-invalid-data` | 1 | Invalid records with error info |

### Message Format

- **Key:** `icao24` (string) - use for grouping by aircraft
- **Value:** JSON object (see schema above)
- **Timestamp:** `ingestion_timestamp` field in ISO format

### Useful Fields for ML

| Field | Type | ML Use Case |
|-------|------|-------------|
| `velocity` | float | Speed anomalies |
| `baro_altitude` | float | Altitude anomalies |
| `vertical_rate` | float | Climb/descent rate anomalies |
| `heading` | float | Direction changes |
| `on_ground` | bool | Ground vs airborne filtering |

### Starting Spark Consumer

```python
# In your Spark application
df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "flight-raw-data") \
    .load()
```

---

## Handoff Checklist

- [x] Producer runs without errors
- [x] Messages flowing to Kafka topics
- [x] Invalid data routed correctly
- [x] Unit tests passing (27 tests)
- [x] Documentation complete
- [x] Sample data provided
- [x] .env.example provided
- [ ] Producer tested for 24+ hours
- [ ] At least 1000 messages in topic
