<div align="center">

# farkad-ai

**A health tracker you talk to. Say what you ate, drank and did in one sentence, and it turns that into structured entries you can correct.**

[![Try the Live Demo](https://img.shields.io/badge/Live%20Demo-farkad.web.app-brightgreen?style=for-the-badge&logo=googlechrome)](https://farkad.web.app)
[![GitHub Discussions](https://img.shields.io/badge/Discussions-Join%20Feedback-blueviolet?style=for-the-badge&logo=github)](https://github.com/brmel/farkad-ai/discussions)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue?style=for-the-badge)](LICENSE)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue?style=for-the-badge&logo=python)](pyproject.toml)

<br/>

[**Try Live Demo**](https://farkad.web.app) • [**Why This Exists**](#why-this-repository-is-open) • [**What I test**](#what-i-test) • [**Quickstart**](#quickstart) • [**Give Feedback**](#give-feedback--collaborate)

</div>

---

## Try It Live

Before running code, you can test the extraction engine directly in your browser:

👉 **[farkad.web.app](https://farkad.web.app)**

Say or type a whole day in one sentence — *"Drank two glasses of water, slept 7 hours, and took 200mg magnesium"* — and watch it come back as separate, editable entries. That sentence covers three different areas, uses a relative time, and carries a dose that has to survive as a number.

---

## Why this repository is open

Most production AI pipelines struggle with a common reality: **ambiguous, multi-intent real-world human input**. When someone talks or types naturally, they mix modalities, switch languages mid-sentence, use relative times ("yesterday afternoon"), and report across several domains at once.

I opened `farkad-ai` so the extraction engine can be read and argued with. It is the part of the product where being wrong is invisible, so it is the part worth showing.

I am not defending one architecture. I measure the approaches against recorded cases and keep whichever is most accurate for the latency and cost it needs.

---

## What I test

These are the techniques I measure here, and where each one currently stands:

| Technique | What I try | Where it stands |
| :--- | :--- | :--- |
| **Multi-Pass Pipelines** | Pass 1 Router (intent, language, scope) + concurrent Pass 2 Specialists | Maintained baseline |
| **Model Agnosticism** | One `ModelPort`, four adapters: Vertex (Gemini), Anthropic, OpenAI, and a recorded-fixture adapter for offline runs | Implemented |
| **Provider Fallback** | A chain that moves to the next adapter when one is unavailable | Implemented |
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

Install the base package (zero vendor lock-in):
```bash
pip install farkad-ai
```

Or install with your preferred model provider SDK:
```bash
# Google GenAI (Gemini 2.5 Flash / Flash-Lite / Pro)
pip install "farkad-ai[google]"

# Anthropic (Claude 3.5 Sonnet / Claude 3.5 Haiku)
pip install "farkad-ai[anthropic]"

# OpenAI (GPT-4o / GPT-4o-mini)
pip install "farkad-ai[openai]"

# All providers + dev & eval tools
pip install "farkad-ai[all]"
```

### 2. Multi-Provider Architecture

Every provider sits behind one `ModelPort` interface, so switching is configuration:

```python
import asyncio
from pathlib import Path
from farkad_ai import (
    AnthropicModel,
    CaptureRequest,
    Logged,
    NothingToLog,
    OpenAIModel,
    RecordedModel,
    TraceObserver,
    VertexModel,
    build_pipeline,
)

# Pick your provider — the pipeline and domain remain identical:
# 1. Google Gemini
from google import genai

model = VertexModel(genai.Client())

# 2. Anthropic Claude
# import anthropic
# model = AnthropicModel(anthropic.AsyncAnthropic())

# 3. OpenAI GPT
# import openai
# model = OpenAIModel(openai.AsyncOpenAI())

# 4. Deterministic Offline Replay (zero network, zero API keys)
# model = RecordedModel(Path("./fixtures"))


async def main():
    observer = TraceObserver()
    pipeline = build_pipeline(
        model, registry=my_registry, extractor=my_extractor, observer=observer
    )

    request = CaptureRequest(
        profile=my_user_profile,
        text="Drank 500ml water and ran 5k this morning at 8am",
    )
    outcome = await pipeline.run(request)

    match outcome:
        case Logged(routes=routes, extracted=entries):
            print(f"Routes identified: {routes}")
        case NothingToLog(reason=reason):
            print(f"Filtered: {reason}")

    # Inspect intermediate pipeline state without domain pollution:
    print(f"Lifecycle events captured: {len(observer.events)}")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Command line and offline evaluation

`farkad-ai` includes a full CLI suite for inspection, live testing, and benchmark evaluation:

```bash
# Inspect all supported model tiers and live pricing
farkad-ai models

# Inspect active prompt templates and cryptographic version hashes
farkad-ai prompts

# Test intent routing against recorded fixtures or live providers
farkad-ai route --text "Ate 2 eggs and slept 8 hours" --fixtures ./fixtures

# Run deterministic evaluation scoring across capture datasets
farkad-ai eval --fixtures ./fixtures
```

---

## Give Feedback & Collaborate

I would like your perspective, and your disagreement:

- 💬 **Join Discussions**: Have an agentic pattern, prompt framework, or MCP tool idea? Start a thread on [GitHub Discussions](https://github.com/brmel/farkad-ai/discussions).
- 🐛 **Open Issues & Proposals**: Found a failure mode where schemas hallucinate or router misses intent? [Open an issue](https://github.com/brmel/farkad-ai/issues).
- 🛠️ **Contribute**: Check out [CONTRIBUTING.md](CONTRIBUTING.md) to add new model adapters, specialist extractors, or evaluation datasets.

---

## Security

Please report vulnerabilities responsibly following my [Security Policy](SECURITY.md).

---

## License

This project is licensed under the [Apache-2.0 License](LICENSE).
