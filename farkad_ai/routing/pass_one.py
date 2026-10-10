from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import time
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from farkad_ai.prompts import PromptAsset, prompt

INSTRUCTIONS = prompt("pass_one")


@dataclass(frozen=True, slots=True)
class StatedTime:
    phrase: str
    day_offset: int
    clock: time | None

    @property
    def names_a_day(self) -> bool:
        return self.day_offset != 0


class TimeHint(BaseModel):
    """A time the user stated, split into the two parts a model is reliable at: which day
    relative to today, and what time of day. It is never asked for a date: the calendar
    arithmetic stays with the consumer, so a misheard word cannot become the year 2019."""

    model_config = ConfigDict(extra="forbid")

    phrase: str = Field(description="The time expression exactly as the user said it")
    day_offset: int = Field(description="0 for today, -1 for yesterday, -7 for this day last week")
    clock: time | None = Field(
        default=None,
        description="Local time of day as HH:MM, or null if only a day was said",
    )

    @field_validator("clock")
    @classmethod
    def _drop_offset(cls, clock: time | None) -> time | None:
        """Gemini answers "at eleven" with `23:00:00Z`, and the Z is formatting, not a zone."""
        return clock.replace(tzinfo=None) if clock else clock

    def stated(self) -> StatedTime:
        return StatedTime(phrase=self.phrase, day_offset=self.day_offset, clock=self.clock)


class Mention(BaseModel):
    """One thing the user logged, and the one pillar that records it."""

    model_config = ConfigDict(extra="forbid")

    pillar: str = Field(description="Id of the one pillar that records this thing")
    said: str = Field(
        description="Every word the user said about this one thing: what, how much, how, when"
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
    occurred_at_hint: TimeHint | None = Field(
        default=None, description="When the user said it happened, or null if unstated"
    )


class PillarSpecProtocol(Protocol):
    @property
    def pillar(self) -> str: ...

    @property
    def intent(self) -> str: ...


class PillarRegistryProtocol(Protocol):
    def __iter__(self) -> Iterator[PillarSpecProtocol]: ...
    def knows(self, route: str) -> bool: ...


def routing_instructions(
    registry: PillarRegistryProtocol, asset: PromptAsset = INSTRUCTIONS
) -> str:
    catalogue = "\n".join(f"- {spec.pillar}: {spec.intent}" for spec in registry)
    return asset.format(pillars=catalogue)
