# farkad-ai

[![CI](https://github.com/brmel/farkad-ai/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/brmel/farkad-ai/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

The AI engine behind [Farkad](https://farkad.web.app): you say what you ate and did, in your own
words and languages, and it becomes structured health entries. I build it in the open to learn
applied AI on a real product.

| You say | It logs |
| --- | --- |
| شربت كأسين ماء et j'ai couru 5 kilometres | **water** 2 glasses, 500 ml · **exercise** run, 5,000 m |

## How it works

A sentence, a recording or a photo goes through two passes:

1. **Route once.** One call writes down what was said, each part in the language it was spoken
   in, and names the topics it mentions.
2. **Extract in parallel.** Each topic it named gets its own call, answering in that topic's
   schema.

The vendor sits behind the `Model` interface and the pipeline behind `CaptureEngine`, so either
can be replaced without touching the other.

## How well it works

Fifteen example sentences, three per language, on seven example topics, replayed from answers
recorded on `gemini-3.5-flash-lite` on 2026-11-09:

| Language | Routing | Fields | Validators | Tokens per sentence (in / out) |
| --- | --: | --: | --: | --: |
| English | 100% | 100% | 100% | 2,628 / 193 |
| French | 100% | 100% | 100% | 2,466 / 173 |
| Arabic | 100% | 100% | 100% | 1,927 / 94 |
| Spanish | 100% | 100% | 100% | 2,288 / 150 |
| Mixed languages | 100% | 100% | 100% | 2,689 / 170 |

## What it uses, and what it leaves out

| | Technique | Why |
| :-: | --- | --- |
| ✅ | [Structured output](https://ai.google.dev/gemini-api/docs/structured-output) | Every answer is validated against a Pydantic schema |
| ✅ | [Multimodal input](https://ai.google.dev/gemini-api/docs/audio) | Voice and photos are transcribed and routed in one call |
| ✅ | [Model cascade](https://arxiv.org/abs/2305.05176) | An answer that fails validation is asked again on the stronger tier |
| ✅ | [Reasoning budget](https://ai.google.dev/gemini-api/docs/thinking) | Chosen per tier, measured in tokens |
| ✅ | [Few-shot examples](https://arxiv.org/abs/2005.14165) | Per topic, in the user's own units |
| ✅ | Long-term memory | Facts the user states are given back to each capture as data, never as instructions |
| ✅ | Evaluation with a gold set | The table above |
| | [RAG](https://arxiv.org/abs/2005.11401) | A user's memory fits in the prompt |
| | Fine-tuning | Prompts and the gold set iterate faster |
| | [Agents](https://www.anthropic.com/research/building-effective-agents), tool calling, agent frameworks | A fixed two-step pipeline is cheaper and reproducible |
| | [Context caching](https://ai.google.dev/gemini-api/docs/caching) | The saving does not pay for managing a cache |

## Try it

No API key is needed to reproduce the table, or to route one of its sentences:

```bash
pip install "farkad-ai @ git+https://github.com/brmel/farkad-ai"
farkad-ai eval
farkad-ai route --text "I drank 500 ml of water"
```

Your own sentences need a live model: install `farkad-ai[google]` and pass `--provider vertex`.

## Extend it

- **A topic**: copy one of the seven in `farkad_ai/eval/pillars.py` and add sentences to
  `farkad_ai/eval/example_gold.json`.
- **A model provider**: one module beside `farkad_ai/models/vertex.py`.
- **A prompt**: a text file in `farkad_ai/prompts/assets/`.

[Contributing](CONTRIBUTING.md) says what each needs · [Changelog](CHANGELOG.md) ·
[Security](SECURITY.md) · [Apache 2.0](LICENSE)
