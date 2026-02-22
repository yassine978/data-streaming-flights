# Dashboard Development By Chiheb

## Overview

This document describes the Real-Time Flight Tracking Dashboard component developed for the M2 BDIA Data Streaming project. The dashboard consumes processed flight data from Apache Kafka and presents live analytics, metrics, and visualizations.

## Project Architecture

The system consists of three integrated components:

1. **Member 1 (Producer)**: Fetches real-time flight data from OpenSky API and publishes to Kafka
2. **Member 2 (Spark Streaming)**: Processes data, applies ML inference, and outputs to Kafka topics
3. **Member 3 (Dashboard)**: Consumes Kafka data and displays interactive visualizations

## Dashboard Component Overview

### Technology Stack

- **Framework**: Streamlit (Python web application framework)
- **Data Processing**: Pandas, NumPy
- **Visualization**: Plotly (interactive charts)
- **Data Source**: Apache Kafka
- **Deployment**: Local development environment

### Project Structure

```
dashboard/
├── app.py                    # Main dashboard application
├── components/
│   ├── __init__.py
│   ├── kafka_consumer.py     # Kafka data consumer
│   ├── metrics.py            # Metrics calculation and display
│   └── charts.py             # Chart rendering logic
└── requirements.txt          # Python dependencies
```

## Kafka Topics Consumed

The dashboard reads from the following Kafka topics:

1. **flight-processed-data**: Individual flight events with ML scoring
   - Contains: icao24, callsign, velocity, altitude, vertical_rate, heading, on_ground, origin_country, flight_phase, ml_is_anomaly, ml_anomaly_score

2. **flight-aggregated-data**: Time-windowed aggregations
   - Contains: window_start, avg_velocity, max_velocity, min_velocity, avg_altitude, anomaly_count

## Features Implemented

### 1. Configuration Panel (Sidebar)

- Refresh Interval: Adjustable (1-10 seconds), default 3 seconds
- Auto-Refresh: Toggle automatic dashboard updates
- Processed Events Buffer: Adjustable view size (50-500 events)
- Aggregated Windows Buffer: Adjustable view size (20-100 windows)
- Kafka Connection Settings: Editable bootstrap servers and connection parameters
- Display Options: Toggle visibility of different sections

### 2. Real-Time Metrics Section

Top-level KPIs displayed with metric cards:

- Total Events: Total number of flight records processed
- Anomalies: Count of anomalous flights detected
- Avg Velocity: Average speed across all aircraft (m/s)
- Avg Altitude: Average altitude across all aircraft (m)
- Aircraft Count: Number of unique aircraft in view

### 3. Summary Statistics

Velocity Statistics:
- Min, Mean, Max velocity values

Altitude Statistics:
- Min, Mean, Max altitude values

Vertical Rate Statistics:
- Min, Mean, Max vertical rate values (climb/descent)

Anomaly Statistics:
- Anomalies Detected: Count of anomalous events
- Anomaly Rate: Percentage of events flagged as anomalies
- Avg Anomaly Score: Average ML anomaly score (0-1)

### 4. Real-Time Event Analysis Charts

#### Velocity Timeline
- X-axis: Time (event_time)
- Y-axis: Velocity (m/s)
- Color: Anomaly status (red for anomalies, blue for normal)
- Purpose: Track velocity changes over time, identify sudden changes

#### Altitude Timeline
- X-axis: Time (event_time)
- Y-axis: Altitude (m)
- Color: Flight phase (landing, climbing, descending, level flight)
- Purpose: Monitor altitude profiles and flight phases

#### Anomaly Scatter Plot
- X-axis: Velocity (m/s)
- Y-axis: Altitude (m)
- Color: Anomaly flag
- Size: Anomaly score magnitude
- Purpose: Identify anomalies in velocity-altitude space

#### Aircraft Distribution
- Top 15 most active aircraft by number of events
- Displays callsign or ICAO24 identifier
- Bar chart sorted by activity
- Purpose: Identify key aircraft in the network

#### Flight Phase Distribution
- Pie chart showing breakdown of flight phases
- Categories: Landing, Climbing, Descending, Level Flight
- Purpose: Understand operational mix

#### Climb/Descent Analysis
- X-axis: Vertical Rate (m/s)
- Y-axis: Altitude (m)
- Color: Flight phase
- Vertical reference line at 0 (no vertical movement)
- Purpose: Analyze climbing and descent rates at different altitudes

### 5. Advanced Analytics Section

