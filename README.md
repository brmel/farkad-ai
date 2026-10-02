<div align="center">

# farkad-ai

The extraction engine behind [Farkad](https://farkad.web.app): converts sentences, audio, or photos into structured health entries.

[![CI](https://github.com/brmel/farkad-ai/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/brmel/farkad-ai/actions/workflows/ci.yml)
[![CodeQL](https://github.com/brmel/farkad-ai/actions/workflows/codeql.yml/badge.svg?branch=main)](https://github.com/brmel/farkad-ai/actions/workflows/codeql.yml)
[![Python 3.13](https://img.shields.io/badge/python-3.13-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![Live demo](https://img.shields.io/badge/live%20demo-farkad.web.app-2ea44f)](https://farkad.web.app)

[Try it live](#try-it-live) · [Design Choices](#design-choices) · [Stack](#stack) · [Quickstart](#quickstart) · [Contributing](CONTRIBUTING.md)

</div>

## Try it live

[**farkad.web.app**](https://farkad.web.app) and the mobile apps run this engine. A sentence like *"two eggs, a big glass of water, and I slept badly"* yields structured entries for food, water, and sleep.

Production installs pinned releases from [GitHub Releases](https://github.com/brmel/farkad-ai/releases). This repository is the pure pipeline; storage, auth, and billing remain in the consumer backend.

## Why this repository is public

Demonstrates production AI techniques, architectural boundaries, and deliberate trade-offs in a shipped health product.

## Design Choices

✅ denotes utilized patterns; unmarked rows explain why alternatives were rejected.

### In the product

#### Models and inference

| | Technique | Purpose | Implementation or Rationale |
| :-: | --- | --- | --- |
| ✅ | [Structured output](https://ai.google.dev/gemini-api/docs/structured-output) | Guaranteed JSON schemas | Gemini `response_schema`, Claude forced tool, OpenAI `response_format`: [`models/`](farkad_ai/models) |
| ✅ | [Audio understanding](https://ai.google.dev/gemini-api/docs/audio) | Direct speech parsing without STT | Pass 1 transcribes and routes audio in one call: [`routing/`](farkad_ai/routing) |
| ✅ | [Image understanding](https://ai.google.dev/gemini-api/docs/image-understanding) | Multimodal input parsing | Meals or medication photos logged like text: [`prompts/assets/photo.txt`](farkad_ai/prompts/assets/photo.txt) |
| ✅ | [Thinking budget](https://ai.google.dev/gemini-api/docs/thinking) | Reasoning token allowance | Configured per tier: [`models/vertex.py`](farkad_ai/models/vertex.py) |
| ✅ | [LLM cascade](https://arxiv.org/abs/2305.05176) | Fast tier first, escalate on error | Escalates when compact output fails schema validation: [`extraction/adaptive.py`](farkad_ai/extraction/adaptive.py) |
| | [Provider fallback](https://docs.litellm.ai/docs/proxy/reliability) | Redundant provider failover | Offered by [`models/fallback.py`](farkad_ai/models/fallback.py); the product runs one provider |
| | Streaming | Incremental token delivery | Full structured payload required before UI rendering |
| | Context caching | Reusing prompt prefixes | Prefix reuse savings do not justify cache lifecycle complexity |
| | Batch inference | Asynchronous queued processing | Interactive user latency required |
| | Fine-tuning | Weight adaptation | Versioned prompts and golden datasets provide faster iteration |
| | Self-hosted serving | On-premise model execution | Managed cloud endpoints prioritized |

#### Workflow patterns

Patterns from Anthropic's [Building effective agents](https://www.anthropic.com/research/building-effective-agents).

| | Pattern | Mechanism | Implementation or Rationale |
| :-: | --- | --- | --- |
| ✅ | Prompt chaining | Sequential dependent execution | Pass 1 routing, then Pass 2 extraction: [`pipeline/two_pass.py`](farkad_ai/pipeline/two_pass.py) |
| ✅ | Routing | Input classification to specialized prompts | Pass 1 maps text to active pillars: [`routing/`](farkad_ai/routing) |
| ✅ | Parallelization | Concurrent independent calls | Parallel extraction across selected pillars: [`pipeline/specialists.py`](farkad_ai/pipeline/specialists.py) |
| | Orchestrator-workers | Dynamic runtime task delegation | Fixed pillar domain boundaries make static dispatch faster and deterministic |
| | Evaluator-optimizer | Critique and refinement loops | User validation and editing replaces autonomous review loops |

#### Agents and tools

| | Concept | Definition | Status |
| :-: | --- | --- | --- |
| | Autonomous agent | Model-directed step iteration | Deterministic pipelines are faster, cheaper, and reproducible |
| | Tool calling | Model invokes external functions | Off for Gemini; Claude forced tools only deliver structured responses |
| | Sub-agents | Autonomous agents delegating tasks | Specialist calls are parallel HTTP requests, not autonomous agents |
| | MCP | Protocol connecting models to external tools | No external tools exposed during inference |

#### Context and memory

| | Technique | Definition | Implementation |
| :-: | --- | --- | --- |
| ✅ | Long-term memory | Cross-session user preferences | Up to 40 stated facts and habits; captures receive max 300 chars: [`memory/`](farkad_ai/memory) |
| ✅ | Few-shot examples | In-prompt demonstrations | Domain-specific prompt examples: [`prompts/assets/extraction.txt`](farkad_ai/prompts/assets/extraction.txt) |
| ✅ | Prompt versioning | Cryptographic prompt tracking | SHA-256 asset content addressing: [`prompts/`](farkad_ai/prompts) |
| | RAG | Vector search over external corpora | User memory sheets fit entirely in context |

#### Evaluation and operations

| | Practice | Role | Implementation |
| :-: | --- | --- | --- |
| ✅ | Golden dataset | Regression evaluation | [`eval/scoring.py`](farkad_ai/eval/scoring.py) against [`eval/gold.json`](farkad_ai/eval/gold.json) |
| ✅ | Record & replay | Deterministic offline test suite | [`models/recorded.py`](farkad_ai/models/recorded.py) |
| ✅ | Guardrails | Input and output validation | Pass 1 filters non-health queries; Pydantic verifies schemas |
| ✅ | Tracing | Step-level telemetry | The product traces every model call; the package also offers step events: [`pipeline/observer.py`](farkad_ai/pipeline/observer.py) |
| ✅ | Token tracking | Token and latency accounting | [`types.py`](farkad_ai/types.py) (`Usage`); billing logic isolated in backend |
| ✅ | Human in the loop | Manual verification | All output remains editable by the user |

## Stack

- **Models:** Gemini 3.5 Flash-Lite on Vertex AI in production; Claude and OpenAI adapters behind the same port.
- **SDKs:** `google-genai`, `anthropic`, `openai` (behind `ModelPort`).
- **Runtime:** Python 3.13, Pydantic v2, AnyIO.
- **Verification:** `mypy` (strict), `ruff`, `pytest`.

## Quickstart

```bash
python3.13 -m venv .venv && source .venv/bin/activate
pip install "farkad-ai[google] @ git+https://github.com/brmel/farkad-ai"
```

Inspect versioned assets:
```bash
farkad-ai prompts
```

Route a health utterance with Google Vertex AI:
```bash
export GOOGLE_CLOUD_PROJECT=your-project GOOGLE_CLOUD_LOCATION=global
farkad-ai route --provider vertex --text "two eggs, a big glass of water, and I slept badly"
```

Output:
```json
{
  "applicable": true,
  "transcript": "two eggs, a big glass of water, and I slept badly",
  "language": "en",
  "pillars": ["food", "sleep", "water"],
  "mentions": {
    "food": ["two eggs"],
    "sleep": ["I slept badly"],
    "water": ["a big glass of water"]
  }
}
```

## Repository layout

```
farkad_ai/
├── routing/      Pass 1: applicability, language, pillar detection
├── extraction/   Pass 2: typed entity extraction with adaptive cascade
├── pipeline/     Two-pass orchestration and trace observation
├── models/       Unified ModelPort (Vertex, Anthropic, OpenAI, Recorded)
├── memory/       Fact and habit inference
├── prompts/      Content-addressed SHA-256 prompt assets
├── eval/         Gold dataset benchmark and scoring harness
└── cli.py        CLI entrypoints: prompts, route
tests/            Offline tests against scripted answers
```

## Contributing & License

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md). Licensed under [Apache 2.0](LICENSE).
