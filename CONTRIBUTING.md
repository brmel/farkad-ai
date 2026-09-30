# Contributing to farkad-ai

Bug reports, sentences the engine gets wrong, and pull requests are welcome.

## Where to start

- **A sentence it got wrong**: open a [wrong extraction](https://github.com/brmel/farkad-ai/issues/new?template=wrong_extraction.yml)
  issue with the exact words and what you expected. These become gold-set cases.
- **A bug in the code**: open a [bug report](https://github.com/brmel/farkad-ai/issues/new?template=bug_report.yml).
- **A question or an idea**: start a thread in [Discussions](https://github.com/brmel/farkad-ai/discussions)
  before writing code.
- **A vulnerability**: follow [SECURITY.md](SECURITY.md), never a public issue.

Welcome ideas: adapters for other providers (Mistral, DeepSeek, a self-hosted model through vLLM or
Ollama), gold-set cases in more languages and dialects, and harder photos.

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

CI installs the same `dev` extra, whose tools are pinned to exact versions, and runs the same four
steps on every pull request, in a fresh environment with no optional provider installed. Follow the rules in [AGENTS.md](AGENTS.md), keep one change per pull request with its
test, and make sure that test fails without the change.

Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md).
