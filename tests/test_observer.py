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
    ExtractionCompleted,
    ExtractionStarted,
    RouteCompleted,
    RouteStarted,
    TraceObserver,
    build_pipeline,
)
from farkad_ai.routing.pass_one import PassOne, TimeHint
from farkad_ai.types import Completion, PipelineStep, Usage


class Spec:
    def __init__(self, pillar: str, intent: str) -> None:
        self.pillar = pillar
        self.intent = intent


class Registry:
    def __init__(self) -> None:
        self._specs = [Spec("water", "water intake"), Spec("sleep", "sleep duration")]

    def __iter__(self) -> Iterator[Spec]:
        return iter(self._specs)

    def knows(self, route: str) -> bool:
        return route in {"water", "sleep"}


class Profile:
    def restrict(self, pillars: frozenset[str]) -> frozenset[str]:
        return pillars

    def config_for(self, pillar: str) -> PillarConfigProtocol:
        mock = Mock(spec=PillarConfigProtocol)
        mock.pillar = pillar
        return mock


def sample_usage(step: PipelineStep) -> Usage:
    return Usage(
        step=step,
        model="gemini-2.5-flash-lite",
        prompt_version="v1",
        input_tokens=10,
        output_tokens=5,
        latency_ms=50,
        cost_cents=Decimal("0.001"),
    )


@pytest.mark.anyio
async def test_trace_observer_records_all_pipeline_lifecycle_events() -> None:
    model = Mock(spec=ModelPort)
    model.complete = AsyncMock(
        return_value=Completion(
            value=PassOne(
                transcript="Drank 2 glasses of water",
                language="en",
                is_health_related=True,
                routes=["water"],
                occurred_at_hint=TimeHint(phrase="now", day_offset=0, clock=time(12, 0)),
            ),
            usage=sample_usage(PipelineStep.routing),
        )
    )

    extractor = Mock(spec=PillarExtractionPort)
    extractor.extract = AsyncMock(
        return_value=ExtractionResult(
            pillar="water",
            entries=({"volume_ml": 500},),
            findings=(Finding(field="volume_ml", reason="ok"),),
            usage=sample_usage(PipelineStep.extraction),
        )
    )

    observer = TraceObserver()
    pipeline = build_pipeline(model, Registry(), extractor, observer=observer)
    request = CaptureRequest(profile=Profile(), text="Drank 2 glasses of water")
    outcome = await pipeline.run(request)
    assert outcome is not None

    assert len(observer.events) == 4
    assert isinstance(observer.events[0], RouteStarted)
    assert observer.events[0].utterance == "Drank 2 glasses of water"
    assert isinstance(observer.events[1], RouteCompleted)
    assert isinstance(observer.events[2], ExtractionStarted)
    assert observer.events[2].pillar == "water"
    assert isinstance(observer.events[3], ExtractionCompleted)
    assert observer.events[3].pillar == "water"

    routes = observer.routes()
    assert len(routes) == 1
    assert routes[0].outcome == observer.events[1].outcome
    extractions = observer.extractions()
    assert len(extractions) == 1
    assert extractions[0].pillar == "water"
