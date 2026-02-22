import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class SparkConfig:

    # Auto-detect if running in Docker
    _in_docker = os.path.exists('/.dockerenv')

    # Kafka Configuration - use Docker network address if in container
    KAFKA_BOOTSTRAP_SERVERS = os.getenv(
        'KAFKA_BOOTSTRAP_SERVERS',
        'kafka_flights:29092' if _in_docker else 'localhost:9092'
    )

    KAFKA_TOPIC_INPUT       = os.getenv('KAFKA_TOPIC_INPUT',       'flight-raw-data')
    KAFKA_TOPIC_OUTPUT      = os.getenv('KAFKA_TOPIC_OUTPUT',      'flight-processed-data')
    KAFKA_TOPIC_AGGREGATED  = os.getenv('KAFKA_TOPIC_AGGREGATED',  'flight-aggregated-data')
    KAFKA_TOPIC_INVALID     = os.getenv('KAFKA_TOPIC_INVALID',     'flight-invalid-spark')

    # Spark Settings
    APP_NAME           = os.getenv('SPARK_APP_NAME', 'FlightStreamingApp')
    MASTER             = os.getenv('SPARK_MASTER', 'local[*]')
    DRIVER_MEMORY      = os.getenv('SPARK_DRIVER_MEMORY', '2g')
    EXECUTOR_MEMORY    = os.getenv('SPARK_EXECUTOR_MEMORY', '2g')
    SHUFFLE_PARTITIONS = int(os.getenv('SPARK_SHUFFLE_PARTITIONS', '8'))

    LOG_LEVEL = os.getenv('SPARK_LOG_LEVEL', 'WARN')

    # Checkpointing - use Docker path if in container
    if _in_docker:
        CHECKPOINT_LOCATION = os.getenv('CHECKPOINT_LOCATION', '/opt/checkpoints')
    else:
        CHECKPOINT_LOCATION = os.getenv('CHECKPOINT_LOCATION', './checkpoints')

    CHECKPOINT_PROCESSED  = os.path.join(CHECKPOINT_LOCATION, "processed")
    CHECKPOINT_AGGREGATED = os.path.join(CHECKPOINT_LOCATION, "aggregated")
    CHECKPOINT_INVALID    = os.path.join(CHECKPOINT_LOCATION, "invalid")

    # Streaming Windows
    TRIGGER_INTERVAL = os.getenv('TRIGGER_INTERVAL', '10 seconds')
    WATERMARK_DELAY  = os.getenv('WATERMARK_DELAY', '10 minutes')
    WINDOW_DURATION  = os.getenv('WINDOW_DURATION', '10 minutes')
    SLIDE_DURATION   = os.getenv('SLIDE_DURATION', '5 minutes')

    @classmethod
    def validate(cls):
        Path(cls.CHECKPOINT_LOCATION).mkdir(parents=True, exist_ok=True)
        return True
