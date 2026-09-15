from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

NUMERIC_TOLERANCE = 0.01
UNSTATED_FIELDS = frozenset({"pillar", "category"})


def holds_nothing(payload: Mapping[str, object]) -> bool:
    return not any(
        value is not None for name, value in payload.items() if name not in UNSTATED_FIELDS
    )


@dataclass(frozen=True, slots=True)
class FieldScore:
    pillar: str
    field: str
    expected: object
    found: object

    @property
    def is_match(self) -> bool:
        return matches(self.expected, self.found)


@dataclass(frozen=True, slots=True)
class CaptureScore:
    utterance: str
    expected_routes: frozenset[str]
    routed: frozenset[str]
    fields: tuple[FieldScore, ...]
    contentless: tuple[str, ...]
    cost_cents: float
    spoken_cost_cents: float
    flagged: frozenset[str]
    expected_flags: frozenset[str]
    unparsed_response_from: str | None

    @property
    def routing_is_exact(self) -> bool:
        return self.expected_routes == self.routed

    @property
    def wrong_fields(self) -> tuple[FieldScore, ...]:
        return tuple(score for score in self.fields if not score.is_match)

    @property
    def unexpected_flags(self) -> frozenset[str]:
        return self.flagged - self.expected_flags

    @property
    def validators_agree(self) -> bool:
        return self.flagged == self.expected_flags


def matches(expected: object, found: object) -> bool:
    match expected:
        case {"min": float() | int() as low, "max": float() | int() as high}:
            magnitude = _magnitude(found)
            return magnitude is not None and low <= magnitude <= high
        case float() | int() if (magnitude := _magnitude(found)) is not None:
            return abs(float(expected) - magnitude) <= NUMERIC_TOLERANCE
        case _:
            return expected == found


def _magnitude(found: object) -> float | None:
    match found:
        case {"value": float() | int() as value}:
            return float(value)
        case float() | int():
            return float(found)
        case _:
            return None


def score_capture(
    *,
    utterance: str,
    expected_routes: Sequence[str],
    expected: Mapping[str, Sequence[Mapping[str, object]]],
    routed: Sequence[str],
    extracted: Mapping[str, Sequence[Mapping[str, object]]],
    cost_cents: float,
    spoken_cost_cents: float,
    flagged: Sequence[str] = (),
    expected_flags: Sequence[str] = (),
    unparsed_response_from: str | None = None,
) -> CaptureScore:
    fields: list[FieldScore] = []
    contentless: list[str] = []
    for pillar, wanted_entries in expected.items():
        found_entries = extracted.get(pillar, ())
        for index, wanted in enumerate(wanted_entries):
            found = found_entries[index] if index < len(found_entries) else {}
            fields += [
                FieldScore(pillar=pillar, field=name, expected=value, found=found.get(name))
                for name, value in wanted.items()
            ]
    for pillar, found_entries in extracted.items():
        contentless += [pillar for entry in found_entries if holds_nothing(entry)]
    return CaptureScore(
        utterance=utterance,
        expected_routes=frozenset(expected_routes),
        routed=frozenset(routed),
        fields=tuple(fields),
        contentless=tuple(sorted(contentless)),
        cost_cents=cost_cents,
        spoken_cost_cents=spoken_cost_cents,
        flagged=frozenset(flagged),
        expected_flags=frozenset(expected_flags),
        unparsed_response_from=unparsed_response_from,
    )


@dataclass(frozen=True, slots=True)
class RunScore:
    captures: tuple[CaptureScore, ...]

    @property
    def routing_accuracy(self) -> float:
        return _share(
            sum(1 for capture in self.captures if capture.routing_is_exact), len(self.captures)
        )

    @property
    def field_accuracy(self) -> float:
        scored = [score for capture in self.captures for score in capture.fields]
        return _share(sum(1 for score in scored if score.is_match), len(scored))

    @property
    def validator_agreement(self) -> float:
        return _share(
            sum(1 for capture in self.captures if capture.validators_agree),
            len(self.captures),
        )

    @property
    def unexpected_flags(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                f"{capture.utterance[:32]}: {flag}"
                for capture in self.captures
                for flag in capture.unexpected_flags
            )
        )

    @property
    def unparsed_responses_by_model(self) -> Mapping[str, int]:
        return Counter(
            capture.unparsed_response_from
            for capture in self.captures
            if capture.unparsed_response_from is not None
        )

    @property
    def cost_cents_per_capture(self) -> float:
        return _share(sum(capture.cost_cents for capture in self.captures), len(self.captures))

    @property
    def spoken_cost_cents_per_capture(self) -> float:
        return _share(
            sum(capture.spoken_cost_cents for capture in self.captures), len(self.captures)
        )

    @property
    def contentless_entries(self) -> int:
        return sum(len(capture.contentless) for capture in self.captures)

    @property
    def p95_cost_cents(self) -> float:
        return _nearest_rank_percentile([capture.cost_cents for capture in self.captures], 0.95)

    @property
    def spoken_p95_cost_cents(self) -> float:
        return _nearest_rank_percentile(
            [capture.spoken_cost_cents for capture in self.captures], 0.95
        )


def _share(total: float, count: int) -> float:
    if count == 0:
        raise ValueError("an eval run with no cases would score 100% and mean nothing")
    return total / count


def _nearest_rank_percentile(values: list[float], share: float) -> float:
    if not values:
        raise ValueError("an eval run with no cases would score 100% and mean nothing")
    ranked = sorted(values)
    index = math.ceil(share * len(ranked)) - 1
    return ranked[max(index, 0)]
