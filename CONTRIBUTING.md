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
venv holding only `.[dev]`, where the core must import no provider SDK and the adapter tests are
skipped, and with `.[dev,google,anthropic,openai]`, where the adapters are type-checked and tested
against the real SDKs.
