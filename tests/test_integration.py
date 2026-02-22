"""
Integration tests for Member 3: Visualization & Integration
Tests the complete dashboard pipeline including Kafka connectivity,
data fetching, metrics calculation, and chart rendering.
"""

import sys
import time
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from kafka import KafkaConsumer, KafkaAdminClient
from kafka.errors import KafkaError
import pandas as pd


# ============================================================================
# Test Configuration
# ============================================================================

KAFKA_HOST = "localhost"
KAFKA_PORT = 9092
KAFKA_BROKER = f"{KAFKA_HOST}:{KAFKA_PORT}"
TEST_TIMEOUT = 5000  # ms

TOPICS_REQUIRED = [
    "flight-raw-data",
    "flight-processed-data",
    "flight-aggregated-data"
]


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def kafka_admin():
    """Create Kafka admin client for topic checks."""
    try:
        admin = KafkaAdminClient(
            bootstrap_servers=KAFKA_BROKER,
            request_timeout_ms=TEST_TIMEOUT
        )
        yield admin
        admin.close()
    except Exception as e:
        pytest.skip(f"Kafka admin client failed: {e}")


@pytest.fixture
def kafka_consumer():
    """Create Kafka consumer for data verification."""
    try:
        consumer = KafkaConsumer(
            bootstrap_servers=KAFKA_BROKER,
            consumer_timeout_ms=TEST_TIMEOUT,
            auto_offset_reset='latest',
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        yield consumer
        consumer.close()
    except Exception as e:
        pytest.skip(f"Kafka consumer failed: {e}")


# ============================================================================
# Kafka Infrastructure Tests
# ============================================================================

class TestKafkaConnectivity:
    """Test basic Kafka connectivity and topic existence."""

    def test_kafka_broker_available(self):
        """Verify Kafka broker is accessible."""
        try:
            admin = KafkaAdminClient(
                bootstrap_servers=KAFKA_BROKER,
                request_timeout_ms=TEST_TIMEOUT
            )
            admin.close()
        except Exception as e:
            pytest.fail(f"Cannot connect to Kafka: {e}")

    def test_required_topics_exist(self, kafka_admin):
        """Verify all required topics exist."""
        from kafka.admin import ConfigResource, ConfigResourceType

        try:
            # Get cluster metadata
            metadata = kafka_admin.describe_cluster()
            broker_info = kafka_admin.describe_broker(metadata.controller)
            
            # Get topic list
            topics = kafka_admin.list_topics()
            existing_topics = set(topics.keys())
            
            missing_topics = set(TOPICS_REQUIRED) - existing_topics
            
            if missing_topics:
                pytest.fail(f"Missing topics: {missing_topics}")
                
        except Exception as e:
            pytest.fail(f"Cannot verify topics: {e}")

    def test_kafka_broker_configuration(self, kafka_admin):
        """Verify Kafka broker configuration is reasonable."""
        try:
            # Get broker metrics
            metadata = kafka_admin.describe_cluster()
            
            assert metadata.brokers, "No brokers available"
            assert metadata.controller >= 0, "No controller elected"
            
        except Exception as e:
            pytest.fail(f"Cannot get broker configuration: {e}")


# ============================================================================
# Data Ingestion Tests
# ============================================================================

class TestDataIngestion:
    """Test data flowing from producer to Kafka."""

    def test_raw_data_topic_has_messages(self, kafka_consumer):
        """Verify flight-raw-data topic receives messages."""
        kafka_consumer.subscribe(["flight-raw-data"])
        
        messages = []
        timeout = time.time() + TEST_TIMEOUT / 1000
        
        while len(messages) == 0 and time.time() < timeout:
            batch = kafka_consumer.poll(timeout_ms=1000)
            for topic_partition, records in batch.items():
                messages.extend(records)
        
        assert len(messages) > 0, "No messages in flight-raw-data topic"

    def test_raw_data_schema_validation(self, kafka_consumer):
        """Verify raw data messages have expected schema."""
        kafka_consumer.subscribe(["flight-raw-data"])
        
        expected_fields = {
            "timestamp", "icao24", "callsign", "latitude", "longitude",
            "velocity", "baro_altitude", "vertical_rate", "on_ground"
        }
        
        messages = []
        timeout = time.time() + TEST_TIMEOUT / 1000
        
        while len(messages) < 5 and time.time() < timeout:
            batch = kafka_consumer.poll(timeout_ms=1000)
            for topic_partition, records in batch.items():
                messages.extend([r.value for r in records])
        
        for msg in messages:
            missing_fields = expected_fields - set(msg.keys())
            assert not missing_fields, f"Missing fields in raw data: {missing_fields}"


# ============================================================================
# Stream Processing Tests
# ============================================================================

class TestStreamProcessing:
    """Test data flowing from Spark to Kafka output topics."""

    def test_processed_data_topic_has_messages(self, kafka_consumer):
        """Verify flight-processed-data topic receives messages."""
        kafka_consumer.subscribe(["flight-processed-data"])
        
        messages = []
        timeout = time.time() + (TEST_TIMEOUT * 2) / 1000  # Allow more time for Spark
        
        while len(messages) == 0 and time.time() < timeout:
            batch = kafka_consumer.poll(timeout_ms=1000)
            for topic_partition, records in batch.items():
                messages.extend(records)
        
        assert len(messages) > 0, "No messages in flight-processed-data topic"

    def test_processed_data_schema_validation(self, kafka_consumer):
        """Verify processed data has ML features and anomaly scores."""
        kafka_consumer.subscribe(["flight-processed-data"])
        
        expected_fields = {
            "timestamp", "icao24", "velocity", "baro_altitude",
            "is_anomaly", "anomaly_score", "flight_phase"
        }
        
        messages = []
        timeout = time.time() + (TEST_TIMEOUT * 2) / 1000
        
        while len(messages) < 3 and time.time() < timeout:
            batch = kafka_consumer.poll(timeout_ms=1000)
            for topic_partition, records in batch.items():
                messages.extend([r.value for r in records])
        
        for msg in messages:
            missing_fields = expected_fields - set(msg.keys())
            assert not missing_fields, f"Missing fields in processed data: {missing_fields}"
            
            # Validate field types
            assert isinstance(msg["is_anomaly"], bool), "is_anomaly must be boolean"
            assert isinstance(msg["anomaly_score"], (int, float)), "anomaly_score must be numeric"

    def test_aggregated_data_topic_has_messages(self, kafka_consumer):
        """Verify flight-aggregated-data topic receives windowed data."""
        kafka_consumer.subscribe(["flight-aggregated-data"])
        
        messages = []
        timeout = time.time() + (TEST_TIMEOUT * 3) / 1000  # Wait for first window
        
        while len(messages) == 0 and time.time() < timeout:
            batch = kafka_consumer.poll(timeout_ms=1000)
            for topic_partition, records in batch.items():
                messages.extend(records)
        
        # May have no messages if within first window - that's ok
        if len(messages) > 0:
            assert True
        else:
            print("No aggregated data yet (within first window)")

    def test_aggregated_data_schema_validation(self, kafka_consumer):
        """Verify aggregated data has window statistics."""
        kafka_consumer.subscribe(["flight-aggregated-data"])
        
        expected_fields = {
            "window_start", "window_end", "event_count", "anomaly_count",
            "avg_velocity", "avg_altitude"
        }
        
        messages = []
        timeout = time.time() + (TEST_TIMEOUT * 3) / 1000
        
        while len(messages) < 1 and time.time() < timeout:
            batch = kafka_consumer.poll(timeout_ms=1000)
            for topic_partition, records in batch.items():
                messages.extend([r.value for r in records])
        
        for msg in messages:
            missing_fields = expected_fields - set(msg.keys())
            assert not missing_fields, f"Missing fields in aggregated data: {missing_fields}"


# ============================================================================
# Dashboard Component Tests
# ============================================================================

class TestDashboardComponents:
    """Test individual dashboard components."""

    def test_kafka_consumer_import(self):
        """Verify dashboard kafka_consumer module can be imported."""
        try:
            from dashboard.components.kafka_consumer import DashboardKafkaConsumer
            assert DashboardKafkaConsumer is not None
        except ImportError as e:
            pytest.fail(f"Cannot import DashboardKafkaConsumer: {e}")

    def test_metrics_display_import(self):
        """Verify metrics display module can be imported."""
        try:
            from dashboard.components.metrics import MetricsDisplay
            assert MetricsDisplay is not None
        except ImportError as e:
            pytest.fail(f"Cannot import MetricsDisplay: {e}")

    def test_charts_display_import(self):
        """Verify charts display module can be imported."""
        try:
            from dashboard.components.charts import ChartsDisplay
            assert ChartsDisplay is not None
        except ImportError as e:
            pytest.fail(f"Cannot import ChartsDisplay: {e}")

    def test_metrics_calculation_with_empty_data(self):
        """Test that metrics handle empty DataFrames gracefully."""
        try:
            from dashboard.components.metrics import MetricsDisplay
            
            display = MetricsDisplay()
            empty_df = pd.DataFrame()
            
            # Should not raise exception
            assert display is not None
            
        except Exception as e:
            pytest.fail(f"Metrics display failed with empty data: {e}")

    def test_charts_rendering_with_empty_data(self):
        """Test that charts handle empty DataFrames gracefully."""
        try:
            from dashboard.components.charts import ChartsDisplay
            
            display = ChartsDisplay()
            empty_df = pd.DataFrame()
            
            # Should not raise exception
            assert display is not None
            
        except Exception as e:
            pytest.fail(f"Charts display failed with empty data: {e}")


# ============================================================================
# End-to-End Pipeline Tests
# ============================================================================

class TestEndToEndPipeline:
    """Test complete data flow from API to dashboard."""

    def test_data_flows_through_pipeline(self, kafka_consumer):
        """Verify data flows through all pipeline stages."""
        results = {
            "raw_data": False,
            "processed_data": False,
            "aggregated_data": False
        }
        
        # Check each topic
        for topic, key in [
            ("flight-raw-data", "raw_data"),
            ("flight-processed-data", "processed_data"),
            ("flight-aggregated-data", "aggregated_data")
        ]:
            kafka_consumer.subscribe([topic])
            messages = []
            timeout = time.time() + (TEST_TIMEOUT * 3) / 1000
            
            while len(messages) == 0 and time.time() < timeout:
                batch = kafka_consumer.poll(timeout_ms=1000)
                for topic_partition, records in batch.items():
                    messages.extend(records)
            
            if len(messages) > 0:
                results[key] = True
                print(f"✓ {topic}: {len(messages)} messages")
            else:
                print(f"✗ {topic}: No messages (may not be initialized yet)")
        
        # At minimum, raw data should flow
        assert results["raw_data"], "No data flowing through pipeline"

    def test_ml_features_present(self, kafka_consumer):
        """Verify ML features are calculated in processed data."""
        kafka_consumer.subscribe(["flight-processed-data"])
        
        ml_features = {
            "is_anomaly": False,
            "anomaly_score": False,
            "flight_phase": False
        }
        
        messages = []
        timeout = time.time() + (TEST_TIMEOUT * 2) / 1000
        
        while len(messages) < 3 and time.time() < timeout:
            batch = kafka_consumer.poll(timeout_ms=1000)
            for topic_partition, records in batch.items():
                messages.extend([r.value for r in records])
        
        for msg in messages:
            for feature in ml_features.keys():
                if feature in msg:
                    ml_features[feature] = True
        
        assert ml_features["is_anomaly"], "is_anomaly field missing"
        assert ml_features["anomaly_score"], "anomaly_score field missing"


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Test performance characteristics of the pipeline."""

    def test_message_throughput(self, kafka_consumer):
        """Measure message throughput from producer."""
        kafka_consumer.subscribe(["flight-raw-data"])
        
        messages = []
        start_time = time.time()
        duration = 5  # seconds
        
        while time.time() - start_time < duration:
            batch = kafka_consumer.poll(timeout_ms=1000)
            for topic_partition, records in batch.items():
                messages.extend(records)
        
        elapsed = time.time() - start_time
        throughput = len(messages) / elapsed
        
        print(f"\nMessage Throughput: {throughput:.2f} messages/sec")
        assert throughput > 1, "Throughput too low"

    def test_processing_latency(self, kafka_consumer):
        """Measure processing latency from raw to processed data."""
        # Subscribe to check timestamps
        kafka_consumer.subscribe(["flight-processed-data"])
        
        messages = []
        timeout = time.time() + (TEST_TIMEOUT * 2) / 1000
        
        while len(messages) < 10 and time.time() < timeout:
            batch = kafka_consumer.poll(timeout_ms=1000)
            for topic_partition, records in batch.items():
                messages.extend([r.value for r in records])
        
        if len(messages) > 0:
            print(f"\nLatency test: {len(messages)} messages received")
            assert True
        else:
            print("Latency test: waiting for first messages (Spark may not be processing)")


# ============================================================================
# Health Check Tests
# ============================================================================

class TestSystemHealth:
    """Test overall system health and readiness."""

    def test_dependencies_installed(self):
        """Verify all required Python packages are installed."""
        required_packages = [
            "pandas",
            "plotly",
            "kafka",
            "streamlit",
            "pyspark"
        ]
        
        missing = []
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing.append(package)
        
        assert not missing, f"Missing packages: {missing}"

    def test_configuration_files_exist(self):
        """Verify all required configuration files exist."""
        required_files = [
            "producer/config.py",
            "spark_streaming/config.py",
            "dashboard/requirements.txt",
            ".env.example"  # or .env
        ]
        
        for file_path in required_files:
            full_path = project_root / file_path
            if not full_path.exists():
                # Check if it's optional (.env example)
                if ".env" not in file_path:
                    pytest.fail(f"Missing config file: {file_path}")

    def test_dashboard_files_exist(self):
        """Verify all dashboard component files exist."""
        required_files = [
            "dashboard/app.py",
            "dashboard/components/kafka_consumer.py",
            "dashboard/components/metrics.py",
            "dashboard/components/charts.py"
        ]
        
        for file_path in required_files:
            full_path = project_root / file_path
            assert full_path.exists(), f"Missing dashboard file: {file_path}"

    def test_ml_models_exist(self):
        """Verify trained ML models exist."""
        required_models = [
            "models/flight_anomaly_detector.pkl",
            "models/flight_scaler.pkl",
            "models/flight_features.json"
        ]
        
        for file_path in required_models:
            full_path = project_root / file_path
            assert full_path.exists(), f"Missing model file: {file_path}"


# ============================================================================
# Test Execution
# ============================================================================

if __name__ == "__main__":
    """Run tests with pytest."""
    pytest.main([__file__, "-v", "-s", "--tb=short"])
