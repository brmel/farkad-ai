from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, create_model, field_validator

from farkad_ai.prompts import prompt, schema_words
from farkad_ai.routing.port import PartOfDay, PillarSpec, StatedTime

_WORDS = schema_words("pass_one")
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
    __doc__ = _WORDS["TimeHint"]
    model_config = ConfigDict(extra="forbid")

    day_offset: int = Field(description=_WORDS["TimeHint.day_offset"])
    clock: time | None = Field(default=None, description=_WORDS["TimeHint.clock"])
    part_of_day: PartOfDay | None = Field(default=None, description=_WORDS["TimeHint.part_of_day"])

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


class Headline(BaseModel):
    model_config = ConfigDict(extra="forbid")

    def in_each_language(self) -> dict[str, str]:
        return self.model_dump()


class Mention(BaseModel):
    __doc__ = _WORDS["Mention"]
    model_config = ConfigDict(extra="forbid")

    pillar: str = Field(description=_WORDS["Mention.pillar"])
    said: str = Field(description=_WORDS["Mention.said"])
    occurred_at_hint: TimeHint | None = Field(
        default=None, description=_WORDS["Mention.occurred_at_hint"]
    )


class PassOne(BaseModel):
    __doc__ = _WORDS["PassOne"]
    model_config = ConfigDict(extra="forbid")

    language: str = Field(description=_WORDS["PassOne.language"])
    is_health_related: bool = Field(description=_WORDS["PassOne.is_health_related"])
    states_a_lasting_fact: bool = Field(description=_WORDS["PassOne.states_a_lasting_fact"])
    mentions: list[Mention] = Field(default_factory=list, description=_WORDS["PassOne.mentions"])
    headline: Headline

    def transcript_of(self, typed: str) -> str:
        return typed


class _Transcript(BaseModel):
    transcript: str = Field(description=_WORDS["TranscribedPassOne.transcript"])


class TranscribedPassOne(PassOne, _Transcript):
    __doc__ = _WORDS["TranscribedPassOne"]

    def transcript_of(self, typed: str) -> str:
        return self.transcript


def answer_schemas(
    headline_languages: Mapping[str, str],
) -> tuple[type[PassOne], type[TranscribedPassOne]]:
    written_in: dict[str, Any] = {
        tag: (str, Field(description=_WORDS["Headline.language"].format(language=name)))
        for tag, name in headline_languages.items()
    }
    in_each_language = create_model("Headline", __base__=Headline, **written_in)
    headline = (in_each_language, Field(description=_WORDS["PassOne.headline"]))
    return (
        create_model("PassOne", __base__=PassOne, headline=headline),
        create_model("TranscribedPassOne", __base__=TranscribedPassOne, headline=headline),
    )
