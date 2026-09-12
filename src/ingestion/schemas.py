"""
Explicit PySpark schemas for each event domain, matching event_contracts.md.

Bronze ingestion uses these instead of Spark's schema inference. Inference
requires an extra pass over the data (slow) and, more importantly, fails
silently when a field is missing or a type doesn't match - exactly the
kind of problem a Bronze layer should surface loudly, not hide.
"""

from pyspark.sql.types import (
    StructType, StructField, StringType, LongType, DoubleType, MapType,
)

# Fields shared by every event domain (the envelope from common.py).
_ENVELOPE_FIELDS = [
    StructField("event_id", StringType(), nullable=True),  # nullable: null_id_rate corruption
    StructField("event_type", StringType(), nullable=False),
    StructField("event_timestamp", StringType(), nullable=False),
    StructField("schema_version", StringType(), nullable=False),
    StructField("user_id", StringType(), nullable=True),   # nullable: null_id_rate corruption
    StructField("device_id", StringType(), nullable=True), # legitimately nullable (manual entry)
    StructField("ingested_at", StringType(), nullable=True),
]

WORKOUT_SCHEMA = StructType(_ENVELOPE_FIELDS + [
    StructField("workout_id", StringType(), nullable=True),
    StructField("workout_type", StringType(), nullable=True),
    StructField("duration_seconds", LongType(), nullable=True),
])

HEART_RATE_SCHEMA = StructType(_ENVELOPE_FIELDS + [
    StructField("workout_id", StringType(), nullable=True),
    StructField("bpm", LongType(), nullable=True),
])

DAILY_ACTIVITY_SCHEMA = StructType(_ENVELOPE_FIELDS + [
    StructField("activity_date", StringType(), nullable=True),
    StructField("steps", LongType(), nullable=True),
    StructField("active_calories", LongType(), nullable=True),
    StructField("distance_meters", DoubleType(), nullable=True),
    StructField("active_minutes", LongType(), nullable=True),
])

SLEEP_SCHEMA = StructType(_ENVELOPE_FIELDS + [
    StructField("sleep_session_id", StringType(), nullable=True),
    StructField("sleep_start", StringType(), nullable=True),
    StructField("sleep_end", StringType(), nullable=True),
    StructField("sleep_stages", MapType(StringType(), LongType()), nullable=True),
    StructField("resting_heart_rate", LongType(), nullable=True),
    StructField("hrv_ms", DoubleType(), nullable=True),
])

SCHEMAS = {
    "workouts": WORKOUT_SCHEMA,
    "heart_rate": HEART_RATE_SCHEMA,
    "daily_activity": DAILY_ACTIVITY_SCHEMA,
    "sleep": SLEEP_SCHEMA,
}