---
name: eval-prompt
description: Benchmark prompts and router against gold evaluation set.
---

# Eval Prompt

Every prompt change must be empirically justified against `farkad_ai/eval/gold.json`.

## 1. Run Benchmark
```bash
pytest tests/test_scoring.py -v
python -m farkad_ai.cli route --text "Grilled chicken and 500ml water after 5km run"
```

## 2. PR Scorecard (Required)
Every PR touching prompts or routing must report:
- **Routing Accuracy:** candidate vs baseline (no regressions on passing cases)
- **Field F1:** nutrition, activity, symptom, biomarker
- **Latency (P50/P95):** candidate vs baseline
- **Tokens:** input and output token counts per capture
