"""
CLI entrypoint for the FitnessPulse synthetic data generator.

Orchestrates, in dependency order:
  1. config      - load run parameters
  2. entities    - generate users and devices (reference data)
  3. events/*    - generate each domain's events, using entities (and,
                   for heart_rate, already-generated workout events)
  4. corruption  - apply dirty-data scenarios to each domain independently
  5. writer      - serialize everything to data/raw/

This file intentionally contains almost no logic of its own - every
interesting decision lives in the module it calls. That's deliberate:
this file should be readable as a summary of the whole pipeline.

Usage:
    python -m src.generators.generate
    python -m src.generators.generate --days 30 --users 50
"""

import argparse
import random
from datetime import date, timedelta

from src.generators.config import GeneratorConfig
from src.generators.entities import generate_users, generate_devices
from src.generators.events.workouts import generate_workout_events
from src.generators.events.heart_rate import generate_heart_rate_events
from src.generators.events.daily_activity import generate_daily_activity_events
from src.generators.events.sleep import generate_sleep_events
from src.generators.corruption import apply_all_corruptions
from src.generators.writer import write_events, write_entities


def parse_args() -> GeneratorConfig:
    parser = argparse.ArgumentParser(description="Generate synthetic FitnessPulse data.")
    parser.add_argument("--users", type=int, default=None, help="Number of users to generate.")
    parser.add_argument("--days", type=int, default=None, help="Number of days of history to simulate.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility.")
    args = parser.parse_args()

    config = GeneratorConfig()
    if args.users is not None:
        config.num_users = args.users
    if args.days is not None:
        config.end_date = config.start_date + timedelta(days=args.days)
    if args.seed is not None:
        config.seed = args.seed
    return config


def run(config: GeneratorConfig) -> None:
    rng = random.Random(config.seed)

    print(f"Generating {config.num_users} users over "
          f"{(config.end_date - config.start_date).days} days (seed={config.seed})...")

    # 1. Entities
    users = generate_users(config, rng)
    devices = generate_devices(users, config, rng)
    print(f"  entities: {len(users)} users, {len(devices)} devices")

    # 2. Events - workouts first, since heart_rate depends on workout events
    workout_events = generate_workout_events(users, devices, config, rng)
    heart_rate_events = generate_heart_rate_events(workout_events, config, rng)
    daily_activity_events = generate_daily_activity_events(users, devices, config, rng)
    sleep_events = generate_sleep_events(users, devices, config, rng)

    print(f"  workouts: {len(workout_events)} events")
    print(f"  heart_rate: {len(heart_rate_events)} events")
    print(f"  daily_activity: {len(daily_activity_events)} events")
    print(f"  sleep: {len(sleep_events)} events")

    # 3. Corruption - applied independently per domain, with domain-specific
    # numeric/duration fields passed in where relevant.
    workout_events = apply_all_corruptions(
        workout_events, config, rng, duration_field="duration_seconds",
    )
    heart_rate_events = apply_all_corruptions(
        heart_rate_events, config, rng, numeric_field="bpm", numeric_range=(0, 300),
    )
    daily_activity_events = apply_all_corruptions(
        daily_activity_events, config, rng, numeric_field="steps", numeric_range=(-100, 200000),
    )
    sleep_events = apply_all_corruptions(sleep_events, config, rng)

    # 4. Write to disk
    write_entities(users, "users.json", config)
    write_entities(devices, "devices.json", config)
    workout_paths = write_events(workout_events, "workouts", config)
    heart_rate_paths = write_events(heart_rate_events, "heart_rate", config)
    daily_activity_paths = write_events(daily_activity_events, "daily_activity", config)
    sleep_paths = write_events(sleep_events, "sleep", config)

    total_files = 2 + len(workout_paths) + len(heart_rate_paths) + len(daily_activity_paths) + len(sleep_paths)
    print(f"Done. Wrote {total_files} files to {config.output_dir}/")


if __name__ == "__main__":
    run(parse_args())