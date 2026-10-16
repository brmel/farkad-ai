import pytest

from farkad_ai.eval.example import evaluate_examples, report
from farkad_ai.eval.run import GoldCase, evaluate
from farkad_ai.extraction.port import Finding
from farkad_ai.models.port import ModelUnavailableError, Unavailability
from farkad_ai.routing.pass_one import Mention, PassOne
from tests.support import AnswersByStep, Spec, Tracked

pytestmark = pytest.mark.anyio

CATALOGUE = (Spec("water", "drinks"),)
A_GLASS = PassOne(
    transcript="a glass",
    language="en",
    is_health_related=True,
    states_a_lasting_fact=False,
    mentions=[Mention(pillar="water", said="a glass")],
)


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

    (scored,) = await evaluate(model, CATALOGUE, (flagged,), [case])

    assert scored.case is case
    assert scored.score.routing_is_exact and not scored.score.wrong_fields
    assert scored.score.validators_agree
    assert len(scored.score.usages) == 2


async def test_the_consumers_routing_rules_reach_the_routing_call() -> None:
    model = AnswersByStep(routing=A_GLASS, extraction={"entries": []})

    await evaluate(
        model,
        CATALOGUE,
        (Tracked("water"),),
        [GoldCase(utterance="a glass", routes=("water",))],
        routing_rules=("a glass is water",),
    )

    (routing, _tier), _extraction = model.asked
    assert routing.instructions.endswith("\n- a glass is water")


async def test_an_answer_that_does_not_parse_scores_zero_and_stays_in_the_run() -> None:
    case = GoldCase(utterance="a glass", routes=("water",))
    model = AnswersByStep(routing=Unavailability.output_did_not_parse)

    (scored,) = await evaluate(model, CATALOGUE, (Tracked("water"),), [case])

    assert not scored.score.routing_is_exact
    assert scored.score.unparsed_response_from == "model-fast"
    assert scored.score.usages == ()


async def test_a_refusal_other_than_an_unparsed_answer_is_raised() -> None:
    case = GoldCase(utterance="a glass", routes=("water",))
    model = AnswersByStep(routing=Unavailability.provider_refused)

    with pytest.raises(ModelUnavailableError):
        await evaluate(model, CATALOGUE, (Tracked("water"),), [case])


async def test_the_example_eval_reports_tokens_for_a_model_of_any_provider() -> None:
    model = AnswersByStep(
        routing=PassOne(
            transcript="",
            language="en",
            is_health_related=False,
            states_a_lasting_fact=False,
            mentions=[],
        )
    )

    table = report(await evaluate_examples(model))

    assert "| all | 15 | 7% | 0% | 10 / 5 | 10 / 5 |" in table
    assert "Model: gemini-2.5-flash-lite" in table
