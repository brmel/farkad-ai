# farkad-ai

[![CI](https://github.com/brmel/farkad-ai/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/brmel/farkad-ai/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

One sentence about your day, typed, spoken or photographed, becomes typed health entries — in
English, French, Arabic, or several of them at once. The engine behind
[Farkad](https://farkad.web.app).

```text
"شربت كأسين ماء et j'ai couru 5 kilometres"        Arabic, then French, in one breath

route     water     ←  شربت كأسين ماء
          exercise  ←  j'ai couru 5 kilometres
extract   water     500 ml
          exercise  cardio · 5,000 m
```

A recorded run on `gemini-3.5-flash-lite`: one routing call, then one extraction call per pillar,
side by side. The transcript stays in the languages it was spoken in; it is never translated.

## How it works

1. **Route once.** One call transcribes the audio, keeps each part in its own language, and splits
   the log into the pillars it mentions (food, water, sleep…).
2. **Extract in parallel.** Each mentioned pillar gets its own call, constrained to the schema the
   consumer supplies, with that pillar's guidance and examples in the user's units.
3. **Validate, then escalate.** Every answer is parsed with Pydantic. One that fails is asked again
   on the stronger tier. A refused pillar is reported with its reason; the others keep their
   entries.

Facts the user stated, such as "I'm vegan", are given back to every capture. Storage, auth and billing stay with the consumer.

## Measured

`farkad-ai eval` captures 15 sentences, three per language, with the example pillars in
[`examples.py`](farkad_ai/examples.py), and scores them against
[`example_gold.json`](farkad_ai/eval/example_gold.json). It replays answers recorded on
`gemini-3.5-flash-lite` on 2026-10-12; `--provider vertex` runs it live.

| Language | Captures | Routing | Fields | Cost per capture |
| --- | --: | --: | --: | --: |
| en | 3 | 100% | 100% | 0.123¢ |
| fr | 3 | 100% | 100% | 0.112¢ |
| ar | 3 | 100% | 100% | 0.079¢ |
| es | 3 | 100% | 100% | 0.103¢ |
| code-switched | 3 | 100% | 90% | 0.127¢ |
| all | 15 | 100% | 97% | 0.109¢ |

Cost is typed text at Vertex AI's list price. The one miss: "un café ce matin" came back
without its count, so the coffee was not logged.

## Try it

```bash
pip install "farkad-ai[google] @ git+https://github.com/brmel/farkad-ai"
export GOOGLE_CLOUD_PROJECT=your-project GOOGLE_CLOUD_LOCATION=global
farkad-ai route --provider vertex --text "two eggs, a big glass of water, and I slept badly"
```

The core imports no provider SDK; pick one extra: `google` (Gemini on Vertex AI), `anthropic` or
`openai`.

## Use it

```python
from farkad_ai import CaptureEngine, CaptureRequest, Logged, NothingToLog
from farkad_ai.models.vertex import VertexModel

engine = CaptureEngine(VertexModel(genai.Client(vertexai=True)), catalogue)

match await engine.capture(CaptureRequest(tracked=(food, water), text="two eggs and a glass")):
    case Logged(extracted=extracted, refused=refused):
        ...
    case NothingToLog(reason=reason):
        ...
```

The pillars are yours. `catalogue` is every pillar routing may name; each tracked pillar carries a
title, guidance, worked examples, an entry schema and a review of each entry. `tests/support.py`
builds small ones.

## AI techniques

| | Technique | Note |
| :-: | --- | --- |
| ✅ | [Structured output](https://ai.google.dev/gemini-api/docs/structured-output) | Every answer is validated against a Pydantic schema |
| ✅ | [Multimodal input](https://ai.google.dev/gemini-api/docs/audio) (audio, image) | Audio is transcribed and routed in the same call |
| ✅ | [Reasoning budget](https://ai.google.dev/gemini-api/docs/thinking) | Set per model tier |
| ✅ | [Model cascade](https://arxiv.org/abs/2305.05176) | Fast tier first; the standard tier only when the answer fails validation |
| ✅ | Provider-independent model port | Vertex AI, Anthropic, OpenAI, and record/replay for tests |
| ✅ | Prompt versioning | A prompt's version is the hash of its text |
| ✅ | Long-term memory | Facts the user states, given back to every capture |
| ✅ | [Few-shot examples](https://arxiv.org/abs/2005.14165) | Per pillar, in the user's own units |
| ✅ | Evaluation with a gold set | Routing, field accuracy and cost per capture |
| | [RAG](https://arxiv.org/abs/2005.11401) | A user's memory fits in the prompt |
| | Fine-tuning | Prompts and the gold set iterate faster |
| | [Agents and tool calling](https://www.anthropic.com/research/building-effective-agents) | A fixed two-step pipeline is cheaper and reproducible |
| | Streaming | An entry is shown only once it is complete |
| | [Context caching](https://ai.google.dev/gemini-api/docs/caching) | The saving does not pay for managing a cache |

[Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Apache 2.0](LICENSE)
