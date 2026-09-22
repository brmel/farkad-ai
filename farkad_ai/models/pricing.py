from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType
from typing import Protocol

CENTS_PER_DOLLAR = Decimal(100)
TOKENS_PER_UNIT = Decimal(1_000_000)


class InputModality(StrEnum):
    text = "text"
    audio = "audio"
    image = "image"


class MediaBlobProtocol(Protocol):
    @property
    def content_type(self) -> str: ...


class PromptMediaProtocol(Protocol):
    @property
    def media(self) -> Sequence[MediaBlobProtocol]: ...


def modality_of(prompt: PromptMediaProtocol) -> InputModality:
    if any(blob.content_type == "audio/aac" for blob in prompt.media):
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


RETIREMENT_OF_2_5 = date(2026, 10, 16)

PRICES: Mapping[str, TokenPrice] = MappingProxyType(
    {
        "gemini-2.5-flash-lite": TokenPrice(
            input_usd_per_million=Decimal("0.10"),
            audio_input_usd_per_million=Decimal("0.30"),
            output_usd_per_million=Decimal("0.40"),
            retires_on=RETIREMENT_OF_2_5,
        ),
        "gemini-2.5-flash": TokenPrice(
            input_usd_per_million=Decimal("0.30"),
            audio_input_usd_per_million=Decimal("1.00"),
            output_usd_per_million=Decimal("2.50"),
            retires_on=RETIREMENT_OF_2_5,
        ),
        "gemini-3.6-flash": TokenPrice(
            input_usd_per_million=Decimal("1.50"),
            audio_input_usd_per_million=Decimal("1.50"),
            output_usd_per_million=Decimal("7.50"),
        ),
        "gemini-3.1-flash-lite": TokenPrice(
            input_usd_per_million=Decimal("0.25"),
            audio_input_usd_per_million=Decimal("0.50"),
            output_usd_per_million=Decimal("1.50"),
        ),
        "gemini-3.5-flash-lite": TokenPrice(
            input_usd_per_million=Decimal("0.30"),
            audio_input_usd_per_million=Decimal("0.30"),
            output_usd_per_million=Decimal("2.50"),
        ),
        "gemini-3.5-flash": TokenPrice(
            input_usd_per_million=Decimal("1.50"),
            audio_input_usd_per_million=Decimal("1.50"),
            output_usd_per_million=Decimal("9.00"),
        ),
        "claude-3-5-haiku-20241022": TokenPrice(
            input_usd_per_million=Decimal("0.80"),
            audio_input_usd_per_million=Decimal("0.80"),
            output_usd_per_million=Decimal("4.00"),
        ),
        "claude-3-5-sonnet-20241022": TokenPrice(
            input_usd_per_million=Decimal("3.00"),
            audio_input_usd_per_million=Decimal("3.00"),
            output_usd_per_million=Decimal("15.00"),
        ),
        "gpt-4o-mini": TokenPrice(
            input_usd_per_million=Decimal("0.15"),
            audio_input_usd_per_million=Decimal("0.15"),
            output_usd_per_million=Decimal("0.60"),
        ),
        "gpt-4o": TokenPrice(
            input_usd_per_million=Decimal("2.50"),
            audio_input_usd_per_million=Decimal("2.50"),
            output_usd_per_million=Decimal("10.00"),
        ),
    }
)


class UnpricedModelError(Exception):
    def __init__(self, model: str) -> None:
        super().__init__(f"no committed price for {model}")
        self.model = model


def price_of(model: str) -> TokenPrice:
    if model not in PRICES:
        raise UnpricedModelError(model)
    return PRICES[model]


NOTICE = timedelta(days=30)


def retiring_within(notice: timedelta, today: date) -> tuple[str, ...]:
    return tuple(
        sorted(
            model
            for model, price in PRICES.items()
            if price.retires_on is not None and price.retires_on - today <= notice
        )
    )
