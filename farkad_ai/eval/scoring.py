from __future__ import annotations

import math
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from farkad_ai.eval.words import word_errors, words
from farkad_ai.models.port import Usage

_NUMERIC_TOLERANCE = 0.01
_NO_HEADLINE: Mapping[str, str] = MappingProxyType({})


class _EmptyRunError(ValueError):
    def __init__(self) -> None:
        super().__init__("an eval run with no cases would score 100% and mean nothing")


@dataclass(frozen=True, slots=True)
class _FieldScore:
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
    heard: str
    headline: Mapping[str, str]
    expected_routes: frozenset[str]
    routed: frozenset[str]
    fields: tuple[_FieldScore, ...]
    usages: tuple[Usage, ...]
    flagged: frozenset[str]
    expected_flags: frozenset[str]
    unparsed_response_from: str | None
    elapsed_ms: int

    @property
    def routing_is_exact(self) -> bool:
        return self.expected_routes == self.routed

    @property
    def input_tokens(self) -> int:
        return sum(usage.input_tokens for usage in self.usages)

    @property
    def cached_input_tokens(self) -> int:
        return sum(usage.cached_input_tokens for usage in self.usages)

    @property
    def output_tokens(self) -> int:
        return sum(usage.output_tokens for usage in self.usages)

    @property
    def elapsed_seconds(self) -> float:
        return self.elapsed_ms / 1000

    @property
    def wrong_fields(self) -> tuple[_FieldScore, ...]:
        return tuple(score for score in self.fields if not score.is_match)

    @property
    def validators_agree(self) -> bool:
        return self.flagged == self.expected_flags

    @property
    def reference_words(self) -> int:
        return len(words(self.utterance))

    @property
    def word_errors(self) -> int:
        return word_errors(self.utterance, self.heard)


def matches(expected: object, found: object) -> bool:
    match expected:
        case {"min": float() | int() as low, "max": float() | int() as high}:
            magnitude = _magnitude(found)
            return magnitude is not None and low <= magnitude <= high
        case float() | int() if (magnitude := _magnitude(found)) is not None:
            return abs(float(expected) - magnitude) <= _NUMERIC_TOLERANCE
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
    heard: str,
    expected_routes: Sequence[str],
    expected: Mapping[str, Sequence[Mapping[str, object]]],
    routed: Sequence[str],
    extracted: Mapping[str, Sequence[Mapping[str, object]]],
    elapsed_ms: int,
    headline: Mapping[str, str] = _NO_HEADLINE,
    usages: Sequence[Usage] = (),
    flagged: Sequence[str] = (),
    expected_flags: Sequence[str] = (),
    unparsed_response_from: str | None = None,
) -> CaptureScore:
    return CaptureScore(
        utterance=utterance,
        heard=heard,
        headline=headline,
        expected_routes=frozenset(expected_routes),
        routed=frozenset(routed),
        fields=_field_scores(expected, extracted),
        usages=tuple(usages),
        flagged=frozenset(flagged),
        expected_flags=frozenset(expected_flags),
        unparsed_response_from=unparsed_response_from,
        elapsed_ms=elapsed_ms,
    )


def _field_scores(
    expected: Mapping[str, Sequence[Mapping[str, object]]],
    extracted: Mapping[str, Sequence[Mapping[str, object]]],
) -> tuple[_FieldScore, ...]:
    fields: list[_FieldScore] = []
    for pillar, wanted_entries in expected.items():
        found_entries = extracted.get(pillar, ())
        for index, wanted in enumerate(wanted_entries):
            found = found_entries[index] if index < len(found_entries) else {}
            fields += [
                _FieldScore(pillar=pillar, field=name, expected=value, found=found.get(name))
                for name, value in wanted.items()
            ]
    return tuple(fields)


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
    def word_error_rate(self) -> float:
        return _share(
            sum(capture.word_errors for capture in self.captures),
            sum(capture.reference_words for capture in self.captures),
        )

    @property
    def validator_agreement(self) -> float:
        return _share(
            sum(1 for capture in self.captures if capture.validators_agree),
            len(self.captures),
        )

    @property
    def unparsed_responses_by_model(self) -> Mapping[str, int]:
        return Counter(
            capture.unparsed_response_from
            for capture in self.captures
            if capture.unparsed_response_from is not None
        )

    @property
    def cached_input_share(self) -> float:
        input_tokens = sum(capture.input_tokens for capture in self.captures)
        if input_tokens == 0:
            return 0.0
        return sum(capture.cached_input_tokens for capture in self.captures) / input_tokens

    def mean(self, measure: Callable[[CaptureScore], float]) -> float:
        return _share(sum(measure(capture) for capture in self.captures), len(self.captures))

    def p50(self, measure: Callable[[CaptureScore], float]) -> float:
        return _nearest_rank_percentile([measure(capture) for capture in self.captures], 0.5)

    def p95(self, measure: Callable[[CaptureScore], float]) -> float:
        return _nearest_rank_percentile([measure(capture) for capture in self.captures], 0.95)


def _share(total: float, count: int) -> float:
    if count == 0:
        raise _EmptyRunError
    return total / count


def _nearest_rank_percentile(values: list[float], share: float) -> float:
    if not values:
        raise _EmptyRunError
    ranked = sorted(values)
    index = math.ceil(share * len(ranked)) - 1
    return ranked[max(index, 0)]
