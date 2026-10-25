# Contributing

Everyone taking part follows the [code of conduct](CODE_OF_CONDUCT.md).

- **A sentence the engine gets wrong**: open a [wrong extraction](https://github.com/brmel/farkad-ai/issues/new?template=wrong_extraction.yml)
  issue; it becomes a gold-set case.
- **A bug**: open a [bug report](https://github.com/brmel/farkad-ai/issues/new?template=bug_report.yml).
- **A feature**: open an issue before writing code. Adapters for other providers and gold-set
  cases in more languages are welcome, and issues labelled
  [good first issue](https://github.com/brmel/farkad-ai/labels/good%20first%20issue) are sized
  for a first pull request.
- **A vulnerability**: follow [SECURITY.md](SECURITY.md).

## Setting up

Python 3.13, the version CI runs. With [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/brmel/farkad-ai && cd farkad-ai
uv venv --python 3.13 && source .venv/bin/activate
uv pip install -e ".[dev]"
```

With pip, the last two lines are `python3.13 -m venv .venv && source .venv/bin/activate` and
`pip install -e ".[dev]"`. Add `google`, `anthropic` or `openai` to the extras to work on that
adapter.

## The checks

```bash
ruff check . && ruff format --check . && mypy farkad_ai tests && pytest
```

They run offline on scripted and recorded answers; no API key is needed. CI runs them twice:
with `.[dev]` alone, where the core must import no provider SDK and the adapter tests are
skipped, and with `.[dev,google,anthropic,openai]`, where the adapters are type-checked and
tested against the real SDKs. CodeQL scans every pull request as well.

## The eval and its recordings

`farkad-ai eval` scores the gold set, `farkad_ai/eval/example_gold.json`, on the example topics
in `farkad_ai/eval/pillars.py`, replaying the answers in `farkad_ai/eval/recordings/`. Each
recording is keyed by a hash of the tier, the answer schema, the instructions and the input
(`farkad_ai/models/recorded.py`). Changing a prompt, a schema or an example topic therefore
leaves sentences with no recorded answer, and `pytest` fails saying whether the prompt or the
schema changed. Record new answers on a live model:

```bash
farkad-ai eval --provider vertex --record
```

Recording asks the model about every gold sentence, which spends money on your account, and
replaces every recording. The committed recordings, and the README's table, come from Vertex;
update the table from the new output. If you cannot record on Vertex, say so in the pull request
and the maintainer records them.

## Adding a model provider

Subclass `ProviderModel` (`farkad_ai/models/provider.py`) in a new module beside
`farkad_ai/models/anthropic.py`: `_send` the prompt, return its structured `_answer`, count its
`_usage`, declare the reasoning levels it honours, and build its client in `connected()`. Name it
in `farkad_ai/models/factory.py`, and give its SDK an extra and a mypy override in
`pyproject.toml` and a place in CI's matrix; no other module imports it.

## Tests and names

- A test's name states the behaviour: `test_a_refusal_neither_tier_can_answer_is_never_paid_for_twice`.
  A test that cannot fail is deleted.
- No test calls a live model: it uses a scripted `Model` from `tests/support.py`, or recordings.
- Names are whole words. An interface is named for the role it plays and an implementation for
  how it plays it: `Model` and `RecordedModel`, `CaptureEngine` and `TwoPassCaptureEngine`. The
  types that cross a package's boundary live in its `port.py`.
- A comment states only a constraint the code cannot, citing its source, as in
  `farkad_ai/models/vertex.py`.

## Pull requests

A pull request holds one change and a test that fails without it. A change a consumer would
notice adds a line under Unreleased in [CHANGELOG.md](CHANGELOG.md). The maintainer reviews it
against this file and the issue it answers, and merges it with a merge commit once CI passes.
