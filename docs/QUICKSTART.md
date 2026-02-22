# Quick Start Reference

**Project:** Real-Time Flight Data Streaming  
**Status:** ✅ Complete & Ready to Run  
**Members:** Yassine (Member 1) | Ramy (Member 2) | Chiheb (Member 3)  

---

## 🚀 One-Minute Setup

```bash
# 1. Setup environment
cd data-streaming-flights
python -m venv venv
source venv/bin/activate                    # Linux/Mac
# venv\Scripts\activate.bat                  # Windows

# 2. Install dependencies
pip install -r producer/requirements.txt
pip install -r spark_streaming/requirements.txt
pip install -r dashboard/requirements.txt

# 3. Configure credentials (.env file)
cp .env.example .env
# Edit .env with your OpenSky credentials

# 4. Start Kafka
cd docker && docker-compose up -d && cd ..

# Done! Now run the three components in separate terminals...
```

---

## 🎯 Running the System (3 Terminal Windows)

### Terminal 1: Start Producer (Data Ingestion)
```bash
python producer/api_producer.py
```
**Expected output:**
```
[2026-01-15 10:30:00] Connecting to OpenSky Network...
[2026-01-15 10:30:02] Connected! ✓
[2026-01-15 10:30:15] Published 42 flights to flight-raw-data
[2026-01-15 10:30:30] Published 38 flights to flight-raw-data
```

### Terminal 2: Start Spark Streaming (Processing & ML)
```bash
spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.apache.spark:spark-sql_2.12:3.5.0 \
  --master local[*] \
  spark_streaming/stream_processor.py
```
**Expected output:**
```
[2026-01-15 10:31:00] Starting Spark Stream Processing...
[2026-01-15 10:31:05] Spark Session initialized
[2026-01-15 10:31:10] Reading from flight-raw-data
[2026-01-15 10:31:15] Batch 1 processed: 40 records
```

### Terminal 3: Start Dashboard (Visualization)
```bash
streamlit run dashboard/app.py
```
**Expected output:**
```
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
```

---

## 📊 Access Dashboard

Open browser: **http://localhost:8501**

### Dashboard Sections
- **Top Left:** 5 KPI Metric Cards
  - Total Events
  - Anomalies Detected
  - Avg Velocity
  - Avg Altitude  
  - Active Aircraft Count

- **Charts:** 7 Interactive Visualizations
  - Velocity Timeline
  - Altitude Timeline
  - Anomaly Scatter (2D)
  - Windowed Metrics Trend
  - Anomaly Count Trend
  - Aircraft Distribution (Top 15)
  - Flight Phase Distribution (Pie)

- **Data Tables:** 3 Views
  - Recent Processed Data (last 20 events)
  - Recent Anomalies (last 10 anomalies)
  - Aggregated Window Statistics

- **Sidebar:** Configuration Controls
  - Refresh Interval slider (1-10 seconds)
  - Auto Refresh toggle
  - Data Buffer Size slider
  - Kafka connection settings

---

## ✅ Verification Checklist

```bash
# 1. Check Kafka is running
docker-compose ps
# OUTPUT: kafka and zookeeper should show "Up"

# 2. Check producer is publishing
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic flight-raw-data \
  --max-messages 1

# 3. Check spark is processing
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic flight-processed-data \
  --max-messages 1

# 4. Check dashboard loads
curl http://localhost:8501
```

---

## 📁 File Structure Quick Reference

