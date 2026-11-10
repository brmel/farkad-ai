from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from importlib.resources import files

_ASSETS = files("farkad_ai.prompts.assets")
_SUFFIX = ".txt"
_VERSION_LENGTH = 12


@dataclass(frozen=True, slots=True)
class PromptAsset:
    name: str
    text: str

    @property
    def version(self) -> str:
        return version_of(self.text)

    def format(self, **values: object) -> str:
        return self.text.format(**values)


def version_of(*parts: str) -> str:
    return sha256("\x00".join(parts).encode()).hexdigest()[:_VERSION_LENGTH]


def prompt(name: str) -> PromptAsset:
    text = _ASSETS.joinpath(f"{name}{_SUFFIX}").read_text(encoding="utf-8").strip()
    return PromptAsset(name=name, text=text)


def list_prompts() -> tuple[PromptAsset, ...]:
    names = sorted(
        entry.name.removesuffix(_SUFFIX)
        for entry in _ASSETS.iterdir()
        if entry.name.endswith(_SUFFIX)
    )
    return tuple(prompt(name) for name in names)


def briefed(instructions: str, briefing: str) -> str:
    return f"{instructions}\n\n{briefing}" if briefing else instructions
