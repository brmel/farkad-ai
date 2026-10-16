"""Docstrings and descriptions here reach the model in its answer schema: they are prompt text."""

from __future__ import annotations

from datetime import time

from pydantic import BaseModel, ConfigDict, Field, field_validator

from farkad_ai.prompts import PromptAsset, prompt
from farkad_ai.routing.port import PartOfDay, PillarRegistry, StatedTime

INSTRUCTIONS = prompt("pass_one")


def routing_instructions(registry: PillarRegistry, asset: PromptAsset = INSTRUCTIONS) -> str:
    catalogue = "\n".join(f"- {spec.pillar}: {spec.intent}" for spec in registry)
    return asset.format(pillars=catalogue)


class TimeHint(BaseModel):
    """A time the user stated, split into the parts a model is reliable at: which day
    relative to today, and the hour or the part of the day they named. It is never asked for
    a date or for a clock the user did not say: the calendar arithmetic stays with the
    consumer, so a misheard word cannot become the year 2019."""

    model_config = ConfigDict(extra="forbid")

    phrase: str = Field(description="The time expression exactly as the user said it")
    day_offset: int = Field(description="0 for today, -1 for yesterday, -7 for this day last week")
    clock: time | None = Field(
        default=None,
        description="Local time of day as HH:MM, only from an hour the user said; null otherwise",
    )
    part_of_day: PartOfDay | None = Field(
        default=None,
        description="The part of the day the user named, or the one a meal they named is eaten "
        "in, when they said no hour; null otherwise",
    )

    @field_validator("clock")
    @classmethod
    def _drop_offset(cls, clock: time | None) -> time | None:
        """Gemini answers "at eleven" with `23:00:00Z`, and the Z is formatting, not a zone."""
        return clock.replace(tzinfo=None) if clock else clock

    def stated(self) -> StatedTime:
        return StatedTime(
            phrase=self.phrase,
            day_offset=self.day_offset,
            time_of_day=self.clock if self.clock is not None else self.part_of_day,
        )


class Mention(BaseModel):
    """One thing the user logged, and the one pillar that records it."""

    model_config = ConfigDict(extra="forbid")

    pillar: str = Field(description="Id of the one pillar that records this thing")
    said: str = Field(
        description="Every word the user said about this one thing: what, how much, how, when"
    )
    occurred_at_hint: TimeHint | None = Field(
        default=None, description="When the user said this one thing happened, or null if unstated"
    )


class PassOne(BaseModel):
    """The model's answer. Deliberately not the domain type: `mentions` here is what the
    model claimed, before it is intersected with what the user actually tracks."""

    model_config = ConfigDict(extra="forbid")

    transcript: str = Field(description="Exactly what was said, in its own language")
    language: str = Field(
        description="BCP-47 tag the sentence begins in; the transcript may mix languages"
    )
    is_health_related: bool = Field(description="False for anything that is not a log")
    mentions: list[Mention] = Field(
        default_factory=list,
        description="Every thing the user logged, each once, under the one pillar that records it",
    )
