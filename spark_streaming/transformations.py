"""
transformations.py — Task 2.2 (Flight Data)
Data cleaning, validation, and feature engineering for flight tracking.
"""

import logging
from typing import Tuple

from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    col, to_timestamp, current_timestamp, coalesce,
    hour, dayofweek, when, avg, stddev, 
    abs as spark_abs, isnan, isnull, lit, count,
    sin, cos, radians
)
from pyspark.sql.window import Window

logger = logging.getLogger(__name__)


class FlightDataCleaner:
    """Task 2.2 — Clean and validate flight tracking data."""

    @staticmethod
    def clean_streaming_data(df: DataFrame) -> DataFrame:
        """
        Clean flight data from Member 1's producer.
        
        Input schema (from Member 1):
            icao24, callsign, origin_country, time_position,
            longitude, latitude, baro_altitude, on_ground,
            velocity, heading, vertical_rate, geo_altitude,
            position_source, ingestion_timestamp, data_valid
        """
        logger.info("▶ FlightDataCleaner.clean_streaming_data")

        # 1. Parse ingestion timestamp
        df_clean = df.withColumn(
            "event_time",
            to_timestamp(col("ingestion_timestamp"))
        )

        # 2. Remove rows missing critical fields
        df_clean = df_clean.filter(
            col("icao24").isNotNull() &
            col("event_time").isNotNull()
        )

        # 3. Deduplicate on (icao24, time_position)
        df_clean = df_clean.dropDuplicates(["icao24", "time_position"])

        # 4. Fill missing numeric fields with safe defaults
        df_clean = (
            df_clean
            .withColumn("latitude",
                       when(col("latitude").isNull() | isnan(col("latitude")), lit(0.0))
                       .otherwise(col("latitude")))
            .withColumn("longitude",
                       when(col("longitude").isNull() | isnan(col("longitude")), lit(0.0))
                       .otherwise(col("longitude")))
            .withColumn("baro_altitude",
                       when(col("baro_altitude").isNull() | isnan(col("baro_altitude")), lit(0.0))
                       .otherwise(col("baro_altitude")))
            .withColumn("velocity",
                       when(col("velocity").isNull() | isnan(col("velocity")), lit(0.0))
                       .otherwise(col("velocity")))
            .withColumn("heading",
                       when(col("heading").isNull() | isnan(col("heading")), lit(0.0))
                       .otherwise(col("heading")))
            .withColumn("vertical_rate",
                       when(col("vertical_rate").isNull() | isnan(col("vertical_rate")), lit(0.0))
                       .otherwise(col("vertical_rate")))
        )

        # 5. Filter physically impossible values
        df_clean = df_clean.filter(
            (col("latitude") >= -90) & (col("latitude") <= 90) &
            (col("longitude") >= -180) & (col("longitude") <= 180) &
            (col("baro_altitude") >= -1000) & (col("baro_altitude") <= 50000) &
            (col("velocity") >= 0) & (col("velocity") <= 1000) &
            (col("heading") >= 0) & (col("heading") <= 360)
        )

        # 6. Add data quality flag
        df_clean = df_clean.withColumn(
            "data_quality",
            when(
                isnull(col("icao24")) |
                ((col("latitude") == 0) & (col("longitude") == 0)) |
                isnull(col("event_time")),
                lit("invalid")
            ).otherwise(lit("valid"))
        )

        logger.info("✅ FlightDataCleaner.clean_streaming_data — complete")
        return df_clean

    @staticmethod
    def add_derived_features(df: DataFrame) -> DataFrame:
        """Add flight-specific features for ML."""
        logger.info("▶ FlightDataCleaner.add_derived_features")

        df_enriched = (
            df
            # Basic time features
            .withColumn("processing_timestamp", current_timestamp())
            .withColumn("hour",        hour(col("event_time")))
            .withColumn("day_of_week", dayofweek(col("event_time")))
            .withColumn("is_weekend",
                       when(dayofweek(col("event_time")).isin([1, 7]), lit(True))
                       .otherwise(lit(False)))
            
            # Cyclic encoding (time)
            .withColumn("hour_sin", sin(radians(col("hour") * 360.0 / 24.0)))
            .withColumn("hour_cos", cos(radians(col("hour") * 360.0 / 24.0)))
            .withColumn("dow_sin",  sin(radians(col("day_of_week") * 360.0 / 7.0)))
            .withColumn("dow_cos",  cos(radians(col("day_of_week") * 360.0 / 7.0)))
            
            # Cyclic encoding (heading)
            .withColumn("heading_sin", sin(radians(col("heading"))))
            .withColumn("heading_cos", cos(radians(col("heading"))))
            
            # Speed conversions
            .withColumn("velocity_kmh",   col("velocity") * 3.6)
            .withColumn("velocity_knots", col("velocity") * 1.94384)
            
            # Altitude conversions
            .withColumn("altitude_feet",  col("baro_altitude") * 3.28084)
            .withColumn("flight_level",   (col("altitude_feet") / 100).cast("int"))
            
            # Flight phase estimation
            .withColumn(
                "flight_phase",
                when(col("on_ground"), lit("ground"))
                .when(col("baro_altitude") < 1000, lit("takeoff_landing"))
                .when(col("vertical_rate") > 5, lit("climbing"))
                .when(col("vertical_rate") < -5, lit("descending"))
                .otherwise(lit("cruise"))
            )
        )

        logger.info("✅ FlightDataCleaner.add_derived_features — complete")
        return df_enriched

    @staticmethod
    def detect_anomalies_zscore(df: DataFrame, 
                                 window_size: int = 100,
                                 threshold: float = 3.0) -> DataFrame:
        """Statistical anomaly detection for flight behavior."""
        logger.info("▶ FlightDataCleaner.detect_anomalies_zscore")

        # Window: per aircraft, ordered by time
        win = (
            Window
            .partitionBy("icao24")
            .orderBy(col("time_position"))
            .rowsBetween(-window_size, 0)
        )

        # Calculate rolling statistics
        df_stats = (
            df
            .withColumn("rolling_velocity_mean", avg("velocity").over(win))
            .withColumn("rolling_velocity_std",  stddev("velocity").over(win))
            .withColumn("rolling_altitude_mean", avg("baro_altitude").over(win))
            .withColumn("rolling_altitude_std",  stddev("baro_altitude").over(win))
            .withColumn("rolling_count", count("velocity").over(win))
        )

        # Calculate z-scores
        df_z = (
            df_stats
            .withColumn(
                "velocity_zscore",
                when(
                    isnull(col("rolling_velocity_std")) |
                    (col("rolling_velocity_std") == 0) |
                    (col("rolling_count") < 2),
                    lit(0.0)
                ).otherwise(
                    (col("velocity") - col("rolling_velocity_mean")) / 
                    col("rolling_velocity_std")
                )
            )
            .withColumn(
                "altitude_zscore",
                when(
                    isnull(col("rolling_altitude_std")) |
                    (col("rolling_altitude_std") == 0) |
                    (col("rolling_count") < 2),
                    lit(0.0)
                ).otherwise(
                    (col("baro_altitude") - col("rolling_altitude_mean")) /
                    col("rolling_altitude_std")
                )
            )
        )

        # Flag anomalies
        df_flagged = df_z.withColumn(
            "is_stat_anomaly",
            when(
                (spark_abs(col("velocity_zscore")) > threshold) |
                (spark_abs(col("altitude_zscore")) > threshold),
                lit(True)
            ).otherwise(lit(False))
        )

        logger.info("✅ FlightDataCleaner.detect_anomalies_zscore — complete")
        return df_flagged


