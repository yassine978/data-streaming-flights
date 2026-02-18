"""
Spark Structured Streaming configuration.
Adapted for flight data from Member 1's producer.
"""

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Running inside Docker without dotenv


class SparkConfig:
    """Spark Structured Streaming configuration"""

    # Kafka Configuration
    # Inside Docker: kafka_flights:29092 | Local: localhost:9092
    KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka_flights:29092')
    KAFKA_TOPIC_INPUT = os.getenv('KAFKA_TOPIC_INPUT', 'flight-raw-data')
    KAFKA_TOPIC_OUTPUT = os.getenv('KAFKA_TOPIC_OUTPUT', 'flight-processed-data')
    KAFKA_TOPIC_AGGREGATED = os.getenv('KAFKA_TOPIC_AGGREGATED', 'flight-aggregated-data')

    # Spark Settings
    APP_NAME = os.getenv('SPARK_APP_NAME', 'FlightStreamingApp')
    CHECKPOINT_LOCATION = os.getenv('CHECKPOINT_LOCATION', '/tmp/spark-checkpoints')

    # Processing Settings
    TRIGGER_INTERVAL = os.getenv('TRIGGER_INTERVAL', '10 seconds')
    WATERMARK_DELAY = os.getenv('WATERMARK_DELAY', '10 minutes')
    WINDOW_DURATION = os.getenv('WINDOW_DURATION', '10 minutes')
    SLIDE_DURATION = os.getenv('SLIDE_DURATION', '5 minutes')