```
Producer (Member 1):
├── producer/api_producer.py      # Main producer logic
├── producer/opensky_client.py    # OpenSky API client
├── producer/config.py            # Configuration
└── producer/requirements.txt     # Dependencies

Spark Streaming (Member 2):
├── spark_streaming/stream_processor.py    # Main Spark job
├── spark_streaming/transformations.py     # Data cleaning & features
├── spark_streaming/ml_inference.py        # ML model inference
├── spark_streaming/aggregations.py        # Windowing
└── spark_streaming/requirements.txt       # Dependencies

Models (Member 2):
├── models/flight_anomaly_detector.pkl   # Trained ML model
├── models/flight_scaler.pkl             # Feature scaler
└── models/flight_features.json          # Feature list

Dashboard (Member 3):
├── dashboard/app.py                          # Main Streamlit app
├── dashboard/components/
│   ├── kafka_consumer.py                    # Kafka integration
│   ├── metrics.py                           # KPI metrics
│   └── charts.py                            # Chart visualizations
└── dashboard/requirements.txt               # Dependencies

Documentation (Member 3):
├── MEMBER3_README.md            # Member 3 comprehensive guide
├── docs/ARCHITECTURE.md         # System design & architecture
├── docs/DEPLOYMENT.md           # Deployment instructions
├── docs/API_REFERENCE.md        # Data schemas & API docs
└── docs/QUICKSTART.md           # This file!

Tests:
├── tests/test_producer.py       # Producer tests
├── tests/test_spark.py          # Spark tests
├── tests/test_integration.py    # Integration tests

Docker:
├── docker/docker-compose.yml    # Kafka infrastructure
└── docker/.env                  # Docker environment variables
```

---

## 🔧 Troubleshooting Quick Fixes

### Dashboard Shows No Data
```bash
# 1. Check producer is running
ps aux | grep api_producer.py
# If empty, start: python producer/api_producer.py

# 2. Check Spark is running
ps aux | grep spark
# If empty, start spark-submit command (see above)

# 3. Check Kafka topics have data
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic flight-processed-data \
  --from-beginning --max-messages 5
```

### Kafka Connection Error
```bash
# Restart Kafka
docker-compose -f docker/docker-compose.yml restart kafka

# Wait 10 seconds and check status
docker-compose -f docker/docker-compose.yml ps
```

### Out of Memory
```bash
# Increase Spark memory
spark-submit \
  --driver-memory 4g \
  --executor-memory 4g \
  spark_streaming/stream_processor.py

# Or reduce dashboard buffer size (sidebar slider)
```

### Python Module Not Found
```bash
# Reinstall dependencies
pip install -r producer/requirements.txt
pip install -r spark_streaming/requirements.txt
pip install -r dashboard/requirements.txt
```

---

## 📊 Data Flow Diagram

```
OpenSky API (every 15s)
        ↓
[Producer] (Member 1)
        ↓
Kafka: flight-raw-data
        ↓
[Spark Streaming] (Member 2)
├── Cleaning
├── Feature Engineering
├── ML Anomaly Detection
└── Windowed Aggregations
        ↓
Kafka: flight-processed-data
Kafka: flight-aggregated-data
        ↓
[Streamlit Dashboard] (Member 3)
        ↓
Browser: http://localhost:8501
```

---

## 🛠️ Common Commands

### Start Services
```bash
# Start everything (must use separate terminals)
python producer/api_producer.py &
spark-submit --packages ... spark_streaming/stream_processor.py &
streamlit run dashboard/app.py
```

### Stop Services
```bash
# Kill by process name
pkill -f api_producer.py
pkill -f spark
lsof -i :8501 | grep LISTEN | awk '{print $2}' | xargs kill -9

# Or stop Docker
docker-compose down
```

### Check Logs
```bash
# Kafka
docker logs kafka

# Producer (if started in terminal)
tail -f producer.log

# Spark (if running locally)
tail -f spark.log

# Dashboard
ps aux | grep streamlit  # Find process
tail -f /tmp/streamlit-logs/
```

### Monitor Kafka Topics
```bash
# List all topics
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Monitor topic (follow latest messages)
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic flight-processed-data

# Get topic details
docker exec kafka kafka-topics \
  --describe \
  --bootstrap-server localhost:9092 \
  --topic flight-processed-data
```

---

## 📝 Configuration Defaults

### Producer (Member 1)
- **API Poll Interval:** 15 seconds
- **Kafka Topic:** flight-raw-data
- **Retry Attempts:** 3
- **API Timeout:** 10 seconds

