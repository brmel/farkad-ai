---
name: record-fixtures
description: Record live provider responses into offline cassettes for zero-cost tests.
---

# Record Fixtures

Record live model responses into offline cassettes (`tests/fixtures/`) for deterministic testing.

## Recording Procedure
```bash
export GEMINI_API_KEY="..."
python -m pytest tests/test_recording.py --record-fixtures
unset GEMINI_API_KEY
pytest -q
```

*Sanity check:* confirm generated JSON contains no API keys or identifiers before committing.
