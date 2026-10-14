# farkad-ai

[![CI](https://github.com/brmel/farkad-ai/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/brmel/farkad-ai/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

The AI engine behind [Farkad](https://farkad.web.app), an app where you say what you ate and did
and it becomes a health log. I build it in the open to learn applied AI on a real product: each
technique below is either used and measured, or left out with the reason.

| You say | It logs |
| --- | --- |
| شربت كأسين ماء et j'ai couru 5 kilometres | **water** 500 ml · **exercise** cardio, 5,000 m |

Arabic, then French, in one sentence: each part goes to its topic, and the transcript keeps the
words as they were said.

## How it works

1. **Route once.** One model call transcribes the audio, keeps each part in the language it was
   spoken in, and names the topics it mentions: food, water, sleep, exercise…
2. **Extract in parallel.** Each topic gets its own call, answering in a schema the app supplies.
3. **Validate, then escalate.** Every answer is checked against its schema; one that fails is asked
   again on a stronger model.

## AI techniques

| | Technique | How it is used here |
| :-: | --- | --- |
| ✅ | [Structured output](https://ai.google.dev/gemini-api/docs/structured-output) | Every answer is validated against a Pydantic schema |
| ✅ | [Multimodal input](https://ai.google.dev/gemini-api/docs/audio) | Voice and photos, transcribed and routed in one call |
| ✅ | [Model cascade](https://arxiv.org/abs/2305.05176) | A fast model first; the stronger one only when the answer fails validation |
| ✅ | [Reasoning budget](https://ai.google.dev/gemini-api/docs/thinking) | Chosen per model tier, measured against cost |
| ✅ | [Few-shot examples](https://arxiv.org/abs/2005.14165) | Worked examples per topic, in the user's own units |
| ✅ | Long-term memory | Facts the user states, such as "I'm vegan", are given back to every capture |
| ✅ | Evaluation with a gold set | Accuracy and cost per language, below |
| ✅ | Several model providers | Gemini, Claude and GPT behind one interface |
| | [RAG](https://arxiv.org/abs/2005.11401) | A user's memory fits in the prompt |
| | Fine-tuning | Prompts and the gold set iterate faster |
| | [Agents and tool calling](https://www.anthropic.com/research/building-effective-agents) | A fixed two-step pipeline is cheaper and reproducible |
| | [Context caching](https://ai.google.dev/gemini-api/docs/caching) | The saving does not pay for managing a cache |

## Measured

Fifteen example sentences, three per language, replayed from answers recorded on
`gemini-3.5-flash-lite` on 2026-10-14:

| Language | Routing | Fields | Cost per sentence |
| --- | --: | --: | --: |
| English | 100% | 100% | 0.124¢ |
| French | 100% | 100% | 0.118¢ |
| Arabic | 100% | 100% | 0.081¢ |
| Spanish | 100% | 100% | 0.103¢ |
| Mixed languages | 100% | 90% | 0.137¢ |

The one miss: in a Darija and French sentence, the coffee was not logged.

## Try it

No API key is needed to reproduce the table:

```bash
pip install "farkad-ai @ git+https://github.com/brmel/farkad-ai"
farkad-ai eval
```

`farkad-ai eval --provider vertex` runs it live on your Google Cloud project, and
`farkad-ai route --provider vertex --text "two eggs and a glass of water"` routes your own sentence.
Install the `google`, `anthropic` or `openai` extra for the provider you use.

[Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Apache 2.0](LICENSE)
