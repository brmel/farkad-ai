from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from importlib.resources import files

VERSION_LENGTH = 12
KNOWN_PROMPTS: tuple[str, ...] = (
    "pass_one",
    "extraction",
    "memory_inference",
)


@dataclass(frozen=True, slots=True)
class PromptAsset:
    name: str
    text: str

    @property
    def version(self) -> str:
        return sha256(self.text.encode()).hexdigest()[:VERSION_LENGTH]

    def format(self, **values: object) -> str:
        return self.text.format(**values)


def prompt(name: str) -> PromptAsset:
    text = (
        files("farkad_ai.prompts.assets")
        .joinpath(f"{name}.txt")
        .read_text(encoding="utf-8")
        .strip()
    )
    return PromptAsset(name=name, text=text)


def list_prompts() -> tuple[PromptAsset, ...]:
    return tuple(prompt(name) for name in KNOWN_PROMPTS)


def briefed(instructions: str, briefing: str) -> str:
    """Unchanged when there is nothing to add, so a recording made without it still replays."""
    return f"{instructions}\n\n{briefing}" if briefing else instructions
