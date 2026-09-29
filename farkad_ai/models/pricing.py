"""Prices per million tokens, transcribed from each provider's price sheet."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType

from farkad_ai.types import MediaType, Prompt

CENTS_PER_DOLLAR = Decimal(100)
TOKENS_PER_UNIT = Decimal(1_000_000)


class InputModality(StrEnum):
    text = "text"
    audio = "audio"
    image = "image"


def modality_of(prompt: Prompt) -> InputModality:
    if any(blob.content_type is MediaType.audio_aac for blob in prompt.media):
        return InputModality.audio
    if prompt.media:
        return InputModality.image
    return InputModality.text


@dataclass(frozen=True, slots=True)
class TokenPrice:
    input_usd_per_million: Decimal
    audio_input_usd_per_million: Decimal
    output_usd_per_million: Decimal
    retires_on: date | None = None

    def cost_cents(
        self, *, input_tokens: int, output_tokens: int, input_modality: InputModality
    ) -> Decimal:
        dollars = (
            self._input_rate(input_modality) * Decimal(input_tokens)
            + self.output_usd_per_million * Decimal(output_tokens)
        ) / TOKENS_PER_UNIT
        return dollars * CENTS_PER_DOLLAR

    def _input_rate(self, modality: InputModality) -> Decimal:
        match modality:
            case InputModality.text | InputModality.image:
                return self.input_usd_per_million
            case InputModality.audio:
                return self.audio_input_usd_per_million


RETIREMENT_OF_2_5 = date(2026, 10, 20)


def _price(
    in_usd: str, out_usd: str, audio: str | None = None, retires: date | None = None
) -> TokenPrice:
    return TokenPrice(
        input_usd_per_million=Decimal(in_usd),
        audio_input_usd_per_million=Decimal(audio if audio is not None else in_usd),
        output_usd_per_million=Decimal(out_usd),
        retires_on=retires,
    )


PRICES: Mapping[str, TokenPrice] = MappingProxyType(
    {
        "gemini-2.5-flash-lite": _price("0.10", "0.40", audio="0.30", retires=RETIREMENT_OF_2_5),
        "gemini-2.5-flash": _price("0.30", "2.50", audio="1.00", retires=RETIREMENT_OF_2_5),
        "gemini-3.6-flash": _price("1.50", "7.50"),
        "gemini-3.1-flash-lite": _price("0.25", "1.50", audio="0.50", retires=date(2027, 5, 7)),
        "gemini-3.5-flash-lite": _price("0.30", "2.50", retires=date(2027, 7, 21)),
        "gemini-3.5-flash": _price("1.50", "9.00", retires=date(2027, 5, 19)),
        "claude-3-5-haiku-20241022": _price("0.80", "4.00"),
        "claude-3-5-sonnet-20241022": _price("3.00", "15.00"),
        "gpt-4o-mini": _price("0.15", "0.60"),
        "gpt-4o": _price("2.50", "10.00"),
    }
)


class UnpricedModelError(Exception):
    """An unpriced model would record every call as free and disarm a spend ceiling."""

    def __init__(self, model: str) -> None:
        super().__init__(f"no committed price for {model}")
        self.model = model


def price_of(model: str) -> TokenPrice:
    if model not in PRICES:
        raise UnpricedModelError(model)
    return PRICES[model]


NOTICE = timedelta(days=30)


def retiring_within(notice: timedelta, today: date) -> tuple[str, ...]:
    """Thirty days' notice keeps a retirement a configuration change rather than an incident."""
    return tuple(
        sorted(
            model
            for model, price in PRICES.items()
            if price.retires_on is not None and price.retires_on - today <= notice
        )
    )
