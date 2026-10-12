import pytest

from farkad_ai.eval.scoring import RunScore, score_capture


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
        cost_cents=0.01,
        spoken_cost_cents=0.01,
    )

    assert score.routing_is_exact
    assert len(score.wrong_fields) == wrong_fields
    run_score = RunScore(captures=(score,))
    assert run_score.routing_accuracy == 1.0
    assert run_score.field_accuracy == field_accuracy
