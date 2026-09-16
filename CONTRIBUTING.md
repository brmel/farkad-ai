# Contributing to farkad-ai

`farkad-ai` is an open-source testbed and benchmarking laboratory for **agentic workflows, multimodal extraction, prompt engineering, and model evaluation**.

We actively encourage feedback, architectural discussions, failure-case reports, and pull requests!

---

## Areas Where We Need Your Ideas & Feedback

1. **Agentic Paradigms & Tool Calling**:
   - Model Context Protocol (MCP) integrations.
   - Dynamic agent skills vs. hardcoded specialist pipelines.
   - Dynamic tool calling vs. constrained schema generation.
2. **Model Providers & SDKs**:
   - Adapters for Anthropic Claude, OpenAI, DeepSeek, Mistral, and local Ollama/vLLM.
3. **Multilingual & Multimodal Routing**:
   - Edge cases with dialect switching, mixed languages, background audio noise, and complex photo recognition.
4. **Evaluation Benchmarks**:
   - Edge-case golden fixtures that push models to their hallucination limits.

---

## Getting Started

### 1. Fork & Setup

```bash
git clone https://github.com/brmel/farkad-ai.git
cd farkad-ai

python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install pytest ruff mypy
```

### 2. Verify Changes Locally

Before submitting code, run the suite (all offline, no API spend or cloud credentials needed):

```bash
ruff check .
ruff format --check .
mypy farkad_ai
pytest
```

---

## Guidelines

- **Clean Protocols**: All new components should implement clear `typing.Protocol` interfaces so the core stays decoupled from vendor SDKs.
- **Zero Cloud Coupling**: Do not introduce database dependencies (e.g. Firebase, Postgres) or user identity systems. Keep the package pure computation and reasoning.
- **Empirical Evaluation**: Whenever proposing a prompt change or new workflow pattern, share benchmark results comparing accuracy, latency, and token cost.

---

## Submitting Pull Requests & Discussions

- **Proposals & Architecture Ideas**: Open a thread in [GitHub Discussions](https://github.com/brmel/farkad-ai/discussions) to brainstorm before writing large chunks of code.
- **Pull Requests**: Keep PRs focused, include unit tests or golden fixture additions, and ensure all CI checks pass.

Thank you for helping build a more transparent, accurate, and cost-effective AI extraction engine!
