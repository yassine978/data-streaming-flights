"""
Kafka consumer for consuming real-time flight data.
Provides interface to fetch processed and aggregated flight data from Kafka.
"""

import json
import logging
from typing import List, Tuple, Optional
from kafka import KafkaConsumer
from kafka.errors import KafkaError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DashboardKafkaConsumer:
    """Kafka consumer for real-time dashboard data."""

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        processed_topic: str = "flight-processed-data",
        aggregated_topic: str = "flight-aggregated-data",
        timeout_ms: int = 2000
    ):
        """
        Initialize Kafka consumers for dashboard.

        Args:
            bootstrap_servers: Kafka bootstrap servers
            processed_topic: Topic for processed flight events
            aggregated_topic: Topic for aggregated windowed data
            timeout_ms: Consumer timeout in milliseconds
        """
        self.processed_topic = processed_topic
        self.aggregated_topic = aggregated_topic

        try:
            # Consumer for processed data (with ML predictions)
            self.consumer_processed = KafkaConsumer(
                processed_topic,
                bootstrap_servers=bootstrap_servers,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="latest",
                enable_auto_commit=True,
                group_id="dashboard-group-processed",
                consumer_timeout_ms=timeout_ms,
                session_timeout_ms=30000
            )
            logger.info(f"✅ Connected to processed topic: {processed_topic}")
        except Exception as e:
            logger.error(f"Failed to connect to processed topic: {e}")
            self.consumer_processed = None

        try:
            # Consumer for aggregated data (windowed metrics)
            self.consumer_aggregated = KafkaConsumer(
                aggregated_topic,
                bootstrap_servers=bootstrap_servers,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="latest",
                enable_auto_commit=True,
                group_id="dashboard-group-aggregated",
                consumer_timeout_ms=timeout_ms,
                session_timeout_ms=30000
            )
            logger.info(f"✅ Connected to aggregated topic: {aggregated_topic}")
        except Exception as e:
            logger.error(f"Failed to connect to aggregated topic: {e}")
            self.consumer_aggregated = None

    def fetch_processed_data(self, max_records: int = 100) -> List[dict]:
        """
        Fetch latest processed flight events.

        Args:
            max_records: Maximum number of records to fetch

        Returns:
            List of processed flight events with ML predictions
        """
        if not self.consumer_processed:
            return []

        messages = []
        try:
            for message in self.consumer_processed:
                try:
                    data = message.value
                    # Handle nested JSON structure
                    if isinstance(data, dict) and "value" in data:
                        if isinstance(data["value"], str):
                            data = json.loads(data["value"])
                    messages.append(data)
                    if len(messages) >= max_records:
                        break
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON: {e}")
                    continue
        except KafkaError as e:
            logger.warning(f"Kafka error: {e}")

        return messages

    def fetch_aggregated_data(self, max_records: int = 50) -> List[dict]:
        """
        Fetch latest aggregated windowed metrics.

        Args:
            max_records: Maximum number of records to fetch

        Returns:
            List of aggregated window metrics
        """
        if not self.consumer_aggregated:
            return []

        messages = []
        try:
            for message in self.consumer_aggregated:
                try:
                    data = message.value
                    # Handle nested JSON structure
                    if isinstance(data, dict) and "value" in data:
                        if isinstance(data["value"], str):
                            data = json.loads(data["value"])
                    messages.append(data)
                    if len(messages) >= max_records:
                        break
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON: {e}")
                    continue
        except KafkaError as e:
            logger.warning(f"Kafka error: {e}")

        return messages

    def fetch_both(
        self,
        processed_limit: int = 100,
        aggregated_limit: int = 50
    ) -> Tuple[List[dict], List[dict]]:
        """
        Fetch both processed and aggregated data in one call.

        Returns:
            Tuple of (processed_data, aggregated_data)
        """
        processed = self.fetch_processed_data(processed_limit)
        aggregated = self.fetch_aggregated_data(aggregated_limit)
        return processed, aggregated

    def close(self):
        """Close Kafka consumers."""
        if self.consumer_processed:
            self.consumer_processed.close()
        if self.consumer_aggregated:
            self.consumer_aggregated.close()
        logger.info("Kafka consumers closed")
