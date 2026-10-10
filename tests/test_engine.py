from datetime import time

import pytest

from farkad_ai.extraction.port import Finding
from farkad_ai.pipeline.engine import CaptureEngine
from farkad_ai.pipeline.types import CaptureRequest, Logged, NothingToLog
from farkad_ai.routing.pass_one import Mention, PassOne, StatedTime
from farkad_ai.routing.router import NothingToLogReason
from farkad_ai.types import ModelTier, PipelineStep, Unavailability
from tests.support import AnswersByStep, Registry, Spec, Tracked

pytestmark = pytest.mark.anyio

CATALOGUE = Registry(Spec("water", "tracks water intake"), Spec("food", "logs meals"))
WATER = Tracked("water", title="Water", guidance="Count the glasses.", examples='"a glass" → 1')


def heard(*said: tuple[str, str]) -> PassOne:
    return PassOne(
        transcript=" and ".join(words for _, words in said),
        language="en",
        is_health_related=bool(said),
        mentions=[Mention(pillar=pillar, said=words) for pillar, words in said],
    )


def entries(*items: str | None) -> dict[str, object]:
    return {"entries": [{"pillar": "water", "item": item} for item in items]}


async def captured(model: AnswersByStep, *tracked: Tracked) -> Logged | NothingToLog:
    return await CaptureEngine(model, CATALOGUE).capture(
        CaptureRequest(tracked=tracked, text="said")
    )


def test_stated_time_names_a_day_invariant() -> None:
    assert not StatedTime(phrase="at 3pm", day_offset=0, clock=time(15, 0)).names_a_day
    assert StatedTime(phrase="yesterday at 3pm", day_offset=-1, clock=time(15, 0)).names_a_day


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


async def test_extraction_asks_the_fast_tier_first() -> None:
    model = AnswersByStep(routing=heard(("water", "a glass")), extraction=entries("glass"))

    await captured(model, WATER)

    assert [tier for _, tier in model.asked] == [ModelTier.fast, ModelTier.fast]


async def test_a_refused_pillar_is_reported_with_why() -> None:
    model = AnswersByStep(
        routing=heard(("water", "a glass")), extraction=Unavailability.provider_refused
    )

    outcome = await captured(model, WATER)

    assert isinstance(outcome, Logged) and outcome.extracted == ()
    assert [(r.pillar, r.because) for r in outcome.refused] == [
        ("water", Unavailability.provider_refused)
    ]


async def test_a_capture_naming_no_tracked_pillar_logs_nothing() -> None:
    model = AnswersByStep(routing=heard(("food", "an egg")))

    outcome = await captured(model, WATER)

    assert isinstance(outcome, NothingToLog)
    assert outcome.reason is NothingToLogReason.no_enabled_pillar
