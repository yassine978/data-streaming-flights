"""
Main flight data producer application.
Fetches data from OpenSky API and publishes to Kafka topics.
"""

import json
import signal
import sys
import time
import logging
from typing import Optional

from kafka import KafkaProducer
from kafka.errors import KafkaError

from config import Config
from opensky_client import OpenSkyClient
from kafka_admin import create_topics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FlightDataValidator:
    """Validates flight data records before sending to Kafka."""

    @staticmethod
    def validate(flight: dict) -> tuple[bool, Optional[str]]:
        """
        Validate a flight record.

        Args:
            flight: Dictionary containing flight data

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Required field: icao24
        if not flight.get('icao24'):
            return False, "Missing icao24"

        # Validate coordinates (if present, must be in valid range)
        lat = flight.get('latitude')
        lon = flight.get('longitude')

        if lat is not None:
            if not isinstance(lat, (int, float)) or lat < -90 or lat > 90:
                return False, f"Invalid latitude: {lat}"

        if lon is not None:
            if not isinstance(lon, (int, float)) or lon < -180 or lon > 180:
                return False, f"Invalid longitude: {lon}"

        # Validate altitude (if present, must be reasonable)
        baro_alt = flight.get('baro_altitude')
        if baro_alt is not None:
            if not isinstance(baro_alt, (int, float)) or baro_alt < -1000 or baro_alt > 50000:
                return False, f"Invalid baro_altitude: {baro_alt}"

        # Validate velocity (if present, must be non-negative)
        velocity = flight.get('velocity')
        if velocity is not None:
            if not isinstance(velocity, (int, float)) or velocity < 0:
                return False, f"Invalid velocity: {velocity}"

        # Validate heading (if present, must be 0-360)
        heading = flight.get('heading')
        if heading is not None:
            if not isinstance(heading, (int, float)) or heading < 0 or heading > 360:
                return False, f"Invalid heading: {heading}"

        return True, None


class FlightProducer:
    """Main producer class that orchestrates data fetching and publishing."""

    def __init__(self):
        self.running = False
        self.opensky_client: Optional[OpenSkyClient] = None
        self.kafka_producer: Optional[KafkaProducer] = None
        self.validator = FlightDataValidator()

        # Statistics
        self.stats = {
            'total_fetched': 0,
            'valid_sent': 0,
            'invalid_sent': 0,
            'errors': 0
        }

    def _setup_signal_handlers(self):
        """Setup handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._shutdown_handler)
        signal.signal(signal.SIGTERM, self._shutdown_handler)

    def _shutdown_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info("Shutdown signal received, stopping...")
        self.running = False

    def _init_kafka_producer(self) -> bool:
        """Initialize the Kafka producer."""
        try:
            self.kafka_producer = KafkaProducer(
                bootstrap_servers=Config.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3,
                retry_backoff_ms=1000
            )
            logger.info("Kafka producer initialized")
            return True
        except KafkaError as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            return False

    def _send_to_kafka(self, topic: str, key: str, value: dict) -> bool:
        """
        Send a message to Kafka.

        Args:
            topic: Target Kafka topic
            key: Message key (icao24)
            value: Message value (flight data dict)

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            future = self.kafka_producer.send(topic, key=key, value=value)
            future.get(timeout=10)  # Wait for confirmation
            return True
        except KafkaError as e:
            logger.error(f"Failed to send message to {topic}: {e}")
            return False

    def _process_flights(self, states: list) -> None:
        """
        Process and route flight data to appropriate Kafka topics.

        Args:
            states: List of raw state vectors from OpenSky API
        """
        valid_count = 0
        invalid_count = 0

        for state in states:
            try:
                # Parse state vector to dictionary
                flight = self.opensky_client.parse_state_vector(state)
                self.stats['total_fetched'] += 1

                # Validate the flight data
                is_valid, error_msg = self.validator.validate(flight)

                if is_valid:
                    flight['data_valid'] = True
                    if self._send_to_kafka(Config.KAFKA_TOPIC_RAW, flight['icao24'], flight):
                        valid_count += 1
                        self.stats['valid_sent'] += 1
                else:
                    flight['data_valid'] = False
                    flight['validation_error'] = error_msg
                    if self._send_to_kafka(Config.KAFKA_TOPIC_INVALID, flight.get('icao24', 'unknown'), flight):
                        invalid_count += 1
                        self.stats['invalid_sent'] += 1

            except Exception as e:
                logger.error(f"Error processing flight: {e}")
                self.stats['errors'] += 1

        # Flush messages
        self.kafka_producer.flush()

        logger.info(f"Processed batch: {valid_count} valid, {invalid_count} invalid")

    def _print_stats(self):
        """Print current statistics."""
        logger.info(
            f"Stats - Total: {self.stats['total_fetched']}, "
            f"Valid: {self.stats['valid_sent']}, "
            f"Invalid: {self.stats['invalid_sent']}, "
            f"Errors: {self.stats['errors']}"
        )

    def run(self):
        """Main producer loop."""
        logger.info("Starting Flight Data Producer...")

        # Validate configuration
        if not Config.validate():
            logger.error("Configuration validation failed")
            sys.exit(1)

        # Setup signal handlers
        self._setup_signal_handlers()

        # Create Kafka topics
        logger.info("Creating Kafka topics...")
        if not create_topics():
            logger.error("Failed to create Kafka topics")
            sys.exit(1)

        # Initialize Kafka producer
        if not self._init_kafka_producer():
            logger.error("Failed to initialize Kafka producer")
            sys.exit(1)

        # Initialize OpenSky client
        self.opensky_client = OpenSkyClient()

        self.running = True
        logger.info(f"Producer running. Polling every {Config.POLLING_INTERVAL} seconds. Press Ctrl+C to stop.")

        while self.running:
            try:
                # Fetch flight data
                states = self.opensky_client.fetch_flights()

                if states:
                    self._process_flights(states)
                else:
                    logger.warning("No data received from API")

                # Print stats periodically
                self._print_stats()

                # Wait for next polling interval
                if self.running:
                    time.sleep(Config.POLLING_INTERVAL)

            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                self.stats['errors'] += 1
                time.sleep(5)  # Brief pause before retry

        # Cleanup
        self._cleanup()

    def _cleanup(self):
        """Clean up resources on shutdown."""
        logger.info("Cleaning up resources...")

        if self.kafka_producer:
            self.kafka_producer.flush()
            self.kafka_producer.close()
            logger.info("Kafka producer closed")

        if self.opensky_client:
            self.opensky_client.close()

        logger.info("Final stats:")
        self._print_stats()
        logger.info("Producer stopped.")


def main():
    """Entry point for the producer application."""
    producer = FlightProducer()
    producer.run()


if __name__ == '__main__':
    main()
