"""
stream_processor.py
Tasks 2.1, 2.2, 2.3: Complete Spark Structured Streaming pipeline.

Run:
    spark-submit \\
        --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \\
        spark_streaming/stream_processor.py
"""

import logging
import sys
import os

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json,lit
from pyspark.sql.types import (
    DoubleType, LongType, StringType, BooleanType, IntegerType,
    StructField, StructType
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import SparkConfig
from transformations import FlightDataCleaner, FlightDataValidator
from aggregations import FlightAggregator
from ml_inference import FlightMLInference

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("FlightStreamProcessor")


# ═══════════════════════════════════════════════════════════════════════════
# Flight Data Schema
# ═══════════════════════════════════════════════════════════════════════════

FLIGHT_SCHEMA = StructType([
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


class FlightStreamProcessor:
    """Complete pipeline for flight data streaming."""

    def __init__(self):
        SparkConfig.validate()
        self.spark = self._build_spark_session()
        logger.info("✅ SparkSession created")

    def _build_spark_session(self) -> SparkSession:
        return (
            SparkSession.builder
            .appName(SparkConfig.APP_NAME)
            .master(SparkConfig.MASTER)
            .config("spark.driver.memory",   SparkConfig.DRIVER_MEMORY)
            .config("spark.executor.memory", SparkConfig.EXECUTOR_MEMORY)
            .config("spark.sql.shuffle.partitions", SparkConfig.SHUFFLE_PARTITIONS)
            .config(
                "spark.jars.packages",
                "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0"
            )
            .config(
                "spark.sql.streaming.checkpointLocation",
                SparkConfig.CHECKPOINT_LOCATION
            )
            .config("spark.sql.execution.arrow.pyspark.enabled", "true")
            .getOrCreate()
        )

    def read_from_kafka(self):
        """Read from Member 1's Kafka topic."""
        logger.info(f"▶ Connecting to Kafka: {SparkConfig.KAFKA_TOPIC_INPUT}")

        df = (
            self.spark.readStream
            .format("kafka")
            .option("kafka.bootstrap.servers", SparkConfig.KAFKA_BOOTSTRAP_SERVERS)
            .option("subscribe",               SparkConfig.KAFKA_TOPIC_INPUT)
            .option("startingOffsets",         "earliest")
            .option("failOnDataLoss",          "false")
            .load()
        )

        logger.info("✅ Connected to Kafka")
        return df

    def parse_json(self, df):
        """Parse Member 1's flight JSON format."""
        logger.info("▶ Parsing flight JSON")

        df_raw_str = (
            df
            .select(
                col("key").cast("string"),
                col("value").cast("string").alias("value_str"),
                col("timestamp").alias("kafka_timestamp"),
            )
        )

        df_parsed = df_raw_str.select(
            col("key"),
            from_json(col("value_str"), FLIGHT_SCHEMA).alias("flight"),
            col("kafka_timestamp"),
        )

        df_flat = df_parsed.select(
            col("key"),
            col("flight.icao24"),
            col("flight.callsign"),
            col("flight.origin_country"),
            col("flight.time_position"),
            col("flight.longitude"),
            col("flight.latitude"),
            col("flight.baro_altitude"),
            col("flight.on_ground"),
            col("flight.velocity"),
            col("flight.heading"),
            col("flight.vertical_rate"),
            col("flight.geo_altitude"),
            col("flight.position_source"),
            col("flight.ingestion_timestamp"),
            col("flight.data_valid"),
            col("kafka_timestamp"),
        )

        logger.info("✅ JSON parsed")
        return df_flat

    def run_complete_pipeline(self):
        """Wire all stages and launch streaming queries."""
        logger.info("🚀 Starting complete flight streaming pipeline")

        # ── Read & Parse ────────────────────────────────────────────────
        df_raw    = self.read_from_kafka()
        df_parsed = self.parse_json(df_raw)

        # ── Task 2.2: Cleaning + Features + Z-score ────────────────────
        df_clean    = FlightDataCleaner.clean_streaming_data(df_parsed)
        df_features = FlightDataCleaner.add_derived_features(df_clean)
        df_z        = FlightDataCleaner.detect_anomalies_zscore(df_features)

        # ── Route valid/invalid ─────────────────────────────────────────
        df_valid, df_invalid = FlightDataValidator.separate_valid_invalid(df_z)

        # ── Task 2.3: ML predictions ────────────────────────────────────
        df_ml = FlightMLInference.apply_ml_predictions(df_valid)

        # ── Task 2.3: Windows + Trends ──────────────────────────────────
        df_windows = FlightAggregator.apply_tumbling_window(df_ml)
        df_trends = df_windows.withColumn("trend_summary", lit("not_calculated"))


        # ── Output 1: Processed events → Kafka ─────────────────────────
        processed_cols = [
            "icao24", "callsign", "origin_country", "event_time",
            "latitude", "longitude", "baro_altitude", "velocity",
            "heading", "vertical_rate", "on_ground",
            "velocity_kmh", "altitude_feet", "flight_phase",
            "hour", "day_of_week", "is_weekend",
            "is_stat_anomaly", "velocity_zscore", "altitude_zscore",
            "ml_anomaly_score", "ml_is_anomaly", "ml_anomaly_reason",
            "data_quality", "processing_timestamp",
        ]

        q_processed = (
            df_ml
            .select(*processed_cols)
            .selectExpr(
                "CAST(icao24 AS STRING) AS key",
                "to_json(struct(*)) AS value"
            )
            .writeStream
            .format("kafka")
            .option("kafka.bootstrap.servers", SparkConfig.KAFKA_BOOTSTRAP_SERVERS)
            .option("topic",                   SparkConfig.KAFKA_TOPIC_OUTPUT)
            .option("checkpointLocation",      SparkConfig.CHECKPOINT_PROCESSED)
            .outputMode("append")
            .trigger(processingTime=SparkConfig.TRIGGER_INTERVAL)
            .start()
        )
        logger.info("✅ Q1 — processed-data sink started")

        # ── Output 2: Aggregated windows → Kafka ───────────────────────
        q_aggregated = (
            df_trends
            .selectExpr(
                "CAST(icao24 AS STRING) AS key",
                "to_json(struct(*)) AS value"
            )
            .writeStream
            .format("kafka")
            .option("kafka.bootstrap.servers", SparkConfig.KAFKA_BOOTSTRAP_SERVERS)
            .option("topic",                   SparkConfig.KAFKA_TOPIC_AGGREGATED)
            .option("checkpointLocation",      SparkConfig.CHECKPOINT_AGGREGATED)
            .outputMode("update")
            .trigger(processingTime=SparkConfig.TRIGGER_INTERVAL)
            .start()
        )
        logger.info("✅ Q2 — aggregated-data sink started")

        # ── Output 3: Invalid rows → Kafka ─────────────────────────────
        q_invalid = FlightDataValidator.write_invalid_to_kafka(df_invalid, SparkConfig)
        logger.info("✅ Q3 — invalid-data sink started")

        # ── Output 4: Console monitoring ────────────────────────────────
        q_console = (
            df_ml
            .select(
                "icao24", "callsign", "event_time",
                "velocity", "baro_altitude", "flight_phase",
                "is_stat_anomaly", "ml_is_anomaly"
            )
            .writeStream
            .outputMode("append")
            .format("console")
            .option("truncate", False)
            .option("numRows", 10)
            .trigger(processingTime=SparkConfig.TRIGGER_INTERVAL)
            .start()
        )
        logger.info("✅ Q4 — console monitoring started")

        logger.info("📡 All queries running. Spark UI → http://localhost:4040")

        try:
            q_aggregated.awaitTermination()
        except KeyboardInterrupt:
            logger.info("🛑 Shutdown requested")
        finally:
            for q in [q_processed, q_aggregated, q_invalid, q_console]:
                try:
                    q.stop()
                except Exception:
                    pass
            self.spark.stop()
            logger.info("✅ Stopped. Goodbye.")

if __name__ == "__main__":
    # Check if model exists
    model_path = os.path.join(os.path.dirname(__file__), "models", "flight_anomaly_detector.pkl")
    
    if not os.path.exists(model_path):
        print("Model not found!")
        print(f"Expected: {model_path}")
        print("\n Please run this first:")
        print(" cd ..\\models")
        print("python train_model.py")
        print("cd ..\\spark_streaming")
        sys.exit(1)

    processor = FlightStreamProcessor()
    processor.run_complete_pipeline()