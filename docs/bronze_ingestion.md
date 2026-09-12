# Bronze Ingestion

## Architecture
Raw JSON (S3 `raw/`) → PySpark read with explicit schema → ingestion metadata
enrichment → Delta Lake MERGE → Bronze Delta tables (S3 `bronze/`), one per domain.

## Idempotency design
Bronze MERGE keys on `(event_id, source_file)`, not `event_id` alone. This makes
Bronze idempotent at the **file level**: re-running ingestion on an already-processed
source file inserts zero duplicate rows. Verified empirically — running ingestion
twice against the same 400K+ row dataset produced byte-for-byte identical row counts
on the second run (see run comparison below).

This deliberately does NOT deduplicate events that share an `event_id` *within* the
same source file - those are preserved and left for Silver to catch, per the
project's dedup-in-Silver requirement. This matters because the synthetic generator's
corruption pipeline intentionally creates same-event_id duplicates within a single
file to simulate producer/retry duplication - collapsing them in Bronze would remove
the exact scenario Silver's dedup logic is meant to demonstrate.

## Verified idempotency (real run data)
| Run | workouts | heart_rate | daily_activity | sleep |
|-----|---------:|-----------:|----------------:|------:|
| 1st (initial_create) | 18,815 | 349,774 | 15,602 | 16,595 |
| 2nd (merge, re-run)  | 18,815 | 349,774 | 15,602 | 16,595 |

## Schema strategy
Explicit PySpark schemas (`src/ingestion/schemas.py`) are used instead of inference.
Timestamps are kept as raw strings in Bronze (not parsed to TimestampType) - Bronze's
job is faithful capture of source data, not transformation. Type/timestamp
standardization happens in Silver.

## Reference data (users, devices)
Ingested via `overwrite` mode, not MERGE - these represent current state, not an
append-only event history.

## Ingestion metadata columns
Every Bronze row includes: `source_file`, `_pipeline_run_id`, `_ingestion_timestamp`,
`_ingestion_code_version`.

## Known platform constraint
Unity Catalog serverless compute does not support the legacy PySpark
`input_file_name()` function; `_metadata.file_path` (the UC-native equivalent) is
used instead.