# Skill: Prompt Engineering & Model Evaluation

Guidelines for modifying prompts or adding new evaluation fixtures in `farkad-ai`.

---

## 1. Modifying Prompts

- Prompts reside in `farkad_ai/prompts/assets/*.txt`.
- Each prompt is hashed via SHA-256 (first 12 characters) as its `instructions_version`.
- Keep instructions direct, imperative, and structured.
- Never hardcode dynamic dates or model names inside prompt files.

## 2. Adding Evaluation Fixtures

- When testing an edge case or multi-intent query, record both the request and response in recorded fixtures.
- Evaluate the impact across all pillars with `farkad-ai eval --fixtures ./fixtures`.
- Ensure accuracy does not regress for existing benchmark cases.
