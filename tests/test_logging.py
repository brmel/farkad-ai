from __future__ import annotations

import json
import logging

from farkad_ai.logging import LOGGED_FIELDS, JsonFormatter


def test_json_formatter_preserves_expected_logged_fields() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="farkad_ai.pipeline",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="routed",
        args=(),
        exc_info=None,
    )
    record.reason = "not_a_health_log"
    record.pillars = ["food", "water"]
    record.untracked_field = "ignored"

    payload = json.loads(formatter.format(record))
    assert payload["reason"] == "not_a_health_log"
    assert payload["pillars"] == ["food", "water"]
    assert "untracked_field" not in payload
    expected_fields = {
        "because",
        "model",
        "pillar",
        "pillars",
        "primary_model",
        "reason",
        "step",
        "tier",
    }
    assert set(LOGGED_FIELDS) == expected_fields
