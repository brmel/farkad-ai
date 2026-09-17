from __future__ import annotations

from pydantic import BaseModel

from farkad_ai.logging import get_logger
from farkad_ai.models.port import ModelPort
from farkad_ai.types import Completion, ModelTier, ModelUnavailableError, Prompt

_log = get_logger(__name__)


class FallbackModel(ModelPort):
    def __init__(self, primary: ModelPort, fallback: ModelPort) -> None:
        self._primary = primary
        self._fallback = fallback

    @property
    def primary(self) -> ModelPort:
        return self._primary

    @property
    def fallback(self) -> ModelPort:
        return self._fallback

    async def complete[T: BaseModel](
        self, prompt: Prompt, *, schema: type[T], tier: ModelTier
    ) -> Completion[T]:
        try:
            return await self._primary.complete(prompt, schema=schema, tier=tier)
        except ModelUnavailableError as error:
            _log.warning(
                "model_fallback_triggered",
                extra={
                    "extra_fields": {
                        "primary_model": error.model,
                        "because": error.because.value,
                        "tier": tier.value,
                        "step": prompt.step.value,
                    }
                },
            )
            return await self._fallback.complete(prompt, schema=schema, tier=tier)
