# Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the Real-Time Flight Data Streaming Application across different environments.

---

## Part 1: Local Development Setup

### Prerequisites

- **Windows/Mac/Linux** with 8GB+ RAM
- **Python 3.9+**
- **Docker & Docker Compose** (for Kafka)
- **Git** (for version control)
- **OpenSky Network credentials** (free account at https://opensky-network.org)

### Step 1: Clone Repository

```bash
# Clone the project
git clone https://github.com/yassine978/data-streaming-flights.git
cd data-streaming-flights

# Create and activate Python virtual environment
python -m venv venv

# Activate (choose based on OS)
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate.bat      # Windows CMD
venv\Scripts\Activate.ps1      # Windows PowerShell
```

### Step 2: Install Dependencies

```bash
# Install all dependencies
pip install -r producer/requirements.txt
pip install -r spark_streaming/requirements.txt
pip install -r dashboard/requirements.txt

# Or install all at once
pip install kafka-python==2.0.2 \
    pyspark==3.5.0 \
    requests==2.31.0 \
    pandas==2.0.3 \
    plotly==5.17.0 \
    streamlit==1.28.1 \
    scikit-learn==1.3.0 \
    python-dotenv==1.0.0
```

### Step 3: Configure Environment Variables

```bash
# Create .env file
cp .env.example .env

# Edit with your OpenSky credentials
nano .env  # or use your editor
```

**.env file content:**
```
# OpenSky Network API
OPENSKY_USERNAME=your_opensky_username
OPENSKY_PASSWORD=your_opensky_password

# Kafka Configuration
KAFKA_HOST=localhost
KAFKA_PORT=9092
KAFKA_BROKER=localhost:9092

# Spark Configuration
SPARK_MASTER=local[*]
SPARK_APP_NAME=FlightStreamingApp

# Dashboard
STREAMLIT_PORT=8501
AUTO_REFRESH=true
REFRESH_INTERVAL=3
```

### Step 4: Start Kafka Infrastructure

```bash
# Navigate to docker directory
cd docker

# Start Kafka and Zookeeper
docker-compose up -d

# Verify containers are running
docker-compose ps

# Check logs (optional)
docker-compose logs -f
```

**Expected Output:**
```
NAME                COMMAND                  SERVICE             STATUS
zookeeper           "/etc/confluent/docker  zookeeper           Up
kafka               "/etc/confluent/docker  kafka               Up
```

### Step 5: Verify Kafka Topics

```bash
# Check created topics
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Should show:
# flight-raw-data
# flight-processed-data  
# flight-aggregated-data
```

### Step 6: Run Components in Separate Terminals

**Terminal 1: Start Producer**
```bash
cd data-streaming-flights
source venv/bin/activate
python producer/api_producer.py

# Expected output:
# [2026-01-15 10:30:00] Connected to OpenSky API
# [2026-01-15 10:30:15] Published 42 flights to flight-raw-data
# [2026-01-15 10:30:30] Published 38 flights to flight-raw-data
```

**Terminal 2: Start Spark Stream Processing**
```bash
cd data-streaming-flights
source venv/bin/activate

spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.apache.spark:spark-sql_2.12:3.5.0 \
  --master local[*] \
  --driver-memory 2g \
  --executor-memory 2g \
  spark_streaming/stream_processor.py

# Expected output:
# [2026-01-15 10:31:00] Starting Spark Stream Processing
# [2026-01-15 10:31:05] Reading from flight-raw-data topic
# [2026-01-15 10:31:10] Processing batch 1: 40 records
# [2026-01-15 10:31:20] Output batch 1: 40 processed + 8 anomalies
```

**Terminal 3: Start Streamlit Dashboard**
```bash
cd data-streaming-flights
source venv/bin/activate
streamlit run dashboard/app.py

# Expected output:
# You can now view your Streamlit app in your browser.
# 
# Local URL: http://localhost:8501
# Network URL: http://192.168.x.x:8501
```

### Step 7: Access Dashboard

Open browser to: **http://localhost:8501**

You should see:
- ✅ KPI metrics refreshing in real-time
- ✅ Charts updating with new data
- ✅ Data tables showing recent events
- ✅ Toggles and controls in sidebar

---

## Part 2: Testing & Validation

### Run Integration Tests

```bash
# Install pytest if needed
pip install pytest pytest-timeout

# Run integration tests
pytest tests/test_integration.py -v -s

# Expected results:
# test_kafka_broker_available PASSED
# test_required_topics_exist PASSED
# test_raw_data_topic_has_messages PASSED
# test_processed_data_schema_validation PASSED
# ... (10+ tests total)
```

### Manual Validation

**Check Producer Output:**
```bash
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic flight-raw-data \
  --from-beginning \
  --max-messages 5 | head -20
```

**Check Processed Data:**
```bash
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic flight-processed-data \
  --from-beginning \
  --max-messages 5 | head -20
```

**Check Dashboard Logs:**
```bash
# Streamlit logs should show:
# 2026-01-15 10:35:00.123 - Fetching processed data...
# 2026-01-15 10:35:01.456 - Rendering metrics...
# 2026-01-15 10:35:02.789 - Rendering charts...
```

---

## Part 3: Production Deployment

### Option A: Docker Deployment

**Build Docker Images:**

```dockerfile
# Create Dockerfile for Producer
cat > Dockerfile.producer << 'EOF'
FROM python:3.9-slim
WORKDIR /app
COPY producer/ producer/
COPY requirements.txt .
RUN pip install -r requirements.txt
CMD ["python", "producer/api_producer.py"]
EOF

# Create Dockerfile for Spark (optional - usually submitted via spark-submit)
# Create Dockerfile for Dashboard
cat > Dockerfile.dashboard << 'EOF'
FROM python:3.9-slim
WORKDIR /app
COPY dashboard/ dashboard/
COPY dashboard/requirements.txt .
RUN pip install -r requirements.txt
EXPOSE 8501
CMD ["streamlit", "run", "dashboard/app.py"]
EOF
```

**Docker Compose for Production:**

```yaml
version: '3.8'

services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    depends_on:
      - zookeeper
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    ports:
      - "9092:9092"

  producer:
    build:
      context: .
      dockerfile: Dockerfile.producer
    environment:
      OPENSKY_USERNAME: ${OPENSKY_USERNAME}
      OPENSKY_PASSWORD: ${OPENSKY_PASSWORD}
      KAFKA_HOST: kafka
      KAFKA_PORT: 9092
    depends_on:
      - kafka

  spark:
    image: bitnami/spark:3.5.0
    environment:
      SPARK_MODE: submit
      SPARK_MASTER_URL: spark://spark-master:7077
    depends_on:
      - kafka

  dashboard:
    build:
      context: .
      dockerfile: Dockerfile.dashboard
    environment:
      KAFKA_HOST: kafka
      KAFKA_PORT: 9092
    ports:
      - "8501:8501"
    depends_on:
      - kafka
      - producer
```

**Deploy:**
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Option B: Kubernetes Deployment

**Create Kubernetes manifests:**

```yaml
# producer-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: flight-producer
spec:
  replicas: 1
  selector:
    matchLabels:
      app: flight-producer
  template:
    metadata:
      labels:
        app: flight-producer
    spec:
      containers:
      - name: producer
        image: flight-producer:latest
        env:
        - name: OPENSKY_USERNAME
          valueFrom:
            secretKeyRef:
              name: opensky-credentials
              key: username
        - name: OPENSKY_PASSWORD
          valueFrom:
            secretKeyRef:
              name: opensky-credentials
              key: password
        - name: KAFKA_HOST
          value: "kafka-broker"
        - name: KAFKA_PORT
          value: "9092"

---
# dashboard-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: flight-dashboard
spec:
  replicas: 1
  selector:
    matchLabels:
      app: flight-dashboard
  template:
    metadata:
      labels:
        app: flight-dashboard
    spec:
      containers:
      - name: dashboard
        image: flight-dashboard:latest
        ports:
        - containerPort: 8501
        env:
        - name: KAFKA_HOST
          value: "kafka-broker"
        - name: KAFKA_PORT
          value: "9092"

---
# dashboard-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: flight-dashboard-service
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8501
  selector:
    app: flight-dashboard
```

**Deploy to Kubernetes:**
```bash
# Create namespace
kubectl create namespace flight-streaming

# Apply manifests
kubectl apply -f kubernetes/ -n flight-streaming

# Check deployment
kubectl get pods -n flight-streaming
kubectl get services -n flight-streaming
```

### Option C: Cloud Platform Deployment

#### AWS Deployment (EC2/ECS)

```bash
# 1. Create EC2 instance
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.large \
  --key-name my-key \
  --security-groups flight-streaming

# 2. SSH into instance
ssh -i my-key.pem ec2-user@<instance-ip>

# 3. Install dependencies
sudo yum update
sudo yum install docker
sudo usermod -a -G docker ec2-user

# 4. Clone and run
git clone <repo-url>
cd data-streaming-flights
./docker-compose up -d

# 5. Access dashboard
# http://<instance-ip>:8501
```

#### Google Cloud Deployment (Cloud Run)

```bash
# Build and push image
gcloud builds submit --tag gcr.io/PROJECT_ID/flight-dashboard
gcloud run deploy flight-dashboard \
  --image gcr.io/PROJECT_ID/flight-dashboard \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --timeout 3600
```

#### Azure Deployment (Container Instances)

```bash
# Create resource group
az group create --name flight-streaming --location eastus

# Deploy container
az container create \
  --resource-group flight-streaming \
  --name flight-dashboard \
  --image flight-dashboard:latest \
  --ports 8501 \
  --environment-variables KAFKA_HOST=kafka KAFKA_PORT=9092
```

---

## Part 4: Monitoring & Operations

### Health Checks

```bash
# Check all services are running
curl http://localhost:8501/_stcore/health  # Dashboard
docker exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092  # Kafka

# Check Spark (if running locally)
curl http://localhost:4040/api/v1/applications  # Spark UI
```

### Log Management

```bash
# Producer logs
docker logs kafka-producer

# Kafka logs  
docker logs kafka

# Dashboard logs
ps aux | grep streamlit  # Find process
tail -f /tmp/streamlit.log  # View logs

# Spark logs (if submitted)
tail -f spark-logs/
```

### Monitoring with Prometheus

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'kafka'
    static_configs:
      - targets: ['localhost:9308']
  
  - job_name: 'spark'
    static_configs:
      - targets: ['localhost:4040']
```

### Alerting Rules

```yaml
# alerts.yml
groups:
  - name: flight_streaming
    rules:
      - alert: KafkaDown
        expr: up{job="kafka"} == 0
        for: 1m
        
      - alert: NoMessagesInTopic
        expr: kafka_topic_partition_current_offset < 100
        for: 5m
```

---

## Part 5: Troubleshooting

### Dashboard Won't Start

**Error:** `ModuleNotFoundError: No module named 'streamlit'`

**Solution:**
```bash
pip install streamlit==1.28.1
# Or reinstall all dashboard requirements
pip install -r dashboard/requirements.txt
```

### Kafka Connection Error

**Error:** `KafkaError: Cannot connect to broker`

**Solution:**
```bash
# Check Kafka is running
docker-compose ps

# Check broker is accessible
docker exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092

# Restart Kafka if needed
docker-compose restart kafka
```

### No Data in Dashboard

**Steps to debug:**

1. **Check producer is running:**
```bash
ps aux | grep api_producer.py
# If not running, start it:
python producer/api_producer.py
```

2. **Check Kafka has data:**
```bash
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic flight-raw-data \
  --max-messages 5
```

3. **Check Spark is running:**
```bash
ps aux | grep spark
# If not running, restart it with command from Step 6 above
```

4. **Check Spark output topic:**
```bash
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic flight-processed-data \
  --max-messages 5
```

### Out of Memory

**Solution:**
```bash
# For Spark, increase memory:
spark-submit \
  --driver-memory 4g \
  --executor-memory 4g \
  spark_streaming/stream_processor.py

# For Dashboard, reduce buffer size (sidebar slider)
```

### Slow Dashboard Refresh

**Solution:**
1. Reduce data buffer size in sidebar
2. Increase refresh interval to 5-10 seconds
3. Reduce number of displayed records in tables
4. Check system resources: `top` or Task Manager

---

## Part 6: Scaling for Production

### Horizontal Scaling

**Multiple Producers:**
```bash
# Start second producer with different geolocation parameters
OPENSKY_LAMIN=45 OPENSKY_LAMAX=55 python producer/api_producer.py &
```

**Spark Cluster Mode:**
```bash
spark-submit \
  --master spark://spark-master:7077 \
  --total-executor-cores 8 \
  --executor-memory 4g \
  spark_streaming/stream_processor.py
```

**Multiple Dashboard Instances:**
```bash
# Use load balancer (nginx, HAProxy) in front
# Each dashboard instance behind LB
streamlit run dashboard/app.py --server.port 8501 &
streamlit run dashboard/app.py --server.port 8502 &
# Point LB to both ports
```

### Vertical Scaling

- **Increase Spark driver/executor memory**
- **Increase Kafka broker heap size**
- **Increase server CPU cores**
- **Use SSD storage for Kafka**

### Kafka Optimization

```yaml
# docker-compose.yml - production settings
environment:
  KAFKA_BROKER_RACK: rack1
  KAFKA_NUM_NETWORK_THREADS: 8
  KAFKA_NUM_IO_THREADS: 8
  KAFKA_SOCKET_SEND_BUFFER_BYTES: 102400
  KAFKA_SOCKET_RECEIVE_BUFFER_BYTES: 102400
  KAFKA_SOCKET_REQUEST_MAX_BYTES: 104857600
```

---

## Part 7: Backing Up & Restoring

### Kafka Data Backup

```bash
# Backup Kafka persistent volume
docker exec kafka sh -c 'tar -czf /tmp/kafka-backup.tar.gz /var/lib/kafka/data'
docker cp kafka:/tmp/kafka-backup.tar.gz ./kafka-backup.tar.gz

# Restore
tar -xzf kafka-backup.tar.gz -C /
```

### Model Backup

```bash
# Backup trained models
tar -czf models-backup.tar.gz models/
s3 cp models-backup.tar.gz s3://my-bucket/backups/  # Upload to cloud
```

### Configuration Backup

```bash
git add .
git commit -m "Production configuration backup"
git push origin main
```

---

## Part 8: Shutdown & Cleanup

### Stop All Services

```bash
# Stop Docker services
docker-compose down

# Kill Producer & Spark processes
pkill -f api_producer.py
pkill -f spark

# Stop Streamlit (find and kill process)
lsof -i :8501  # Find process
kill -9 <PID>

# Deactivate Python environment
deactivate
```

### Clean Up Resources

```bash
# Remove Docker containers & volumes
docker-compose down -v

# Remove Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Remove logs & temp files
rm -rf spark-logs/
rm -rf .streamlit/
```

---

## Summary Checklist

- ✅ Python 3.9+ installed
- ✅ Docker & Docker Compose running
- ✅ .env file configured with OpenSky credentials
- ✅ All dependencies installed (`pip install -r ...`)
- ✅ Kafka topics created and verified
- ✅ Producer running and publishing messages
- ✅ Spark streaming job running and processing
- ✅ Dashboard accessible at http://localhost:8501
- ✅ Integration tests passing
- ✅ Data flowing through all components

**Deployment Complete!** 🎉
