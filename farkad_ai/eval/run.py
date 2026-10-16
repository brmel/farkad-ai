from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from functools import partial

from pydantic import BaseModel, ConfigDict, Field

from farkad_ai.eval.scoring import CaptureScore, score_capture
from farkad_ai.extraction.port import TrackedPillar
from farkad_ai.models.port import Model, ModelUnavailableError, Unavailability
from farkad_ai.pipeline.engine import TwoPassCaptureEngine
from farkad_ai.pipeline.port import CaptureRequest, Logged
from farkad_ai.routing.port import NothingToLog, PillarSpec


class GoldCase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    utterance: str
    routes: tuple[str, ...]
    expected: dict[str, tuple[dict[str, object], ...]] = Field(default_factory=dict)
    flags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Scored[Case: GoldCase]:
    case: Case
    score: CaptureScore


async def evaluate[Case: GoldCase](
    model: Model,
    catalogue: Iterable[PillarSpec],
    tracked: tuple[TrackedPillar, ...],
    cases: Iterable[Case],
    *,
    routing_rules: tuple[str, ...] = (),
) -> tuple[Scored[Case], ...]:
    engine = TwoPassCaptureEngine(model, catalogue, routing_rules=routing_rules)
    return tuple([Scored(case, await _scored(engine, tracked, case)) for case in cases])


async def _scored(
    engine: TwoPassCaptureEngine, tracked: tuple[TrackedPillar, ...], case: GoldCase
) -> CaptureScore:
    scored = partial(
        score_capture,
        utterance=case.utterance,
        expected_routes=case.routes,
        expected=case.expected,
        expected_flags=case.flags,
    )
    try:
        outcome = await engine.capture(CaptureRequest(tracked=tracked, text=case.utterance))
    except ModelUnavailableError as unavailable:
        if unavailable.because is not Unavailability.output_did_not_parse:
            raise
        return scored(routed=(), extracted={}, unparsed_response_from=unavailable.model)
    match outcome:
        case Logged(routes=routes, extracted=extracted):
            pass
        case NothingToLog():
            routes, extracted = frozenset(), ()
    return scored(
        routed=sorted(routes),
        extracted={each.pillar: [entry.values for entry in each.entries] for each in extracted},
        usages=outcome.usages,
        flagged=[
            f"{each.pillar}.{finding.field}"
            for each in extracted
            for entry in each.entries
            for finding in entry.findings
        ],
    )
