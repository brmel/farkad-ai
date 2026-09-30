---
name: record-fixtures
description: Record live provider responses into offline cassette fixtures for deterministic, zero-cost unit testing. Use when adding new test cases, supporting new entities, or capturing real model outputs.
---

# Record Fixtures

`farkad-ai` executes all CI and developer tests offline against recorded model responses (`RecordedModel`). This guarantees determinism, zero flaky network runs, and zero API costs during development.

---

## 1. How Fixtures Work

Cassettes reside in `tests/fixtures/` as structured JSON files mapping request hashes to provider responses, token usage, and latency.

The `RecordingModel` wraps any live `ModelPort` adapter (`VertexModel`, `AnthropicModel`, `OpenAIModel`), records inputs and outputs, and writes serialized fixtures to disk.

---

## 2. Recording Procedure

When adding a new test case or capturing outputs for a new prompt version:

1. **Provide Temporary API Key:**
   ```bash
   export GEMINI_API_KEY="your-temp-key"
   ```

2. **Run the Recording Script:**
   ```bash
   python -m pytest tests/test_recording.py --record-fixtures
   ```

3. **Verify Fixture Contents:**
   Inspect the generated JSON cassette in `tests/fixtures/`:
   - Confirm prompt and output match the expected schema.
   - **CRITICAL:** Ensure NO API keys, internal tokens, or user personal identifiers are serialized into the fixture.

4. **Verify Offline Execution:**
   Unset API key and run the test suite to ensure tests pass completely offline:
   ```bash
   unset GEMINI_API_KEY
   pytest -q
   ```
