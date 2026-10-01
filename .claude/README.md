# farkad-ai — agentic surface

Constitution: [`SOUL.md`](../SOUL.md); manual: [`AGENTS.md`](../AGENTS.md); state: [`MEMORY.md`](../MEMORY.md).

| File | Purpose |
| :--- | :--- |
| `SOUL.md` | Values: zero infrastructure, provider agnosticism, offline evaluation, immutable prompt assets. |
| `AGENTS.md` | Quality gates (`ruff`, `mypy`, `pytest`), skills matrix, and package architecture. |
| `MEMORY.md` | Living inventory of active package version, gold-set baseline, and model configuration. |
| `skills/eval-prompt` | Benchmark prompts and router against `gold.json` (accuracy, latency, tokens). |
| `skills/record-fixtures` | Record provider responses into offline cassette fixtures for reproducible tests. |
