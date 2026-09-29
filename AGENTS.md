# AGENTS.md

Instructions for coding agents, and for people, working in `farkad-ai`.

## Rules

- **No infrastructure.** No database, account system or cloud service in this package. It takes a
  request and returns entries.
- **Providers behind `ModelPort`.** Never call a provider SDK from the pipeline or the routing
  pass; add an adapter in `farkad_ai/models/`. An adapter maps network and rate-limit errors to
  `ModelUnavailableError`, reports exact token counts and prices them with `TokenPrice.cost_cents()`.
- **Prompts are text files** in `farkad_ai/prompts/assets/`, versioned by the first 12 characters
  of their SHA-256. A prompt never names a date or a model.
- **Types decide branches.** `match` over typed values, frozen dataclasses, strict types. No
  `isinstance` on untyped data, no `getattr`/`hasattr`, no `except` that hides a bug.
- **Offline first.** Every change is testable on recorded answers (`RecordedModel`), with no key
  and no spend. A test that needs an optional provider SDK skips without it.
- **Small.** Functions under 40 lines, files under 250. No dead code, no abstraction without a
  second case, no duplicate tests, no comment the code can say.
- **Measure prompt changes.** Show the gold-set score before and after, with latency and cost.

The layout is in the [README](README.md#repository-layout); the checks to run before a pull request
are in [CONTRIBUTING.md](CONTRIBUTING.md#before-you-open-a-pull-request).
