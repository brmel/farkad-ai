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
    PROMPT_CHANGED,
    SCHEMA_CHANGED,
    NoRecordedResponseError,
    RecordedModel,
    RecordingModel,
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


async def test_a_run_that_finishes_writes_its_recordings(tmp_path: Path) -> None:
    recorder = await record(QuotaLimitedModel(before_failing=3), tmp_path, ["one", "two", "three"])

    assert recorder.commit() == 3
    assert len(list(tmp_path.glob("*.json"))) == 3


async def test_a_run_that_dies_part_way_writes_nothing(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError):
        await record(QuotaLimitedModel(before_failing=2), tmp_path, ["one", "two", "three"])

    assert list(tmp_path.glob("*.json")) == []


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


async def test_a_schema_changed_under_the_same_name_is_not_replayed(tmp_path: Path) -> None:
    (await record(QuotaLimitedModel(before_failing=1), tmp_path, ["one"])).commit()
    changed = type("Answer", (Reworded,), {})
    asked = Prompt(
        step=PipelineStep.routing,
        instructions="say it back",
        instructions_version="v1",
        utterance="one",
    )

    with pytest.raises(NoRecordedResponseError) as missing:
        await RecordedModel(tmp_path).complete(asked, schema=changed, tier=ModelTier.fast)

    assert missing.value.because == SCHEMA_CHANGED
    replayed = await RecordedModel(tmp_path).complete(asked, schema=Answer, tier=ModelTier.fast)
    assert replayed.value == Answer(said="one")


async def test_a_recording_made_against_other_instructions_says_the_prompt_changed(
    tmp_path: Path,
) -> None:
    (await record(QuotaLimitedModel(before_failing=1), tmp_path, ["one"])).commit()
    reworded = replace(said_back("one"), instructions="say it twice")

    with pytest.raises(NoRecordedResponseError) as missing:
        await RecordedModel(tmp_path).complete(reworded, schema=Answer, tier=ModelTier.fast)

    assert missing.value.because == PROMPT_CHANGED
    assert "the prompt changed" in str(missing.value)


async def test_an_utterance_never_recorded_has_no_diagnosis(tmp_path: Path) -> None:
    (await record(QuotaLimitedModel(before_failing=1), tmp_path, ["one"])).commit()

    with pytest.raises(NoRecordedResponseError) as missing:
        await RecordedModel(tmp_path).complete(said_back("two"), schema=Answer, tier=ModelTier.fast)

    assert missing.value.because is None


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
