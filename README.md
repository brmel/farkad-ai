<div align="center">

# farkad-ai

**An open experimentation lab and benchmark harness for agentic workflows, multi-pass reasoning, and multimodal structured extraction.**

[![Try the Live Demo](https://img.shields.io/badge/Live%20Demo-farkad.web.app-brightgreen?style=for-the-badge&logo=googlechrome)](https://farkad.web.app)
[![GitHub Discussions](https://img.shields.io/badge/Discussions-Join%20Feedback-blueviolet?style=for-the-badge&logo=github)](https://github.com/brmel/farkad-ai/discussions)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue?style=for-the-badge)](LICENSE)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue?style=for-the-badge&logo=python)](pyproject.toml)

<br/>

[**Try Live Demo**](https://farkad.web.app) • [**Why This Exists**](#why-this-open-repo-exists) • [**Workflows We Test**](#agentic-workflows--best-practices-under-test) • [**Quickstart**](#quickstart) • [**Give Feedback**](#give-feedback--collaborate)

</div>

---

## Try It Live

Before running code, you can test the extraction engine directly in your browser:

👉 **[farkad.web.app](https://farkad.web.app)**

Speak or type multi-intent queries (e.g. *"Drank two glasses of water, slept 7 hours, and took 200mg magnesium"*). Watch how the prompt and model routing handles ambiguity, temporal anchors, and strict numeric schemas in real-time.

---

## Why This Open Repo Exists

Most production AI pipelines struggle with a common reality: **ambiguous, multi-intent real-world human input**. When someone talks or types naturally, they mix modalities, switch languages mid-sentence, use relative times ("yesterday afternoon"), and report across several domains at once.

We created `farkad-ai` as an **open playground and benchmark** to test every modern agentic pattern, tool mechanism, and model capability against real extraction challenges.

Our goal is not to lock in a single rigid architecture, but to **empirically compare workflows and keep only the ones that yield the highest accuracy at the lowest latency and cost**.

---

## Agentic Workflows & Best Practices Under Test

We actively benchmark and iterate on these techniques in this repository:

| Pattern / Paradigm | What We Experiment With | Current Status |
| :--- | :--- | :--- |
| **Multi-Pass Pipelines** | Pass 1 Router (intent, language, scope) + concurrent Pass 2 Specialists | Maintained baseline |
| **Model Context Protocol (MCP)** | Decoupled tool servers for external registries and knowledge lookups | In design / prototyping |
| **Agent Skills & Workflows** | Modular specialized subagents invoked dynamically per domain | Active exploration |
| **Tool Calling vs. Structured Outputs** | Comparing vendor tool-calling protocols vs. strict schema completion | Continuously measured |
| **Model Agnosticism** | Seamless switching: Gemini 2.5 Flash/Pro, Claude 3.5 Sonnet, GPT-4o, local Ollama | Abstracted via `ModelPort` |
| **Deterministic Golden Evals** | Offline fixture replay scoring tolerance, field drift, and token pricing | Built into CLI |

---

## Architecture: The Two-Pass Seam

The baseline architecture separates high-level classification from low-level schema extraction:

```
                  User Speech / Text / Image
                              │
                              ▼
        ┌───────────────────────────────────────────┐
        │        Pass 1: Intent & Route Router      │
        │   - Evaluates health/domain relevance     │
        │   - Discovers temporal anchors / clocks   │
        │   - Emits target specialist routes        │
        └─────────────────────┬─────────────────────┘
                              │
             ┌────────────────┴────────────────┐
             ▼                                 ▼
   ┌───────────────────┐             ┌───────────────────┐
   │ Pass 2 Specialist │             │ Pass 2 Specialist │
   │ (e.g. Nutrition)  │             │   (e.g. Sleep)    │
   │ Strict Pydantic   │             │ Strict Pydantic   │
   └─────────┬─────────┘             └─────────┬─────────┘
             │                                 │
             └────────────────┬────────────────┘
                              ▼
                     Validated Extraction
```

- **Zero Cloud State**: Pure Python protocols. No coupling to Firestore, Postgres, Redis, or proprietary databases.
- **Provider Agnostic**: The engine interacts solely with `ModelPort` protocols.

---

## Quickstart

### 1. Installation

```bash
pip install farkad-ai
```

Or clone for local development and experimentation:

```bash
git clone https://github.com/brmel/farkad-ai.git
cd farkad-ai
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Running a Pipeline

```python
import asyncio
from farkad_ai import (
    CaptureRequest,
    Logged,
    NothingToLog,
    VertexModel,
    build_pipeline,
)
from google import genai

async def main():
    # 1. Connect your model provider (or use RecordedModel for offline tests)
    client = genai.Client()
    model = VertexModel(client)

    # 2. Build the pipeline with your registry and specialist extractor
    pipeline = build_pipeline(model, registry=my_registry, extractor=my_extractor)

    # 3. Process natural human input
    request = CaptureRequest(
        profile=my_user_profile,
        text="Drank 500ml water and ran 5k this morning at 8am",
    )
    outcome = await pipeline.run(request)

    match outcome:
        case Logged(routes=routes, extracted=entries):
            print(f"Routes identified: {routes}")
            for entry in entries:
                print(f"Extracted [{entry['pillar']}]: {entry['data']}")
        case NothingToLog(reason=reason):
            print(f"Filtered: {reason}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Offline Deterministic Benchmark Harness

You don't need an API key or cloud budget to experiment with prompts or evaluate routing accuracy. Use the recorded fixture replay engine:

```bash
# Test routing against pre-recorded golden fixtures
farkad-ai route --text "Ate an apple and slept 8 hours" --fixtures ./fixtures

# Run full evaluation scoring (accuracy, token counts, latency, cost in cents)
farkad-ai eval --fixtures ./fixtures
```

---

## Give Feedback & Collaborate

We actively want your perspective, challenge, and ideas:

- 💬 **Join Discussions**: Have an agentic pattern, prompt framework, or MCP tool idea? Start a thread on [GitHub Discussions](https://github.com/brmel/farkad-ai/discussions).
- 🐛 **Open Issues & Proposals**: Found a failure mode where schemas hallucinate or router misses intent? [Open an issue](https://github.com/brmel/farkad-ai/issues).
- 🛠️ **Contribute**: Check out [CONTRIBUTING.md](CONTRIBUTING.md) to add new model adapters, specialist extractors, or evaluation datasets.

---

## Security

Please report vulnerabilities responsibly following our [Security Policy](SECURITY.md).

---

## License

This project is licensed under the [Apache-2.0 License](LICENSE).
