from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel

from farkad_ai.models.port import ModelPort
from farkad_ai.models.pricing import InputModality, modality_of, price_of
from farkad_ai.types import Completion, ModelTier, Prompt, Usage


class NoRecordedResponseError(Exception):
    def __init__(self, key: str, directory: Path, because: str | None = None) -> None:
        super().__init__(
            f"no recorded response {key} in {directory}"
            + (f" — {because}" if because is not None else "")
            + "; record one with RecordingModel against the live provider "
            "rather than writing it"
        )
        self.key = key
        self.because = because


PROMPT_CHANGED = (
    "the same utterance is recorded against different instructions, so the prompt "
    "changed and every recording made against the old one is now unreachable"
)


class UnrecordedModelError(Exception):
    def __init__(self, key: str, tier: ModelTier, *, pinned: str, recorded: str) -> None:
        super().__init__(
            f"the {tier} tier is pinned to {pinned}, but {key}.json holds {recorded}'s "
            f"answer; re-record with `make record-fixtures` — replaying {recorded} would "
            f"report a score and a cost {pinned} has never produced"
        )
        self.pinned = pinned
        self.recorded = recorded


def fingerprint(prompt: Prompt, *, schema: type[BaseModel], tier: ModelTier) -> str:
    canonical = json.dumps(
        {
            "tier": tier.value,
            "schema": schema.__name__,
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


def repriced(counted: Usage, *, input_modality: InputModality) -> Usage:
    return counted.model_copy(
        update={
            "cost_cents": price_of(counted.model).cost_cents(
                input_tokens=counted.input_tokens,
                output_tokens=counted.output_tokens,
                input_modality=input_modality,
            )
        }
    )


class RecordedModel(ModelPort):
    def __init__(
        self,
        directory: Path,
        expected_models: Mapping[ModelTier, str] | None = None,
    ) -> None:
        self._directory = directory
        self._expected_models = expected_models

    async def complete[T: BaseModel](
        self, prompt: Prompt, *, schema: type[T], tier: ModelTier
    ) -> Completion[T]:
        key = fingerprint(prompt, schema=schema, tier=tier)
        path = self._directory / f"{key}.json"
        if not path.exists():
            raise NoRecordedResponseError(
                key, self._directory, self._diagnose(prompt, schema, tier)
            )
        recording = json.loads(path.read_text())
        counted = Usage.model_validate(
            recording["usage"]
            | {"step": prompt.step, "prompt_version": prompt.instructions_version}
        )
        if self._expected_models is not None and tier in self._expected_models:
            pinned = self._expected_models[tier]
            if counted.model != pinned:
                raise UnrecordedModelError(key, tier, pinned=pinned, recorded=counted.model)
        return Completion(
            value=schema.model_validate(recording["value"]),
            usage=repriced(counted, input_modality=modality_of(prompt)),
        )

    def _diagnose(self, prompt: Prompt, schema: type[BaseModel], tier: ModelTier) -> str | None:
        for path in sorted(self._directory.glob("*.json")):
            recorded = json.loads(path.read_text())
            if (
                recorded.get("tier") == tier.value
                and recorded.get("schema") == schema.__name__
                and recorded.get("utterance") == prompt.utterance
                and recorded.get("instructions") != prompt.instructions
            ):
                return PROMPT_CHANGED
        return None


class RecordingModel(ModelPort):
    def __init__(self, live: ModelPort, directory: Path) -> None:
        self._live = live
        self._directory = directory
        self._pending: dict[str, str] = {}

    async def complete[T: BaseModel](
        self, prompt: Prompt, *, schema: type[T], tier: ModelTier
    ) -> Completion[T]:
        completion = await self._live.complete(prompt, schema=schema, tier=tier)
        recording = {
            "tier": tier.value,
            "schema": schema.__name__,
            "instructions": prompt.instructions,
            "utterance": prompt.utterance,
            "value": completion.value.model_dump(mode="json"),
            "usage": completion.usage.model_dump(mode="json", exclude={"step", "prompt_version"}),
        }
        key = fingerprint(prompt, schema=schema, tier=tier)
        self._pending[key] = json.dumps(recording, indent=2) + "\n"
        return completion

    def commit(self) -> int:
        self._directory.mkdir(parents=True, exist_ok=True)
        for key, recording in self._pending.items():
            (self._directory / f"{key}.json").write_text(recording)
        return len(self._pending)
