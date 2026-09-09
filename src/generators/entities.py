"""
Generates reference/dimension data: users and devices.

This runs once per generation run, before any event domains are generated.
Every event generator (workouts, heart_rate, daily_activity, sleep) references
the user_id and device_id values produced here - they are the "known good"
set of identifiers that dirty-data scenarios like unknown_reference_rate
are defined relative to.
"""

import random
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta

from src.generators.config import GeneratorConfig

GOAL_TYPES = ["endurance", "weight_loss", "general_fitness", "strength"]
DEVICE_TYPES = ["watch", "chest_strap", "ring"]
DEVICE_MANUFACTURERS = {
    "watch": [("Garmin", "Forerunner 265"), ("Apple", "Watch Series 10"), ("Fitbit", "Sense 2")],
    "chest_strap": [("Polar", "H10"), ("Wahoo", "TICKR")],
    "ring": [("Oura", "Ring Gen 4")],
}


@dataclass
class User:
    user_id: str
    display_name: str
    date_of_birth: date
    sex: str
    height_cm: float
    weight_kg: float
    goal_type: str
    created_at: str


@dataclass
class Device:
    device_id: str
    user_id: str
    device_type: str
    manufacturer: str
    model: str
    registered_at: str


def generate_users(config: GeneratorConfig, rng: random.Random) -> list[User]:
    """Generate `config.num_users` synthetic user profiles."""
    users = []
    for i in range(config.num_users):
        sex = rng.choice(["female", "male"])
        # Rough, plausible adult height/weight ranges by sex - not clinically
        # precise, just enough realism for downstream metric calculations.
        height_cm = round(rng.uniform(155, 180), 1) if sex == "female" else round(rng.uniform(165, 195), 1)
        weight_kg = round(rng.uniform(50, 80), 1) if sex == "female" else round(rng.uniform(60, 100), 1)

        dob = date(
            rng.randint(1970, 2005),
            rng.randint(1, 12),
            rng.randint(1, 28),
        )

        users.append(
            User(
                user_id=str(uuid.uuid4()),
                display_name=f"user_{i:04d}",
                date_of_birth=dob,
                sex=sex,
                height_cm=height_cm,
                weight_kg=weight_kg,
                goal_type=rng.choice(GOAL_TYPES),
                created_at=(config.start_date - timedelta(days=rng.randint(1, 365))).isoformat(),
            )
        )
    return users


def generate_devices(users: list[User], config: GeneratorConfig, rng: random.Random) -> list[Device]:
    """Generate 1-2 devices per user, per config.num_devices_per_user_range."""
    devices = []
    low, high = config.num_devices_per_user_range
    for user in users:
        num_devices = rng.randint(low, high)
        for _ in range(num_devices):
            device_type = rng.choice(DEVICE_TYPES)
            manufacturer, model = rng.choice(DEVICE_MANUFACTURERS[device_type])
            devices.append(
                Device(
                    device_id=str(uuid.uuid4()),
                    user_id=user.user_id,
                    device_type=device_type,
                    manufacturer=manufacturer,
                    model=model,
                    registered_at=user.created_at,
                )
            )
    return devices