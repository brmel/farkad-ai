from farkad_ai.eval.scoring import RunScore, score_capture


def test_a_capture_matching_every_field_scores_no_wrong_field() -> None:
    expected = {
        "nutrition": [{"name": "Apple", "calories": 95}],
    }
    actual = {
        "nutrition": [{"name": "Apple", "calories": 95}],
    }
    score = score_capture(
        utterance="Ate an apple",
        expected_routes=["nutrition"],
        expected=expected,
        routed=["nutrition"],
        extracted=actual,
        cost_cents=0.01,
        spoken_cost_cents=0.01,
    )
    assert score.routing_is_exact
    assert len(score.wrong_fields) == 0
    assert score.fields[0].is_match


def test_each_wrong_field_counts_against_field_accuracy() -> None:
    expected = {
        "nutrition": [{"name": "Apple", "calories": 95}],
    }
    actual = {
        "nutrition": [{"name": "Banana", "calories": 105}],
    }
    score = score_capture(
        utterance="Ate a fruit",
        expected_routes=["nutrition"],
        expected=expected,
        routed=["nutrition"],
        extracted=actual,
        cost_cents=0.01,
        spoken_cost_cents=0.01,
    )
    assert score.routing_is_exact
    assert len(score.wrong_fields) == 2
    run_score = RunScore(captures=(score,))
    assert run_score.routing_accuracy == 1.0
    assert run_score.field_accuracy == 0.0
