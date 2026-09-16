from __future__ import annotations

from collections import OrderedDict
from decimal import Decimal
import hashlib
from typing import Any

from pydantic import BaseModel

from farkad_ai.logging import get_logger
from farkad_ai.models.port import ModelPort
from farkad_ai.pipeline.observer import CacheHit, CacheMiss, PipelineObserver
from farkad_ai.types import Completion, ModelTier, Prompt, Usage

_log = get_logger(__name__)


def cache_key_of(prompt: Prompt, schema: type[BaseModel], tier: ModelTier) -> str:
    media_hashes = tuple(hashlib.sha256(m.data).hexdigest() for m in prompt.media)
    raw = (
        prompt.step.value,
        prompt.instructions_version,
        prompt.utterance.strip().lower(),
        schema.__name__,
        tier.value,
        media_hashes,
    )
    return hashlib.sha256(repr(raw).encode("utf-8")).hexdigest()


def _cached_completion[T: BaseModel](cached: Completion[Any]) -> Completion[T]:
    cached_usage = Usage(
        step=cached.usage.step,
        model=f"{cached.usage.model}-cached",
        prompt_version=cached.usage.prompt_version,
        input_tokens=0,
        output_tokens=0,
        latency_ms=0,
        cost_cents=Decimal("0.0"),
    )
    typed_value: T = cached.value
    return Completion(value=typed_value, usage=cached_usage)


class CachedModel(ModelPort):
    def __init__(
        self,
        inner: ModelPort,
        *,
        capacity: int = 256,
        observer: PipelineObserver | None = None,
    ) -> None:
        self._inner = inner
        self._capacity = max(1, capacity)
        self._observer = observer
        self._cache: OrderedDict[str, Completion[Any]] = OrderedDict()
        self._hits = 0
        self._misses = 0

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses

    @property
    def size(self) -> int:
        return len(self._cache)

    @property
    def capacity(self) -> int:
        return self._capacity

    def clear(self) -> None:
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def _on_hit[T: BaseModel](
        self,
        key: str,
        cached: Completion[Any],
        prompt: Prompt,
        schema: type[T],
        tier: ModelTier,
    ) -> Completion[T]:
        self._cache.move_to_end(key)
        self._hits += 1
        if self._observer is not None:
            self._observer.on_event(CacheHit(key=key, step=prompt.step))
        _log.info(
            "model_cache_hit",
            extra={
                "extra_fields": {
                    "key": key[:16],
                    "step": prompt.step.value,
                    "schema": schema.__name__,
                    "tier": tier.value,
                    "saved_latency_ms": cached.usage.latency_ms,
                }
            },
        )
        return _cached_completion(cached)

    def _store(
        self,
        key: str,
        completion: Completion[Any],
        prompt: Prompt,
        schema: type[BaseModel],
        tier: ModelTier,
    ) -> None:
        self._cache[key] = completion
        if len(self._cache) > self._capacity:
            self._cache.popitem(last=False)
        _log.info(
            "model_cache_miss",
            extra={
                "extra_fields": {
                    "key": key[:16],
                    "step": prompt.step.value,
                    "schema": schema.__name__,
                    "tier": tier.value,
                    "latency_ms": completion.usage.latency_ms,
                }
            },
        )

    async def complete[T: BaseModel](
        self, prompt: Prompt, *, schema: type[T], tier: ModelTier
    ) -> Completion[T]:
        key = cache_key_of(prompt, schema, tier)
        cached = self._cache.get(key)
        if cached is not None:
            return self._on_hit(key, cached, prompt, schema, tier)
        self._misses += 1
        if self._observer is not None:
            self._observer.on_event(CacheMiss(key=key, step=prompt.step))
        completion = await self._inner.complete(prompt, schema=schema, tier=tier)
        self._store(key, completion, prompt, schema, tier)
        return completion
