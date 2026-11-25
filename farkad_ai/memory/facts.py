from __future__ import annotations

from dataclasses import dataclass
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
