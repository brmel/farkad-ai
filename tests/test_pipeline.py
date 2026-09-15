from collections.abc import Iterator
from datetime import time
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest
from farkad_ai.extraction.port import (
    ExtractionResult,
    Finding,
    PillarConfigProtocol,
    PillarExtractionPort,
)
from farkad_ai.models.port import ModelPort
from farkad_ai.pipeline import (
    CaptureRequest,
    FailureReason,
    Logged,
    build_pipeline,
)
from farkad_ai.routing.pass_one import PassOne, PillarSpecProtocol, StatedTime, TimeHint
from farkad_ai.routing.router import NothingToLogReason
from farkad_ai.types import (
    Completion,
    ModelTier,
    ModelUnavailableError,
    PipelineStep,
    Unavailability,
    Usage,
)


class MockSpec:
    def __init__(self, pillar: str, intent: str) -> None:
        self.pillar = pillar
        self.intent = intent


class MockRegistry:
    def __init__(self) -> None:
        self._specs: list[PillarSpecProtocol] = [
            MockSpec("water", "tracks water intake"),
        ]

    def __iter__(self) -> Iterator[PillarSpecProtocol]:
        return iter(self._specs)

    def knows(self, route: str) -> bool:
        return route == "water"


class MockPillarConfig(PillarConfigProtocol):
    def __init__(self, pillar: str) -> None:
        self._pillar = pillar

    @property
    def pillar(self) -> str:
        return self._pillar


class MockProfile:
    def restrict(self, pillars: frozenset[str]) -> frozenset[str]:
        return pillars

    def config_for(self, pillar: str) -> PillarConfigProtocol:
        return MockPillarConfig(pillar)


def sample_usage(step: PipelineStep) -> Usage:
    return Usage(
        step=step,
        model="gemini-2.5-flash-lite",
        prompt_version="v1",
        input_tokens=20,
        output_tokens=10,
        latency_ms=100,
        cost_cents=Decimal("0.002"),
    )


def test_stated_time_names_a_day_invariant() -> None:
    today = StatedTime(phrase="at 3pm", day_offset=0, clock=time(15, 0))
    yesterday = StatedTime(phrase="yesterday at 3pm", day_offset=-1, clock=time(15, 0))
    last_week = StatedTime(phrase="last monday", day_offset=-7, clock=None)

    assert not today.names_a_day
    assert yesterday.names_a_day
    assert last_week.names_a_day


def test_nothing_to_log_reasons_contain_expected_members() -> None:
    assert NothingToLogReason.not_a_health_log == "not_a_health_log"
    assert NothingToLogReason.no_enabled_pillar == "no_enabled_pillar"
    assert len(NothingToLogReason) == 2


@pytest.mark.anyio
async def test_build_pipeline_runs_capture_successfully() -> None:
    model = Mock(spec=ModelPort)
    model.complete = AsyncMock(
        return_value=Completion(
            value=PassOne(
                transcript="Drank 500ml of water",
                language="en",
                is_health_related=True,
                routes=["water"],
                occurred_at_hint=TimeHint(phrase="at 10am", day_offset=0, clock=time(10, 0)),
            ),
            usage=sample_usage(PipelineStep.routing),
        )
    )

    extractor = Mock(spec=PillarExtractionPort)
    extractor.extract = AsyncMock(
        return_value=ExtractionResult(
            pillar="water",
            entries=({"volume_ml": 500},),
            findings=(Finding(field="volume_ml", reason="valid"),),
            usage=sample_usage(PipelineStep.extraction),
        )
    )

    pipeline = build_pipeline(model, MockRegistry(), extractor)
    request = CaptureRequest(
        profile=MockProfile(),
        text="Drank 500ml of water",
        media=(),
    )
    outcome = await pipeline.run(request)

    match outcome:
        case Logged():
            assert outcome.routes == frozenset({"water"})
            assert len(outcome.extracted) == 1
            assert outcome.extracted[0].pillar == "water"
            assert outcome.extracted[0].entries == ({"volume_ml": 500},)
            assert len(outcome.refused) == 0
        case _:
            pytest.fail(f"Expected Logged, got {outcome}")


@pytest.mark.anyio
async def test_pipeline_records_refused_with_typed_failure_reason() -> None:
    model = Mock(spec=ModelPort)
    model.complete = AsyncMock(
        return_value=Completion(
            value=PassOne(
                transcript="Drank water",
                language="en",
                is_health_related=True,
                routes=["water"],
                occurred_at_hint=None,
            ),
            usage=sample_usage(PipelineStep.routing),
        )
    )

    extractor = Mock(spec=PillarExtractionPort)
    extractor.extract = AsyncMock(
        side_effect=ModelUnavailableError(
            tier=ModelTier.standard,
            model="gemini-2.5-flash",
            because=Unavailability.provider_refused,
            detail="service overloaded",
        )
    )

    pipeline = build_pipeline(model, MockRegistry(), extractor)
    request = CaptureRequest(
        profile=MockProfile(),
        text="Drank water",
        media=(),
    )
    outcome = await pipeline.run(request)

    match outcome:
        case Logged():
            assert len(outcome.extracted) == 0
            assert len(outcome.refused) == 1
            refused = outcome.refused[0]
            assert refused.pillar == "water"
            assert refused.reason is FailureReason.model_error
        case _:
            pytest.fail(f"Expected Logged, got {outcome}")
