# agentic-ai-gh-guard

[![CI](https://github.com/hbelmiro/agentic-ai-gh-guard/actions/workflows/ci.yml/badge.svg)](https://github.com/hbelmiro/agentic-ai-gh-guard/actions/workflows/ci.yml)

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) and Codex hook that auto-allows recognized read-only `gh` CLI commands. Claude Code prompts for every other `gh` command; Codex defers other approval requests to its normal flow.

## The problem

When using AI coding agents, `gh` is frequently used to review PRs, check CI, and read issues. But `gh` can also create PRs, merge branches, delete repos, and more. You can't just allowlist `gh` broadly without risking unintended writes.

## How it works

This hook uses a **positive-list** approach:

- **Read-only commands** (e.g. `gh pr view`, `gh issue list`, `gh api repos/.../pulls`) are **auto-allowed** -- no permission prompt
- **Everything else** (e.g. `gh pr create`, `gh repo delete`, `gh api -X POST`) triggers the **normal permission prompt** so you can approve or deny case-by-case
- **Fail closed** -- unknown commands, parse errors, and unrecognized flags all prompt for permission

```
gh pr list          --> auto-allowed
gh pr view 123      --> auto-allowed
gh api repos/x/pulls --> auto-allowed
gh pr create --fill --> prompts you
gh api -X POST ...  --> prompts you
gh repo delete x    --> prompts you
```

## Installation

### 1. Clone the repository

```sh
git clone https://github.com/hbelmiro/agentic-ai-gh-guard.git
```

### 2. Configure Claude Code

Add the hook to your Claude Code settings:

- **Global** (all projects): `~/.claude/settings.json`
- **Project-level** (single repo): `.claude/settings.json`

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "if": "Bash(gh *)",
            "command": "python3 /path/to/agentic-ai-gh-guard/src/gh_guard.py --log-level info"
          }
        ]
      }
    ]
  }
}
```

Replace `/path/to/agentic-ai-gh-guard` with the absolute path where you cloned the repository.

### 3. Configure Codex

Copy [`codex-hooks.json.example`](codex-hooks.json.example) to one of Codex's hook locations:

- **Global** (all projects): `~/.codex/hooks.json`
- **Project-level** (single repo): `.codex/hooks.json`

Replace `/absolute/path/to/src/gh_guard.py` with the script's absolute path. Codex runs the hook for Bash approval requests. It auto-allows an approval only when every command in the request is a recognized read-only `gh` command. For every other request, it makes no decision and Codex shows its normal approval prompt.

Codex requires review and trust for non-managed hooks. Run `/hooks` in Codex to review and trust the configured hook.

### 4. That's it

No dependencies to install -- the hook uses only Python standard library.

## Read-only commands

The following commands are auto-allowed:

| Command          | Subcommands                                          |
|------------------|------------------------------------------------------|
| `gh pr`          | `view`, `list`, `status`, `checks`, `diff`           |
| `gh issue`       | `view`, `list`, `status`                             |
| `gh repo`        | `view`, `list`, `gitignore`, `license`               |
| `gh run`         | `view`, `list`, `watch`                              |
| `gh release`     | `view`, `list`                                       |
| `gh gist`        | `view`, `list`                                       |
| `gh workflow`    | `view`, `list`                                       |
| `gh cache`       | `list`                                               |
| `gh search`      | all subcommands                                      |
| `gh label`       | `list`                                               |
| `gh ruleset`     | `view`, `list`, `check`                              |
| `gh secret`      | `list`                                               |
| `gh variable`    | `list`, `get`                                        |
| `gh ssh-key`     | `list`                                               |
| `gh gpg-key`     | `list`                                               |
| `gh codespace`   | `list`, `view`, `logs`, `ports`                      |
| `gh project`     | `view`, `list`, `field-list`, `item-list`            |
| `gh org`         | `list`                                               |
| `gh attestation` | `verify`, `verify-asset`, `download`, `trusted-root` |
| `gh status`      | *(top-level, no subcommand)*                         |

### `gh api`

`gh api` is allowed only when it's a plain GET request:

- No `-X POST/PUT/PATCH/DELETE` or `--method POST/PUT/PATCH/DELETE`
- No body flags (`-f`, `-F`, `--field`, `--raw-field`, `--input`)
- Endpoint is not `graphql` (GraphQL uses POST and can contain mutations)

### Compound commands

For compound commands (`&&`, `||`, `;`, `|`), each part is evaluated independently. If **any** part is not read-only, the entire command prompts for permission.

Commands containing command substitution (`$(...)` or backticks) always prompt for permission.

## How hooks work

This is a Claude Code [PreToolUse hook](https://code.claude.com/docs/en/hooks). When Claude tries to run a Bash command matching `gh *`:

1. The hook receives the command as JSON on stdin
2. It evaluates whether the command is read-only
3. It outputs a JSON decision using the [`hookSpecificOutput` format](https://code.claude.com/docs/en/hooks)
4. Claude Code either auto-allows or shows the normal permission prompt

The hook only runs when **Claude** uses `gh` -- it does not affect commands you run directly in your terminal.

In Codex, the hook runs only when Codex is about to show a Bash approval prompt. It does not make commands prompt that Codex would otherwise run without approval.

## Logging

The hook logs decisions to `~/.agentic-ai-gh-guard/logs/gh_guard.log` using a rotating file handler (1 MB max, 3 backups).

The `--log-level` flag is required and accepts: `debug`, `info`, `warning`, `error`, `critical`.

| Level      | What it logs                                          |
|------------|-------------------------------------------------------|
| `debug`    | Token parsing, subcommand matching, and all decisions |
| `info`     | Final allow/ask decision for each command             |
| `warning`  | Input parsing failures                                |
| `error`    | Errors                                                |
| `critical` | Critical failures                                     |

Example:

```json
"command": "python3 /path/to/agentic-ai-gh-guard/src/gh_guard.py --log-level debug"
```

## Development

### Setup

```sh
uv sync --group dev --group ci
```

### Running checks

```sh
uv run pytest -v            # tests
uv run ruff check           # lint
uv run ruff format --check  # format
uv run ty check             # type check
uv run yamllint .           # yaml lint
uv run pip-audit            # vulnerability scan
```

## License

[Apache License 2.0](LICENSE)

## Sponsor

If you find this useful, consider [sponsoring](https://github.com/sponsors/hbelmiro).
