# AGENTS — FARKAD-AI

Operational manual for coding agents in `farkad-ai`. Law: [SOUL](SOUL.md). State: [MEMORY](MEMORY.md).

## 1. Quality Gates (Must Pass 100%)
```bash
ruff check . && ruff format --check .
mypy farkad_ai tests
pytest -q
```

## 2. Skills
| When | Skill | Purpose |
| :--- | :--- | :--- |
| Prompt/router changes | `/eval-prompt` | Scores against `gold.json` (routing, field F1, tokens, latency) |
| Live provider capture | `/record-fixtures` | Records live outputs into offline cassettes (`tests/fixtures/`) |
| Dead code sweep | `/clean-sweep` | Finds unreferenced imports, dead branches, unused prompt assets |

## 3. Package Seams
- `farkad_ai/models/`: Adapters behind `ModelPort`.
- `farkad_ai/routing/`: Pass 1: identify applicable pillars.
- `farkad_ai/extraction/`: Pass 2: extract typed health entities.
- `farkad_ai/memory/`: Fact and habit inference.
- `farkad_ai/prompts/`: sha256-addressed prompt assets (`assets/`).
- `farkad_ai/eval/`: Gold set (`gold.json`) and scoring (`scoring.py`).
