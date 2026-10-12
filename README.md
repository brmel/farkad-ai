# farkad-ai

[![CI](https://github.com/brmel/farkad-ai/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/brmel/farkad-ai/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

The extraction engine behind [Farkad](https://farkad.web.app): it turns a sentence, a voice note or
a photo into typed health entries. One routing call reads the capture and names the pillars it
mentions (food, water, sleep…); one extraction call per tracked pillar it names then runs in
parallel and answers in the schema the consumer supplies. Storage, auth and billing stay with the consumer.

## Install

```bash
pip install "farkad-ai[google] @ git+https://github.com/brmel/farkad-ai"
```

The core imports no provider SDK. Pick one as an extra: `google` (Gemini on Vertex AI),
`anthropic` or `openai`.

## Usage

```python
from google import genai

from farkad_ai import CaptureEngine, CaptureRequest, Logged, NothingToLog
from farkad_ai.models.vertex import VertexModel

engine = CaptureEngine(VertexModel(genai.Client(vertexai=True)), catalogue)
outcome = await engine.capture(CaptureRequest(tracked=(food, water), text="two eggs and a glass"))

match outcome:
    case Logged(extracted=extracted, refused=refused):
        print(extracted, refused)
    case NothingToLog(reason=reason):
        print(reason)
```

`catalogue` is every pillar routing may name (`PillarRegistryProtocol`). Each tracked pillar is a
`TrackedPillar`: title, guidance, worked examples, entry schema and a `review` of each entry.

From the command line:

```bash
export GOOGLE_CLOUD_PROJECT=your-project GOOGLE_CLOUD_LOCATION=global
farkad-ai route --provider vertex --text "two eggs, a big glass of water, and I slept badly"
```

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
