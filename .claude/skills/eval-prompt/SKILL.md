---
name: eval-prompt
description: Benchmark extraction prompts and model routing against the gold evaluation dataset. Use when modifying prompt assets, updating router logic, tuning system instructions, or evaluating a new model.
---

# Eval Prompt

Every prompt alteration in `farkad-ai` must be empirically justified. Never change a prompt on intuition alone.

---

## 1. The Gold Dataset

The benchmark resides at `farkad_ai/eval/gold.json`. It contains multi-pillar captures across varied modalities, complex health contexts, and multiple languages (English, French, Arabic, Spanish).

Each test case defines:
- `utterance`: The raw input text.
- `expected_routes`: The set of target pillars (e.g. `["food", "water"]`).
- `expected`: The ground-truth structured entities and fields.

---

## 2. Running the Evaluation

Execute the evaluation benchmark suite:

```bash
# Run evaluation test suite with verbose scoring table
pytest tests/test_scoring.py -v
```

To run an interactive routing test via CLI:
```bash
python -m farkad_ai.cli route --text "Had a grilled chicken breast and 500ml water after a 5km run"
```

---

## 3. Metrics to Report

A pull request modifying a prompt or routing logic must publish this scorecard in its description:

| Metric | Baseline | Candidate | Delta |
| :--- | :--- | :--- | :--- |
| **Routing Accuracy** | `94.2%` | `96.1%` | `+1.9%` |
| **Field-level Accuracy** | `88.5%` | `90.0%` | `+1.5%` |
| **P50 Latency** | `420ms` | `415ms` | `-5ms` |
| **Cost per 1,000 Captures** | `$0.042` | `$0.040` | `-$0.002` |

### Acceptance Criteria:
1. Routing accuracy must not regress on any previously passing case.
2. Field-level precision and recall must not regress on core health metrics (e.g. calories, blood pressure, medication dose).
3. If token length increases, the cost increase must be explicitly justified by accuracy gains.
