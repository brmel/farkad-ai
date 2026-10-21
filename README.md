# farkad-ai

[![CI](https://github.com/brmel/farkad-ai/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/brmel/farkad-ai/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

The AI engine behind [Farkad](https://farkad.web.app), an app where you say what you ate and did
and it becomes a health log. I build it in the open to learn applied AI on a real product: each
technique below is either used and measured, or left out with the reason.

| You say | It logs |
| --- | --- |
| شربت كأسين ماء et j'ai couru 5 kilometres | **water** 2 glasses, 500 ml · **exercise** run, 5,000 m |

Arabic, then French, in one sentence: each part goes to its topic, and the transcript keeps the
words as they were said.

## How it works

`TwoPassCaptureEngine` (`pipeline/`) turns a sentence, a recording or a photo into entries:

1. **Route once** (`routing/`). One call writes down what was said, each part in the language it
   was spoken in, names the topics it mentions, and says whether it states a lasting fact about
   the person.
2. **Extract in parallel** (`extraction/`). Each tracked topic it named gets its own call,
   answering in the schema the consumer supplies for it.
3. **Validate, then escalate.** Every answer is validated against its schema; a topic whose
   answer does not parse is asked again of a stronger model, or of the same one given time to
   reason.

Topics are *pillars* in the code, and the consumer passes them in. `memory/` learns the lasting
facts a person states and counts habits from what they log, as a sheet given back to every
capture. Every call goes through one `Model` (`models/`). Each name is imported from the module
that defines it: `from farkad_ai.pipeline.engine import TwoPassCaptureEngine`.

## AI techniques

| | Technique | How it is used here |
| :-: | --- | --- |
| ✅ | [Structured output](https://ai.google.dev/gemini-api/docs/structured-output) | Every answer is validated against a Pydantic schema |
| ✅ | [Multimodal input](https://ai.google.dev/gemini-api/docs/audio) | Voice and photos, transcribed and routed in one call |
| ✅ | [Model cascade](https://arxiv.org/abs/2305.05176) | The fast tier first; a topic whose answer fails validation is asked again, of a stronger model or of the same one given time to reason |
| ✅ | [Reasoning budget](https://ai.google.dev/gemini-api/docs/thinking) | Chosen per model tier, measured in tokens |
| ✅ | [Few-shot examples](https://arxiv.org/abs/2005.14165) | Worked examples per topic, in the user's own units |
| ✅ | Long-term memory | Facts the user states, such as "I'm vegan", are given back to every capture as data, never as instructions |
| ✅ | Evaluation with a gold set | Accuracy and tokens per language, below |
| ✅ | Several model providers | Gemini, Claude and GPT behind one interface |
| | [RAG](https://arxiv.org/abs/2005.11401) | A user's memory fits in the prompt |
| | Fine-tuning | Prompts and the gold set iterate faster |
| | [Agents and tool calling](https://www.anthropic.com/research/building-effective-agents) | A fixed two-step pipeline is cheaper and reproducible |
| | [Context caching](https://ai.google.dev/gemini-api/docs/caching) | The saving does not pay for managing a cache |

## Measured

Fifteen example sentences, three per language, on the seven example topics in `eval/` rather than
the app's own, replayed from answers recorded on `gemini-3.5-flash-lite` on 2026-10-16:

| Language | Routing | Fields | Tokens per sentence (in / out) |
| --- | --: | --: | --: |
| English | 100% | 100% | 2,873 / 206 |
| French | 100% | 100% | 2,711 / 192 |
| Arabic | 100% | 100% | 2,172 / 111 |
| Spanish | 100% | 100% | 2,531 / 166 |
| Mixed languages | 100% | 100% | 2,934 / 239 |

## Try it

No API key is needed to reproduce the table, or to route one of its sentences:

```bash
pip install "farkad-ai @ git+https://github.com/brmel/farkad-ai"
farkad-ai eval
farkad-ai route --text "I drank 500 ml of water"
```

Your own sentences need a live model: install the `google`, `anthropic` or `openai` extra and
pass `--provider vertex`, `anthropic` or `openai`. A missing credential is named in one line.

```bash
pip install "farkad-ai[google] @ git+https://github.com/brmel/farkad-ai"
farkad-ai route --provider vertex --text "two eggs and a glass of water"
```

## Extend it

- **A topic.** A consumer describes each one twice: a `PillarSpec` for routing, its id and what
  it covers (`routing/port.py`), and a `TrackedPillar` for extraction, its guidance, worked
  examples, Pydantic entry schema and a review of each entry (`extraction/port.py`).
  `eval/pillars.py` holds seven; add one there, with sentences in `eval/example_gold.json`, and
  the eval scores it.
- **A model provider.** Subclass `ProviderModel` (`models/provider.py`) in a new module beside
  `models/anthropic.py`: `_send` the prompt, return its structured `_answer`, count its `_usage`,
  declare the reasoning levels it honours, and build its client in `connected()`. Name it in
  `models/factory.py`, and give its SDK an extra and a mypy override in `pyproject.toml` and a
  place in CI's matrix; no other module imports it.
- **A prompt.** Each is a text file in `prompts/assets/`, loaded by the module that sends it and
  versioned by a hash of its text; `farkad-ai prompts` lists them. The docstrings and field
  descriptions in `routing/pass_one.py` and `memory/inference.py` reach the model too.

A new topic or prompt changes what the model is asked, so the eval needs new recordings:
[Contributing](CONTRIBUTING.md#the-eval-and-its-recordings) says how.

[Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md) · [Security](SECURITY.md) ·
[Apache 2.0](LICENSE)
