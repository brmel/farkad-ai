# Agents

[CONTRIBUTING.md](CONTRIBUTING.md) is the contract for every change, by a person or an agent: set
up, the four checks, and how a release is cut. What the maintainer adds to it:

- Run the four checks in a **fresh venv with only `.[dev]`** before merging. CI installs no
  provider SDK, so an import that only an SDK in your venv satisfies passes locally and fails there.
- One change per branch, merged to `main` with `--no-ff`, then the branch is deleted.
- This history is **public**: commit with the repository-local `user.email`, and never name a
  private issue, project id or address in a branch, commit or file.
