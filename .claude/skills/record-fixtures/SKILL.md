---
name: record-fixtures
description: Record live provider responses into offline cassettes for zero-cost tests.
---

# Record Fixtures

Record live model responses into offline cassettes (`tests/fixtures/`) for deterministic unit testing.

## Recording Procedure
```bash
# 1. Provide temp key
export GEMINI_API_KEY="..."

# 2. Record cassette
python -m pytest tests/test_recording.py --record-fixtures

# 3. Clean environment and verify offline execution
unset GEMINI_API_KEY
pytest -q
```

*Sanity check:* verify the generated JSON contains no API keys or personal identifiers before committing.