#### Country Distribution
- Top 12 countries by flight count
- Color gradient representing activity level
- Purpose: Geographic distribution of flights

#### Velocity Distribution
- Histogram of all velocities
- 40 bins for granular distribution view
- Purpose: Statistical analysis of speed patterns, identify outliers

#### Flight Direction Distribution
- Compass rose showing eight cardinal directions (N, NE, E, SE, S, SW, W, NW)
- Bar chart with color gradient
- Purpose: Identify dominant traffic corridors

#### Aircraft Status
- Pie chart: On-ground vs In-air split
- Real-time fleet operational status
- Purpose: Monitor fleet readiness

#### Data Quality Metrics
- Total Events Processed: Cumulative count
- Unique Aircraft: Count of distinct aircraft
- Events with Valid Position: Data completeness percentage
- Events with Altitude: Data completeness percentage
- Average Events per Aircraft: Mean events per aircraft
- Purpose: Monitor data quality and processing completeness

### 6. Windowed Aggregations

#### Windowed Velocity Statistics
- Line chart with average, max, min velocities over time windows
- 20 most recent windows displayed
- Purpose: Trend analysis of velocity at different time scales

#### Anomalies Per Time Window
- Bar chart of anomaly counts per window
- Color intensity represents anomaly count
- 30 most recent windows displayed
- Purpose: Detect time periods with elevated anomaly activity

### 7. Raw Data Tables (Optional)

Two tabs for detailed record inspection:

- Processed Events: Last 50 records with all fields
- Aggregated Windows: Last 30 window records
- Toggled via "Show Raw Data Tables" checkbox

## How to Run

### Prerequisites

1. Docker containers running (Zookeeper, Kafka, Spark)
2. Producer sending data to Kafka
3. Spark processing data and publishing to processed/aggregated topics
4. Python 3.8+ installed locally

### Installation

```bash
# Install Python dependencies
pip install -r dashboard/requirements.txt
```

### Launch Dashboard

```bash
cd c:\Users\Lenovo\data-streaming-flights
streamlit run dashboard/app.py
```

Dashboard will be available at: http://localhost:8501

### Configuration

Before running, ensure:

1. Kafka bootstrap servers are accessible at localhost:9092
2. Topics exist in Kafka:
   - flight-raw-data
   - flight-processed-data
   - flight-aggregated-data
   - flight-invalid-spark

If needed, create topics:
```bash
docker exec kafka_flights kafka-topics --bootstrap-server kafka_flights:29092 --create --topic flight-processed-data --partitions 1 --replication-factor 1
docker exec kafka_flights kafka-topics --bootstrap-server kafka_flights:29092 --create --topic flight-aggregated-data --partitions 1 --replication-factor 1
```

## Auto-Refresh Mechanism

The dashboard automatically refreshes every N seconds (default: 3 seconds):

1. Waits for configured refresh interval
2. Calls update_data() to fetch latest Kafka messages
3. Uses st.rerun() to reload the dashboard
4. All charts and metrics are recalculated with new data

This ensures real-time visualization of streaming flight data.

## Data Processing Pipeline

```
OpenSky API
    |
    v
Producer (Member 1)
    |
    v
Kafka Topic: flight-raw-data
    |
    v
Spark Streaming (Member 2)
    - Transformations (speed, altitude, vertical rate)
    - ML Inference (anomaly detection with Isolation Forest)
    - Aggregations (windowed metrics)
    |
    +---> Kafka Topic: flight-processed-data
    |
    +---> Kafka Topic: flight-aggregated-data
    |
    v
Dashboard (Member 3)
    - Consume processed data
    - Calculate metrics
    - Render visualizations
    - Auto-refresh every 3 seconds
```

## ML Model Integration

The dashboard displays results from Member 2's ML model:

- Model Type: Isolation Forest (scikit-learn)
- Features: velocity, baro_altitude, vertical_rate, hour, day_of_week
- Contamination: 1% (flags ~1% of data as anomalies)
- Training Accuracy: 100% on test set
- Output Fields:
  - ml_is_anomaly: Boolean flag (True = anomalous)
  - ml_anomaly_score: Float (0-1, higher = more anomalous)

## Performance Metrics

Current system performance (measured):

- Input Rate: 40-50 rows/second from OpenSky API
- Processing Rate: 120-170 rows/second in Spark
- Data Lag: 0 (real-time, no backlog)
- Dashboard Refresh: 3 seconds
- Active Aircraft: 200+
- Events Processed: 40,000+ 
- Anomalies Detected: Based on 1% contamination threshold

