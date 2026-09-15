# Contributing to farkad-ai

Thank you for your interest in contributing to `farkad-ai`! We welcome contributions from the community to improve multimodal extraction, prompt engineering, evaluation benchmarks, and model provider integrations.

---

## Code of Conduct

We are committed to providing a welcoming, inclusive, and harassment-free experience for everyone. Please be respectful, constructive, and considerate in all interactions.

---

## Development Setup

`farkad-ai` requires Python 3.13+ and uses modern Python packaging (`hatchling` / `uv` / standard virtual environments).

### 1. Clone and Set Up

```bash
git clone https://github.com/brmel/farkad-ai.git
cd farkad-ai

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"   # or pip install -e . pytest ruff mypy
```

### 2. Run Tests & Lints

```bash
pytest
ruff check .
ruff format --check .
mypy farkad_ai
```

All tests are completely offline and deterministic—no cloud credentials or API keys are required.

---

## Design Principles

When contributing code, please keep the following architecture principles in mind:

1. **Deterministic & Static**:
   - Favor structural pattern matching (`match / case`) and strict types over runtime `isinstance` or dynamic property lookups.
   - All public interfaces are declared via strict `typing.Protocol`.
2. **Provider Agnostic**:
   - Core routing, extraction, and pipeline logic must not depend on any specific LLM SDK. All providers implement `ModelPort`.
3. **No Private State**:
   - `farkad-ai` is completely decoupled from databases, cloud services, user management, and billing. Avoid introducing cloud or framework dependencies.
4. **Golden Replayability**:
   - Prompt and model changes should be verified with the evaluation suite (`farkad-ai eval` / committed fixtures).

---

## Submitting Pull Requests

1. **Fork the repository** and create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-improvement
   ```
2. **Make your changes** following the code standards above.
3. **Add tests** covering the new behavior or edge cases.
4. **Ensure all checks pass**:
   ```bash
   ruff check . && ruff format --check . && mypy farkad_ai && pytest
   ```
5. **Open a Pull Request**:
   - Provide a clear, concise description of the motivation and changes.
   - Reference any related issues.

---

## Security

If you discover a security vulnerability, please follow our [Security Policy](SECURITY.md) and do not open a public issue.
