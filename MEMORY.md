# MEMORY — FARKAD-AI

Current engine state, gold set baseline, and runtime facts.

## 1. Package State
| Item | State | Notes |
| :--- | :--- | :--- |
| **Version** | `0.3.0` | PyPI / SHA-256 pinned in monorepo backend (D441) |
| **Commit** | `dc4bcfa` | Clean on `main` |
| **Python** | `>=3.13` | Pydantic v2, AnyIO (asyncio) |
| **Providers** | Google, Anthropic, OpenAI, Recorded | Behind `ModelPort` |

## 2. Evaluation Baseline
- **Gold Set:** `farkad_ai/eval/gold.json`
- **Pillars (7):** `food`, `water`, `exercise`, `sleep`, `supplements`, `drugs`, `recovery`.
- **Production Model:** `gemini-2.5-flash-lite`.

## 3. Operational Rules
- `pytest` runs offline against recorded cassettes (`ProviderName.recorded`).
- Prompts in `farkad_ai/prompts/assets/` are immutable sha256 assets.
- Token pricing defined in `farkad_ai/models/pricing.py`.
