# AGENTS.md

## Project overview

A Claude Code `PreToolUse` hook that guards `gh` CLI commands using a positive-list approach: known read-only commands are auto-allowed, everything else triggers a permission prompt. Stdlib-only Python — no runtime dependencies.

## Architecture

- `src/gh_guard.py` — single-file hook script. Reads JSON from stdin (`tool_input.command`), writes JSON to stdout (`permissionDecision: "allow" | "ask"`). Always exits 0.
- `evaluate_command(command)` — core logic, returns `"allow"` or `"ask"`. Handles compound commands (`&&`, `||`, `;`, `|`) by evaluating each part independently — if any part is not read-only, returns `"ask"`.
- `gh api` has special handling: only allows GET requests with no body flags and no `graphql` endpoint.
- Design principle: **fail closed**. Unknown commands, parse errors, and unrecognized flags all return `"ask"`.

## Development

### Setup

```sh
uv sync --group dev --group ci
```

### Dependency groups

- **default**: no dependencies (stdlib only)
- **dev**: pytest, ruff, ty, pre-commit
- **ci**: yamllint, pip-audit

### Commands

```sh
uv run pytest -v            # tests
uv run ruff check           # lint
uv run ruff format --check  # format check
uv run ty check             # type check
uv run yamllint .           # yaml lint
uv run pip-audit            # vulnerability scan
```

### Workflow

- Use TDD: write failing tests first, then implement.
- Run all checks before submitting changes.
- The test suite calls `evaluate_command()` directly — no subprocess or stdin mocking needed for most tests. The `TestMain` class tests the stdin/stdout JSON wrapper.

## Code conventions

- Python 3.14+, stdlib only for runtime code.
- Ruff with `select = ["ALL"]` — see `pyproject.toml` for ignored rules.
- No comments unless the "why" is non-obvious.
- No docstrings on internal functions.

## Security model

- **Positive-list only**: commands must be explicitly listed as read-only to be auto-allowed.
- **Fail closed**: any parse error, unknown command, or unrecognized flag results in `"ask"` (prompts the user).
- `gh api` body flags (`-f`, `-F`, `--field`, `--raw-field`, `--input`) always trigger `"ask"`, even with `-X GET`.
- `gh api graphql` always triggers `"ask"` (GraphQL uses POST and can contain mutations).
