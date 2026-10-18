from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum


class FactSource(StrEnum):
    spoken = "spoken"
    entered = "entered"


class EmptyFactError(ValueError):
    def __init__(self, subject: str) -> None:
        super().__init__(f"the fact about {subject!r} says nothing")


def folded(said: str) -> str:
    return " ".join(said.casefold().split())


@dataclass(frozen=True, slots=True)
class Disclosure[Category: StrEnum]:
    subject: str
    category: Category
    content: str

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise EmptyFactError(self.subject)

    @property
    def said(self) -> str:
        return folded(self.content)


@dataclass(frozen=True, slots=True)
class Fact[Category: StrEnum]:
    disclosure: Disclosure[Category]
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
class Remembered[Category: StrEnum]:
    fact: Fact[Category]


@dataclass(frozen=True, slots=True)
class Superseded[Category: StrEnum]:
    fact: Fact[Category]
    replaced: Fact[Category]


@dataclass(frozen=True, slots=True)
class Confirmed[Category: StrEnum]:
    fact: Fact[Category]


@dataclass(frozen=True, slots=True)
class Declined[Category: StrEnum]:
    disclosure: Disclosure[Category]
    because: Refusal


type Learning[Category: StrEnum] = (
    Remembered[Category] | Superseded[Category] | Confirmed[Category] | Declined[Category]
)


def learn_all[Category: StrEnum](
    known: Mapping[str, Fact[Category]],
    heard: Iterable[Disclosure[Category]],
    *,
    at: datetime,
    max_facts: int,
) -> tuple[Learning[Category], ...]:
    kept = dict(known)
    learned: list[Learning[Category]] = []
    for disclosure in heard:
        if disclosure.subject not in kept and len(kept) >= max_facts:
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


def learn[Category: StrEnum](
    known: Fact[Category] | None, heard: Disclosure[Category], *, at: datetime
) -> Learning[Category]:
    if known is None:
        return Remembered(Fact(heard, FactSource.spoken, enabled=True, since=at))
    if not known.enabled:
        return Declined(heard, Refusal.switched_off)
    if known.source is FactSource.entered:
        return Declined(heard, Refusal.written_by_user)
    if known.disclosure.said == heard.said:
        return Confirmed(replace(known, since=at))
    return Superseded(replace(known, disclosure=heard, since=at), replaced=known)
