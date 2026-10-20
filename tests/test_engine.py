import asyncio
from collections.abc import Mapping

import pytest
from pydantic import BaseModel

from farkad_ai.extraction.port import Finding
from farkad_ai.models.port import (
    Completion,
    ModelTier,
    ModelUnavailableError,
    PipelineStep,
    Prompt,
    Unavailability,
)
from farkad_ai.pipeline.engine import TwoPassCaptureEngine
from farkad_ai.pipeline.port import CaptureRequest, Logged
from farkad_ai.routing.pass_one import Mention, PassOne
from farkad_ai.routing.port import NothingToLog, NothingToLogReason
from tests.support import AnswersByStep, Spec, Tracked

pytestmark = pytest.mark.anyio

CATALOGUE = (Spec("water", "tracks water intake"), Spec("food", "logs meals"))
WATER = Tracked("water", title="Water", guidance="Count the glasses.", examples='"a glass" → 1')


def heard(*said: tuple[str, str], states_a_lasting_fact: bool = False) -> PassOne:
    return PassOne(
        transcript=" and ".join(words for _, words in said),
        language="en",
        is_health_related=bool(said),
        states_a_lasting_fact=states_a_lasting_fact,
        mentions=[Mention(pillar=pillar, said=words) for pillar, words in said],
    )


def entries(*items: str | None) -> dict[str, object]:
    return {"entries": [{"pillar": "water", "item": item} for item in items]}


class RefusesToHear(AnswersByStep):
    def __init__(self, refused: str, **answers: BaseModel | dict[str, object]) -> None:
        super().__init__(**answers)
        self._refused = refused

    async def complete[T: BaseModel](
        self, prompt: Prompt, *, schema: type[T], tier: ModelTier
    ) -> Completion[T]:
        if prompt.utterance == self._refused:
            raise ModelUnavailableError(tier, "model", Unavailability.provider_refused, "detail")
        return await super().complete(prompt, schema=schema, tier=tier)


class BreaksOnExtraction(AnswersByStep):
    async def complete[T: BaseModel](
        self, prompt: Prompt, *, schema: type[T], tier: ModelTier
    ) -> Completion[T]:
        if prompt.step is PipelineStep.extraction:
            raise KeyError("entries")
        return await super().complete(prompt, schema=schema, tier=tier)


class Overlapping(AnswersByStep):
    def __init__(self, **answers: BaseModel | Mapping[str, object] | Unavailability) -> None:
        super().__init__(**answers)
        self._in_flight = 0
        self.most_at_once = 0

    async def complete[T: BaseModel](
        self, prompt: Prompt, *, schema: type[T], tier: ModelTier
    ) -> Completion[T]:
        self._in_flight += 1
        self.most_at_once = max(self.most_at_once, self._in_flight)
        try:
            await asyncio.sleep(0)
            return await super().complete(prompt, schema=schema, tier=tier)
        finally:
            self._in_flight -= 1


async def captured(model: AnswersByStep, *tracked: Tracked) -> Logged | NothingToLog:
    return await TwoPassCaptureEngine(model, CATALOGUE).capture(
        CaptureRequest(tracked=tracked, text="said")
    )


async def test_each_tracked_pillar_named_comes_back_with_its_entries() -> None:
    model = AnswersByStep(routing=heard(("water", "a glass")), extraction=entries("glass"))

    outcome = await captured(model, WATER)

    assert isinstance(outcome, Logged)
    assert outcome.routes == frozenset({"water"})
    assert [entry.values for entry in outcome.extracted[0].entries] == [
        {"pillar": "water", "item": "glass"}
    ]
    assert outcome.refused == ()
    assert [usage.step for usage in outcome.usages] == ["routing", "extraction"]


async def test_the_pillars_a_capture_names_are_extracted_at_the_same_time() -> None:
    model = Overlapping(
        routing=heard(("water", "a glass"), ("food", "an egg")), extraction=entries("glass")
    )

    await captured(model, WATER, Tracked("food"))

    assert model.most_at_once == 2


async def test_a_lasting_fact_stated_beside_a_log_is_reported_with_it() -> None:
    model = AnswersByStep(
        routing=heard(("water", "a glass"), states_a_lasting_fact=True),
        extraction=entries("glass"),
    )

    outcome = await captured(model, WATER)

    assert isinstance(outcome, Logged) and outcome.states_a_lasting_fact


async def test_the_specialist_is_asked_only_what_its_pillar_records() -> None:
    model = AnswersByStep(
        routing=heard(("water", "a glass"), ("food", "an egg")), extraction=entries("glass")
    )

    outcome = await captured(model, WATER)

    assert isinstance(outcome, Logged) and outcome.untracked == frozenset({"food"})
    asked = [prompt for prompt, _ in model.asked if prompt.step is PipelineStep.extraction]
    assert [prompt.utterance for prompt in asked] == ["a glass"]
    assert asked[0].instructions.startswith("Extract every Water entry")
    assert (
        "Count the glasses." in asked[0].instructions and '"a glass" → 1' in asked[0].instructions
    )


async def test_an_entry_that_holds_nothing_is_dropped_and_findings_stay_on_theirs() -> None:
    flagged = Tracked("water", flagged=(Finding(field="item", reason="implausible"),))
    model = AnswersByStep(routing=heard(("water", "a glass")), extraction=entries(None, "glass"))

    outcome = await captured(model, flagged)

    assert isinstance(outcome, Logged)
    (entry,) = outcome.extracted[0].entries
    assert entry.values["item"] == "glass" and entry.stale_fields == frozenset({"item"})


async def test_which_fields_only_label_an_entry_is_the_pillars_to_declare() -> None:
    labelled_by_item = Tracked("water", label_fields=frozenset({"pillar", "item"}))
    model = AnswersByStep(routing=heard(("water", "a glass")), extraction=entries("glass"))

    outcome = await captured(model, labelled_by_item)

    assert isinstance(outcome, Logged) and outcome.extracted[0].entries == ()


async def test_extraction_asks_the_fast_tier_first() -> None:
    model = AnswersByStep(routing=heard(("water", "a glass")), extraction=entries("glass"))

    await captured(model, WATER)

    assert [tier for _, tier in model.asked] == [ModelTier.fast, ModelTier.fast]


async def test_a_refused_pillar_is_reported_with_why_and_the_other_keeps_its_entries() -> None:
    model = RefusesToHear(
        "an egg",
        routing=heard(("water", "a glass"), ("food", "an egg")),
        extraction=entries("glass"),
    )

    outcome = await captured(model, WATER, Tracked("food"))

    assert isinstance(outcome, Logged)
    assert [(r.pillar, r.because) for r in outcome.refused] == [
        ("food", Unavailability.provider_refused)
    ]
    assert [
        (extracted.pillar, [entry.values["item"] for entry in extracted.entries])
        for extracted in outcome.extracted
    ] == [("water", ["glass"])]


async def test_a_bug_in_a_specialist_is_raised_not_reported_as_refused() -> None:
    model = BreaksOnExtraction(routing=heard(("water", "a glass")))

    with pytest.raises(KeyError):
        await captured(model, WATER)


async def test_a_capture_naming_no_tracked_pillar_logs_nothing() -> None:
    model = AnswersByStep(routing=heard(("food", "an egg")))

    outcome = await captured(model, WATER)

    assert isinstance(outcome, NothingToLog)
    assert outcome.reason is NothingToLogReason.no_enabled_pillar
