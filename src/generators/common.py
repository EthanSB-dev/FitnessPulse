"""
Generates workout lifecycle events: workout_started, workout_paused,
workout_resumed, workout_completed.

Each simulated workout produces 2-4 related events sharing a workout_id,
modeling a real device's start/pause/resume/complete session lifecycle.
"""

import uuid
from datetime import datetime, timedelta

from src.generators.config import GeneratorConfig
from src.generators.common import make_envelope
from src.generators.entities import User, Device

WORKOUT_TYPES = ["run", "ride", "strength", "swim", "walk"]
# Typical duration ranges (minutes) by workout type - used to keep durations plausible.
DURATION_RANGES_MIN = {
    "run": (20, 60),
    "ride": (30, 90),
    "strength": (30, 75),
    "swim": (20, 50),
    "walk": (15, 45),
}


def _pick_device_for_user(user_id: str, devices_by_user: dict[str, list[str]], rng) -> str | None:
    """Most workouts are logged via a device; a small fraction have none (manual entry)."""
    user_devices = devices_by_user.get(user_id, [])
    if not user_devices or rng.random() < 0.05:
        return None
    return rng.choice(user_devices)


def generate_workout_events(
    users: list[User],
    devices: list[Device],
    config: GeneratorConfig,
    rng,
) -> list[dict]:
    """Generate workout_started/paused/resumed/completed events for all users."""
    devices_by_user: dict[str, list[str]] = {}
    for d in devices:
        devices_by_user.setdefault(d.user_id, []).append(d.device_id)

    total_days = (config.end_date - config.start_date).days
    weeks = max(total_days / 7, 1)

    events: list[dict] = []

    for user in users:
        expected_workouts = config.workouts_per_user_per_week * weeks
        num_workouts = max(0, round(rng.gauss(expected_workouts, expected_workouts * 0.25)))

        for _ in range(num_workouts):
            day_offset = rng.randint(0, total_days)
            workout_day = config.start_date + timedelta(days=day_offset)
            start_hour = rng.randint(5, 21)  # workouts happen 5am-9pm
            start_time = datetime(
                workout_day.year, workout_day.month, workout_day.day,
                start_hour, rng.randint(0, 59), rng.randint(0, 59),
            )

            workout_id = str(uuid.uuid4())
            workout_type = rng.choice(WORKOUT_TYPES)
            device_id = _pick_device_for_user(user.user_id, devices_by_user, rng)
            schema_version = config.schema_version_before  # corruption.py handles evolution cutover

            low, high = DURATION_RANGES_MIN[workout_type]
            duration_min = rng.randint(low, high)

            # ~20% of workouts include a pause/resume cycle
            has_pause = rng.random() < 0.20
            events.append({
                **make_envelope("workout_started", start_time, user.user_id, device_id, schema_version),
                "workout_id": workout_id,
                "workout_type": workout_type,
            })

            current_time = start_time
            remaining_active_min = duration_min

            if has_pause:
                pause_after_min = rng.randint(3, max(4, duration_min - 3))
                pause_time = current_time + timedelta(minutes=pause_after_min)
                pause_duration_min = rng.randint(1, 15)
                resume_time = pause_time + timedelta(minutes=pause_duration_min)

                events.append({
                    **make_envelope("workout_paused", pause_time, user.user_id, device_id, schema_version),
                    "workout_id": workout_id,
                    "workout_type": workout_type,
                })
                events.append({
                    **make_envelope("workout_resumed", resume_time, user.user_id, device_id, schema_version),
                    "workout_id": workout_id,
                    "workout_type": workout_type,
                })
                current_time = resume_time
            else:
                current_time = start_time

            completed_time = current_time + timedelta(minutes=(remaining_active_min if not has_pause else duration_min - pause_after_min))
            events.append({
                **make_envelope("workout_completed", completed_time, user.user_id, device_id, schema_version),
                "workout_id": workout_id,
                "workout_type": workout_type,
                "duration_seconds": duration_min * 60,
            })

    return events