# MEMORY — FARKAD-AI

Current engine state, gold set baseline, and runtime facts.

## 1. Package State
| Item | State | Notes |
| :--- | :--- | :--- |
| **Version** | `0.4.0` | Wheel pinned by SHA-256 in monorepo backend (D441) |
| **Commit** | `d2c86d0` | Tag `v0.4.0` on `main` |
| **Python** | `>=3.13` | Pydantic v2, AnyIO (asyncio) |
| **Providers** | Google, Anthropic, OpenAI, Recorded | Behind `ModelPort` |

## 2. Evaluation Baseline
- **Gold Set:** `farkad_ai/eval/gold.json`
- **Pillars (7):** `food`, `water`, `exercise`, `sleep`, `supplements`, `drugs`, `recovery`.
- **Production Model:** `gemini-2.5-flash-lite`.

## 3. Operational Rules
- `pytest` runs offline against recorded cassettes (`ProviderName.recorded`).
- Prompts in `farkad_ai/prompts/assets/` are immutable sha256 assets.
- Pure AI execution: commercial pricing and billing live in the backend consumer.
