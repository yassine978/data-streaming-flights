"""
OpenSky Network API client with OAuth2 authentication.
Handles token management, data fetching, and error handling.
"""

import time
import logging
from datetime import datetime, timezone
from typing import Optional

import requests

from config import Config, StateVectorIndex

logger = logging.getLogger(__name__)


class OpenSkyClient:
    """Client for interacting with the OpenSky Network API."""

    def __init__(self):
        self.access_token: Optional[str] = None
        self.token_expiry: float = 0
        self.session = requests.Session()

    def _get_token(self) -> bool:
        """
        Obtain a new access token using client credentials.
        Returns True if successful, False otherwise.
        """
        try:
            response = self.session.post(
                Config.OPENSKY_TOKEN_URL,
                data={
                    'grant_type': 'client_credentials',
                    'client_id': Config.OPENSKY_CLIENT_ID,
                    'client_secret': Config.OPENSKY_CLIENT_SECRET
                },
                timeout=30
            )

            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                expires_in = token_data.get('expires_in', 1800)  # Default 30 min
                self.token_expiry = time.time() + expires_in
                logger.info(f"Token obtained, expires in {expires_in} seconds")
                return True
            else:
                logger.error(f"Token request failed: {response.status_code} - {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Token request error: {e}")
            return False

    def _ensure_valid_token(self) -> bool:
        """
        Ensure we have a valid token, refreshing if necessary.
        Returns True if we have a valid token, False otherwise.
        """
        # Check if token needs refresh (with buffer)
        if self.access_token is None or time.time() >= (self.token_expiry - Config.TOKEN_REFRESH_BUFFER):
            logger.info("Token expired or expiring soon, refreshing...")
            return self._get_token()
        return True

    def fetch_flights(self) -> Optional[list]:
        """
        Fetch current flight data from OpenSky API.
        Returns a list of raw state vectors, or None on error.
        """
        if not self._ensure_valid_token():
            logger.error("Failed to obtain valid token")
            return None

        try:
            headers = {'Authorization': f'Bearer {self.access_token}'}
            params = Config.get_bbox_params()

            response = self.session.get(
                Config.OPENSKY_API_URL,
                headers=headers,
                params=params,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                states = data.get('states', [])
                logger.info(f"Fetched {len(states)} flights from API")
                return states

            elif response.status_code == 401:
                logger.warning("Token expired, refreshing...")
                self.access_token = None
                return self.fetch_flights()  # Retry with new token

            elif response.status_code == 429:
                logger.warning("Rate limited by API, waiting...")
                time.sleep(60)
                return None

            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.Timeout:
            logger.error("API request timed out")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"API request error: {e}")
            return None

    def parse_state_vector(self, state: list) -> dict:
        """
        Parse a raw state vector array into a structured dictionary.

        Args:
            state: A 17-element array from the OpenSky API

        Returns:
            Dictionary with named fields matching the schema for Member 2
        """
        ingestion_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

        # Safely extract callsign and strip whitespace
        callsign = state[StateVectorIndex.CALLSIGN]
        if callsign:
            callsign = callsign.strip()

        return {
            'icao24': state[StateVectorIndex.ICAO24],
            'callsign': callsign,
            'origin_country': state[StateVectorIndex.ORIGIN_COUNTRY],
            'time_position': state[StateVectorIndex.TIME_POSITION],
            'longitude': state[StateVectorIndex.LONGITUDE],
            'latitude': state[StateVectorIndex.LATITUDE],
            'baro_altitude': state[StateVectorIndex.BARO_ALTITUDE],
            'on_ground': state[StateVectorIndex.ON_GROUND],
            'velocity': state[StateVectorIndex.VELOCITY],
            'heading': state[StateVectorIndex.TRUE_TRACK],
            'vertical_rate': state[StateVectorIndex.VERTICAL_RATE],
            'geo_altitude': state[StateVectorIndex.GEO_ALTITUDE],
            'position_source': state[StateVectorIndex.POSITION_SOURCE],
            'ingestion_timestamp': ingestion_time,
            'data_valid': True  # Will be set by validator
        }

    def close(self):
        """Close the HTTP session."""
        self.session.close()
        logger.info("OpenSky client session closed")
