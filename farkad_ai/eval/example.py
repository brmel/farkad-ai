from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from farkad_ai.eval.run import GoldCase, Scored, evaluate
from farkad_ai.eval.scoring import RunScore
from farkad_ai.examples import EXAMPLE_PILLARS, ExampleCatalogue
from farkad_ai.models.port import Model

RECORDINGS = Path(__file__).parent / "recordings"
GOLD = Path(__file__).parent / "example_gold.json"


class Language(StrEnum):
    en = "en"
    fr = "fr"
    ar = "ar"
    es = "es"
    code_switched = "code-switched"


class ExampleCase(GoldCase):
    language: Language


class ExampleGold(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    why: str
    cases: tuple[ExampleCase, ...]


type ExampleRun = tuple[Scored[ExampleCase], ...]


async def evaluate_examples(model: Model) -> ExampleRun:
    gold = ExampleGold.model_validate_json(GOLD.read_text(encoding="utf-8"))
    return await evaluate(model, ExampleCatalogue(), EXAMPLE_PILLARS, gold.cases)


def report(run: ExampleRun) -> str:
    rows = [
        "| Language | Captures | Routing | Fields | Tokens in / out | p95 in / out |",
        "| --- | --: | --: | --: | --: | --: |",
    ]
    for language in Language:
        rows.append(_row(language.value, [each for each in run if each.case.language is language]))
    rows.append(_row("all", list(run)))
    models = sorted({usage.model for each in run for usage in each.score.usages})
    return (
        "\n".join(
            [*rows, "", f"Model: {', '.join(models)}", *(f"Miss: {miss}" for miss in _misses(run))]
        )
        + "\n"
    )


def _row(label: str, scored: list[Scored[ExampleCase]]) -> str:
    score = RunScore(tuple(each.score for each in scored))
    mean_in = score.mean(lambda capture: capture.input_tokens)
    mean_out = score.mean(lambda capture: capture.output_tokens)
    p95_in = score.p95(lambda capture: capture.input_tokens)
    p95_out = score.p95(lambda capture: capture.output_tokens)
    return (
        f"| {label} | {len(scored)} | {score.routing_accuracy:.0%} | "
        f"{score.field_accuracy:.0%} | {mean_in:.0f} / {mean_out:.0f} | "
        f"{p95_in:.0f} / {p95_out:.0f} |"
    )


def _misses(run: ExampleRun) -> list[str]:
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
