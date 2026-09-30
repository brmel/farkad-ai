"""Vertex answers a spent quota with 429, so a recording run can stop at any answer."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel

from farkad_ai.models.recorded import RecordingModel
from farkad_ai.types import Completion, ModelTier, PipelineStep, Prompt
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


async def record(
    model: QuotaLimitedModel, directory: Path, utterances: list[str]
) -> RecordingModel:
    recorder = RecordingModel(model, directory)
    for utterance in utterances:
        await recorder.complete(
            Prompt(
                step=PipelineStep.routing,
                instructions="say it back",
                instructions_version="v1",
                utterance=utterance,
            ),
            schema=Answer,
            tier=ModelTier.fast,
        )
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
