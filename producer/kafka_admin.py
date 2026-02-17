"""
Kafka administration utilities.
Creates and manages Kafka topics for the flight data pipeline.
"""

import logging
import time

from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError, NoBrokersAvailable

from config import Config

logger = logging.getLogger(__name__)


def create_topics(max_retries: int = 5, retry_delay: int = 5) -> bool:
    """
    Create the required Kafka topics.

    Args:
        max_retries: Maximum number of connection attempts
        retry_delay: Seconds to wait between retries

    Returns:
        True if topics are ready, False on failure
    """
    admin_client = None

    for attempt in range(max_retries):
        try:
            logger.info(f"Connecting to Kafka (attempt {attempt + 1}/{max_retries})...")

            admin_client = KafkaAdminClient(
                bootstrap_servers=Config.KAFKA_BOOTSTRAP_SERVERS,
                client_id='flight-admin'
            )

            # Get existing topics
            existing_topics = admin_client.list_topics()
            logger.info(f"Existing topics: {existing_topics}")

            # Prepare topics to create
            topics_to_create = []

            for topic_name, topic_config in Config.TOPIC_CONFIG.items():
                if topic_name not in existing_topics:
                    topics_to_create.append(NewTopic(
                        name=topic_name,
                        num_partitions=topic_config['num_partitions'],
                        replication_factor=topic_config['replication_factor']
                    ))
                    logger.info(f"Will create topic: {topic_name}")
                else:
                    logger.info(f"Topic already exists: {topic_name}")

            # Create new topics
            if topics_to_create:
                try:
                    admin_client.create_topics(
                        new_topics=topics_to_create,
                        validate_only=False
                    )
                    logger.info(f"Created {len(topics_to_create)} topic(s)")
                except TopicAlreadyExistsError:
                    logger.info("Topics already exist (race condition handled)")

            # Verify all topics exist
            final_topics = admin_client.list_topics()
            required_topics = set(Config.TOPIC_CONFIG.keys())

            if required_topics.issubset(set(final_topics)):
                logger.info("All required topics are ready")
                return True
            else:
                missing = required_topics - set(final_topics)
                logger.error(f"Missing topics: {missing}")
                return False

        except NoBrokersAvailable:
            logger.warning(f"Kafka not available, retrying in {retry_delay}s...")
            time.sleep(retry_delay)

        except Exception as e:
            logger.error(f"Error creating topics: {e}")
            time.sleep(retry_delay)

        finally:
            if admin_client:
                admin_client.close()

    logger.error("Failed to create topics after all retries")
    return False


def delete_topics() -> bool:
    """
    Delete the Kafka topics (useful for testing/cleanup).

    Returns:
        True if successful, False otherwise
    """
    try:
        admin_client = KafkaAdminClient(
            bootstrap_servers=Config.KAFKA_BOOTSTRAP_SERVERS,
            client_id='flight-admin'
        )

        topics_to_delete = list(Config.TOPIC_CONFIG.keys())
        existing_topics = admin_client.list_topics()

        topics_to_actually_delete = [t for t in topics_to_delete if t in existing_topics]

        if topics_to_actually_delete:
            admin_client.delete_topics(topics_to_actually_delete)
            logger.info(f"Deleted topics: {topics_to_actually_delete}")
        else:
            logger.info("No topics to delete")

        admin_client.close()
        return True

    except Exception as e:
        logger.error(f"Error deleting topics: {e}")
        return False


if __name__ == '__main__':
    # Setup logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("Creating Kafka topics...")
    if create_topics():
        print("Topics created successfully!")
    else:
        print("Failed to create topics. Is Kafka running?")
        exit(1)
