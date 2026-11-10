"""Docstrings and descriptions here reach the model in its answer schema: they are prompt text."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import time

from pydantic import BaseModel, ConfigDict, Field, field_validator

from farkad_ai.prompts import prompt
from farkad_ai.routing.port import PartOfDay, PillarSpec, StatedTime

INSTRUCTIONS = prompt("pass_one")
_RULES = prompt("pass_one_rules")
_TRANSCRIBING = prompt("pass_one_transcribed")
_TYPED = prompt("pass_one_typed")


def routing_instructions(
    catalogue: Iterable[PillarSpec], *, rules: tuple[str, ...] = (), transcribing: bool = False
) -> str:
    instructions = INSTRUCTIONS.format(
        opening=(_TRANSCRIBING if transcribing else _TYPED).text,
        pillars=_listed(f"{spec.pillar}: {spec.intent}" for spec in catalogue),
    )
    if not rules:
        return instructions
    return f"{instructions}\n\n{_RULES.format(rules=_listed(rules))}"


def _listed(lines: Iterable[str]) -> str:
    return "\n".join(f"- {line}" for line in lines)


class TimeHint(BaseModel):
    """A time the user stated: which day relative to today, and the hour or the part of the
    day they named. Never a date, and never a clock the user did not say."""

    model_config = ConfigDict(extra="forbid")

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
    """Your answer about one log."""

    model_config = ConfigDict(extra="forbid")

    language: str = Field(
        description="BCP-47 tag the sentence begins in; the sentence may mix languages"
    )
    is_health_related: bool = Field(description="False for anything that is not a log")
    states_a_lasting_fact: bool = Field(
        description="True when the person states something about themselves that stays true "
        "beyond this one log; false for a log of what happened"
    )
    mentions: list[Mention] = Field(
        default_factory=list,
        description="Every thing the user logged, each once, under the one pillar that records it",
    )

    def transcript_of(self, typed: str) -> str:
        return typed


class _Transcript(BaseModel):
    transcript: str = Field(description="Exactly what was said, in its own language")


class TranscribedPassOne(PassOne, _Transcript):
    """Your answer about one log that you hear or see, and so write down first."""

    def transcript_of(self, typed: str) -> str:
        return self.transcript
