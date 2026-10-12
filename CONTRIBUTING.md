# Contributing

- **A sentence the engine gets wrong**: open a [wrong extraction](https://github.com/brmel/farkad-ai/issues/new?template=wrong_extraction.yml)
  issue.
- **A bug**: open a [bug report](https://github.com/brmel/farkad-ai/issues/new?template=bug_report.yml).
- **An idea**: open an issue before writing code. Adapters for other providers and gold-set cases
  in more languages are welcome.
- **A vulnerability**: follow [SECURITY.md](SECURITY.md).

A pull request holds one change and a test that fails without it.

## Setting up

```bash
git clone https://github.com/brmel/farkad-ai && cd farkad-ai
python3.13 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
ruff check . && ruff format --check . && mypy farkad_ai tests && pytest
```

Tests run offline on scripted answers; no API key is needed. CI runs the same checks twice: in a
venv holding only `.[dev]`, where the core must import no provider SDK, and with
`.[dev,google,anthropic,openai]`, where the adapters are type-checked against the real SDKs.

## Releasing

Releases are immutable: a wrong wheel is fixed by a new version.

1. Bump `version` in `pyproject.toml`, merge to `main`, and wait for CI to pass.
2. Tag the merge `vX.Y.Z` and push the tag.
3. `git archive vX.Y.Z | tar -x -C <dir>`, then `uv build` in `<dir>`.
4. `gh release create vX.Y.Z <dir>/dist/*`.
5. Check that `curl -sL <wheel url> | shasum -a 256` matches the local wheel: consumers pin that
   URL and digest.
