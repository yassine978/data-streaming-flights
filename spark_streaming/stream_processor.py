"""
Spark Structured Streaming processor for flight data.
Reads from Kafka (Member 1's producer), parses JSON, and outputs to console.
Task 2.1: Basic Spark setup and Kafka connection.
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, to_timestamp
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType,
    BooleanType, LongType, IntegerType
)
import logging

from config import SparkConfig

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Flight data schema matching Member 1's Kafka messages
FLIGHT_SCHEMA = StructType([
    StructField("icao24", StringType(), False),
    StructField("callsign", StringType(), True),
    StructField("origin_country", StringType(), True),
    StructField("time_position", LongType(), True),
    StructField("longitude", DoubleType(), True),
    StructField("latitude", DoubleType(), True),
    StructField("baro_altitude", DoubleType(), True),
    StructField("on_ground", BooleanType(), True),
    StructField("velocity", DoubleType(), True),
    StructField("heading", DoubleType(), True),
    StructField("vertical_rate", DoubleType(), True),
    StructField("geo_altitude", DoubleType(), True),
    StructField("position_source", IntegerType(), True),
    StructField("ingestion_timestamp", StringType(), False),
    StructField("data_valid", BooleanType(), False)
])


class StreamProcessor:
    """Main Spark Structured Streaming processor for flight data."""

    def __init__(self):
        self.spark = SparkSession.builder \
            .appName(SparkConfig.APP_NAME) \
            .config("spark.jars.packages",
                    "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
            .config("spark.sql.streaming.checkpointLocation",
                    SparkConfig.CHECKPOINT_LOCATION) \
            .getOrCreate()

        self.spark.sparkContext.setLogLevel("WARN")
        logger.info("Spark session created")

    def read_from_kafka(self):
        """Read streaming data from Kafka flight-raw-data topic."""
        logger.info(f"Reading from Kafka topic: {SparkConfig.KAFKA_TOPIC_INPUT}")

        df = self.spark.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", SparkConfig.KAFKA_BOOTSTRAP_SERVERS) \
            .option("subscribe", SparkConfig.KAFKA_TOPIC_INPUT) \
            .option("startingOffsets", "earliest") \
            .load()

        logger.info("Connected to Kafka")
        return df

    def parse_json(self, df):
        """Parse flight JSON from Kafka value using Member 1's schema."""
        # Convert Kafka value from bytes to string, then parse JSON
        df_string = df.select(
            col("key").cast("string").alias("aircraft_id"),
            col("value").cast("string").alias("value_str"),
            col("timestamp").alias("kafka_timestamp")
        )

        # Parse JSON using flight schema
        df_parsed = df_string.select(
            col("aircraft_id"),
            from_json(col("value_str"), FLIGHT_SCHEMA).alias("flight"),
            col("kafka_timestamp")
        )

        # Flatten the structure
        df_flattened = df_parsed.select(
            col("aircraft_id"),
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
            to_timestamp(col("flight.ingestion_timestamp")).alias("ingestion_time"),
            col("flight.data_valid"),
            col("kafka_timestamp")
        )

        logger.info("JSON parsed successfully")
        return df_flattened

    def run_basic_pipeline(self):
        """Run basic streaming pipeline - read, parse, display to console."""
        # Read from Kafka
        df_raw = self.read_from_kafka()

        # Parse JSON
        df_parsed = self.parse_json(df_raw)

        # Write to console for verification
        query = df_parsed \
            .select(
                "icao24", "callsign", "origin_country",
                "latitude", "longitude", "baro_altitude",
                "velocity", "heading", "on_ground",
                "ingestion_time"
            ) \
            .writeStream \
            .outputMode("append") \
            .format("console") \
            .option("truncate", False) \
            .option("numRows", 20) \
            .trigger(processingTime=SparkConfig.TRIGGER_INTERVAL) \
            .start()

        logger.info("Streaming query started - displaying flight data to console")
        logger.info("Spark UI available at http://localhost:4040")
        query.awaitTermination()

    def stop(self):
        """Stop the Spark session."""
        self.spark.stop()
        logger.info("Spark session stopped")


if __name__ == "__main__":
    processor = StreamProcessor()
    processor.run_basic_pipeline()
