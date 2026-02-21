"""
create_topics.py
Creates output Kafka topics for flight processed/aggregated data.

Usage:
    python spark_streaming/create_topics.py
"""

from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("create_topics")

BOOTSTRAP_SERVERS = "localhost:9092"

TOPICS = [
    NewTopic(name="flight-processed-data",   num_partitions=3, replication_factor=1),
    NewTopic(name="flight-aggregated-data",  num_partitions=3, replication_factor=1),
    NewTopic(name="flight-invalid-spark",    num_partitions=1, replication_factor=1),
]


def main():
    client = KafkaAdminClient(bootstrap_servers=BOOTSTRAP_SERVERS)

    for topic in TOPICS:
        try:
            client.create_topics([topic], validate_only=False)
            logger.info(f"✅ Created topic: {topic.name}")
        except TopicAlreadyExistsError:
            logger.info(f"ℹ️  Topic already exists: {topic.name}")
        except Exception as e:
            logger.error(f"❌ Failed to create topic {topic.name}: {e}")

    logger.info("\nAll topics:")
    for t in client.list_topics():
        logger.info(f"   • {t}")

    client.close()


if __name__ == "__main__":
    main()