## Visualizations Summary

The dashboard includes 12 interactive visualizations:

1. Velocity Timeline (line scatter)
2. Altitude Timeline (line scatter)
3. Anomaly Scatter (velocity vs altitude)
4. Aircraft Distribution (top 15, bar)
5. Flight Phase Distribution (pie)
6. Climb/Descent Analysis (scatter)
7. Country Distribution (top 12, bar)
8. Velocity Distribution (histogram)
9. Flight Direction (compass, bar)
10. Aircraft Status (pie)
11. Data Quality Metrics (bar)
12. Windowed Metrics (line) + Anomaly Trends (bar)

Plus 5 metric cards (KPIs) and 3 summary statistic groups.

## Code Structure

### Main Dashboard (app.py)

- Page configuration and styling
- Sidebar controls for refresh rate, buffer sizes, display options
- Kafka consumer initialization with caching
- Data fetching and session state management
- Layout with columns and tabs
- Auto-refresh loop

### Kafka Consumer (components/kafka_consumer.py)

- DashboardKafkaConsumer class
- Methods to fetch processed and aggregated events
- Batch consumption from Kafka topics
- Error handling and logging

### Metrics Display (components/metrics.py)

- MetricsDisplay class
- Top-level KPI rendering
- Summary statistics calculation
- Anomaly statistics display

### Charts Display (components/charts.py)

- ChartsDisplay class
- 12 different chart rendering methods
- Error handling for missing data
- Plotly-based interactive visualizations

## Known Limitations

1. Data is consumed in-memory (not persisted)
2. Scrolling through history is limited to buffered events
3. Kafka consumer starts from latest offset (does not replay history)
4. Single-threaded Streamlit execution

## Future Enhancements

Potential improvements for production deployment:

1. Time-series database (InfluxDB, TimescaleDB) for historical data
2. Persistent storage of events for replay and analysis
3. Export functionality (CSV, JSON)
4. Custom time range selection
5. Alerting system for anomalies
6. User authentication
7. Horizontal scaling with multiple dashboard instances
8. Mobile-responsive design
9. Performance profiling
10. Integration with external alerting systems (Slack, PagerDuty)

## Testing

To verify the dashboard is working:

1. Check Kafka has data: 
   ```bash
   docker exec kafka_flights kafka-console-consumer --bootstrap-server kafka_flights:29092 --topic flight-processed-data --from-beginning --max-messages 1
   ```

2. Verify Spark is processing:
   ```bash
   docker logs spark_flights 2>&1 | tail -20
   ```

3. Verify Producer is running:
   ```bash
   python producer/api_producer.py
   ```

4. Open dashboard at http://localhost:8501 and verify:
   - Metrics display non-zero values
   - Charts update every 3 seconds
   - No error messages in console

## Key Metrics Observed

From recent runs:

- Total Events: 200-600 (depends on buffer size)
- Unique Aircraft: 200+
- Avg Velocity: 206 m/s
- Avg Altitude: 8,684 m
- Anomalies: 0 (normal flight operations)
- Anomaly Rate: 0.00%
- Data Quality: 100% with valid positions and altitudes

## Troubleshooting

### Dashboard shows "Offline" status

- Check Kafka is running: `docker-compose -f docker/docker-compose.yml ps`
- Verify bootstrap servers: Change in sidebar if needed
- Check Spark has created topics

### Plots are empty

- Ensure Producer is running with `python producer/api_producer.py`
- Ensure Spark is processing with `docker logs spark_flights`
- Wait for buffering (30-60 seconds of data)

### Dashboard freezes

- Normal Streamlit behavior during data fetch
- Increase refresh interval in sidebar if experiencing lag
- Check Kafka broker is responsive
- Verify network connectivity

### "ModuleNotFoundError" when running

- Reinstall requirements: `pip install -r dashboard/requirements.txt`
- Verify Python version (3.8+)

## Dependencies

See dashboard/requirements.txt for complete list. Main dependencies:

- streamlit>=1.28.0
- pandas>=1.5.0
- plotly>=5.17.0
- kafka-python>=2.3.0

## Author

Member 3: Chiheb (Dashboard Development)

## References

- Streamlit Documentation: https://docs.streamlit.io
- Plotly Documentation: https://plotly.com/python/
- Kafka Python Client: https://kafka-python.readthedocs.io
- OpenSky API: https://opensky-network.org/api
