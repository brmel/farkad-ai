# farkad-ai — agentic surface

Constitution is [`SOUL.md`](../SOUL.md); operating manual is [`AGENTS.md`](../AGENTS.md); living ledger is [`MEMORY.md`](../MEMORY.md).

| File | Purpose |
| :--- | :--- |
| `SOUL.md` | Immutable values: zero infrastructure, provider agnosticism behind `ModelPort`, offline-first evaluation, sha256 prompt assets. |
| `AGENTS.md` | Operating rules, quality gates (`ruff`, `mypy`, `pytest`), skills matrix, and package layout. |
| `MEMORY.md` | Living inventory of active package version, gold-set baseline, and supported model pricing. |
| `skills/eval-prompt` | Benchmark extraction prompts and router logic against `gold.json`, scoring accuracy, latency, and cost deltas. |
| `skills/record-fixtures` | Records live provider responses into offline cassette fixtures for zero-cost reproducible tests. |
