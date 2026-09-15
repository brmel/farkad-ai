# farkad-ai

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](pyproject.toml)
[![Type Checked: mypy](https://img.shields.io/badge/mypy-checked-blue)](pyproject.toml)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

Autonomous, multimodal structured extraction and health logging pipeline.

Inspired by open-source algorithms and protocol architectures like **Twitter/X Algorithm** and **Telegram TDLib**, `farkad-ai` decouples the core artificial intelligence intelligence, routing decisions, prompt evaluation, and schema extraction engine from proprietary infrastructure, databases, and billing.

---

## Highlights

- 🎯 **Two-Pass AI Loop**: Deterministic Pass 1 router for intent, language, and pillar routing, followed by concurrent Pass 2 specialists for granular schema extraction.
- 🔌 **Provider Agnostic (`ModelPort`)**: Clean protocol interface supporting Google Gemini, Anthropic Claude, OpenAI, and custom or local models.
- ⚡ **Zero Cloud Dependencies**: Runs completely self-contained with pure Pydantic schemas and standard library typing.
- 🧪 **Offline Deterministic Replay**: Test and evaluate the full pipeline offline with `RecordedModel` without API keys, tokens, or network I/O.
- 📊 **Benchmarking Harness**: Measure extraction accuracy, token counts, latency, and exact cost in cents.

---

## Installation

```bash
pip install farkad-ai
```

Or from source:

```bash
git clone https://github.com/brmel/farkad-ai.git
cd farkad-ai
pip install -e .
```

---

## Quickstart

### 1. Simple Two-Pass Pipeline

```python
import asyncio
from google import genai
from farkad_ai import (
    CaptureRequest,
    Logged,
    NothingToLog,
    VertexModel,
    build_pipeline,
)

async def main():
    # 1. Connect model provider (or use RecordedModel for offline/test environments)
    client = genai.Client()
    model = VertexModel(client)

    # 2. Build pipeline with your registry and specialist extractor
    pipeline = build_pipeline(
        model=model,
        registry=my_pillar_registry,
        extractor=my_specialist_extractor,
    )

    # 3. Process spoken or typed input
    request = CaptureRequest(
        profile=my_user_profile,
        text="I drank 500ml of water after my 5k run",
    )
    outcome = await pipeline.run(request)

    match outcome:
        case Logged(routes=routes, extracted=entries):
            print(f"Routes identified: {routes}")
            for entry in entries:
                print(f"Extracted [{entry['pillar']}]: {entry['data']}")
        case NothingToLog(reason=reason):
            print(f"No health actions identified: {reason}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Architecture

```
User Input (Audio / Text / Image)
            │
            ▼
┌───────────────────────────────────────┐
│     Pass 1: Intent & Route Router     │
│  - Health relevance check             │
│  - Stated time & temporal anchors     │
│  - Target specialist pillars (sleep,  │
│    water, nutrition, vitals, etc.)    │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│     Pass 2: Specialist Extractors     │
│  - Concurrent execution per pillar    │
│  - Strict Pydantic schema validation  │
│  - Unit conversion & range guards     │
└───────────────────┬───────────────────┘
                    │
                    ▼
           Validated Extraction
```

---

## Core Protocols & Extension Points

Every component in `farkad-ai` is exposed via clean Python protocols in [`types.py`](farkad_ai/types.py), [`models/port.py`](farkad_ai/models/port.py), and [`extraction/port.py`](farkad_ai/extraction/port.py):

| Protocol | Purpose | Key Method / Properties |
| :--- | :--- | :--- |
| `ModelPort` | Pluggable LLM interface | `complete(prompt, schema, tier) -> Completion` |
| `PillarRegistryProtocol` | Available domain/pillar definitions | `all_descriptors()`, `names()`, `spec_for()` |
| `PillarExtractionPort` | Pass 2 specialist extraction logic | `extract(context) -> ExtractionResult` |
| `CaptureProfileProtocol` | Per-user tracking restrictions | `restrict(routes)`, `config_for(pillar)` |
| `PillarConfigProtocol` | Config and validation boundaries per pillar | `pillar` |

---

## Offline Testing & CLI

`farkad-ai` includes a CLI for offline testing and benchmarking against pre-recorded fixtures:

```bash
# Route a test utterance against recorded responses
farkad-ai route --text "Ate an apple and slept 8 hours" --fixtures ./fixtures

# Run the full deterministic evaluation benchmark
farkad-ai eval --fixtures ./fixtures
```

---

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for local setup, testing workflows, and coding standards.

---

## Security

Please report security issues and vulnerabilities responsibly by following [SECURITY.md](SECURITY.md). Do not report vulnerabilities through public issues.

---

## License

This project is licensed under the [Apache-2.0 License](LICENSE).
