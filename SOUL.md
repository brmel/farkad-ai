# SOUL OF FARKAD-AI

> *"A model is not a brain; it is an untrusted remote service that predicts text under a schema."*

You are working in `farkad-ai`. This package is the intelligence core of Farkad: it receives multimodal human expressions (audio, text, photos of meals or blood pressure monitors) and extracts clean, strictly validated health entities.

Because this engine powers personal health understanding, it must be predictable, auditable, and resilient to model flakiness.

---

## 1. Zero Infrastructure Dependencies

- `farkad-ai` contains no databases, no user accounts, no cloud buckets, and no network frameworks.
- It accepts domain requests and returns validated entries.
- If a concept requires Firestore, Supabase, Redis, or Celery, it belongs in an application layer, not here.

---

## 2. Provider Agnosticism Behind `ModelPort`

- No business logic or pipeline may ever import a provider SDK (`google.genai`, `anthropic`, `openai`).
- All provider integrations live behind `ModelPort` in `farkad_ai/models/`.
- Every adapter must:
  1. Map network drops, rate limits, and provider quirks to `ModelUnavailableError`.
  2. Report exact input/output token counts.
  3. Calculate exact transaction cost in cents using `TokenPrice.cost_cents()`.

---

## 3. Prompts are Cryptographic Assets

- Prompts are raw text files in `farkad_ai/prompts/assets/`.
- They are identified and versioned strictly by the first 12 characters of their SHA-256 hash.
- A prompt must never mention a specific date, a calendar year, or a model vendor's marketing name.
- Prompts are immutable: never edit a prompt asset in place. Add a new prompt asset, update the version reference, and benchmark the delta.

---

## 4. Offline First & Zero-Cost Testing

- Every unit and pipeline test must execute completely offline using `RecordedModel`.
- A developer or CI runner without an API key must be able to run `pytest` and see 100% green tests.
- Live provider tests belong in dedicated integration suites marked with `@pytest.mark.integration` and must skip cleanly if keys are absent.

---

## 5. Empirical Prompt & Model Engineering

- Never modify a prompt or change model routing based on vibes or a single anecdote.
- Every prompt change requires evaluating against the gold evaluation set (`make eval` or `/eval-prompt`).
- The PR description must publish:
  - Overall extraction accuracy (%)
  - Field-level F1 scores (Food, Activity, Symptom, Biomarker)
  - P50 and P95 latency (seconds)
  - Cost per 1,000 extractions (cents)

---

## 6. Strict Types & Exhaustive Dispatch

- Pydantic models are frozen where feasible.
- Dispatch logic uses exhaustive `match` over typed discriminated unions.
- No `isinstance` checks on untyped dictionaries; parse once at the perimeter.
