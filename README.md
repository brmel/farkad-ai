# farkad-ai

[![CI](https://github.com/brmel/farkad-ai/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/brmel/farkad-ai/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

The AI engine behind [Farkad](https://farkad.web.app). You say what you ate and did, in your own
words and languages, and it turns that into structured health entries. I build it in the open to
learn applied AI on a real product. This page shows what it does today and what it does not do
yet.

| You say | It notes |
| --- | --- |
| شربت كأسين ماء et j'ai couru 5 kilometres | **water** 2 glasses, 500 ml · **exercise** run, 5,000 m |

## How it works

Typed text, a voice recording or a photo goes through two passes:

1. **Route.** One call names the topics the input mentions: water, food, sleep and so on. For a
   recording or a photo, the same call also writes down what was said, each part in the language
   it was spoken in.
2. **Extract.** Each topic gets its own call, run in parallel, which answers in that topic's
   schema.

Beside the two passes:

- **Memory** learns lasting facts ("I'm vegetarian") and counts habits, then hands both to every
  later call as data, never as instructions.
- **Recompute** works the derived values out again when a person edits an entry.

The vendor sits behind the `Model` interface and the pipeline behind `CaptureEngine`. Either one
can be replaced without touching the other.

## How well it works

Fifteen examples, three per language, on seven example topics. The answers were recorded on
`gemini-3.5-flash-lite` on 2026-11-09 and are replayed for this table:

| Language | Routing | Fields | Validators | Tokens per example (in / out) |
| --- | --: | --: | --: | --: |
| English | 100% | 100% | 100% | 2,628 / 193 |
| French | 100% | 100% | 100% | 2,466 / 173 |
| Arabic | 100% | 100% | 100% | 1,927 / 94 |
| Spanish | 100% | 100% | 100% | 2,288 / 150 |
| Mixed languages | 100% | 100% | 100% | 2,689 / 170 |

Fifteen examples is a small set: read the table as a regression check, not as a benchmark.

## Done

| | Feature | How |
| :-: | --- | --- |
| ✅ | Text, voice and photo input | A recording or a photo is transcribed and routed in one call |
| ✅ | Four languages, mixed in one breath | English, French, Arabic (Darija too) and Spanish |
| ✅ | [Structured output](https://ai.google.dev/gemini-api/docs/structured-output) | Every answer is validated against a Pydantic schema |
| ✅ | [Model cascade](https://arxiv.org/abs/2305.05176) | An answer that fails validation is asked again on the stronger tier |
| ✅ | [Reasoning budget](https://ai.google.dev/gemini-api/docs/thinking) | Chosen per tier: none, brief or thorough |
| ✅ | [Few-shot examples](https://arxiv.org/abs/2005.14165) | Per topic, in the person's own units |
| ✅ | Long-term memory | Facts a person types in or says, plus habits from the last four weeks |
| ✅ | Recompute on edit | Changing an amount works the derived values out again |
| ✅ | [Implicit caching](https://ai.google.dev/gemini-api/docs/caching) | Prompts put the fixed words first, so Gemini can reuse them |
| ✅ | Evaluation with a gold set | Recorded real answers, replayed in CI with no API key |

## Not done yet

These are AI features the engine does not have. Each row says what the feature would add and
where it stands.

| Feature | What it would add | Where it stands |
| --- | --- | --- |
| [Decisions API](https://blog.google/innovation-and-ai/technology/developers-tools/gemini-decisions-api/) (`gemini-decision-1`) | Fast, cheap yes/no and scored answers, for example grading the gold set by meaning | Watching: launched 2026-11-11 on the Gemini Developer API only, not yet on Vertex AI |
| [Tool calling](https://ai.google.dev/gemini-api/docs/function-calling) | The model looks a food up in a nutrition database instead of estimating it | Not started: the fixed two-pass pipeline is cheaper and reproducible |
| Grounding in a food database | Calories and macros from a published source, not the model's estimate | Not started: today every value is an editable estimate |
| [Video input](https://ai.google.dev/gemini-api/docs/video-understanding) | A short clip of a meal or a workout becomes entries | Not started: Gemini reads video, but a clip costs far more tokens than a photo |
| [Audio output](https://ai.google.dev/gemini-api/docs/speech-generation) | Farkad says back what it noted, hands-free | Not started |
| [Live voice](https://ai.google.dev/gemini-api/docs/live) | A spoken conversation, answered as you talk | Not started: today a recording is sent once it ends |
| Food recommendations | Meal ideas that fit your goals, memory and history | Not started: it must stay a suggestion, never medical advice |
| Written summaries and coaching | A weekly recap of your patterns, in plain words | Not started: trends are computed, not written |
| [Embeddings](https://ai.google.dev/gemini-api/docs/embeddings) | Search your diary by meaning ("when did I last eat fish?") | Not started |
| On-device models | Routing on the phone, offline and private | Not started |
| [Batch API](https://ai.google.dev/gemini-api/docs/batch-api) | Half-price evaluation runs | Not started: entries are answered in real time |

Left out on purpose, until a measurement says otherwise:

| Technique | Why not |
| --- | --- |
| [RAG](https://arxiv.org/abs/2005.11401) | A person's memory fits in the prompt |
| Fine-tuning | Prompts and the gold set iterate faster |
| [Agents](https://www.anthropic.com/research/building-effective-agents) and agent frameworks | A fixed two-pass pipeline is cheaper and reproducible |
| [Explicit context caching](https://ai.google.dev/gemini-api/docs/caching) | Implicit caching already reuses the fixed words, with no cache to manage |

## Try it

You can reproduce the table, or route one of its examples, with no API key:

```bash
pip install "farkad-ai @ git+https://github.com/brmel/farkad-ai"
farkad-ai eval
farkad-ai route --text "I drank 500 ml of water"
```

Your own input needs a live model: install `farkad-ai[google]` and pass `--provider vertex`.

## Extend it

- **A topic:** copy one of the seven in `farkad_ai/eval/pillars.py` and add examples to
  `farkad_ai/eval/example_gold.json`.
- **A model provider:** add one module beside `farkad_ai/models/vertex.py`.
- **A prompt:** add a text file in `farkad_ai/prompts/assets/`.

[Contributing](CONTRIBUTING.md) says what each one needs · [Changelog](CHANGELOG.md) ·
[Security](SECURITY.md) · [Apache 2.0](LICENSE)
