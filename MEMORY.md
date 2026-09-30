# LIVING SYSTEM MEMORY — FARKAD-AI

> Living state of truth for the AI extraction engine.

---

## 1. Package & Distribution State

| Metric / Item | Current State | Notes |
| :--- | :--- | :--- |
| **Active Version** | `0.3.0` | Released on PyPI / pinned by SHA-256 in monorepo `backend/` (D441). |
| **Current Git Commit** | `dc4bcfa` | Clean on `main`. |
| **Target Python** | `>=3.13` | Strict typing, Pydantic v2, AnyIO async testing. |
| **Supported Providers** | `google` (`google-genai>=2.14.0`), `anthropic` (`anthropic>=0.40.0`), `openai` (`openai>=1.50.0`), `recorded` | All behind `ModelPort`. |

---

## 2. Evaluation Baseline (Gold Set)

- **Dataset:** `farkad_ai/eval/gold.json`
- **Supported Pillars:**
  1. `food` (meals, snacks, drinks with energy)
  2. `water` (hydration without caloric energy)
  3. `exercise` (workouts, sport, movement)
  4. `sleep` (nights, naps, sleep quality metrics)
  5. `supplements` (vitamins, minerals, protein, creatine)
  6. `drugs` (medications, pharmaceuticals)
  7. `recovery` (sauna, cold plunge, breathwork, deliberate recovery)
- **Active Production Model:** `gemini-2.5-flash-lite` (low-cost, sub-second latency, structured JSON mode).

---

## 3. Operational Rules & Quirks

- **No Remote Calls in Default Test Suite:** Running `pytest` runs purely on offline cassettes (`ProviderName.recorded`).
- **Prompt Immutability:** Prompts are sha256-addressed assets under `farkad_ai/prompts/assets/`. Never edit an asset in place; add a new file and update the resolver.
- **Cost Calculation:** Every token usage is translated to microcents via `farkad_ai/models/pricing.py`. Keep pricing table synchronized when vendor rates change.
