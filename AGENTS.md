# Agents

[CONTRIBUTING.md](CONTRIBUTING.md) applies to every change. Maintainers add:

- Maintainer work is tracked privately; this repository's issues are for outside reports.
- A branch merges to `main` with `--no-ff` and is then deleted.
- The history is **public**: commit with the repository-local `user.email`, and never name a
  private issue, project id or address in a branch, commit or file.

## Working within a budget

- One task per session. This file and `CONTRIBUTING.md` are already in context.
- Independent reads and searches go in one call; `rg -n` first, then read the line range it
  points at, never the whole file.
- An issue is fetched once, with only the fields needed:
  `gh issue view <n> --json title,body --jq …`.
- The checks run under the Bash tool's `timeout`, and their verdict is their exit code: never poll
  a log.

## Releasing

Releases are immutable: a wrong wheel is fixed by a new version.

1. Bump `version` in `pyproject.toml`, move `CHANGELOG.md`'s Unreleased entries under
   `## [X.Y.Z] - YYYY-MM-DD` with its compare link, merge to `main`, and wait for CI to pass.
2. Tag the merge `vX.Y.Z` and push the tag.
3. `git archive vX.Y.Z | tar -x -C <dir>`, then `uv build` in `<dir>`.
4. `gh release create vX.Y.Z <dir>/dist/*`, with that version's changelog entries as its notes.
5. Check that `curl -sL <wheel url> | shasum -a 256` matches the local wheel: consumers pin that
   URL and digest.
