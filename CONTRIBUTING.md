# Contributing to farkad-ai

Bug reports, sentences the engine gets wrong, and pull requests are welcome.

## Where to start

- **A sentence it got wrong**: open a [wrong extraction](https://github.com/brmel/farkad-ai/issues/new?template=wrong_extraction.yml)
  issue with the exact words and what you expected. These become gold-set cases.
- **A bug in the code**: open a [bug report](https://github.com/brmel/farkad-ai/issues/new?template=bug_report.yml).
- **A question or an idea**: open an issue before writing code.
- **A vulnerability**: follow [SECURITY.md](SECURITY.md), never a public issue.

Welcome ideas: adapters for other providers (Mistral, DeepSeek, a self-hosted model through vLLM or
Ollama), gold-set cases in more languages and dialects, and harder photos.

## Setting up

```bash
git clone https://github.com/brmel/farkad-ai && cd farkad-ai
python3.13 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Every test runs offline on scripted answers, so no API key or cloud account is needed.

## Before you open a pull request

```bash
ruff check .
ruff format --check .
mypy farkad_ai tests
pytest
```

CI installs the same `dev` extra, whose tools are pinned to exact versions, and runs the same
steps on every pull request, in a fresh environment with no optional provider installed. Keep one
change per pull request with its test, and make sure that test fails without the change.

The package is laid out by stage: [Repository layout](README.md#repository-layout).

## Releasing

Maintainers only. Releases are immutable: a wrong wheel is fixed by a new version, never by
replacing an asset.

1. Bump the version in `pyproject.toml`, merge to `main`, and wait for CI.
2. Tag the merge `vX.Y.Z` and build from a clean export of the tag
   (`git archive vX.Y.Z | tar -x -C <dir>`, then `uv build` there). The wheel is reproducible:
   the same tree gives the same sha256.
3. `gh release create vX.Y.Z dist/*`, then confirm the uploaded wheel's digest with
   `curl -sL <wheel url> | shasum -a 256`. Consumers pin that URL and digest.
