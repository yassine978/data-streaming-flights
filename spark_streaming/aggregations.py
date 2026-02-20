"""
aggregations.py
Windowed aggregations for aircraft behavior analysis.
"""

import logging
from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    col, window, count, avg, max as spark_max, min as spark_min,
    stddev, sum as spark_sum, when, lag, lit, first, last
)
from pyspark.sql.window import Window

from config import SparkConfig

logger = logging.getLogger(__name__)


class FlightAggregator:
    """Task 2.3 — Windowed aggregations for flight data."""

    @staticmethod
    def apply_tumbling_window(df: DataFrame) -> DataFrame:
        """
        10-minute tumbling windows per aircraft.

        Aggregates flight behavior metrics for each aircraft.
        """
        logger.info("▶ FlightAggregator.apply_tumbling_window")

        df_windowed = (
            df
            .withWatermark("event_time", SparkConfig.WATERMARK_DELAY)
            .groupBy(
                window(col("event_time"), SparkConfig.WINDOW_DURATION),
                col("icao24")
            )
            .agg(
                # Basic counts
                count("*")                      .alias("flight_events"),

                # Velocity statistics
                avg("velocity")                 .alias("avg_velocity"),
                spark_max("velocity")           .alias("max_velocity"),
                spark_min("velocity")           .alias("min_velocity"),
                stddev("velocity")              .alias("velocity_variance"),

                # Altitude statistics
                avg("baro_altitude")            .alias("avg_altitude"),
                spark_max("baro_altitude")      .alias("max_altitude"),
                spark_min("baro_altitude")      .alias("min_altitude"),
                stddev("baro_altitude")         .alias("altitude_variance"),

                # Vertical rate
                avg("vertical_rate")            .alias("avg_vertical_rate"),
                spark_max("vertical_rate")      .alias("max_climb_rate"),
                spark_min("vertical_rate")      .alias("max_descent_rate"),

                # Anomaly tracking
                spark_sum(
                    when(col("is_stat_anomaly"), 1).otherwise(0)
                )                               .alias("anomaly_count"),

                # Flight info
                first("callsign")               .alias("callsign"),
                first("origin_country")         .alias("origin_country"),
                first("on_ground")              .alias("start_on_ground"),
                last("on_ground")               .alias("end_on_ground"),

                # Position tracking
                first("latitude")               .alias("start_latitude"),
                first("longitude")              .alias("start_longitude"),
                last("latitude")                .alias("end_latitude"),
                last("longitude")               .alias("end_longitude")
            )
        )

        # Flatten window struct
        df_final = (
            df_windowed
            .select(
                col("window.start").alias("window_start"),
                col("window.end")  .alias("window_end"),
                col("icao24"),
                col("callsign"),
                col("origin_country"),
                col("flight_events"),
                col("avg_velocity"),
                col("max_velocity"),
                col("min_velocity"),
                col("velocity_variance"),
                col("avg_altitude"),
                col("max_altitude"),
                col("min_altitude"),
                col("altitude_variance"),
                col("avg_vertical_rate"),
                col("max_climb_rate"),
                col("max_descent_rate"),
                col("anomaly_count"),
                col("start_on_ground"),
                col("end_on_ground"),
                col("start_latitude"),
                col("start_longitude"),
                col("end_latitude"),
                col("end_longitude")
            )
            # Add computed metrics
            .withColumn(
                "anomaly_rate",
                when(col("flight_events") > 0,
                     col("anomaly_count") / col("flight_events") * 100)
                .otherwise(lit(0.0))
            )
            .withColumn(
                "altitude_change",
                col("max_altitude") - col("min_altitude")
            )
            .withColumn(
                "velocity_range",
                col("max_velocity") - col("min_velocity")
            )
            .withColumn(
                "flight_behavior",
                when(col("start_on_ground") & col(
                    "end_on_ground"), lit("stationary"))
                .when(col("start_on_ground"), lit("takeoff"))
                .when(col("end_on_ground"), lit("landing"))
                .when(col("altitude_variance") < 100, lit("stable_cruise"))
                .otherwise(lit("maneuvering"))
            )
        )

        logger.info("✅ FlightAggregator.apply_tumbling_window — complete")
        return df_final

    @staticmethod
    def calculate_trends(df_windowed: DataFrame) -> DataFrame:
        """
        Calculate flight behavior trends across windows.
        """
        logger.info("▶ FlightAggregator.calculate_trends")

        win = (
            Window
            .partitionBy("icao24")
            .orderBy("window_start")
        )

        df_trends = (
            df_windowed
            # Previous window comparison
            .withColumn("prev_avg_velocity", lag("avg_velocity", 1).over(win))
            .withColumn("prev_avg_altitude", lag("avg_altitude", 1).over(win))

            # Calculate changes
            .withColumn(
                "velocity_change",
                col("avg_velocity") - col("prev_avg_velocity")
            )
            .withColumn(
                "altitude_change_from_prev",
                col("avg_altitude") - col("prev_avg_altitude")
            )

            # Velocity trend
            .withColumn(
                "velocity_trend",
                when(col("prev_avg_velocity").isNull(), lit("no_history"))
                .when(col("velocity_change") > 10, lit("accelerating"))
                .when(col("velocity_change") < -10, lit("decelerating"))
                .otherwise(lit("stable_speed"))
            )

            # Altitude trend
            .withColumn(
                "altitude_trend",
                when(col("prev_avg_altitude").isNull(), lit("no_history"))
                .when(col("altitude_change_from_prev") > 500, lit("climbing"))
                .when(col("altitude_change_from_prev") < -500, lit("descending"))
                .otherwise(lit("stable_altitude"))
            )

            # Final trend summary
            .withColumn(
                "trend_summary",
                when(col("velocity_trend") == "no_history",
                     lit("initial_observation"))
                .when(
                    (col("velocity_trend") == "stable_speed") &
                    (col("altitude_trend") == "stable_altitude"),
                    lit("stable_flight")
                )
                .when(col("altitude_trend") == "climbing", lit("ascending"))
                .when(col("altitude_trend") == "descending", lit("descending"))
                .otherwise(lit("maneuvering"))
            )
        )

        logger.info("✅ FlightAggregator.calculate_trends — complete")
        return df_trends
