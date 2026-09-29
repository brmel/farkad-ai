<div align="center">

# farkad-ai

The extraction engine behind [Farkad](https://farkad.web.app): one sentence about your day, typed,
spoken or photographed, becomes separate health entries you can correct.

[![CI](https://github.com/brmel/farkad-ai/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/brmel/farkad-ai/actions/workflows/ci.yml)
[![CodeQL](https://github.com/brmel/farkad-ai/actions/workflows/codeql.yml/badge.svg?branch=main)](https://github.com/brmel/farkad-ai/actions/workflows/codeql.yml)
[![Python 3.13](https://img.shields.io/badge/python-3.13-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![Live demo](https://img.shields.io/badge/live%20demo-farkad.web.app-2ea44f)](https://farkad.web.app)

[Try it live](#try-it-live) · [What is used](#what-is-used-and-what-is-not) · [Stack](#stack) ·
[Quickstart](#quickstart) · [Contributing](CONTRIBUTING.md)

</div>

## Try it live

[**farkad.web.app**](https://farkad.web.app) runs this engine, and so do the Farkad apps for iOS
and Android. Type *"two eggs, a big glass of water, and I slept badly"* and it comes back as three
entries: food, water and sleep.

The prompts on `main` are the ones production sends, byte for byte; a parity test in the private
product repository keeps them, the pricing and the memory rules identical. Production connects
this pipeline to Firebase; this repository is the pipeline alone.

## Why this repository is public

To show, in a shipped product, which AI techniques were needed, where each one sits in the code,
and which ones were left out and why: in the product itself, and in how a coding agent builds it.

## What is used, and what is not

✅ marks what Farkad uses; an unmarked row is left out, with the reason. Each term links to its
definition.

### In the product

#### Models and inference

| | Term | What it means | Where in the code, or why not |
| :-: | --- | --- | --- |
| ✅ | [Structured output](https://ai.google.dev/gemini-api/docs/structured-output) | The model must answer in a given JSON schema | Gemini `response_schema`, a forced tool for Claude, `response_format` for OpenAI: [`models/`](farkad_ai/models) |
| ✅ | [Audio understanding](https://ai.google.dev/gemini-api/docs/audio) | The model takes speech directly, with no separate speech-to-text step | Pass 1 transcribes and routes a recording in one call: [`routing/`](farkad_ai/routing) |
| ✅ | [Image understanding](https://ai.google.dev/gemini-api/docs/image-understanding) | The model reads a photo | A photo of a plate or a label is logged like a sentence: [`prompts/assets/photo.txt`](farkad_ai/prompts/assets/photo.txt) |
| ✅ | [Thinking budget](https://ai.google.dev/gemini-api/docs/thinking) | How many tokens the model may reason with before it answers | Set per tier: [`models/vertex.py`](farkad_ai/models/vertex.py) |
| ✅ | [LLM cascade](https://arxiv.org/abs/2305.05176) | A cheap model first, a stronger one only when needed | Escalates when the cheap answer does not parse: [`extraction/adaptive.py`](farkad_ai/extraction/adaptive.py) |
| ✅ | [Provider fallback](https://docs.litellm.ai/docs/proxy/reliability) | Another provider takes over when one fails | [`models/fallback.py`](farkad_ai/models/fallback.py) |
| | [Streaming](https://til.simonwillison.net/llms/streaming-llm-apis) | The answer arrives token by token | The app needs the whole structured answer before it can show an entry |
| | [Context caching](https://ai.google.dev/gemini-api/docs/caching) | Reusing an already processed prompt prefix at a lower price | No code creates or reads a cache |
| | [Batch inference](https://ai.google.dev/gemini-api/docs/batch-api) | Many requests sent together, answered later at a lower price | A person is waiting for every answer |
| | [Fine-tuning](https://cloud.google.com/blog/products/ai-machine-learning/supervised-fine-tuning-for-gemini-llm) | Training a model further on your own examples | The prompts and the gold set carry the domain |
| | Self-hosted serving ([vLLM](https://github.com/vllm-project/vllm), [Ollama](https://github.com/ollama/ollama)) | Running open models on your own machines | Hosted APIs only |

#### Workflow patterns

The five patterns from Anthropic's [Building effective agents](https://www.anthropic.com/research/building-effective-agents).

| | Term | What it means | Where in the code, or why not |
| :-: | --- | --- | --- |
| ✅ | Prompt chaining | Calls in sequence, each using the previous answer | Pass 1, then pass 2: [`pipeline/two_pass.py`](farkad_ai/pipeline/two_pass.py) |
| ✅ | Routing | One call classifies the input and sends it to a specialised prompt | Pass 1 picks the topics a sentence covers: [`routing/`](farkad_ai/routing) |
| ✅ | Parallelization | Independent calls run at the same time | One extraction call per topic, all at once: [`pipeline/specialists.py`](farkad_ai/pipeline/specialists.py) |
| | Orchestrator-workers | A model splits the task at run time and hands out the parts | The topics are fixed in advance, and code merges the results |
| | Evaluator-optimizer | One call answers, another critiques, in a loop | One answer per topic; the person corrects the rest |

#### Agents and tools

| | Term | What it means | Where in the code, or why not |
| :-: | --- | --- | --- |
| | [Agent](https://www.anthropic.com/research/building-effective-agents) | A model that directs its own steps and tool use until the task is done | Every step is known in advance, so a fixed workflow is cheaper, faster and testable |
| | [Tool calling](https://ai.google.dev/gemini-api/docs/function-calling) | The model chooses a function and its arguments, and the code runs it | Gemini's automatic function calling is off; Claude's forced tool only carries the structured answer |
| | [Sub-agents](https://code.claude.com/docs/en/sub-agents) | An agent handing parts of a task to other agents | The topic specialists are parallel calls, not agents |
| | [MCP](https://modelcontextprotocol.io/) | An open protocol that connects AI applications to tools and data | Nothing in the product is called by an AI application |
| | [Agent skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) | Folders of instructions an agent loads when a task needs them | There is no agent in the product |

#### Context and memory

| | Term | What it means | Where in the code, or why not |
| :-: | --- | --- | --- |
| ✅ | [Long-term memory](https://www.philschmid.de/memory-in-agents) | What the system remembers about a user across sessions | Up to 40 facts the user stated, and habits counted from their entries; each capture is told at most 300 characters of them, medical facts first: [`memory/`](farkad_ai/memory) |
| ✅ | [Few-shot examples](https://arxiv.org/abs/2005.14165) | Worked examples placed in the prompt | The extraction prompt carries each topic's examples: [`prompts/assets/extraction.txt`](farkad_ai/prompts/assets/extraction.txt) |
| ✅ | [Prompt versioning](https://agenta.ai/blog/prompt-versioning-guide) | Every prompt change is tracked and named | Each prompt is named by a hash of its text: [`prompts/`](farkad_ai/prompts) |
| | [RAG](https://arxiv.org/abs/2005.11401) | Searching a document store, usually by embeddings, for text to add to the prompt | The memory sheet is small enough to send whole |

#### Evaluation and operations

| | Term | What it means | Where in the code, or why not |
| :-: | --- | --- | --- |
| ✅ | [Golden dataset](https://langfuse.com/resources/engineering/golden-dataset-evaluation) | Known inputs with expected outputs, scored after every change | [`eval/scoring.py`](farkad_ai/eval/scoring.py) and [`eval/gold.json`](farkad_ai/eval/gold.json) |
| ✅ | [Record and replay](https://vcrpy.readthedocs.io/) | Tests reuse recorded model answers, so they are repeatable, free and offline | [`models/recorded.py`](farkad_ai/models/recorded.py) |
| ✅ | [Guardrails](https://www.datadoghq.com/blog/llm-guardrails-best-practices/) | Checks on what goes into and comes out of the model | Pass 1 turns away sentences that are not about health; every answer is validated against its Pydantic schema |
| ✅ | [Tracing](https://opentelemetry.io/blog/2026/genai-observability/) | A record of every step and model call in a run | [`pipeline/observer.py`](farkad_ai/pipeline/observer.py), kept in process rather than exported to OpenTelemetry |
| ✅ | [Token and cost tracking](https://langfuse.com/docs/observability/features/token-and-cost-tracking) | The tokens and the price of every call | [`models/pricing.py`](farkad_ai/models/pricing.py) |
| ✅ | [Human in the loop](https://www.ibm.com/think/topics/human-in-the-loop) | A person reviews and corrects the output | Every entry is editable in the app and keeps the words it came from |
| | [LLM as a judge](https://arxiv.org/abs/2306.05685) | A model grades another model's answers | The gold set is scored field by field in code |

### In how it is built

The private product repository, where a coding agent writes, tests and ships the app, the backend
and the website.

#### The coding agent

| | Term | What it means | How it is used |
| :-: | --- | --- | --- |
| ✅ | [Coding agent](https://code.claude.com/docs/en/overview) | An agent that reads code, edits it, runs commands and commits | Claude Code writes, tests and ships the app, the backend and the website |
| ✅ | [Agent harness](https://en.wikipedia.org/wiki/Agent_harness) | The software around a model that gives it tools, state and limits | Claude Code runs the agent |
| ✅ | [Sub-agents](https://code.claude.com/docs/en/sub-agents) | Separate agents, each with its own context, working in parallel | Code reviews and clean-up sweeps, one area each |

#### Extending the agent

| | Term | What it means | How it is used |
| :-: | --- | --- | --- |
| ✅ | [Agent skills](https://code.claude.com/docs/en/skills) | Folders of instructions an agent loads when a task needs them | `slice` (an issue from pickup to merge), `verify` (see a change work on a device or in production logs), `clean-sweep`, and planning skills that turn a conversation into issues |
| ✅ | [MCP servers](https://modelcontextprotocol.io/) | Tools from other systems, offered to the agent through one protocol | Firebase (logs, Auth, Firestore), Dart and Flutter (the running app), Playwright (the website in a browser) |
| ✅ | [Plugins](https://code.claude.com/docs/en/plugins) | Installable bundles of skills, hooks and MCP servers | Skills for test-first work and code review, and the Firebase MCP server |

#### Context for the agent

| | Term | What it means | How it is used |
| :-: | --- | --- | --- |
| ✅ | [AGENTS.md](https://agents.md/) | A file of rules every agent session reads first | The product repository has one, and so does [this one](AGENTS.md) |
| ✅ | [Agent memory](https://code.claude.com/docs/en/memory) | Notes the agent writes for itself, kept between sessions | Corrections, decisions and pitfalls, one fact per note |

#### Guardrails for the agent

| | Term | What it means | How it is used |
| :-: | --- | --- | --- |
| ✅ | [Permission rules](https://code.claude.com/docs/en/permissions) | Which commands the agent may run without asking | An allowlist of commands |
| ✅ | [Hooks](https://code.claude.com/docs/en/hooks) | Scripts the harness runs before or after an agent's action | Block a bare deploy and destructive commands, block edits to generated files, format each edited file |
| ✅ | [Evaluation gate](https://langfuse.com/resources/engineering/golden-dataset-evaluation) | The build fails when accuracy on the golden dataset drops below a floor | `make gate` replays the gold set before every merge |

## Stack

#### Models and SDKs

| | Technology | What it is | Where, or why not |
| :-: | --- | --- | --- |
| ✅ | [Gemini 3.5 Flash-Lite](https://ai.google.dev/gemini-api/docs/models) on [Vertex AI](https://cloud.google.com/vertex-ai) | Google's model, served from Google Cloud | Production, for both tiers |
| ✅ | [Google Gen AI SDK](https://github.com/googleapis/python-genai) | Google's Python client for Gemini | [`models/vertex.py`](farkad_ai/models/vertex.py) |
| ✅ | [Anthropic SDK](https://github.com/anthropics/anthropic-sdk-python), [OpenAI SDK](https://github.com/openai/openai-python) | The providers' Python clients | Optional adapters; production runs on Gemini |

#### Agent and LLM frameworks

| | Technology | What it is | Where, or why not |
| :-: | --- | --- | --- |
| | [Google ADK](https://google.github.io/adk-docs/) | Google's framework for building, evaluating and deploying agents | There is no agent in the product; the pipeline calls the model SDK directly |
| | [Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview) | The agent loop and tools behind Claude Code, as a library | No agent in the product; development uses Claude Code itself |
| | [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/) | OpenAI's framework for multi-agent workflows | No agent in the product |
| | [LangChain](https://docs.langchain.com/), [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview) | Model integrations, agent loops and stateful graphs | Two fixed passes need no graph runtime |
| | [LlamaIndex](https://developers.llamaindex.ai/python/framework/) | A framework for retrieval over your own documents | There are no documents to retrieve |
| | [LiteLLM](https://docs.litellm.ai/docs/) | One API over more than a hundred providers | One small `ModelPort` covers the three providers used |

#### Language and tooling

| | Technology | What it is | Where, or why not |
| :-: | --- | --- | --- |
| ✅ | Python 3.13 | The language of this package and of the backend | |
| ✅ | [Pydantic](https://docs.pydantic.dev/) | Data validation from type hints | Every schema the model answers in |
| ✅ | mypy, ruff, pytest | Strict type checking, lint and format, tests | [CI](.github/workflows/ci.yml) on every push and pull request |
| ✅ | [CodeQL](https://docs.github.com/en/code-security/code-scanning/introduction-to-code-scanning/about-code-scanning-with-codeql), [Dependabot](https://docs.github.com/en/code-security/dependabot) | Code scanning, dependency updates | CodeQL on every push; Dependabot weekly |

#### Product infrastructure (private repository)

| | Technology | What it is | Where, or why not |
| :-: | --- | --- | --- |
| ✅ | [Cloud Functions for Firebase](https://firebase.google.com/docs/functions) | Serverless backend, here in Python | The API, the worker that runs the pipeline, scheduled jobs |
| ✅ | Firestore, Cloud Storage, Cloud Tasks, Remote Config, Firebase Auth, App Check | Google Cloud and Firebase services | Entries, recordings, the job queue, settings, accounts, abuse protection |
| ✅ | [Flutter](https://flutter.dev) | One codebase for iOS and Android | The app |
| ✅ | TypeScript, React, Vite, Tailwind CSS, Firebase Hosting | Web stack | [farkad.web.app](https://farkad.web.app) |
| ✅ | [Stripe](https://stripe.com) | Payments | Premium |

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

With a Google Cloud project that has Vertex AI on (`gcloud auth application-default login`):

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

`--provider anthropic` and `--provider openai` read `ANTHROPIC_API_KEY` and `OPENAI_API_KEY`, with
the matching extra installed.

## Repository layout

```
farkad_ai/
├── routing/      pass 1: is this about health, in which language, which topics
├── extraction/   pass 2: one topic's fields, with a stronger model when a cheap one fails
├── pipeline/     the two passes together, and the trace of a run
├── models/       one interface; Gemini, Claude, OpenAI and recorded answers behind it
├── memory/       facts and habits, and the sheet a capture is told
├── prompts/      the prompt text files, versioned by hash
├── eval/         the gold set, and scoring against it
└── cli.py        farkad-ai models | prompts | route
tests/            offline: every test runs on recorded answers
```

## Contributing, security, license

Read [CONTRIBUTING.md](CONTRIBUTING.md) before a pull request, and use
[Discussions](https://github.com/brmel/farkad-ai/discussions) for questions. Report a vulnerability
privately, as [SECURITY.md](SECURITY.md) describes. Licensed under [Apache 2.0](LICENSE).
