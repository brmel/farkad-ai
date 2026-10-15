from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from farkad_ai.models.port import Usage


@dataclass(frozen=True, slots=True)
class TokenPrice:
    input_usd_per_million: float
    output_usd_per_million: float

    def cents(self, usage: Usage) -> float:
        dollars = (
            usage.input_tokens * self.input_usd_per_million
            + usage.output_tokens * self.output_usd_per_million
        ) / 1_000_000
        return dollars * 100


# Vertex AI's list price for text input: https://cloud.google.com/vertex-ai/generative-ai/pricing
PRICES: Mapping[str, TokenPrice] = {"gemini-3.5-flash-lite": TokenPrice(0.30, 2.50)}


class UnpricedModelError(Exception):
    def __init__(self, model: str) -> None:
        super().__init__(f"no price for {model}; add it to PRICES to measure its cost")
        self.model = model


def cost_cents(usage: Usage) -> float:
    if usage.model not in PRICES:
        raise UnpricedModelError(usage.model)
    return PRICES[usage.model].cents(usage)
