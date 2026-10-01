# SOUL OF FARKAD-AI

Core tenets for the pure AI extraction engine.

## 1. Zero Infrastructure
- No databases, auth, buckets, or networking. Accepts requests, returns validated entries.
- Commercial pricing and user billing belong in consumers, never in this engine.

## 2. Providers Behind ModelPort
- Pipeline and domain code never import vendor SDKs (`google.genai`, `anthropic`, `openai`).
- Adapters in `farkad_ai/models/` map errors to `ModelUnavailableError` and report token counts and latency in `Usage`.

## 3. Cryptographic Prompts
- Raw text in `farkad_ai/prompts/assets/`, versioned by 12-char SHA-256 prefixes.
- Prompts are immutable and vendor-neutral: add new assets, never edit in place.

## 4. Offline First
- Default test suite runs offline against `RecordedModel` with zero API keys and zero cost.
- Live provider tests run only when explicitly targeted and credentials exist.

## 5. Empirical Prompt Changes
- Never change prompts on intuition. Benchmark against `farkad_ai/eval/gold.json`.
- Report routing accuracy, field F1, latency, and token consumption in every PR.

## 6. Strict Types
- Frozen Pydantic models. Exhaustive `match` on sealed unions. No untyped dynamic dispatch.
