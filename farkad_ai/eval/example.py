from __future__ import annotations

import unicodedata
from enum import StrEnum
from pathlib import Path
from statistics import mean

from pydantic import BaseModel, ConfigDict

from farkad_ai.eval.pillars import EXAMPLE_PILLARS
from farkad_ai.eval.run import GoldCase, Scored, evaluate
from farkad_ai.eval.scoring import RunScore
from farkad_ai.eval.words import words
from farkad_ai.models.port import Model

RECORDINGS = Path(__file__).parent / "recordings"
GOLD = Path(__file__).parent / "example_gold.json"


class Language(StrEnum):
    en = "en"
    fr = "fr"
    ar = "ar"
    es = "es"
    code_switched = "code-switched"


HEADLINE_LANGUAGES = {"en": "English", "fr": "French", "ar": "Arabic", "es": "Spanish"}


class _ExampleCase(GoldCase):
    language: Language


class ExampleGold(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    why: str
    cases: tuple[_ExampleCase, ...]


type ExampleRun = tuple[Scored[_ExampleCase], ...]


async def evaluate_examples(model: Model) -> ExampleRun:
    gold = ExampleGold.model_validate_json(GOLD.read_text(encoding="utf-8"))
    return await evaluate(
        model,
        EXAMPLE_PILLARS,
        EXAMPLE_PILLARS,
        gold.cases,
        headline_languages=HEADLINE_LANGUAGES,
    )


def report(run: ExampleRun) -> str:
    rows = [
        "| Language | Captures | Routing | Fields | Validators | Tokens in / out | p95 in / out |",
        "| --- | --: | --: | --: | --: | --: | --: |",
    ]
    for language in Language:
        rows.append(_row(language.value, [each for each in run if each.case.language is language]))
    rows.append(_row("all", list(run)))
    models = sorted({usage.model for each in run for usage in each.score.usages})
    unparsed = RunScore(tuple(each.score for each in run)).unparsed_responses_by_model
    return (
        "\n".join(
            [
                *rows,
                "",
                *_headlines(run),
                f"Model: {', '.join(models)}",
                *(f"Unparsed: {model} x{count}" for model, count in sorted(unparsed.items())),
                *(f"Miss: {miss}" for miss in _misses(run)),
            ]
        )
        + "\n"
    )


def _row(label: str, scored: list[Scored[_ExampleCase]]) -> str:
    score = RunScore(tuple(each.score for each in scored))
    mean_in = score.mean(lambda capture: capture.input_tokens)
    mean_out = score.mean(lambda capture: capture.output_tokens)
    p95_in = score.p95(lambda capture: capture.input_tokens)
    p95_out = score.p95(lambda capture: capture.output_tokens)
    return (
        f"| {label} | {len(scored)} | {score.routing_accuracy:.0%} | "
        f"{score.field_accuracy:.0%} | {score.validator_agreement:.0%} | "
        f"{mean_in:.0f} / {mean_out:.0f} | "
        f"{p95_in:.0f} / {p95_out:.0f} |"
    )


def _headlines(run: ExampleRun) -> list[str]:
    written = [each.score.headline for each in run if each.score.headline]
    if not written:
        return []
    rows = [
        "| Headline in | Words, mean | Words, most | In its own script |",
        "| --- | --: | --: | --: |",
    ]
    for tag in HEADLINE_LANGUAGES:
        lengths = [len(words(headline[tag])) for headline in written]
        in_script = [_is_in_its_own_script(tag, headline[tag]) for headline in written]
        rows.append(
            f"| {tag} | {mean(lengths):.1f} | {max(lengths)} | "
            f"{sum(in_script) / len(in_script):.0%} |"
        )
    return [*rows, ""]


def _is_in_its_own_script(tag: str, headline: str) -> bool:
    is_arabic = any("ARABIC" in unicodedata.name(letter, "") for letter in headline)
    return is_arabic is (tag == Language.ar)


def _misses(run: ExampleRun) -> list[str]:
    found = []
    for each in run:
        score = each.score
        if not score.routing_is_exact:
            found.append(
                f"{score.utterance}: routed {sorted(score.routed)}, "
                f"wanted {sorted(score.expected_routes)}"
            )
        if not score.validators_agree:
            found.append(
                f"{score.utterance}: flagged {sorted(score.flagged)}, "
                f"wanted {sorted(score.expected_flags)}"
            )
        found += [
            f"{score.utterance}: {wrong.pillar}.{wrong.field} wanted {wrong.expected!r}, "
            f"got {wrong.found!r}"
            for wrong in score.wrong_fields
        ]
    return found
