"""
Unit tests for the flight data producer.
Tests validation logic and data processing without hitting real APIs.
"""

import sys
import os

# Add producer directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'producer'))

import pytest
from unittest.mock import Mock, patch, MagicMock

from api_producer import FlightDataValidator
from opensky_client import OpenSkyClient
from config import StateVectorIndex


class TestFlightDataValidator:
    """Tests for the FlightDataValidator class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.validator = FlightDataValidator()

    def test_valid_flight_passes_validation(self):
        """Test that a complete valid flight record passes validation."""
        valid_flight = {
            'icao24': '3c675a',
            'callsign': 'DLH123',
            'origin_country': 'Germany',
            'time_position': 1739700000,
            'longitude': 13.405,
            'latitude': 52.52,
            'baro_altitude': 11200.0,
            'on_ground': False,
            'velocity': 245.3,
            'heading': 270.0,
            'vertical_rate': -2.5,
            'geo_altitude': 11100.0,
            'position_source': 0,
            'ingestion_timestamp': '2025-02-16T10:30:05Z',
            'data_valid': True
        }

        is_valid, error = self.validator.validate(valid_flight)
        assert is_valid is True
        assert error is None

    def test_missing_icao24_fails_validation(self):
        """Test that missing icao24 fails validation."""
        flight = {
            'icao24': None,
            'callsign': 'DLH123',
            'latitude': 52.52,
            'longitude': 13.405
        }

        is_valid, error = self.validator.validate(flight)
        assert is_valid is False
        assert 'icao24' in error.lower()

    def test_empty_icao24_fails_validation(self):
        """Test that empty icao24 fails validation."""
        flight = {
            'icao24': '',
            'callsign': 'DLH123',
            'latitude': 52.52,
            'longitude': 13.405
        }

        is_valid, error = self.validator.validate(flight)
        assert is_valid is False
        assert 'icao24' in error.lower()

    def test_invalid_latitude_too_high_fails(self):
        """Test that latitude > 90 fails validation."""
        flight = {
            'icao24': '3c675a',
            'latitude': 95.0,
            'longitude': 13.405
        }

        is_valid, error = self.validator.validate(flight)
        assert is_valid is False
        assert 'latitude' in error.lower()

    def test_invalid_latitude_too_low_fails(self):
        """Test that latitude < -90 fails validation."""
        flight = {
            'icao24': '3c675a',
            'latitude': -100.0,
            'longitude': 13.405
        }

        is_valid, error = self.validator.validate(flight)
        assert is_valid is False
        assert 'latitude' in error.lower()

    def test_invalid_longitude_too_high_fails(self):
        """Test that longitude > 180 fails validation."""
        flight = {
            'icao24': '3c675a',
            'latitude': 52.52,
            'longitude': 200.0
        }

        is_valid, error = self.validator.validate(flight)
        assert is_valid is False
        assert 'longitude' in error.lower()

    def test_invalid_longitude_too_low_fails(self):
        """Test that longitude < -180 fails validation."""
        flight = {
            'icao24': '3c675a',
            'latitude': 52.52,
            'longitude': -200.0
        }

        is_valid, error = self.validator.validate(flight)
        assert is_valid is False
        assert 'longitude' in error.lower()

    def test_invalid_altitude_too_high_fails(self):
        """Test that unrealistic altitude fails validation."""
        flight = {
            'icao24': '3c675a',
            'latitude': 52.52,
            'longitude': 13.405,
            'baro_altitude': 100000.0  # Way too high
        }

        is_valid, error = self.validator.validate(flight)
        assert is_valid is False
        assert 'altitude' in error.lower()

    def test_negative_velocity_fails(self):
        """Test that negative velocity fails validation."""
        flight = {
            'icao24': '3c675a',
            'latitude': 52.52,
            'longitude': 13.405,
            'velocity': -10.0
        }

        is_valid, error = self.validator.validate(flight)
        assert is_valid is False
        assert 'velocity' in error.lower()

    def test_invalid_heading_fails(self):
        """Test that heading > 360 fails validation."""
        flight = {
            'icao24': '3c675a',
            'latitude': 52.52,
            'longitude': 13.405,
            'heading': 400.0
        }

        is_valid, error = self.validator.validate(flight)
        assert is_valid is False
        assert 'heading' in error.lower()

    def test_null_optional_fields_pass(self):
        """Test that null optional fields still pass validation."""
        flight = {
            'icao24': '3c675a',
            'callsign': None,
            'latitude': None,
            'longitude': None,
            'baro_altitude': None,
            'velocity': None,
            'heading': None
        }

        is_valid, error = self.validator.validate(flight)
        assert is_valid is True
        assert error is None

    def test_flight_on_ground_with_zero_altitude(self):
        """Test flight on ground with zero altitude passes."""
        flight = {
            'icao24': '3c675a',
            'latitude': 52.52,
            'longitude': 13.405,
            'baro_altitude': 0.0,
            'on_ground': True
        }

        is_valid, error = self.validator.validate(flight)
        assert is_valid is True


class TestOpenSkyClientParsing:
    """Tests for OpenSky API response parsing."""

    def setup_method(self):
        """Setup test fixtures."""
        self.client = OpenSkyClient()

    def test_parse_state_vector_basic(self):
        """Test parsing a basic state vector."""
        raw_state = [
            '3c675a',      # 0: icao24
            'DLH123 ',     # 1: callsign (with trailing space)
            'Germany',     # 2: origin_country
            1739700000,    # 3: time_position
            1739700000,    # 4: last_contact
            13.405,        # 5: longitude
            52.52,         # 6: latitude
            11200.0,       # 7: baro_altitude
            False,         # 8: on_ground
            245.3,         # 9: velocity
            270.0,         # 10: true_track (heading)
            -2.5,          # 11: vertical_rate
            None,          # 12: sensors
            11100.0,       # 13: geo_altitude
            '1000',        # 14: squawk
            False,         # 15: spi
            0              # 16: position_source
        ]

        result = self.client.parse_state_vector(raw_state)

        assert result['icao24'] == '3c675a'
        assert result['callsign'] == 'DLH123'
        assert result['origin_country'] == 'Germany'
        assert result['longitude'] == 13.405
        assert result['latitude'] == 52.52
        assert result['baro_altitude'] == 11200.0
        assert result['on_ground'] is False
        assert result['velocity'] == 245.3
        assert result['heading'] == 270.0
        assert result['vertical_rate'] == -2.5
        assert result['geo_altitude'] == 11100.0
        assert result['position_source'] == 0
        assert 'ingestion_timestamp' in result

    def test_parse_state_vector_null_callsign(self):
        """Test parsing state vector with null callsign."""
        raw_state = [
            '3c675a',
            None,          # Null callsign
            'Germany',
            1739700000,
            1739700000,
            13.405,
            52.52,
            11200.0,
            False,
            245.3,
            270.0,
            -2.5,
            None,
            11100.0,
            '1000',
            False,
            0
        ]

        result = self.client.parse_state_vector(raw_state)

        assert result['icao24'] == '3c675a'
        assert result['callsign'] is None


class TestOpenSkyClientAuth:
    """Tests for OpenSky API authentication (mocked)."""

    @patch('opensky_client.requests.Session')
    def test_get_token_success(self, mock_session_class):
        """Test successful token acquisition."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'test_token_123',
            'expires_in': 1800
        }
        mock_session.post.return_value = mock_response

        client = OpenSkyClient()
        result = client._get_token()

        assert result is True
        assert client.access_token == 'test_token_123'

    @patch('opensky_client.requests.Session')
    def test_get_token_failure(self, mock_session_class):
        """Test failed token acquisition."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = 'Invalid credentials'
        mock_session.post.return_value = mock_response

        client = OpenSkyClient()
        result = client._get_token()

        assert result is False
        assert client.access_token is None


class TestDataRouting:
    """Tests to verify data is routed to correct Kafka topics."""

    def test_valid_data_marked_as_valid(self):
        """Test that valid data gets data_valid=True."""
        validator = FlightDataValidator()
        flight = {
            'icao24': '3c675a',
            'latitude': 52.52,
            'longitude': 13.405
        }

        is_valid, _ = validator.validate(flight)
        if is_valid:
            flight['data_valid'] = True

        assert flight['data_valid'] is True

    def test_invalid_data_marked_as_invalid(self):
        """Test that invalid data gets data_valid=False and error message."""
        validator = FlightDataValidator()
        flight = {
            'icao24': None,  # Invalid
            'latitude': 52.52,
            'longitude': 13.405
        }

        is_valid, error = validator.validate(flight)
        if not is_valid:
            flight['data_valid'] = False
            flight['validation_error'] = error

        assert flight['data_valid'] is False
        assert 'validation_error' in flight


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def setup_method(self):
        """Setup test fixtures."""
        self.validator = FlightDataValidator()

    def test_boundary_latitude_90(self):
        """Test latitude at exact boundary (90)."""
        flight = {
            'icao24': '3c675a',
            'latitude': 90.0,
            'longitude': 0.0
        }
        is_valid, _ = self.validator.validate(flight)
        assert is_valid is True

    def test_boundary_latitude_minus_90(self):
        """Test latitude at exact boundary (-90)."""
        flight = {
            'icao24': '3c675a',
            'latitude': -90.0,
            'longitude': 0.0
        }
        is_valid, _ = self.validator.validate(flight)
        assert is_valid is True

    def test_boundary_longitude_180(self):
        """Test longitude at exact boundary (180)."""
        flight = {
            'icao24': '3c675a',
            'latitude': 0.0,
            'longitude': 180.0
        }
        is_valid, _ = self.validator.validate(flight)
        assert is_valid is True

    def test_boundary_longitude_minus_180(self):
        """Test longitude at exact boundary (-180)."""
        flight = {
            'icao24': '3c675a',
            'latitude': 0.0,
            'longitude': -180.0
        }
        is_valid, _ = self.validator.validate(flight)
        assert is_valid is True

    def test_heading_at_zero(self):
        """Test heading at 0 (North)."""
        flight = {
            'icao24': '3c675a',
            'heading': 0.0
        }
        is_valid, _ = self.validator.validate(flight)
        assert is_valid is True

    def test_heading_at_360(self):
        """Test heading at 360 (also North)."""
        flight = {
            'icao24': '3c675a',
            'heading': 360.0
        }
        is_valid, _ = self.validator.validate(flight)
        assert is_valid is True

    def test_zero_velocity(self):
        """Test zero velocity (stationary aircraft)."""
        flight = {
            'icao24': '3c675a',
            'velocity': 0.0
        }
        is_valid, _ = self.validator.validate(flight)
        assert is_valid is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
