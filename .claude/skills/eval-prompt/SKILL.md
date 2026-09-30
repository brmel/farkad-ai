---
name: eval-prompt
description: Benchmark prompts and router against gold evaluation set.
---

# Eval Prompt

Every prompt change must be empirically justified against `farkad_ai/eval/gold.json`.

## 1. Run Benchmark
```bash
# Run evaluation suite
pytest tests/test_scoring.py -v

# Interactive test
python -m farkad_ai.cli route --text "Grilled chicken and 500ml water after 5km run"
```

## 2. PR Scorecard (Required)
Every PR touching prompts or routing must report:
- **Routing Accuracy:** candidate vs baseline (must not regress on passing cases)
- **Field F1:** nutrition, activity, symptom, biomarker
- **Latency (P50/P95):** candidate vs baseline
- **Cost:** microcents per 1,000 captures