class FlightDataValidator:
    """Route valid and invalid flight data."""

    @staticmethod
    def separate_valid_invalid(df: DataFrame) -> Tuple[DataFrame, DataFrame]:
        """Split on data_quality flag."""
        logger.info("▶ FlightDataValidator.separate_valid_invalid")
        
        df_valid   = df.filter(col("data_quality") == "valid")
        df_invalid = df.filter(col("data_quality") != "valid")
        
        logger.info("✅ FlightDataValidator.separate_valid_invalid — complete")
        return df_valid, df_invalid

    @staticmethod
    def write_invalid_to_kafka(df_invalid: DataFrame, config) -> object:
        """Stream invalid rows to Kafka."""
        logger.info(f"▶ Writing invalid data to: {config.KAFKA_TOPIC_INVALID}")

        query = (
            df_invalid
            .select(
                col("icao24"),
                col("callsign"),
                col("latitude"),
                col("longitude"),
                col("data_quality"),
                col("processing_timestamp")
            )
            .selectExpr(
                "CAST(icao24 AS STRING) AS key",
                "to_json(struct(*))  AS value"
            )
            .writeStream
            .format("kafka")
            .option("kafka.bootstrap.servers", config.KAFKA_BOOTSTRAP_SERVERS)
            .option("topic",                   config.KAFKA_TOPIC_INVALID)
            .option("checkpointLocation",      config.CHECKPOINT_INVALID)
            .outputMode("append")
            .trigger(processingTime=config.TRIGGER_INTERVAL)
            .start()
        )

        logger.info("✅ Invalid-data sink started")
        return query