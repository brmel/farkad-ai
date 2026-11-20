import pytest

from farkad_ai.eval.example import ExampleCase, evaluate_cases, gold_cases
from farkad_ai.models.port import Model

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize(
    "case", gold_cases(), ids=lambda case: f"{case.language}: {case.utterance}"
)
async def test_the_engine_answers_a_gold_case_as_the_dataset_expects(
    case: ExampleCase, gold_model: Model
) -> None:
    (scored,) = await evaluate_cases(gold_model, [case])
    score = scored.score

    assert sorted(score.routed) == sorted(score.expected_routes)
    assert [
        f"{wrong.pillar}.{wrong.field}: wanted {wrong.expected!r}, got {wrong.found!r}"
        for wrong in score.wrong_fields
    ] == []
    assert sorted(score.flagged) == sorted(score.expected_flags)
