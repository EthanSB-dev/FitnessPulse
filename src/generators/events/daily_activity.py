"""
Generates daily activity rollup events: steps, active calories,
distance, and active minutes, one record per user per day.

Unlike workouts or heart_rate, this domain has no internal state machine
or dependency on other event types - each record stands alone, representing
a device's end-of-day summary rollup.
"""

from datetime import datetime, timedelta

from src.generators.config import GeneratorConfig
from src.generators.common import make_envelope
from src.generators.entities import User, Device


def generate_daily_activity_events(
    users: list[User],
    devices: list[Device],
    config: GeneratorConfig,
    rng,
) -> list[dict]:
    """Generate one daily activity rollup per user per day, for most days."""
    devices_by_user: dict[str, list[str]] = {}
    for d in devices:
        devices_by_user.setdefault(d.user_id, []).append(d.device_id)

    total_days = (config.end_date - config.start_date).days
    events: list[dict] = []

    for user in users:
        user_devices = devices_by_user.get(user.user_id, [])
        # A user's baseline activity level varies person-to-person (some are
        # more active than others) - modeled as a per-user multiplier.
        activity_multiplier = rng.uniform(0.6, 1.5)

        for day_offset in range(total_days + 1):
            # Not every user logs activity every single day (missed days,
            # device not worn, etc.) - roughly 85% day coverage.
            if rng.random() > 0.85:
                continue

            record_day = config.start_date + timedelta(days=day_offset)
            # Rollup is generated end-of-day, timestamped in the evening.
            record_time = datetime(
                record_day.year, record_day.month, record_day.day,
                rng.randint(20, 23), rng.randint(0, 59), 0,
            )

            device_id = rng.choice(user_devices) if user_devices else None

            base_steps = rng.gauss(7500, 2500) * activity_multiplier
            steps = max(0, round(base_steps))
            active_minutes = max(0, round(steps / 130 + rng.uniform(-5, 5)))
            distance_meters = round(steps * rng.uniform(0.68, 0.82), 1)  # avg stride length range
            active_calories = round(steps * rng.uniform(0.035, 0.045))

            events.append({
                **make_envelope(
                    "daily_activity_recorded", record_time, user.user_id, device_id,
                    config.schema_version_before,
                ),
                "activity_date": record_day.isoformat(),
                "steps": steps,
                "active_calories": active_calories,
                "distance_meters": distance_meters,
                "active_minutes": active_minutes,
            })

    return events