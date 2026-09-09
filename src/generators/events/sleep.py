"""
Generates sleep session events: duration, sleep stage breakdown,
resting heart rate, and HRV.

This is the most structurally complex domain: sessions span midnight
(a session starting at 11pm ends the next calendar day), and stage
minutes (light/deep/rem/awake) must sum consistently to the total
session duration - the same kind of cross-field consistency that
Silver-layer validation will eventually check.

Per project scope, all recovery/wellness metrics here are explicitly
non-clinical - HRV and resting HR are simplified numeric approximations
for analytics purposes only, not medically meaningful values.
"""

import uuid
from datetime import datetime, timedelta

from src.generators.config import GeneratorConfig
from src.generators.common import make_envelope
from src.generators.entities import User, Device


def generate_sleep_events(
    users: list[User],
    devices: list[Device],
    config: GeneratorConfig,
    rng,
) -> list[dict]:
    """Generate one sleep session per user per night, for most nights."""
    devices_by_user: dict[str, list[str]] = {}
    for d in devices:
        devices_by_user.setdefault(d.user_id, []).append(d.device_id)

    total_days = (config.end_date - config.start_date).days
    events: list[dict] = []

    for user in users:
        user_devices = devices_by_user.get(user.user_id, [])

        for day_offset in range(total_days + 1):
            if rng.random() > config.sleep_sessions_per_user_per_day:
                continue

            sleep_day = config.start_date + timedelta(days=day_offset)

            # Sleep starts the evening of sleep_day, typically 9pm-1am.
            start_hour = rng.randint(21, 23) if rng.random() < 0.7 else rng.randint(0, 1)
            start_time = datetime(
                sleep_day.year, sleep_day.month, sleep_day.day, 21, 0, 0
            ) + timedelta(hours=(start_hour - 21) % 24, minutes=rng.randint(0, 59))

            total_sleep_minutes = max(180, round(rng.gauss(440, 60)))  # ~7.3h average, floor 3h
            sleep_end = start_time + timedelta(minutes=total_sleep_minutes)

            # Split total duration into stages - proportions roughly reflect
            # typical adult sleep architecture, with noise for realism.
            awake_min = round(total_sleep_minutes * rng.uniform(0.03, 0.08))
            deep_min = round(total_sleep_minutes * rng.uniform(0.12, 0.20))
            rem_min = round(total_sleep_minutes * rng.uniform(0.18, 0.25))
            light_min = max(0, total_sleep_minutes - awake_min - deep_min - rem_min)

            device_id = rng.choice(user_devices) if user_devices else None
            resting_hr = rng.randint(48, 65)
            hrv_ms = round(rng.uniform(25, 70), 1)  # non-clinical analytical approximation only

            events.append({
                **make_envelope(
                    "sleep_session_recorded", sleep_end, user.user_id, device_id,
                    config.schema_version_before,
                ),
                "sleep_session_id": str(uuid.uuid4()),
                "sleep_start": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "sleep_end": sleep_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "sleep_stages": {
                    "light": light_min,
                    "deep": deep_min,
                    "rem": rem_min,
                    "awake": awake_min,
                },
                "resting_heart_rate": resting_hr,
                "hrv_ms": hrv_ms,
            })

    return events