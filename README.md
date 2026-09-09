# FitnessPulse

A cloud fitness telemetry lakehouse -- ingests simulated wearable and workout-platform
data through a Bronze/Silver/Gold medallion architecture on AWS S3 and Databricks,
modeled with dbt Core, tested with pytest and dbt tests, provisioned with Terraform,
and validated by GitHub Actions CI.

> Status: In development -- Milestone 1 (scope & architecture) complete.

## Architecture
See [`docs/architecture.md`](docs/architecture.md) for the full architecture,
MVP scope, and diagram.

## Event Contracts
See [`docs/event_contracts.md`](docs/event_contracts.md) for source event schemas
and intentional dirty-data scenarios.

## Tech Stack
AWS · S3 · Databricks · PySpark · Delta Lake · dbt Core (dbt-databricks) · Python ·
pytest · Terraform · GitHub Actions · Streamlit / Databricks SQL

## How to Run

### Synthetic Data Generator
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m src.generators.generate
```
Generates ~400K+ events across 7 domains (users, devices, workouts, heart rate,
daily activity, sleep) into `data/raw/`, partitioned by domain and date as
JSON Lines files. Fully reproducible via `--seed` (default 42).

Optional flags:
```bash
python -m src.generators.generate --users 50 --days 30 --seed 7
```

## Project Structure
```
fitnesspulse/
├── docs/            # architecture & event contracts
├── src/
│   ├── generators/  # synthetic data generator
│   ├── ingestion/   # Bronze ingestion (PySpark)
│   ├── quality/     # validation rules engine
│   └── utils/
├── dbt/fitnesspulse/  # Silver/Gold dbt models
├── infra/terraform/   # AWS infrastructure as code
├── notebooks/          # exploration only
├── tests/unit/
└── dashboard/           # Streamlit app
```