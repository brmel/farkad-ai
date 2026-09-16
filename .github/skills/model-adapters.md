# Skill: Adding Model Adapters

Guidelines for implementing new LLM providers in `farkad-ai`.

---

## 1. Interface Contract

Every model adapter must implement the `ModelPort` protocol from `farkad_ai.models.port`:

```python
class ModelPort(Protocol):
    async def complete[T: BaseModel](
        self, prompt: Prompt, *, schema: type[T], tier: ModelTier
    ) -> Completion[T]: ...
```

## 2. Rules

- **Strict Error Handling**: Map provider-specific network or rate-limit errors to `ModelUnavailableError(tier, model, because, detail)`.
- **Token Usage Tracking**: Report exact `input_tokens`, `output_tokens`, `latency_ms`, and compute `cost_cents` via `TokenPrice.cost_cents()`.
- **Media Support**: If supporting vision or audio modalities, inspect `prompt.media` and convert `MediaBlob` payloads accordingly.
