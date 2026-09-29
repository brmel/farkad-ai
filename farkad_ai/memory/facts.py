"""The model decides what a sentence means; this decides what memory keeps."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum

MAX_CONTENT_CHARACTERS = 250
MAX_FACTS = 40


class MemoryCategory(StrEnum):
    dietary = "dietary"
    routine = "routine"
    preference = "preference"
    medical = "medical"
    general = "general"


class FactSource(StrEnum):
    spoken = "spoken"
    entered = "entered"


class EmptyFactError(ValueError):
    def __init__(self, subject: str) -> None:
        super().__init__(f"the fact about {subject!r} says nothing")


class OverlongFactError(ValueError):
    def __init__(self, subject: str) -> None:
        super().__init__(f"the fact about {subject!r} exceeds {MAX_CONTENT_CHARACTERS} characters")


@dataclass(frozen=True, slots=True)
class Disclosure:
    """What a sentence revealed, as the model read it: one topic, one sentence."""

    subject: str
    category: MemoryCategory
    content: str

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise EmptyFactError(self.subject)
        if len(self.content) > MAX_CONTENT_CHARACTERS:
            raise OverlongFactError(self.subject)

    @property
    def said(self) -> str:
        return " ".join(self.content.casefold().split())


@dataclass(frozen=True, slots=True)
class Fact:
    """One per subject, so a newer word on a topic replaces the older one by construction."""

    disclosure: Disclosure
    source: FactSource
    enabled: bool
    since: datetime

    @property
    def subject(self) -> str:
        return self.disclosure.subject


class Refusal(StrEnum):
    switched_off = "switched_off"
    written_by_user = "written_by_user"
    memory_full = "memory_full"


@dataclass(frozen=True, slots=True)
class Remembered:
    fact: Fact


@dataclass(frozen=True, slots=True)
class Superseded:
    fact: Fact
    replaced: Fact


@dataclass(frozen=True, slots=True)
class Confirmed:
    fact: Fact


@dataclass(frozen=True, slots=True)
class Declined:
    disclosure: Disclosure
    because: Refusal


type Learning = Remembered | Superseded | Confirmed | Declined


def learn(known: Fact | None, heard: Disclosure, *, at: datetime) -> Learning:
    """A switched-off fact is the user's refusal and a typed one is their own words: a model's
    reading of a later sentence outranks neither."""
    if known is None:
        return Remembered(Fact(heard, FactSource.spoken, enabled=True, since=at))
    if not known.enabled:
        return Declined(heard, Refusal.switched_off)
    if known.source is FactSource.entered:
        return Declined(heard, Refusal.written_by_user)
    if known.disclosure.said == heard.said:
        return Confirmed(replace(known, since=at))
    return Superseded(replace(known, disclosure=heard, since=at), replaced=known)


def learn_all(
    known: Mapping[str, Fact], heard: Iterable[Disclosure], *, at: datetime
) -> tuple[Learning, ...]:
    kept = dict(known)
    learned: list[Learning] = []
    for disclosure in heard:
        if disclosure.subject not in kept and len(kept) >= MAX_FACTS:
            learned.append(Declined(disclosure, Refusal.memory_full))
            continue
        learning = learn(kept.get(disclosure.subject), disclosure, at=at)
        match learning:
            case Remembered(fact=fact) | Superseded(fact=fact) | Confirmed(fact=fact):
                kept[fact.subject] = fact
            case Declined():
                pass
        learned.append(learning)
    return tuple(learned)
