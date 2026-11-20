import anyio
import pytest
from pydantic import BaseModel

from farkad_ai.eval.example import evaluate_examples, report
from farkad_ai.eval.run import GoldCase, Scored, evaluate
from farkad_ai.extraction.port import Finding, TrackedPillar
from farkad_ai.models.port import (
    Completion,
    MediaBlob,
    MediaType,
    ModelTier,
    ModelUnavailableError,
    Prompt,
    Unavailability,
)
from farkad_ai.pipeline.port import CaptureRequest
from farkad_ai.routing.pass_one import Mention
from tests.support import HEADLINE, HEADLINE_LANGUAGES, AnswersByStep, Spec, Tracked, routing_answer

pytestmark = pytest.mark.anyio

CATALOGUE = (Spec("water", "drinks"),)
A_GLASS = routing_answer(Mention(pillar="water", said="a glass"))


async def evaluated[Case: GoldCase](
    model: AnswersByStep, tracked: tuple[TrackedPillar, ...], case: Case
) -> tuple[Scored[Case], ...]:
    return await evaluate(model, CATALOGUE, tracked, [case], headline_languages=HEADLINE_LANGUAGES)


class NotedCase(GoldCase):
    note: str


async def test_a_case_is_scored_with_its_findings_and_returned_as_the_consumers_own() -> None:
    flagged = Tracked("water", flagged=(Finding(field="item", reason="implausible"),))
    case = NotedCase(
        utterance="a glass",
        routes=("water",),
        expected={"water": ({"item": "glass"},)},
        flags=("water.item",),
        note="a consumer's own field",
    )
    model = AnswersByStep(
        routing=A_GLASS, extraction={"entries": [{"pillar": "water", "item": "glass"}]}
    )

    (scored,) = await evaluated(model, (flagged,), case)

    assert scored.case is case
    assert scored.score.headline == HEADLINE
    assert scored.score.routing_is_exact and not scored.score.wrong_fields
    assert scored.score.validators_agree
    assert len(scored.score.usages) == 2


class SpokenCase(GoldCase):
    def request(self, tracked: tuple[TrackedPillar, ...]) -> CaptureRequest:
        return CaptureRequest(tracked=tracked, media=(MediaBlob(MediaType.audio_aac, b"clip"),))


async def test_a_case_that_asks_with_a_clip_is_scored_on_the_words_heard_from_it() -> None:
    model = AnswersByStep(routing=A_GLASS | {"transcript": "a gas"}, extraction={"entries": []})

    (scored,) = await evaluated(
        model, (Tracked("water"),), SpokenCase(utterance="a glass", routes=("water",))
    )

    (routing, _tier), _extraction = model.asked
    assert routing.media == (MediaBlob(MediaType.audio_aac, b"clip"),)
    assert (scored.score.heard, scored.score.word_errors) == ("a gas", 1)


async def test_the_consumers_routing_rules_reach_the_routing_call() -> None:
    model = AnswersByStep(routing=A_GLASS, extraction={"entries": []})

    await evaluate(
        model,
        CATALOGUE,
        (Tracked("water"),),
        [GoldCase(utterance="a glass", routes=("water",))],
        headline_languages=HEADLINE_LANGUAGES,
        routing_rules=("a glass is water",),
    )

    (routing, _tier), _extraction = model.asked
    assert routing.instructions.endswith("\n- a glass is water")


async def test_an_answer_that_does_not_parse_scores_zero_and_stays_in_the_run() -> None:
    case = GoldCase(utterance="a glass", routes=("water",))
    model = AnswersByStep(routing=Unavailability.output_did_not_parse)

    (scored,) = await evaluated(model, (Tracked("water"),), case)

    assert not scored.score.routing_is_exact
    assert scored.score.unparsed_response_from == "model-fast"
    assert scored.score.usages == ()


class AnswersAfterAPause(AnswersByStep):
    async def complete[T: BaseModel](
        self, prompt: Prompt, *, schema: type[T], tier: ModelTier
    ) -> Completion[T]:
        await anyio.sleep(PAUSE_SECONDS)
        return await super().complete(prompt, schema=schema, tier=tier)


PAUSE_SECONDS = 0.05


async def test_a_capture_is_timed_across_every_call_it_waited_for_answered_or_not() -> None:
    case = GoldCase(utterance="a glass", routes=("water",))
    answered = AnswersAfterAPause(routing=A_GLASS, extraction={"entries": []})
    unparsed = AnswersAfterAPause(routing=Unavailability.output_did_not_parse)

    (logged,) = await evaluated(answered, (Tracked("water"),), case)
    (refused,) = await evaluated(unparsed, (Tracked("water"),), case)

    assert logged.score.elapsed_ms >= 2 * PAUSE_SECONDS * 1000
    assert PAUSE_SECONDS * 1000 <= refused.score.elapsed_ms < logged.score.elapsed_ms


async def test_a_refusal_other_than_an_unparsed_answer_is_raised() -> None:
    case = GoldCase(utterance="a glass", routes=("water",))
    model = AnswersByStep(routing=Unavailability.provider_refused)

    with pytest.raises(ModelUnavailableError):
        await evaluated(model, (Tracked("water"),), case)


NOT_A_LOG = routing_answer(is_health_related=False) | {
    "headline": {"en": "Rain today", "fr": "Pluie ce matin", "ar": "مطر اليوم", "es": "مطر اليوم"}
}


async def test_the_example_eval_reports_tokens_for_a_model_of_any_provider() -> None:
    model = AnswersByStep(routing=NOT_A_LOG)

    table = report(await evaluate_examples(model))

    assert "| all | 16 | 6% | 0% | 100% | 10 / 5 | 10 / 5 |" in table
    assert "Model: gemini-2.5-flash-lite" in table
    assert "Prompts: routing " in table


async def test_the_example_report_counts_each_languages_headline_words_and_its_script() -> None:
    model = AnswersByStep(routing=NOT_A_LOG)

    table = report(await evaluate_examples(model))

    assert "| fr | 3.0 | 3 | 100% |" in table
    assert "| ar | 2.0 | 2 | 100% |" in table
    assert "| es | 2.0 | 2 | 0% |" in table


async def test_the_example_report_counts_the_answers_that_did_not_parse_per_model() -> None:
    model = AnswersByStep(routing=Unavailability.output_did_not_parse)

    table = report(await evaluate_examples(model))

    assert "Unparsed: model-fast x16" in table
