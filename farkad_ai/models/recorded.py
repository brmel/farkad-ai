from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from farkad_ai.models.port import Completion, Model, ModelTier, Prompt, TierChoices, Usage


class Unreachable(StrEnum):
    never_recorded = "the utterance was never recorded"
    prompt_changed = (
        "the same utterance is recorded against different instructions, so the prompt "
        "changed and every recording made against the old one is now unreachable"
    )
    schema_changed = (
        "the same utterance is recorded against the same instructions but another answer "
        "schema, so the schema changed and the recording would replay an answer to the old one"
    )


class NoRecordedResponseError(Exception):
    def __init__(self, key: str, directory: Path, because: Unreachable) -> None:
        super().__init__(
            f"no recorded response {key} in {directory} — {because}; record one with "
            "RecordingModel against the live provider rather than writing it"
        )
        self.because = because


class UnrecordedModelError(Exception):
    def __init__(self, key: str, tier: ModelTier, *, pinned: str, recorded: str) -> None:
        super().__init__(
            f"the {tier} tier is pinned to {pinned}, but {key}.json holds {recorded}'s "
            f"answer; re-record the fixtures — replaying {recorded} would report a score "
            f"and a cost {pinned} has never produced"
        )
        self.pinned = pinned
        self.recorded = recorded


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


class RecordedModel(Model):
    def __init__(self, directory: Path, *, pinned: TierChoices | None = None) -> None:
        self._directory = directory
        self._pinned = pinned

    async def complete[T: BaseModel](
        self, prompt: Prompt, *, schema: type[T], tier: ModelTier
    ) -> Completion[T]:
        key = fingerprint(prompt, schema=schema, tier=tier)
        path = self._directory / f"{key}.json"
        if not path.exists():
            raise NoRecordedResponseError(
                key, self._directory, self._diagnose(prompt, schema, tier)
            )
        recording = Recording.read(path)
        counted = Usage.answering(prompt, **recording.usage.model_dump())
        if self._pinned is not None:
            pinned = (await self._pinned(tier)).model
            if counted.model != pinned:
                raise UnrecordedModelError(key, tier, pinned=pinned, recorded=counted.model)
        return Completion(value=schema.model_validate(recording.value), usage=counted)

    def _diagnose(self, prompt: Prompt, schema: type[BaseModel], tier: ModelTier) -> Unreachable:
        for path in sorted(self._directory.glob("*.json")):
            recorded = Recording.read(path)
            if (recorded.tier, recorded.schema_name, recorded.utterance) != (
                tier,
                schema.__name__,
                prompt.utterance,
            ):
                continue
            if recorded.instructions != prompt.instructions:
                return Unreachable.prompt_changed
            return Unreachable.schema_changed
        return Unreachable.never_recorded


class RecordingModel(Model):
    def __init__(self, live: Model, directory: Path) -> None:
        self._live = live
        self._directory = directory
        self._pending: dict[str, str] = {}
        self._answered: dict[str, Completion[BaseModel]] = {}

    async def complete[T: BaseModel](
        self, prompt: Prompt, *, schema: type[T], tier: ModelTier
    ) -> Completion[T]:
        key = fingerprint(prompt, schema=schema, tier=tier)
        if key in self._answered:
            return Completion(
                value=schema.model_validate(self._answered[key].value.model_dump()),
                usage=self._answered[key].usage,
            )
        completion = await self._live.complete(prompt, schema=schema, tier=tier)
        self._answered[key] = completion
        recording = Recording(
            tier=tier,
            schema=schema.__name__,
            instructions=prompt.instructions,
            utterance=prompt.utterance,
            value=completion.value.model_dump(mode="json"),
            usage=RecordedUsage.model_validate(completion.usage, from_attributes=True),
        )
        self._pending[key] = recording.written()
        return completion

    def commit(self) -> int:
        self._directory.mkdir(parents=True, exist_ok=True)
        for stale in self._directory.glob("*.json"):
            stale.unlink()
        for key, recording in self._pending.items():
            (self._directory / f"{key}.json").write_text(recording)
        return len(self._pending)


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
