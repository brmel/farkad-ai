from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from farkad_ai.eval.scoring import CaptureScore, score_capture


def parse_entry_map(raw: object) -> dict[str, Sequence[Mapping[str, object]]]:
    result: dict[str, Sequence[Mapping[str, object]]] = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            if isinstance(v, list):
                result[str(k)] = [e for e in v if isinstance(e, dict)]
    return result


def score_fixture_case(case: dict[str, object]) -> CaptureScore:
    routes_raw = case.get("routes") or case.get("expected_routes") or []
    expected_routes = (
        tuple(str(r) for r in routes_raw) if isinstance(routes_raw, (list, tuple)) else ()
    )
    expected = parse_entry_map(case.get("expected"))
    raw_routed = case.get("routed")
    routed = (
        tuple(str(r) for r in raw_routed)
        if isinstance(raw_routed, (list, tuple))
        else expected_routes
    )
    raw_ext = case.get("extracted")
    extracted = parse_entry_map(raw_ext) if raw_ext is not None else expected
    cost = float(str(case.get("cost_cents", 0.0)))
    spoken = float(str(case.get("spoken_cost_cents", 0.0)))
    return score_capture(
        utterance=str(case.get("utterance", "")),
        expected_routes=expected_routes,
        expected=expected,
        routed=routed,
        extracted=extracted,
        cost_cents=cost,
        spoken_cost_cents=spoken,
    )


def replay_fixtures(path: Path) -> tuple[int, int]:
    if not path.exists():
        raise FileNotFoundError(f"Fixtures path not found: {path}")
    raw_cases: list[dict[str, object]] = []
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        raw_cases = data.get("cases", [data])
    else:
        for p in sorted(path.glob("*.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                raw_cases.extend(data.get("cases", [data]))
            except Exception:
                continue
    if not raw_cases:
        raise ValueError(f"No test cases found in {path}")
    passed = 0
    for case in raw_cases:
        score = score_fixture_case(case)
        if score.routing_is_exact and not score.wrong_fields:
            passed += 1
    return passed, len(raw_cases)
