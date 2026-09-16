# farkad-ai — Agent & Contributor Guidance

Operational rules and conventions for AI coding agents and human contributors working on `farkad-ai`.

---

## 1. Core Principles

- **Zero Cloud Coupling**: `farkad-ai` is pure Python logic and protocols. Never import or introduce dependencies on Firestore, Firebase, Postgres, Stripe, or proprietary infrastructure.
- **Provider Agnostic**: LLMs must implement the `ModelPort` protocol. Never hardcode SDK calls directly into the pipeline or routing passes.
- **Static Over Dynamic**: Use structural pattern matching (`match / case`), frozen dataclasses, and strict types. Avoid runtime `isinstance` on untyped data, `getattr`/`hasattr`, or defensive `try/catch` hiding bugs.
- **Deterministic Offline Replay**: Every prompt or pipeline change must be testable offline using `RecordedModel` without requiring cloud credentials or incurring API spend.
- **Concise, High-Signal Code**: Functions ≤ 40 lines, files ≤ 250 lines. Remove dead code, redundant abstractions, and duplicate tests. Do not add speculative code or layers without real variation.

---

## 2. Agent Skills & Directory Layout

Task-specific guidelines and conventions:

- `farkad_ai/types.py`: Fundamental primitives (`Prompt`, `Completion`, `Usage`, `MediaBlob`, `PipelineStep`).
- `farkad_ai/models/`: Model ports (`port.py`), token pricing (`pricing.py`), providers (`vertex.py`), and offline fixtures (`recorded.py`).
- `farkad_ai/prompts/`: Raw prompt text files under `assets/` and sha256 versioning loader.
- `farkad_ai/routing/`: Pass 1 intent detection and domain classification (`router.py`, `pass_one.py`).
- `farkad_ai/extraction/`: Pass 2 specialist extraction protocols (`port.py`).
- `farkad_ai/pipeline/`: Two-pass orchestrator (`two_pass.py`) and specialist concurrency (`specialists.py`).
- `farkad_ai/eval/`: Offline scoring metrics, token counts, and accuracy percentiles (`scoring.py`).
- `tests/`: Offline pytest suite testing router, pipeline, and scoring.

---

## 3. Pull Request & Verification Checklist

Always run all three checks locally before opening a pull request:

```bash
# 1. Format & Lint
ruff check .
ruff format --check .

# 2. Strict Type Check
mypy farkad_ai

# 3. Deterministic Test Suite
pytest
```
