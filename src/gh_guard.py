from __future__ import annotations

import json
import re
import shlex
import sys

READONLY_SUBCOMMANDS: dict[str, set[str]] = {
    "pr": {"view", "list", "status", "checks", "diff"},
    "issue": {"view", "list", "status"},
    "repo": {"view", "list", "gitignore", "license"},
    "run": {"view", "list", "watch"},
    "release": {"view", "list"},
    "gist": {"view", "list"},
    "workflow": {"view", "list"},
    "cache": {"list"},
    "label": {"list"},
    "ruleset": {"view", "list", "check"},
    "secret": {"list"},
    "variable": {"list", "get"},
    "ssh-key": {"list"},
    "gpg-key": {"list"},
    "codespace": {"list", "view", "logs", "ports"},
    "project": {"view", "list", "field-list", "item-list"},
    "org": {"list"},
    "attestation": {"verify", "verify-asset", "download", "trusted-root"},
}

ALLOW_ALL_SUBCOMMANDS: set[str] = {"search"}

TOP_LEVEL_READONLY: set[str] = {"status"}

API_BODY_FLAGS: set[str] = {"-f", "-F", "--field", "--raw-field", "--input"}
API_METHOD_FLAGS: set[str] = {"-X", "--method"}
API_STANDALONE_FLAGS: set[str] = {
    "--paginate",
    "--slurp",
    "--silent",
    "--verbose",
    "--include",
    "-i",
}
API_VALUE_FLAGS: set[str] = {
    "-p",
    "-q",
    "--jq",
    "-t",
    "--template",
    "-H",
    "--header",
    "--hostname",
    "--cache",
    "--preview",
}
WRITE_METHODS: set[str] = {"POST", "PUT", "PATCH", "DELETE"}

ALLOW = "allow"
ASK = "ask"

_COMPOUND_SPLIT = re.compile(r"\s*(?:&&|\|\||[;|])\s*")


def _parse_api_args(args: list[str]) -> tuple[str | None, str | None, bool]:
    has_body_flag = False
    method: str | None = None
    endpoint: str | None = None

    i = 0
    while i < len(args):
        tok = args[i]
        if tok in API_BODY_FLAGS:
            has_body_flag = True
            i += 2
        elif tok in API_METHOD_FLAGS:
            if i + 1 < len(args):
                method = args[i + 1].upper()
            i += 2
        elif tok in API_STANDALONE_FLAGS:
            i += 1
        elif tok in API_VALUE_FLAGS:
            i += 2
        elif tok.startswith("-"):
            i += 1
        else:
            if endpoint is None:
                endpoint = tok
            i += 1

    return endpoint, method, has_body_flag


def _is_api_readonly(tokens: list[str]) -> bool:
    endpoint, method, has_body_flag = _parse_api_args(tokens[2:])

    if endpoint is None or endpoint.lower() == "graphql":
        return False

    if has_body_flag:
        return False

    return method is None or method not in WRITE_METHODS


def _evaluate_single(command: str) -> str:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return ASK

    if not tokens or tokens[0] != "gh":
        return ALLOW

    if len(tokens) < 2:
        return ASK

    cmd = tokens[1]

    if cmd in TOP_LEVEL_READONLY:
        return ALLOW

    if cmd in ALLOW_ALL_SUBCOMMANDS and len(tokens) >= 3:
        return ALLOW

    if cmd == "api":
        return ALLOW if _is_api_readonly(tokens) else ASK

    if cmd in READONLY_SUBCOMMANDS:
        subcmd = tokens[2] if len(tokens) >= 3 else None
        if subcmd in READONLY_SUBCOMMANDS[cmd]:
            return ALLOW

    return ASK


def evaluate_command(command: str) -> str:
    parts = _COMPOUND_SPLIT.split(command)
    for part in parts:
        stripped = part.strip()
        if not stripped:
            continue
        if _evaluate_single(stripped) == ASK:
            return ASK
    return ALLOW


def main() -> None:
    try:
        data = json.load(sys.stdin)
        command = data.get("tool_input", {}).get("command", "")
        decision = evaluate_command(command)
    except (json.JSONDecodeError, KeyError, TypeError):
        decision = ASK

    json.dump({"permissionDecision": decision}, sys.stdout)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
