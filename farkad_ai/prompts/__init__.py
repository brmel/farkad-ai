from __future__ import annotations

import os
from dataclasses import dataclass
from hashlib import sha256
from importlib.resources import files
from pathlib import Path

VERSION_LENGTH = 12
KNOWN_PROMPTS: tuple[str, ...] = ("pass_one", "extraction", "recompute", "demo", "memory_inference")


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
    override_dir = os.environ.get("FARKAD_PROMPTS_DIR")
    if override_dir:
        override_path = Path(override_dir) / f"{name}.txt"
        if override_path.is_file():
            return PromptAsset(name=name, text=override_path.read_text(encoding="utf-8").strip())

    text = (
        files("farkad_ai.prompts.assets")
        .joinpath(f"{name}.txt")
        .read_text(encoding="utf-8")
        .strip()
    )
    return PromptAsset(name=name, text=text)


def list_prompts() -> tuple[PromptAsset, ...]:
    return tuple(prompt(name) for name in KNOWN_PROMPTS)
