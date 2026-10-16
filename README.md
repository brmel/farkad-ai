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

1. **Route once.** One model call transcribes the audio, keeps each part in the language it was
   spoken in, names the topics it mentions: food, water, sleep, exercise…, and says whether it
   states a lasting fact about the person, the only sentences worth learning from.
2. **Extract in parallel.** Each topic gets its own call, answering in a schema the app supplies.
3. **Validate, then escalate.** Every answer is checked against its schema; a topic whose answer
   fails is asked again, of a stronger model or of the same one given time to reason.

## AI techniques

| | Technique | How it is used here |
| :-: | --- | --- |
| ✅ | [Structured output](https://ai.google.dev/gemini-api/docs/structured-output) | Every answer is validated against a Pydantic schema |
| ✅ | [Multimodal input](https://ai.google.dev/gemini-api/docs/audio) | Voice and photos, transcribed and routed in one call |
| ✅ | [Model cascade](https://arxiv.org/abs/2305.05176) | A fast model first; the stronger one only when the answer fails validation |
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

Fifteen example sentences, three per language, replayed from answers recorded on
`gemini-3.5-flash-lite` on 2026-10-16:

| Language | Routing | Fields | Tokens per sentence (in / out) |
| --- | --: | --: | --: |
| English | 100% | 100% | 2,807 / 205 |
| French | 100% | 100% | 2,646 / 190 |
| Arabic | 100% | 100% | 2,106 / 107 |
| Spanish | 100% | 100% | 2,465 / 165 |
| Mixed languages | 100% | 100% | 2,869 / 236 |

## Try it

No API key is needed to reproduce the table:

```bash
pip install "farkad-ai @ git+https://github.com/brmel/farkad-ai"
farkad-ai eval
```

`farkad-ai eval --provider vertex` runs it live on your Google Cloud project, and
`farkad-ai route --provider vertex --text "two eggs and a glass of water"` routes your own sentence.
Install the `google`, `anthropic` or `openai` extra for the provider you use.

## Layout

In the order a capture flows through `farkad_ai/`; each name is imported from the module that
defines it. Where a package has a `port.py`, it holds the types that cross its boundary. An
interface there is named for the role it plays, with no `Port` or `Protocol` suffix since `port.py`
already says it is one, and an implementation for how it plays it: `Model` and `RecordedModel`,
`CaptureEngine` and `TwoPassCaptureEngine`.

- `pipeline/`: `TwoPassCaptureEngine`, which routes a capture once and extracts each topic it names,
  and `photo_briefing`, which reads a photo as a log
- `routing/`: the one call that transcribes the capture and names its topics
- `extraction/`: one call per topic, in the app's schema, escalated when the answer does not parse
- `memory/`: facts the user states, and the sheet of them given back to every capture
- `models/`: the `Model` every stage calls, with the prompt, completion and usage it speaks in;
  adapters for Gemini on Vertex AI, Claude and GPT; and the replay of recorded answers
- `eval/`: the gold set, its recorded answers, and the runner that scores any catalogue's own
- `prompts/`: the prompt texts, each versioned by a hash of its text
- `examples.py`: the seven example topics the gold set and `farkad-ai route` use
- `cli.py`: `farkad-ai route`, `eval` and `prompts`

[Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Apache 2.0](LICENSE)
