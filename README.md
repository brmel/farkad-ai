<div align="center">

# farkad-ai

The extraction engine behind [Farkad](https://farkad.web.app): one sentence about your day, typed,
spoken or photographed, becomes separate health entries you can correct.

[![CI](https://github.com/brmel/farkad-ai/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/brmel/farkad-ai/actions/workflows/ci.yml)
[![CodeQL](https://github.com/brmel/farkad-ai/actions/workflows/codeql.yml/badge.svg?branch=main)](https://github.com/brmel/farkad-ai/actions/workflows/codeql.yml)
[![Python 3.13](https://img.shields.io/badge/python-3.13-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![Live demo](https://img.shields.io/badge/live%20demo-farkad.web.app-2ea44f)](https://farkad.web.app)

[Try it live](#try-it-live) · [Why it is public](#why-this-repository-is-public) ·
[What is used](#what-is-used-and-what-is-not) · [Stack](#stack) · [Quickstart](#quickstart) ·
[Contributing](CONTRIBUTING.md)

</div>

## Try it live

[**farkad.web.app**](https://farkad.web.app) runs this engine. Type a day in one sentence, for
example *"two eggs, a big glass of water, and I slept badly"*, and it comes back as three entries:
food, water and sleep. The same engine serves the Farkad apps for iOS and Android.

The prompts on `main` are the prompts production sends, byte for byte. The pricing table, the
memory rules and the data contracts are held equal to production by a parity test in the product
repository. Production wires the same two-pass pipeline to Firebase; this repository is the
pipeline without the infrastructure.

## Why this repository is public

AI tooling comes with a lot of vocabulary: agents, tool calling, MCP servers, skills, memory,
harnesses, sub-agents. This repository shows which of them a shipped product actually needed,
where each one sits in the code, and which ones it does without and why.

It covers two things:

- **The product**: the code in this repository, which turns a sentence into entries.
- **How it is built**: the private product repository, where a coding agent writes, tests and
  ships the app, the backend and the website.

## What is used, and what is not

🟢 used · 🔴 not used

### In the product

| Term | What it means | | Where, or why not |
| --- | --- | :-: | --- |
| Workflow | The code fixes the steps; the model fills each one in | 🟢 | Pass 1 routes the sentence, pass 2 extracts each topic: [`pipeline/two_pass.py`](farkad_ai/pipeline/two_pass.py) |
| Structured output | The answer must match a JSON schema | 🟢 | Gemini `response_schema`, a forced tool for Claude, `response_format` for OpenAI, then Pydantic validation: [`models/`](farkad_ai/models) |
| Parallel model calls | Several calls at once, results merged | 🟢 | One specialist call per topic: [`pipeline/specialists.py`](farkad_ai/pipeline/specialists.py) |
| Model tiers | A cheap model first, a stronger one when the answer does not parse | 🟢 | [`extraction/adaptive.py`](farkad_ai/extraction/adaptive.py) |
| Provider fallback | Another provider when the first one is down | 🟢 | [`models/fallback.py`](farkad_ai/models/fallback.py) |
| Multimodal input | Audio and images, not only text | 🟢 | Pass 1 transcribes speech itself; a photo prompt reads labels and plates: [`prompts/assets/`](farkad_ai/prompts/assets) |
| Long-term memory | What the model knows about the user across sessions | 🟢 | Up to 40 facts the user stated and habits counted from their entries, sent as a short sheet: [`memory/`](farkad_ai/memory) |
| Reasoning budget | How many tokens the model may think before it answers | 🟢 | Set per tier: [`models/vertex.py`](farkad_ai/models/vertex.py) |
| Evaluation harness | Replaying known cases and scoring every field | 🟢 | [`eval/scoring.py`](farkad_ai/eval/scoring.py) and the gold set in [`tests/fixtures/`](tests/fixtures) |
| Offline replay | Recorded answers, so tests need no key and cost nothing | 🟢 | [`models/recorded.py`](farkad_ai/models/recorded.py) |
| Prompt versioning | Each prompt is named by a hash of its text | 🟢 | [`prompts/`](farkad_ai/prompts) |
| Tracing | A record of every step of a run | 🟢 | [`pipeline/observer.py`](farkad_ai/pipeline/observer.py) |
| Human in the loop | A person confirms or corrects the output | 🟢 | Every entry is editable in the app, and keeps the words it came from |
| Agent | A model that plans its own steps and calls tools in a loop | 🔴 | Every step is known in advance, so a fixed workflow is cheaper, faster and testable |
| Tool calling | The model picks a function and its arguments | 🔴 | Gemini's automatic function calling is off; Claude's tool is forced and only carries the answer |
| Sub-agents | An agent handing tasks to other agents | 🔴 | The specialists are parallel calls, not agents |
| MCP server | A standard way to expose tools and data to an agent | 🔴 | No agent calls this code |
| Skills | Instructions an agent loads for one kind of task | 🔴 | No agent in the product |
| RAG and embeddings | Searching a vector index for text to add to the prompt | 🔴 | The memory sheet is small enough to send whole |
| Prompt caching | Reusing a processed prompt prefix across calls | 🔴 | |
| Streaming | Receiving the answer token by token | 🔴 | The app needs the whole structured answer |
| Fine-tuning | Training a model further on your own data | 🔴 | The prompts and the gold set carry the domain |
| Self-hosted models | Running open models on your own servers (vLLM, Ollama) | 🔴 | Hosted APIs only |
| LLM as judge | A model grading another model's answers | 🔴 | The gold set is scored field by field in code |

### In how it is built

| Term | What it means | | How |
| --- | --- | :-: | --- |
| Coding agent | A model that edits code, runs commands and reads the results | 🟢 | Claude Code writes, tests and ships the app, the backend and the website |
| Agent harness | The program that runs an agent: its tools, permissions and hooks | 🟢 | Claude Code, with an allowlist of commands and three hooks |
| Hooks | Scripts the harness runs around an agent's actions | 🟢 | Block a bare deploy and destructive commands, block edits to generated files, format each edited file |
| Skills | Instructions an agent loads for one kind of task | 🟢 | `slice` (an issue from pickup to merge), `verify` (see a change work on a device or in production logs), `clean-sweep`; plugin skills for test-first work, code review and planning |
| MCP servers | Tools from other systems, offered to the agent | 🟢 | Firebase (logs, Auth, Firestore), Dart and Flutter (the running app), Playwright (the website in a browser) |
| Sub-agents | An agent handing tasks to other agents | 🟢 | Parallel code reviews and clean-up sweeps, one area each |
| Agent memory | Notes the agent keeps between sessions | 🟢 | Corrections, decisions and pitfalls, one fact per note |
| Agent instructions | A file every agent session reads first | 🟢 | `AGENTS.md`; this repository has [its own](AGENTS.md) |
| Evaluation gate | The build fails when extraction accuracy drops | 🟢 | The gold set is replayed on every merge, against a recorded floor |

## Stack

| Layer | Used | Not used |
| --- | --- | --- |
| Model | Gemini 3.5 Flash-Lite on Vertex AI, for both tiers | Self-hosted models |
| Model SDKs | `google-genai`; `anthropic` and `openai` as optional adapters | Google ADK, Claude Agent SDK, OpenAI Agents SDK, LangChain, LangGraph, LlamaIndex, LiteLLM |
| Language and checks | Python 3.13, Pydantic 2, mypy (strict), ruff, pytest | |
| Backend (private) | Cloud Functions for Firebase in Python, Firestore, Cloud Storage, Cloud Tasks, Remote Config, Firebase Auth, App Check | |
| App (private) | Flutter, for iOS and Android | |
| Website | TypeScript, React, Vite and Tailwind CSS on Firebase Hosting | |
| Payments | Stripe | |
| Development | Claude Code, GitHub Actions, CodeQL, Dependabot | |

## Quickstart

The package is installed from GitHub; it is not on PyPI.

```bash
python3.13 -m venv .venv && source .venv/bin/activate
pip install "farkad-ai[google] @ git+https://github.com/brmel/farkad-ai"
```

Without a key or an account:

```bash
farkad-ai models    # every model it can price, and when each one retires
farkad-ai prompts   # the prompts, each with its version hash
```

With a Google Cloud project that has Vertex AI enabled (`gcloud auth application-default login`):

```bash
export GOOGLE_CLOUD_PROJECT=your-project GOOGLE_CLOUD_LOCATION=global
farkad-ai route --provider vertex --text "two eggs, a big glass of water, and I slept badly"
```

```json
{
  "applicable": true,
  "transcript": "two eggs, a big glass of water, and I slept badly",
  "language": "en",
  "pillars": ["food", "sleep", "water"]
}
```

`--provider anthropic` and `--provider openai` read `ANTHROPIC_API_KEY` and `OPENAI_API_KEY`;
install the matching extra (`farkad-ai[anthropic]`, `farkad-ai[openai]`) first.

## Repository layout

```
farkad_ai/
├── routing/      pass 1: is this about health, in which language, which topics
├── extraction/   pass 2: one topic's fields, with a stronger model when a cheap one fails
├── pipeline/     the two passes together, and the trace of a run
├── models/       one interface; Gemini, Claude, OpenAI and recorded answers behind it
├── memory/       facts and habits, and the sheet a capture is told
├── prompts/      the prompt text files, versioned by hash
├── eval/         scoring against the gold set
└── cli.py        farkad-ai models | prompts | route
tests/            offline: every test runs on recorded answers
```

## Development

```bash
git clone https://github.com/brmel/farkad-ai && cd farkad-ai
python3.13 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

ruff check . && ruff format --check . && mypy farkad_ai && pytest
```

These are the four steps [CI](.github/workflows/ci.yml) runs on every push and pull request.

## Contributing

Bug reports, failure cases and pull requests are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md)
first, and use [Discussions](https://github.com/brmel/farkad-ai/discussions) for questions and
ideas. Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md).

## Security

Report a vulnerability privately, as [SECURITY.md](SECURITY.md) describes, never in a public
issue.

## License

[Apache 2.0](LICENSE).
