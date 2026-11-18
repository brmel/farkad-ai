from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from farkad_ai.models.port import ModelTier, Prompt


class RecordedUsage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    model: str
    input_tokens: int = Field(ge=0)
    cached_input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    latency_ms: int = Field(ge=0)


class Recording(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tier: ModelTier
    schema_name: str = Field(alias="schema")
    instructions: str
    utterance: str
    value: dict[str, object]
    usage: RecordedUsage

    @classmethod
    def read(cls, path: Path) -> Recording:
        return cls.model_validate_json(path.read_text())

    def written(self) -> str:
        return json.dumps(self.model_dump(mode="json", by_alias=True), indent=2) + "\n"


def fingerprint(prompt: Prompt, *, schema: type[BaseModel], tier: ModelTier) -> str:
    canonical = json.dumps(
        {
            "tier": tier.value,
            "schema": schema.model_json_schema(),
            "instructions": prompt.instructions,
            "utterance": prompt.utterance,
            "media": [
                {"content_type": blob.content_type, "sha256": hashlib.sha256(blob.data).hexdigest()}
                for blob in prompt.media
            ],
        },
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]
