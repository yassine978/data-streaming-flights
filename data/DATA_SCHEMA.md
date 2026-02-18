# Data Schema Documentation

**API:** OpenSky Network
**Endpoint:** `https://opensky-network.org/api/states/all`
**Update Frequency:** Every 15 seconds
**Authentication:** OAuth2 Bearer Token

---

## Kafka Message Schema

Each message in `flight-raw-data` topic has this structure:

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

## Field Descriptions

| Field | Type | Description | Nullable | Unit |
|-------|------|-------------|----------|------|
| `icao24` | string | Unique ICAO 24-bit aircraft address (hex) | No | - |
| `callsign` | string | Flight callsign (8 chars max) | Yes | - |
| `origin_country` | string | Country of aircraft registration | Yes | - |
| `time_position` | integer | Unix timestamp of last position update | Yes | seconds |
| `longitude` | float | WGS-84 longitude | Yes | degrees |
| `latitude` | float | WGS-84 latitude | Yes | degrees |
| `baro_altitude` | float | Barometric altitude | Yes | meters |
| `on_ground` | boolean | Whether aircraft is on ground | Yes | - |
| `velocity` | float | Ground speed | Yes | m/s |
| `heading` | float | True track (clockwise from north) | Yes | degrees (0-360) |
| `vertical_rate` | float | Vertical rate (positive=climbing) | Yes | m/s |
| `geo_altitude` | float | Geometric altitude | Yes | meters |
| `position_source` | integer | Position source type | Yes | enum |
| `ingestion_timestamp` | string | When producer received data | No | ISO 8601 |
| `data_valid` | boolean | Passed validation checks | No | - |

---

## Position Source Values

| Value | Meaning |
|-------|---------|
| 0 | ADS-B |
| 1 | ASTERIX |
| 2 | MLAT (Multilateration) |
| 3 | FLARM |

---

## Data Quality Notes

### Missing Values

- **Callsign:** Often null for private aircraft or military
- **Altitude:** Null when aircraft is on ground or transponder off
- **Velocity/Heading:** Null when stationary or data unavailable
- **Position:** Null if no recent position report

### Typical Value Ranges

| Field | Typical Range | Extreme Values |
|-------|---------------|----------------|
| `baro_altitude` | 0 - 12,000 m | Max ~15,000 m (high altitude) |
| `velocity` | 0 - 300 m/s | Max ~340 m/s (supersonic rare) |
| `vertical_rate` | -30 to +30 m/s | Emergency descent can exceed |
| `heading` | 0 - 360 | Exactly 0 or 360 = North |

### Update Latency

- **API Polling:** Every 15 seconds
- **Position Age:** Usually < 5 seconds old
- **Token Refresh:** Every 25 minutes (before 30-min expiry)

### Rate Limits

- **Free Tier:** 4000 credits/day
- **Credit Usage:** Each API call uses credits based on result size
- **Recommended:** Don't poll faster than 10 seconds

---

## Invalid Data Topic Schema

Messages in `flight-invalid-data` topic have additional field:

```json
{
  "icao24": null,
  "callsign": "TEST123",
  "latitude": 95.0,
  ...
  "data_valid": false,
  "validation_error": "Invalid latitude: 95.0"
}
```

### Validation Errors

| Error | Cause |
|-------|-------|
| `Missing icao24` | Required field is null or empty |
| `Invalid latitude: X` | Latitude outside -90 to 90 |
| `Invalid longitude: X` | Longitude outside -180 to 180 |
| `Invalid baro_altitude: X` | Altitude outside -1000 to 50000 |
| `Invalid velocity: X` | Negative velocity |
| `Invalid heading: X` | Heading outside 0 to 360 |

---

## Sample Raw API Response

The OpenSky API returns this format:

```json
{
  "time": 1739700000,
  "states": [
    ["3c675a", "DLH123 ", "Germany", 1739700000, 1739700000,
     13.405, 52.52, 11200.0, false, 245.3, 270.0, -2.5,
     null, 11100.0, "1000", false, 0]
  ]
}
```

### State Vector Array Index Mapping

| Index | Field | Type |
|-------|-------|------|
| 0 | icao24 | string |
| 1 | callsign | string (whitespace padded) |
| 2 | origin_country | string |
| 3 | time_position | int |
| 4 | last_contact | int |
| 5 | longitude | float |
| 6 | latitude | float |
| 7 | baro_altitude | float |
| 8 | on_ground | bool |
| 9 | velocity | float |
| 10 | true_track (heading) | float |
| 11 | vertical_rate | float |
| 12 | sensors | array (usually null) |
| 13 | geo_altitude | float |
| 14 | squawk | string |
| 15 | spi | bool |
| 16 | position_source | int |

---

## For Spark Structured Streaming

### Recommended Schema Definition

```python
from pyspark.sql.types import *

flight_schema = StructType([
    StructField("icao24", StringType(), False),
    StructField("callsign", StringType(), True),
    StructField("origin_country", StringType(), True),
    StructField("time_position", LongType(), True),
    StructField("longitude", DoubleType(), True),
    StructField("latitude", DoubleType(), True),
    StructField("baro_altitude", DoubleType(), True),
    StructField("on_ground", BooleanType(), True),
    StructField("velocity", DoubleType(), True),
    StructField("heading", DoubleType(), True),
    StructField("vertical_rate", DoubleType(), True),
    StructField("geo_altitude", DoubleType(), True),
    StructField("position_source", IntegerType(), True),
    StructField("ingestion_timestamp", StringType(), False),
    StructField("data_valid", BooleanType(), False)
])
```

### Reading from Kafka

```python
df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "flight-raw-data") \
    .option("startingOffsets", "earliest") \
    .load()

# Parse JSON value
from pyspark.sql.functions import from_json, col

parsed_df = df.select(
    col("key").cast("string").alias("aircraft_id"),
    from_json(col("value").cast("string"), flight_schema).alias("data")
).select("aircraft_id", "data.*")
```

---

## ML Feature Suggestions

| Feature | Description | Anomaly Use Case |
|---------|-------------|------------------|
| `velocity` | Ground speed | Unusually slow/fast aircraft |
| `baro_altitude` | Flight level | Abnormal altitude for phase |
| `vertical_rate` | Climb/descent | Emergency descent detection |
| `heading` changes | Direction shifts | Erratic flight path |
| `on_ground` transitions | Takeoff/landing | Unexpected ground contact |

### Derived Features

```python
# Speed in km/h
velocity_kmh = velocity * 3.6

# Speed in knots
velocity_knots = velocity * 1.944

# Altitude in feet
altitude_feet = baro_altitude * 3.281

# Time since position update
position_age = current_time - time_position
```

---

## Bounding Box (Europe)

The producer fetches flights within:

| Parameter | Value | Description |
|-----------|-------|-------------|
| `lamin` | 35.0 | South border (Portugal/Spain) |
| `lamax` | 72.0 | North border (Norway) |
| `lomin` | -10.0 | West border (Atlantic) |
| `lomax` | 40.0 | East border (Turkey/Russia) |
