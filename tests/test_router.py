from collections.abc import Iterator
from datetime import time
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest
from farkad_ai.models.port import ModelPort
from farkad_ai.routing.pass_one import PassOne, PillarSpecProtocol, TimeHint
from farkad_ai.routing.router import NotApplicable, Routed, Router
from farkad_ai.types import Completion, PipelineStep, Usage


class DummySpec:
    def __init__(self, pillar: str, intent: str) -> None:
        self.pillar = pillar
        self.intent = intent


class DummyRegistry:
    def __init__(self) -> None:
        self._specs: list[PillarSpecProtocol] = [
            DummySpec("nutrition", "logs food and drinks"),
            DummySpec("movement", "logs exercise and steps"),
        ]

    def __iter__(self) -> Iterator[PillarSpecProtocol]:
        return iter(self._specs)

    def knows(self, route: str) -> bool:
        return route in {"nutrition", "movement"}


class DummyProfile:
    def restrict(self, pillars: frozenset[str]) -> frozenset[str]:
        return pillars


def make_usage() -> Usage:
    return Usage(
        step=PipelineStep.routing,
        model="gemini-2.5-flash",
        prompt_version="v1",
        input_tokens=10,
        output_tokens=5,
        latency_ms=120,
        cost_cents=Decimal("0.001"),
    )


@pytest.mark.anyio
async def test_router_routes_applicable_capture() -> None:
    model = Mock(spec=ModelPort)
    model.complete = AsyncMock(
        return_value=Completion(
            value=PassOne(
                transcript="Ate lunch at 12:30",
                language="en",
                is_health_related=True,
                routes=["nutrition", "movement"],
                occurred_at_hint=TimeHint(phrase="at 12:30", day_offset=0, clock=time(12, 30)),
            ),
            usage=make_usage(),
        )
    )
    router = Router(model, DummyRegistry())
    outcome = await router.route(DummyProfile(), text="Ate lunch at 12:30", media=())
    match outcome:
        case Routed():
            assert outcome.pillars == frozenset({"nutrition", "movement"})
            assert outcome.occurred_at_hint is not None
            assert outcome.occurred_at_hint.clock == time(12, 30)
            assert outcome.occurred_at_hint.day_offset == 0
        case _:
            pytest.fail(f"Expected Routed, got {outcome}")


@pytest.mark.anyio
async def test_router_returns_not_applicable_when_not_health() -> None:
    model = Mock(spec=ModelPort)
    model.complete = AsyncMock(
        return_value=Completion(
            value=PassOne(
                transcript="Hello world nothing to log",
                language="en",
                is_health_related=False,
                routes=[],
                occurred_at_hint=None,
            ),
            usage=make_usage(),
        )
    )
    router = Router(model, DummyRegistry())
    outcome = await router.route(DummyProfile(), text="Hello world nothing to log", media=())
    match outcome:
        case NotApplicable():
            assert outcome.reason.value == "not_a_health_log"
        case _:
            pytest.fail(f"Expected NotApplicable, got {outcome}")
