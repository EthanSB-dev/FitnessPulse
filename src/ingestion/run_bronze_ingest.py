"""
Orchestrates Bronze ingestion: loops over all event domains, plus a
one-time ingestion of reference data (users, devices).

This is the file a Databricks notebook actually calls - the notebook
itself should contain nothing but an import and a call to run(), keeping
all real logic here, in version-controlled, testable code.
"""

import uuid
from datetime import datetime, timezone

from pyspark.sql import SparkSession
from pyspark.sql.functions import current_timestamp, lit

from src.ingestion.config import IngestionConfig, EVENT_DOMAINS
from src.ingestion.schemas import SCHEMAS
from src.ingestion.bronze_ingest import ingest_domain

INGESTION_CODE_VERSION = "1.0"


def ingest_reference_data(spark: SparkSession, filename: str, table_name: str, config: IngestionConfig, run_id: str) -> dict:
    """
    Ingest a single-file reference dataset (users.json or devices.json).
    These are small, don't grow per-day, and are simply overwritten each
    run - the whole point of reference data is that it reflects current
    state, not an immutable event history.
    """
    path = f"{config.raw_root}/{filename}"
    df = spark.read.json(path)
    enriched = (
        df
        .withColumn("_ingestion_timestamp", current_timestamp())
        .withColumn("_pipeline_run_id", lit(run_id))
        .withColumn("_ingestion_code_version", lit(INGESTION_CODE_VERSION))
    )
    table_path = f"{config.bronze_root}/{table_name}"
    enriched.write.format("delta").mode("overwrite").save(table_path)
    row_count = spark.read.format("delta").load(table_path).count()
    return {"domain": table_name, "mode": "overwrite", "bronze_row_count": row_count, "raw_row_count": row_count}


def run(spark: SparkSession = None) -> list[dict]:
    """Run the full Bronze ingestion pipeline. Returns a list of per-domain summary dicts."""
    if spark is None:
        spark = SparkSession.builder.getOrCreate()

    config = IngestionConfig()
    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)

    print(f"Bronze ingestion run_id={run_id} starting at {started_at.isoformat()}")

    results = []

    # Reference data first (small, fast, and event domains don't depend on it
    # being ingested first - but doing it first makes the console output
    # read in a sensible order: entities, then events).
    results.append(ingest_reference_data(spark, "users.json", "users", config, run_id))
    results.append(ingest_reference_data(spark, "devices.json", "devices", config, run_id))

    for domain in EVENT_DOMAINS:
        schema = SCHEMAS[domain]
        result = ingest_domain(spark, domain, schema, config, run_id, INGESTION_CODE_VERSION)
        results.append(result)

    finished_at = datetime.now(timezone.utc)
    duration_seconds = (finished_at - started_at).total_seconds()

    print(f"\nBronze ingestion summary (run_id={run_id}, duration={duration_seconds:.1f}s):")
    for r in results:
        print(f"  {r['domain']:<16} raw={r['raw_row_count']:>7}  bronze_total={r['bronze_row_count']:>7}  mode={r['mode']}")

    return results


if __name__ == "__main__":
    run()