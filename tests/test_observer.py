import pytest

from farkad_ai.pipeline import (
    CaptureRequest,
    ExtractionCompleted,
    ExtractionStarted,
    RouteCompleted,
    RouteStarted,
    TraceObserver,
    build_pipeline,
)
from farkad_ai.routing.pass_one import Mention, PassOne
from tests.support import Profile, Registry, ScriptedModel, Spec, SuccessfulExtractor


@pytest.mark.anyio
async def test_trace_observer_records_all_pipeline_lifecycle_events() -> None:
    model = ScriptedModel(
        PassOne(
            transcript="Drank 2 glasses of water",
            language="en",
            is_health_related=True,
            mentions=[Mention(pillar="water", said="2 glasses of water")],
        )
    )
    observer = TraceObserver()
    pipeline = build_pipeline(
        model,
        Registry(Spec("water", "water intake")),
        SuccessfulExtractor("specialist"),
        observer=observer,
    )

    await pipeline.run(CaptureRequest(profile=Profile("water"), text="Drank 2 glasses of water"))

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
