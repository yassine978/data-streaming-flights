"""
Configuration management for the flight data producer.
Loads settings from environment variables using python-dotenv.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Central configuration class for the producer application."""

    # OpenSky API Configuration
    OPENSKY_CLIENT_ID = os.getenv('OPENSKY_CLIENT_ID')
    OPENSKY_CLIENT_SECRET = os.getenv('OPENSKY_CLIENT_SECRET')
    OPENSKY_TOKEN_URL = 'https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token'
    OPENSKY_API_URL = 'https://opensky-network.org/api/states/all'

    # Bounding box for Europe
    BBOX_LAMIN = float(os.getenv('BBOX_LAMIN', 35.0))
    BBOX_LAMAX = float(os.getenv('BBOX_LAMAX', 72.0))
    BBOX_LOMIN = float(os.getenv('BBOX_LOMIN', -10.0))
    BBOX_LOMAX = float(os.getenv('BBOX_LOMAX', 40.0))

    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    KAFKA_TOPIC_RAW = os.getenv('KAFKA_TOPIC_RAW', 'flight-raw-data')
    KAFKA_TOPIC_INVALID = os.getenv('KAFKA_TOPIC_INVALID', 'flight-invalid-data')

    # Producer Settings
    POLLING_INTERVAL = int(os.getenv('POLLING_INTERVAL', 15))
    TOKEN_REFRESH_BUFFER = 300  # Refresh token 5 minutes before expiry

    # Kafka Topic Configuration
    TOPIC_CONFIG = {
        KAFKA_TOPIC_RAW: {
            'num_partitions': 3,
            'replication_factor': 1
        },
        KAFKA_TOPIC_INVALID: {
            'num_partitions': 1,
            'replication_factor': 1
        }
    }

    @classmethod
    def validate(cls) -> bool:
        """Validate that all required configuration is present."""
        required = [
            ('OPENSKY_CLIENT_ID', cls.OPENSKY_CLIENT_ID),
            ('OPENSKY_CLIENT_SECRET', cls.OPENSKY_CLIENT_SECRET),
        ]

        missing = [name for name, value in required if not value]

        if missing:
            print(f"Missing required configuration: {', '.join(missing)}")
            print("Please ensure your .env file contains all required variables.")
            return False

        return True

    @classmethod
    def get_bbox_params(cls) -> dict:
        """Return bounding box parameters for API request."""
        return {
            'lamin': cls.BBOX_LAMIN,
            'lamax': cls.BBOX_LAMAX,
            'lomin': cls.BBOX_LOMIN,
            'lomax': cls.BBOX_LOMAX
        }


# State vector field indices (from OpenSky API documentation)
class StateVectorIndex:
    """Indices for the state vector array returned by OpenSky API."""
    ICAO24 = 0
    CALLSIGN = 1
    ORIGIN_COUNTRY = 2
    TIME_POSITION = 3
    LAST_CONTACT = 4
    LONGITUDE = 5
    LATITUDE = 6
    BARO_ALTITUDE = 7
    ON_GROUND = 8
    VELOCITY = 9
    TRUE_TRACK = 10
    VERTICAL_RATE = 11
    SENSORS = 12
    GEO_ALTITUDE = 13
    SQUAWK = 14
    SPI = 15
    POSITION_SOURCE = 16
