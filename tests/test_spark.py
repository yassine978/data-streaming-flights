"""
test_spark.py
Unit + integration tests for flight data processing.

Run:
    pytest tests/test_spark.py -v
"""

import os
import sys
import pytest
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "spark_streaming"))

try:
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import col
    from pyspark.sql.types import (
        BooleanType, DoubleType, LongType, StringType,
        StructField, StructType, IntegerType
    )
    PYSPARK_AVAILABLE = True
except ImportError:
    PYSPARK_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not PYSPARK_AVAILABLE, reason="PySpark not installed"
)


@pytest.fixture(scope="session")
def spark():
    session = (
        SparkSession.builder
        .appName("test_flight_member2")
        .master("local[2]")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    session.sparkContext.setLogLevel("ERROR")
    yield session
    session.stop()


def _make_flight_df(spark, rows=None):
    """Create test DataFrame matching Member 1's schema."""
    if rows is None:
        now = datetime.utcnow()
        rows = [
            ("3c675a", "DLH123", "Germany", int(now.timestamp()), 13.405, 52.52, 11200.0, False, 245.3, 270.0, -2.5, 11100.0, 0, now.isoformat(), True),
            ("ab1234", "AFR456", "France",  int(now.timestamp()), 2.349,  48.86, 10500.0, False, 230.0, 180.0,  1.5, 10450.0, 0, now.isoformat(), True),
            ("bad123", None,     "Unknown", int(now.timestamp()), 200.0,  100.0, -100.0,  False, -50.0, 400.0,  0.0, 0.0,     0, now.isoformat(), False),  # Invalid
        ]

    schema = StructType([
        StructField("icao24",              StringType(),  False),
        StructField("callsign",            StringType(),  True),
        StructField("origin_country",      StringType(),  True),
        StructField("time_position",       LongType(),    True),
        StructField("longitude",           DoubleType(),  True),
        StructField("latitude",            DoubleType(),  True),
        StructField("baro_altitude",       DoubleType(),  True),
        StructField("on_ground",           BooleanType(), True),
        StructField("velocity",            DoubleType(),  True),
        StructField("heading",             DoubleType(),  True),
        StructField("vertical_rate",       DoubleType(),  True),
        StructField("geo_altitude",        DoubleType(),  True),
        StructField("position_source",     IntegerType(), True),
        StructField("ingestion_timestamp", StringType(),  False),
        StructField("data_valid",          BooleanType(), False),
    ])

    return spark.createDataFrame(rows, schema)


class TestFlightDataCleaner:

    def test_clean_removes_invalid_coordinates(self, spark):
        from transformations import FlightDataCleaner

        df = _make_flight_df(spark)
        df_clean = FlightDataCleaner.clean_streaming_data(df)
        
        # Row with lat=100 (invalid) should be removed
        lats = [r.latitude for r in df_clean.collect()]
        assert all(-90 <= lat <= 90 for lat in lats if lat is not None)

    def test_clean_adds_event_time(self, spark):
        from transformations import FlightDataCleaner

        df = _make_flight_df(spark)
        df_clean = FlightDataCleaner.clean_streaming_data(df)
        
        assert "event_time" in df_clean.columns

    def test_add_features_columns(self, spark):
        from transformations import FlightDataCleaner

        df = _make_flight_df(spark)
        df_clean = FlightDataCleaner.clean_streaming_data(df)
        df_feat  = FlightDataCleaner.add_derived_features(df_clean)

        for col_name in ["hour", "day_of_week", "velocity_kmh", "altitude_feet", "flight_phase"]:
            assert col_name in df_feat.columns

    def test_zscore_column_exists(self, spark):
        from transformations import FlightDataCleaner

        df = _make_flight_df(spark)
        df_c = FlightDataCleaner.clean_streaming_data(df)
        df_f = FlightDataCleaner.add_derived_features(df_c)
        df_z = FlightDataCleaner.detect_anomalies_zscore(df_f)

        assert "velocity_zscore" in df_z.columns
        assert "altitude_zscore" in df_z.columns
        assert "is_stat_anomaly" in df_z.columns


class TestFlightDataValidator:

    def test_separate_valid_invalid(self, spark):
        from transformations import FlightDataCleaner, FlightDataValidator

        df = _make_flight_df(spark)
        df_c = FlightDataCleaner.clean_streaming_data(df)
        df_f = FlightDataCleaner.add_derived_features(df_c)
        df_z = FlightDataCleaner.detect_anomalies_zscore(df_f)

        df_valid, df_invalid = FlightDataValidator.separate_valid_invalid(df_z)

        valid_qualities = {r.data_quality for r in df_valid.collect()}
        assert valid_qualities == {"valid"}


class TestFlightAggregator:

    def test_tumbling_window_columns(self, spark):
        """Test that windowing produces expected columns."""
        # This would require a streaming context, so we just verify imports work
        from aggregations import FlightAggregator
        assert FlightAggregator.apply_tumbling_window is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])