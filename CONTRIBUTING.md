# Contributing to farkad-ai

Thank you for taking the time. Bug reports, sentences the engine gets wrong, and pull requests are
all welcome.

## Where to start

- **A sentence it got wrong**: open a [wrong extraction](https://github.com/brmel/farkad-ai/issues/new?template=wrong_extraction.yml)
  issue with the exact words and what you expected. These become gold-set cases, which is the
  most useful contribution there is.
- **A bug in the code**: open a [bug report](https://github.com/brmel/farkad-ai/issues/new?template=bug_report.yml).
- **A question or an idea**: start a thread in [Discussions](https://github.com/brmel/farkad-ai/discussions)
  before writing code, so the design can be agreed first.
- **A vulnerability**: follow [SECURITY.md](SECURITY.md), never a public issue.

Ideas that would be welcome: adapters for other providers (Mistral, DeepSeek, a self-hosted
model through vLLM or Ollama), gold-set cases in more languages and dialects, and harder photos.

## Setting up

```bash
git clone https://github.com/brmel/farkad-ai && cd farkad-ai
python3.13 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Every test runs offline on recorded answers, so no API key or cloud account is needed.

## Before you open a pull request

```bash
ruff check .
ruff format --check .
mypy farkad_ai
pytest
```

CI runs the same four steps on every pull request, in a fresh environment with no optional
provider installed.

## Conventions

- **No infrastructure.** No database, user accounts or cloud storage in this package; it takes a
  request and returns entries.
- **Providers behind one interface.** A new provider implements `ModelPort`, maps its network and
  rate-limit errors to `ModelUnavailableError`, reports exact token counts, and prices them
  through `TokenPrice.cost_cents()`.
- **Prompts are text files.** They live in `farkad_ai/prompts/assets/` and are versioned by the
  first 12 characters of their SHA-256. A prompt never names a date or a model.
- **Measure a prompt change.** Show the gold-set score before and after, with the latency and the
  token cost.
- **Small units.** Functions stay under 40 lines and files under 250. Types are strict, branches
  use `match` over typed values, and nothing is kept "for later".
- **One change per pull request**, with its test. A test must fail when the behaviour it names
  breaks.

## Code of Conduct

Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md).
