"""
Core Bronze ingestion logic: read raw JSON from S3, add ingestion metadata,
and MERGE into a Delta table.

One generic function serves all four event domains (workouts, heart_rate,
daily_activity, sleep) - unlike the generator, where each domain needed
genuinely different generation logic, ingestion logic here is identical
across domains. Only the schema and path differ, so those become parameters
rather than a reason to duplicate this function four times.

MERGE key is (event_id, source_file), not event_id alone - this makes
Bronze idempotent at the FILE level (safe to re-run ingestion on the same
source file without creating duplicate rows) while deliberately preserving
duplicate event_ids that originate WITHIN the same file (the corruption
pipeline's inject_duplicates scenario). Those in-file duplicates are left
for Silver to catch, per the project's stated dedup-in-Silver requirement.
"""

import uuid
from datetime import datetime, timezone

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import input_file_name, current_timestamp, lit, regexp_extract
from delta.tables import DeltaTable

from src.ingestion.config import IngestionConfig


def read_raw_domain(spark: SparkSession, domain: str, schema, config: IngestionConfig) -> DataFrame:
    """Read all JSON Lines files for a domain from the raw/ zone, using an explicit schema."""
    path = f"{config.raw_root}/{domain}/"
    df = spark.read.schema(schema).json(path)
    return df


def add_ingestion_metadata(df: DataFrame, run_id: str, source_version: str) -> DataFrame:
    """
    Add Bronze ingestion metadata columns, per the project's engineering
    requirements: ingestion timestamp, source file, pipeline run ID, and
    schema version (schema_version already exists per-event from the
    generator; source_version here refers to this ingestion code's version).
    """
    return (
        df
        .withColumn("_ingestion_timestamp", current_timestamp())
        .withColumn("_source_file", input_file_name())
        .withColumn(
            "source_file",
            regexp_extract("_source_file", r"([^/]+\.json)$", 1),
        )
        .drop("_source_file")
        .withColumn("_pipeline_run_id", lit(run_id))
        .withColumn("_ingestion_code_version", lit(source_version))
    )


def merge_into_bronze(df: DataFrame, spark: SparkSession, domain: str, config: IngestionConfig) -> dict:
    """
    MERGE the enriched dataframe into the domain's Bronze Delta table,
    keyed on (event_id, source_file) for file-level idempotency.
    Creates the table on first run if it doesn't exist yet.
    """
    table_path = f"{config.bronze_root}/{domain}"
    view_name = f"bronze_updates_{domain}"
    df.createOrReplaceTempView(view_name)

    if DeltaTable.isDeltaTable(spark, table_path):
        delta_table = DeltaTable.forPath(spark, table_path)
        (
            delta_table.alias("target")
            .merge(
                df.alias("source"),
                "target.event_id = source.event_id AND target.source_file = source.source_file",
            )
            .whenNotMatchedInsertAll()
            .execute()
        )
        mode = "merge"
    else:
        df.write.format("delta").mode("overwrite").save(table_path)
        mode = "initial_create"

    spark.catalog.dropTempView(view_name)
    row_count = spark.read.format("delta").load(table_path).count()
    return {"domain": domain, "mode": mode, "bronze_row_count": row_count}


def ingest_domain(spark: SparkSession, domain: str, schema, config: IngestionConfig, run_id: str, source_version: str) -> dict:
    """Full pipeline for one domain: read -> enrich -> merge. Returns a summary dict."""
    raw_df = read_raw_domain(spark, domain, schema, config)
    raw_count = raw_df.count()

    enriched_df = add_ingestion_metadata(raw_df, run_id, source_version)
    result = merge_into_bronze(enriched_df, spark, domain, config)
    result["raw_row_count"] = raw_count
    return result