from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from importlib.resources import files
from importlib.resources.abc import Traversable

ASSETS = files("farkad_ai.prompts.assets")
SUFFIX = ".txt"
VERSION_LENGTH = 12


@dataclass(frozen=True, slots=True)
class PromptAsset:
    name: str
    text: str

    @property
    def version(self) -> str:
        return sha256(self.text.encode()).hexdigest()[:VERSION_LENGTH]

    def format(self, **values: object) -> str:
        return self.text.format(**values)


def prompt(name: str, assets: Traversable = ASSETS) -> PromptAsset:
    text = assets.joinpath(f"{name}{SUFFIX}").read_text(encoding="utf-8").strip()
    return PromptAsset(name=name, text=text)


def list_prompts(assets: Traversable = ASSETS) -> tuple[PromptAsset, ...]:
    names = sorted(
        entry.name.removesuffix(SUFFIX) for entry in assets.iterdir() if entry.name.endswith(SUFFIX)
    )
    return tuple(prompt(name, assets) for name in names)


def briefed(instructions: str, briefing: str) -> str:
    return f"{instructions}\n\n{briefing}" if briefing else instructions