### Spark (Member 2)
- **Window Size:** 10 minutes
- **Watermark:** 5 minutes
- **Micro-batch Interval:** 10 seconds
- **ML Model:** Isolation Forest (trained)

### Dashboard (Member 3)
- **Default Refresh:** 3 seconds
- **Refresh Range:** 1-10 seconds
- **Data Buffer:** 500 records
- **Kafka Consumer Timeout:** 1 second

---

## 🔗 Important URLs & Ports

| Service | URL | Default Port |
|---------|-----|--------------|
| Dashboard | http://localhost:8501 | 8501 |
| Kafka | localhost:9092 | 9092 |
| Zookeeper | localhost:2181 | 2181 |
| Spark UI | http://localhost:4040 | 4040 |

---

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | Main project overview |
| `MEMBER3_README.md` | Complete Member 3 documentation |
| `docs/ARCHITECTURE.md` | System design & architecture (600+ lines) |
| `docs/DEPLOYMENT.md` | Deployment guide for all environments |
| `docs/API_REFERENCE.md` | Kafka topics, data schemas, APIs |
| `PROJECT_STRATEGY_COMPLETE.md` | Overall project strategy & phases |
| `README_Yassine.md` | Member 1: Data ingestion details |
| `Ramyreadme.md` | Member 2: Stream processing & ML details |

---

## ✨ Key Features at a Glance

✅ **Real-Time Ingestion**
- 450 flights/min from OpenSky API
- 15-second polling interval
- OAuth2 authentication

✅ **Stream Processing**
- Apache Spark Structured Streaming
- 15+ derived features
- Windowed aggregations (10-min)

✅ **Machine Learning**
- Isolation Forest anomaly detection
- 100% F1-score on test data
- Real-time inference via Spark UDFs

✅ **Visualization**
- 7 interactive Plotly charts
- 5 KPI metric cards
- 3 data views
- Auto-refresh (configurable 1-10s)

✅ **Production Ready**
- Error handling & retries
- Comprehensive logging
- Configuration management
- Docker containerization

---

## 🎯 Next Steps

1. **Run the System** → Follow "Running the System" section above
2. **Access Dashboard** → Open http://localhost:8501
3. **Monitor Performance** → Use sidebar controls & watch metrics
4. **Run Tests** → `pytest tests/test_integration.py -v`
5. **Deploy** → See `docs/DEPLOYMENT.md` for production setup

---

## 💡 Tips & Tricks

### Adjust Dashboard Refresh
Use the sidebar slider to change refresh interval from 1-10 seconds. Faster updates = higher latency, higher lag.

### View Raw Kafka Data
```bash
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic flight-processed-data \
  --property print.key=true --property key.separator=":"
```

### Monitor System Performance
```bash
# CPU/Memory usage
top
# or on Windows: Task Manager

# Kafka lag
docker exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group flight-dashboard-group \
  --describe
```

### Replay Historical Data
Change `auto_offset_reset` in dashboard config from "latest" to "earliest" to see all historical data.

---

## 📞 Support & Documentation

**For Issues:**
- Producer Issues → Check `README_Yassine.md`
- Spark Issues → Check `Ramyreadme.md`  
- Dashboard Issues → Check `MEMBER3_README.md`
- Architecture Questions → See `docs/ARCHITECTURE.md`
- Deployment Help → See `docs/DEPLOYMENT.md`
- Data Schema Questions → See `docs/API_REFERENCE.md`

**Quick Links:**
- Project GitHub: [Repository URL]
- OpenSky Network: https://opensky-network.org
- Apache Kafka Docs: https://kafka.apache.org
- Streamlit Docs: https://docs.streamlit.io
- Spark Docs: https://spark.apache.org/docs

---

## 🎉 You're All Set!

The system is fully implemented and ready to run. All three components (Producer, Spark, Dashboard) are complete and integrated.

**Happy streaming!** ✈️
