# AGENTS.md

Instructions for coding agents, and for people, working in `farkad-ai`. Agents that read
`AGENTS.md` (Claude Code, Codex, Cursor and others) load this file before they start.

## Rules

- **No infrastructure.** No Firestore, Firebase, Postgres, Stripe or any other service in this
  package. It takes a request and returns entries.
- **Providers behind `ModelPort`.** Never call a provider SDK from the pipeline or the routing
  pass; add an adapter in `farkad_ai/models/`.
- **Types decide branches.** Use `match` over typed values, frozen dataclasses and strict types.
  No `isinstance` on untyped data, no `getattr`/`hasattr`, no `except` that hides a bug.
- **Offline first.** Every change is testable on recorded answers (`RecordedModel`), with no key
  and no spend.
- **Small and lean.** Functions under 40 lines, files under 250. No dead code, no abstraction
  without a second case that needs it, no duplicate tests.
- **Comments state an outside constraint, with its source.** Anything else is said by a name.

## Layout

| Path | What it holds |
| --- | --- |
| `farkad_ai/types.py` | `Prompt`, `Completion`, `Usage`, `MediaBlob`, `PipelineStep` |
| `farkad_ai/models/` | `ModelPort`, the Gemini, Claude, OpenAI and recorded adapters, fallback, pricing |
| `farkad_ai/prompts/` | the prompt text files and their hash versions |
| `farkad_ai/routing/` | pass 1: relevance, language and topics |
| `farkad_ai/extraction/` | pass 2: one topic's fields, and tier escalation |
| `farkad_ai/pipeline/` | the two passes together, and the trace of a run |
| `farkad_ai/memory/` | facts, habits and the sheet a capture is told |
| `farkad_ai/eval/` | scoring against the gold set |
| `tests/` | the offline suite |

## Before a pull request

```bash
ruff check .
ruff format --check .
mypy farkad_ai
pytest
```

CI runs the same four steps in a fresh environment with no optional provider installed, so a
test that needs `google-genai`, `anthropic` or `openai` must skip without it.
