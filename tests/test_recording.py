"""Vertex answers a spent quota with 429, so a recording run can stop at any answer."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import BaseModel

from farkad_ai.models.port import (
    Completion,
    MediaBlob,
    MediaType,
    ModelChoice,
    ModelTier,
    PipelineStep,
    Prompt,
    fixed,
)
from farkad_ai.models.recorded import (
    NoRecordedResponseError,
    RecordedModel,
    RecordingModel,
    Unreachable,
    UnrecordedModelError,
    fingerprint,
)
from tests.support import a_usage

pytestmark = pytest.mark.anyio


class Answer(BaseModel):
    said: str


class QuotaLimitedModel:
    def __init__(self, before_failing: int) -> None:
        self._answers_left = before_failing

    async def complete[T: BaseModel](
        self, prompt: Prompt, *, schema: type[T], tier: ModelTier
    ) -> Completion[T]:
        if self._answers_left == 0:
            raise RuntimeError("ClientError 429")
        self._answers_left -= 1
        return Completion(value=schema(said=prompt.utterance), usage=a_usage(prompt.step))


def said_back(utterance: str, *media: MediaBlob) -> Prompt:
    return Prompt(
        step=PipelineStep.routing,
        instructions="say it back",
        instructions_version="v1",
        utterance=utterance,
        media=media,
    )


async def record(
    model: QuotaLimitedModel, directory: Path, utterances: list[str]
) -> RecordingModel:
    recorder = RecordingModel(model, directory)
    for utterance in utterances:
        await recorder.complete(said_back(utterance), schema=Answer, tier=ModelTier.fast)
    return recorder


async def test_an_existing_set_survives_a_failed_run(tmp_path: Path) -> None:
    (tmp_path / "already-here.json").write_text('{"kept": true}\n')

    with pytest.raises(RuntimeError):
        await record(QuotaLimitedModel(before_failing=1), tmp_path, ["one", "two"])

    assert [path.name for path in tmp_path.glob("*.json")] == ["already-here.json"]
    assert (tmp_path / "already-here.json").read_text() == '{"kept": true}\n'


async def test_committing_twice_is_not_two_sets(tmp_path: Path) -> None:
    recorder = await record(QuotaLimitedModel(before_failing=2), tmp_path, ["one", "two"])
    recorder.commit()

    assert recorder.commit() == 2
    assert len(list(tmp_path.glob("*.json"))) == 2


async def test_a_commit_replaces_the_recordings_already_there(tmp_path: Path) -> None:
    (tmp_path / "stale.json").write_text('{"stale": true}\n')
    recorder = await record(QuotaLimitedModel(before_failing=1), tmp_path, ["one"])

    assert recorder.commit() == 1
    assert not (tmp_path / "stale.json").exists()
    assert len(list(tmp_path.glob("*.json"))) == 1


class Reworded(BaseModel):
    said: str
    loudly: bool = False


@pytest.mark.parametrize(
    ("asked", "schema", "because"),
    [
        (said_back("one"), type("Answer", (Reworded,), {}), Unreachable.schema_changed),
        (replace(said_back("one"), instructions="twice"), Answer, Unreachable.prompt_changed),
        (said_back("two"), Answer, Unreachable.never_recorded),
    ],
    ids=["schema", "prompt", "never recorded"],
)
async def test_a_missing_recording_says_why_it_is_missing(
    tmp_path: Path, asked: Prompt, schema: type[BaseModel], because: Unreachable
) -> None:
    (await record(QuotaLimitedModel(before_failing=1), tmp_path, ["one"])).commit()

    with pytest.raises(NoRecordedResponseError) as missing:
        await RecordedModel(tmp_path).complete(asked, schema=schema, tier=ModelTier.fast)

    assert missing.value.because is because


async def test_only_a_recording_answered_by_the_pinned_model_replays(tmp_path: Path) -> None:
    (await record(QuotaLimitedModel(before_failing=1), tmp_path, ["one"])).commit()
    answered_by = a_usage(PipelineStep.routing).model

    def pinned_to(model: str) -> RecordedModel:
        return RecordedModel(tmp_path, pinned=fixed({ModelTier.fast: ModelChoice(model)}))

    with pytest.raises(UnrecordedModelError) as unrecorded:
        await pinned_to("gemini-3.5-flash").complete(
            said_back("one"), schema=Answer, tier=ModelTier.fast
        )

    assert (unrecorded.value.recorded, unrecorded.value.pinned) == (answered_by, "gemini-3.5-flash")
    replayed = await pinned_to(answered_by).complete(
        said_back("one"), schema=Answer, tier=ModelTier.fast
    )
    assert replayed.usage.model == answered_by


async def test_a_question_asked_twice_in_a_run_is_answered_once(tmp_path: Path) -> None:
    recorder = await record(QuotaLimitedModel(before_failing=1), tmp_path, ["one", "one"])

    assert recorder.commit() == 1


def test_a_recording_is_keyed_by_its_tier_and_the_audio_it_carried() -> None:
    key = fingerprint(said_back("one"), schema=Answer, tier=ModelTier.fast)
    spoken = said_back("one", MediaBlob(content_type=MediaType.audio_aac, data=b"clip"))

    other_clip = said_back("one", MediaBlob(content_type=MediaType.audio_aac, data=b"other clip"))

    assert key == fingerprint(said_back("one"), schema=Answer, tier=ModelTier.fast)
    assert key != fingerprint(said_back("one"), schema=Answer, tier=ModelTier.standard)
    assert key != fingerprint(spoken, schema=Answer, tier=ModelTier.fast)
    assert fingerprint(spoken, schema=Answer, tier=ModelTier.fast) != fingerprint(
        other_clip, schema=Answer, tier=ModelTier.fast
    )


async def test_a_recorded_completion_replays_with_its_usage(tmp_path: Path) -> None:
    recorder = RecordingModel(QuotaLimitedModel(before_failing=1), tmp_path)
    recorded = await recorder.complete(said_back("one"), schema=Answer, tier=ModelTier.fast)
    recorder.commit()

    replayed = await RecordedModel(tmp_path).complete(
        said_back("one"), schema=Answer, tier=ModelTier.fast
    )

    assert replayed == recorded


async def test_a_replayed_answer_carries_the_prompt_version_asked(tmp_path: Path) -> None:
    (await record(QuotaLimitedModel(before_failing=1), tmp_path, ["one"])).commit()
    asked = replace(said_back("one"), instructions_version="v2")

    replayed = await RecordedModel(tmp_path).complete(asked, schema=Answer, tier=ModelTier.fast)

    assert replayed.usage.prompt_version == "v2"
