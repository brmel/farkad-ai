# farkad-ai — Agent Operating Manual

Binding instructions for coding agents and developers working in `farkad-ai`.

Context: [SOUL](SOUL.md) · [MEMORY](MEMORY.md) · [README](README.md) · [CONTRIBUTING](CONTRIBUTING.md)

---

## 1. Core Principles

- **No infrastructure.** No database, auth system, or cloud bucket in this package. It takes an input (text, audio, image) and produces validated health entities.
- **Providers behind `ModelPort`.** Never call a vendor SDK (`google-genai`, `anthropic`, `openai`) directly from pipelines. Write an adapter in `farkad_ai/models/` implementing `ModelPort`.
- **Prompts are cryptographic assets.** Stored in `farkad_ai/prompts/assets/`, versioned by the first 12 chars of their SHA-256 hash. Prompts never contain dates or vendor names.
- **Offline first.** Every pipeline unit test must pass against `RecordedModel` without network access or API keys.
- **Strict types & exhaustive dispatch.** Pattern match on sealed unions (`match x: case ...`). No `isinstance` on untyped data, no `getattr`/`hasattr`, no silent exception swallowing.
- **Measure every prompt modification.** Every prompt change must publish before-and-after gold-set metrics (routing accuracy, field-level F1, latency, cost).

---

## 2. Validation & Quality Gates

Run these commands before opening any pull request:

```bash
# Linting & Formatting
ruff check .
ruff format --check .

# Static Type Verification
mypy farkad_ai tests

# Offline Unit Tests
pytest -q
```

All four checks must pass with zero warnings or errors.

---

## 3. Skills Matrix

Invoke these skills for specialized tasks:

| When | Skill | Purpose & Scope |
| :--- | :--- | :--- |
| Evaluating prompt or routing changes | `/eval-prompt` | Runs benchmark against `farkad_ai/eval/gold.json`, scores routing and field accuracy, reports cost & latency deltas. |
| Recording live provider responses | `/record-fixtures` | Captures live model outputs into offline cassettes for zero-cost reproducible testing. |
| Code cleanup and dead code removal | `/clean-sweep` | Removes unused imports, unreachable branches, and dead prompt assets. |

---

## 4. Layout & Seams

- `farkad_ai/models/`: Vendor adapters implementing `ModelPort`. Maps network faults to `ModelUnavailableError`.
- `farkad_ai/routing/`: Pass 1 router; identifies applicable pillars (`food`, `water`, `exercise`, etc.).
- `farkad_ai/extraction/`: Pass 2 extraction; produces typed domain entities.
- `farkad_ai/memory/`: Fact and habit inference from historical captures.
- `farkad_ai/prompts/`: Prompt registry and sha256 asset management.
- `farkad_ai/eval/`: Gold evaluation benchmark and scoring metrics (`scoring.py`).
