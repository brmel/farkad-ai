# SOUL OF FARKAD-AI

Core tenets for the AI extraction engine.

## 1. Zero Infrastructure
- No databases, auth, buckets, or networking. Accepts requests, returns validated entries.
- Application concerns belong in the consumer, never here.

## 2. Providers Behind ModelPort
- No pipeline or domain code imports vendor SDKs (`google.genai`, `anthropic`, `openai`).
- Adapters live in `farkad_ai/models/`, map errors to `ModelUnavailableError`, report token counts, and calculate costs via `TokenPrice.cost_cents()`.

## 3. Cryptographic Prompts
- Raw text in `farkad_ai/prompts/assets/`, versioned by the first 12 characters of SHA-256.
- Prompts never name dates, years, or vendor names. Immutable: add new assets, never edit in place.

## 4. Offline First
- Default test suite runs offline against `RecordedModel` with zero keys and zero spend.
- Live provider tests belong in integration suites and skip if keys are missing.

## 5. Empirical Prompt Changes
- Never change a prompt on intuition. Benchmark against `farkad_ai/eval/gold.json`.
- Report routing accuracy, field F1, latency, and cost per 1,000 extractions in every PR.

## 6. Strict Types
- Frozen Pydantic models. Exhaustive `match` on sealed unions. No untyped `isinstance` or dynamic lookups.
