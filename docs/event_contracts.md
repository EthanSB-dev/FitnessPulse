# FitnessPulse — Event Contracts

All events are emitted as JSON. Every event includes a common envelope plus
domain-specific fields. Fields marked **(dirty)** are intentionally used to
generate bad-data scenarios in the synthetic generator (Milestone 3).

## Common Envelope (all events)
| Field | Type | Notes |
|---|---|---|
| `event_id` | string (UUID) | Unique per event; **(dirty)**: duplicated intentionally |
| `event_type` | string | e.g. `workout_started`, `heart_rate_sample` |
| `event_timestamp` | ISO-8601 UTC | Event time; **(dirty)**: future timestamps, late arrival |
| `schema_version` | string | e.g. `"1.0"`; supports schema-evolution scenario |
| `user_id` | string | **(dirty)**: unknown/missing user_id |
| `device_id` | string, nullable | **(dirty)**: unknown device_id |

## 1. User Profiles
`user_id`, `display_name`, `date_of_birth`, `sex`, `height_cm`, `weight_kg`,
`goal_type` (e.g. `endurance`, `weight_loss`, `general_fitness`), `created_at`.

## 2. Devices
`device_id`, `user_id`, `device_type` (e.g. `watch`, `chest_strap`, `ring`),
`manufacturer`, `model`, `registered_at`.

## 3. Workout Events
`event_type` ∈ {`workout_started`, `workout_paused`, `workout_resumed`, `workout_completed`},
`workout_id`, `workout_type` (e.g. `run`, `ride`, `strength`), `duration_seconds`
(**(dirty)**: impossible durations, e.g. negative or >24h).

## 4. Heart-Rate Telemetry
`workout_id` (nullable — some HR samples are outside workouts), `bpm`
(**(dirty)**: invalid ranges, e.g. 0 or 300), `sample_timestamp`.

## 5. Daily Activity Events
`activity_date`, `steps`, `active_calories`, `distance_meters`, `active_minutes`
(**(dirty)**: invalid ranges, e.g. negative steps).

## 6. Sleep Sessions
`sleep_session_id`, `sleep_start`, `sleep_end`, `sleep_stages` (map of stage →
minutes: `light`, `deep`, `rem`, `awake`), `resting_heart_rate`, `hrv_ms`
(**(dirty)**: impossible durations, stage minutes exceeding session length).

## 7. Pipeline Metadata
`run_id`, `source_file` or `kafka_topic`, `row_count`, `validation_failure_count`,
`processing_duration_seconds`, `ingested_at`, `data_freshness_minutes`.

## Dirty-Data Scenarios (generator must produce)
- Null/missing required IDs
- Duplicate `event_id`s
- Invalid metric ranges (negative steps, bpm out of range)
- Impossible durations (negative or excessive)
- Future timestamps
- Unknown `user_id` / `device_id` (referential integrity violations)
- Late-arriving events (event_timestamp well before ingestion_timestamp)
- One schema-evolution scenario (e.g. `schema_version` `"1.0"` → `"1.1"` adding a field)