from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from farkad_ai.extraction.port import Finding


class Drink(StrEnum):
    water = "water"
    tea = "tea"
    coffee = "coffee"
    other = "other"


class Activity(StrEnum):
    walk = "walk"
    run = "run"
    cycle = "cycle"
    swim = "swim"
    strength = "strength"
    other = "other"


class Rest(StrEnum):
    night = "night"
    nap = "nap"


class SupplementKind(StrEnum):
    vitamin = "vitamin"
    mineral = "mineral"
    performance = "performance"
    other = "other"


class RecoveryKind(StrEnum):
    sauna = "sauna"
    cold_plunge = "cold_plunge"
    breathwork = "breathwork"
    other = "other"


class Entry(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WaterEntry(Entry):
    category: Drink
    count: float | None = Field(default=None, description="How many glasses, cups or bottles")
    volume_ml: float | None = Field(default=None, description="Volume drunk in millilitres")


class FoodEntry(Entry):
    name: str | None = Field(default=None, description="What was eaten, in the user's words")
    count: float | None = Field(default=None, description="How many pieces or servings")


class ExerciseEntry(Entry):
    category: Activity
    duration_minutes: float | None = None
    distance_m: float | None = Field(default=None, description="Distance in metres")


class SleepEntry(Entry):
    category: Rest
    duration_minutes: float | None = None


class SupplementEntry(Entry):
    category: SupplementKind
    name: str | None = None


class DrugEntry(Entry):
    name: str | None = None
    dose_mg: float | None = Field(default=None, description="One dose in milligrams")


class RecoveryEntry(Entry):
    category: RecoveryKind
    duration_minutes: float | None = None


@dataclass(frozen=True, slots=True)
class ExamplePillar:
    """What a consumer supplies for one pillar: small on purpose, with nothing to review."""

    pillar: str
    intent: str
    title: str
    guidance: str
    examples: str
    entry_schema: type[BaseModel]
    label_fields: frozenset[str] = frozenset()

    def review(self, entry: Mapping[str, object]) -> Iterable[Finding]:
        return ()


EXAMPLE_PILLARS: tuple[ExamplePillar, ...] = (
    ExamplePillar(
        "food",
        "meals, snacks, drinks that carry energy, and protein shakes",
        "food",
        "One entry per thing eaten.",
        '"half a pizza" → {"name": "pizza", "count": 0.5}',
        FoodEntry,
    ),
    ExamplePillar(
        "water",
        "water, tea, black coffee and other drinks without energy",
        "drink",
        "A glass is 250 ml and a cup 200 ml unless the user said otherwise. A container word "
        "in any language is the container it names.",
        '"a cup of mint tea" → {"category": "tea", "count": 1, "volume_ml": 200}',
        WaterEntry,
    ),
    ExamplePillar(
        "exercise",
        "workouts, sport, movement",
        "exercise",
        "Distances in metres, durations in minutes.",
        '"swam 1.5 km" → {"category": "swim", "distance_m": 1500}',
        ExerciseEntry,
    ),
    ExamplePillar(
        "sleep",
        "nights, naps and sleep quality",
        "sleep",
        "A night is the main sleep; anything shorter during the day is a nap.",
        '"a two-hour nap" → {"category": "nap", "duration_minutes": 120}',
        SleepEntry,
    ),
    ExamplePillar(
        "supplements",
        "vitamins, minerals, creatine and the rest",
        "supplement",
        "One entry per product taken.",
        '"beta-alanine before my workout" → {"category": "performance", "name": "beta-alanine"}',
        SupplementEntry,
    ),
    ExamplePillar(
        "drugs",
        "medications and pharmaceuticals",
        "medication",
        "One entry per medication taken.",
        '"levothyroxine, 50 micrograms" → {"name": "levothyroxine", "dose_mg": 0.05}',
        DrugEntry,
    ),
    ExamplePillar(
        "recovery",
        "sauna, cold plunge, breathwork and other deliberate recovery",
        "recovery session",
        "Durations in minutes.",
        '"a quarter of an hour of foam rolling" → {"category": "other", "duration_minutes": 15}',
        RecoveryEntry,
    ),
)
