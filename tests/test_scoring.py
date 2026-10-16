import pytest

from farkad_ai.eval.scoring import RunScore, matches, score_capture
from farkad_ai.models.port import PipelineStep
from tests.support import a_usage


@pytest.mark.parametrize(
    ("eaten", "wrong_fields", "field_accuracy"),
    [
        ({"name": "Apple", "calories": 95}, 0, 1.0),
        ({"name": "Banana", "calories": 105}, 2, 0.0),
    ],
)
def test_each_wrong_field_counts_against_field_accuracy(
    eaten: dict[str, object], wrong_fields: int, field_accuracy: float
) -> None:
    score = score_capture(
        utterance="Ate a fruit",
        expected_routes=["nutrition"],
        expected={"nutrition": [{"name": "Apple", "calories": 95}]},
        routed=["nutrition"],
        extracted={"nutrition": [eaten]},
    )

    assert score.routing_is_exact
    assert len(score.wrong_fields) == wrong_fields
    run_score = RunScore(captures=(score,))
    assert run_score.routing_accuracy == 1.0
    assert run_score.field_accuracy == field_accuracy


@pytest.mark.parametrize(
    ("expected", "found", "is_match"),
    [
        ({"value": 500, "unit": "mg"}, {"value": 500, "unit": "mg"}, True),
        ({"value": 500, "unit": "mg"}, {"value": 500, "unit": "g"}, False),
        (500, {"value": 500, "unit": "mg"}, True),
    ],
)
def test_a_stated_unit_must_be_the_unit_found_and_a_bare_number_is_in_the_fields_own(
    expected: object, found: object, is_match: bool
) -> None:
    assert matches(expected, found) is is_match


def test_a_run_reports_the_mean_and_p95_of_the_tokens_its_captures_spent() -> None:
    captures = tuple(
        score_capture(
            utterance=f"capture {calls}",
            expected_routes=[],
            expected={},
            routed=[],
            extracted={},
            usages=[a_usage(PipelineStep.routing)] * calls,
        )
        for calls in range(1, 21)
    )
    run = RunScore(captures)

    assert (captures[1].input_tokens, captures[1].output_tokens) == (20, 10)
    assert run.mean(lambda capture: capture.input_tokens) == 105
    assert run.p95(lambda capture: capture.output_tokens) == 95
