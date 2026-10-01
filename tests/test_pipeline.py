from datetime import time

import pytest

from farkad_ai.pipeline import CaptureRequest, FailureReason, Logged, build_pipeline
from farkad_ai.routing.pass_one import Mention, PassOne, StatedTime
from farkad_ai.routing.router import NothingToLogReason
from farkad_ai.types import Unavailability
from tests.support import (
    Profile,
    RefusingExtractor,
    Registry,
    ScriptedModel,
    Spec,
    SuccessfulExtractor,
)

WATER = Registry(Spec("water", "tracks water intake"))


def routing_to_water(transcript: str) -> ScriptedModel:
    return ScriptedModel(
        PassOne(
            transcript=transcript,
            language="en",
            is_health_related=True,
            mentions=[Mention(pillar="water", said=transcript)],
        )
    )


def test_stated_time_names_a_day_invariant() -> None:
    assert not StatedTime(phrase="at 3pm", day_offset=0, clock=time(15, 0)).names_a_day
    assert StatedTime(phrase="yesterday at 3pm", day_offset=-1, clock=time(15, 0)).names_a_day
    assert StatedTime(phrase="last monday", day_offset=-7, clock=None).names_a_day


def test_nothing_to_log_reasons_contain_expected_members() -> None:
    assert NothingToLogReason.not_a_health_log == "not_a_health_log"
    assert NothingToLogReason.no_enabled_pillar == "no_enabled_pillar"
    assert len(NothingToLogReason) == 2


@pytest.mark.anyio
async def test_build_pipeline_runs_capture_successfully() -> None:
    pipeline = build_pipeline(
        routing_to_water("Drank 500ml of water"), WATER, SuccessfulExtractor("specialist")
    )
    request = CaptureRequest(profile=Profile("water"), text="Drank 500ml of water", media=())
    outcome = await pipeline.run(request)
    assert isinstance(outcome, Logged)
    assert outcome.routes == frozenset({"water"})
    assert len(outcome.extracted) == 1
    assert outcome.extracted[0].pillar == "water"
    assert [entry.values for entry in outcome.extracted[0].entries] == [{"item": "specialist"}]
    assert len(outcome.refused) == 0


@pytest.mark.anyio
async def test_a_specialist_is_told_what_it_records() -> None:
    specialist = SuccessfulExtractor("specialist")
    pipeline = build_pipeline(routing_to_water("Drank 500ml of water"), WATER, specialist)

    await pipeline.run(CaptureRequest(profile=Profile("water"), text="Drank 500ml of water"))

    assert specialist.told == {"water": ("Drank 500ml of water",)}


@pytest.mark.anyio
async def test_pipeline_records_refused_with_typed_failure_reason() -> None:
    pipeline = build_pipeline(
        routing_to_water("Drank water"),
        WATER,
        RefusingExtractor(Unavailability.provider_refused),
    )
    request = CaptureRequest(profile=Profile("water"), text="Drank water", media=())
    outcome = await pipeline.run(request)
    assert isinstance(outcome, Logged)
    assert len(outcome.extracted) == 0
    assert len(outcome.refused) == 1
    assert outcome.refused[0].pillar == "water"
    assert outcome.refused[0].reason is FailureReason.model_error
