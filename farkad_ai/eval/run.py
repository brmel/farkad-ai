from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from farkad_ai.eval.scoring import CaptureScore, RunScore, score_capture
from farkad_ai.examples import EXAMPLE_PILLARS, ExampleCatalogue
from farkad_ai.models.port import ModelPort
from farkad_ai.models.recorded import RecordingModel
from farkad_ai.pipeline.engine import CaptureEngine
from farkad_ai.pipeline.types import CaptureRequest, Logged, NothingToLog
from farkad_ai.types import Usage

RECORDINGS = Path(__file__).parent / "recordings"
GOLD = Path(__file__).parent / "example_gold.json"


class Language(StrEnum):
    en = "en"
    fr = "fr"
    ar = "ar"
    es = "es"
    code_switched = "code-switched"


class GoldCase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    language: Language
    utterance: str
    routes: tuple[str, ...]
    expected: dict[str, tuple[dict[str, object], ...]] = Field(default_factory=dict)


class GoldSet(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    why: str
    cases: tuple[GoldCase, ...]


@dataclass(frozen=True, slots=True)
class TokenPrice:
    input_usd_per_million: float
    output_usd_per_million: float

    def cents(self, usage: Usage) -> float:
        dollars = (
            usage.input_tokens * self.input_usd_per_million
            + usage.output_tokens * self.output_usd_per_million
        ) / 1_000_000
        return dollars * 100


# Vertex AI's list price for text input: https://cloud.google.com/vertex-ai/generative-ai/pricing
PRICES: Mapping[str, TokenPrice] = {"gemini-3.5-flash-lite": TokenPrice(0.30, 2.50)}


class UnpricedModelError(Exception):
    def __init__(self, model: str) -> None:
        super().__init__(f"no price for {model}; add it to PRICES to measure its cost")
        self.model = model


def cost_cents(usage: Usage) -> float:
    if usage.model not in PRICES:
        raise UnpricedModelError(usage.model)
    return PRICES[usage.model].cents(usage)


@dataclass(frozen=True, slots=True)
class Scored:
    case: GoldCase
    score: CaptureScore
    models: frozenset[str]


async def score_case(engine: CaptureEngine, case: GoldCase) -> Scored:
    outcome = await engine.capture(CaptureRequest(tracked=EXAMPLE_PILLARS, text=case.utterance))
    match outcome:
        case Logged(routes=routes, extracted=extracted):
            found = {each.pillar: [entry.values for entry in each.entries] for each in extracted}
        case NothingToLog():
            routes, found = frozenset(), {}
    score = score_capture(
        utterance=case.utterance,
        expected_routes=case.routes,
        expected=case.expected,
        routed=sorted(routes),
        extracted=found,
        cost_cents=sum(cost_cents(usage) for usage in outcome.usages),
    )
    return Scored(case, score, frozenset(usage.model for usage in outcome.usages))


async def evaluate(model: ModelPort, gold: Path = GOLD) -> tuple[Scored, ...]:
    engine = CaptureEngine(model, ExampleCatalogue())
    cases = GoldSet.model_validate(json.loads(gold.read_text(encoding="utf-8"))).cases
    return tuple([await score_case(engine, case) for case in cases])


def replace_recordings(recorder: RecordingModel) -> int:
    for stale in RECORDINGS.glob("*.json"):
        stale.unlink()
    return recorder.commit()


def report(run: tuple[Scored, ...]) -> str:
    rows = [
        "| Language | Captures | Routing | Fields | Cost per capture |",
        "| --- | --: | --: | --: | --: |",
    ]
    for language in Language:
        rows.append(row(language.value, [each for each in run if each.case.language is language]))
    rows.append(row("all", list(run)))
    models = sorted(frozenset().union(*(each.models for each in run)))
    return (
        "\n".join(
            [*rows, "", f"Model: {', '.join(models)}", *(f"Miss: {miss}" for miss in misses(run))]
        )
        + "\n"
    )


def row(label: str, scored: list[Scored]) -> str:
    score = RunScore(tuple(each.score for each in scored))
    return (
        f"| {label} | {len(scored)} | {score.routing_accuracy:.0%} | "
        f"{score.field_accuracy:.0%} | {score.cost_cents_per_capture:.3f}¢ |"
    )


def misses(run: tuple[Scored, ...]) -> list[str]:
    found = []
    for each in run:
        score = each.score
        if not score.routing_is_exact:
            found.append(
                f"{score.utterance}: routed {sorted(score.routed)}, "
                f"wanted {sorted(score.expected_routes)}"
            )
        found += [
            f"{score.utterance}: {wrong.pillar}.{wrong.field} wanted {wrong.expected!r}, "
            f"got {wrong.found!r}"
            for wrong in score.wrong_fields
        ]
    return found
