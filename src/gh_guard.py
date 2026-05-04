from __future__ import annotations

import argparse
import contextlib
import json
import logging
import re
import shlex
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

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

_logger = logging.getLogger("gh_guard")


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
    _logger.debug(
        "api args: endpoint=%s method=%s has_body_flag=%s",
        endpoint,
        method,
        has_body_flag,
    )

    if endpoint is None or endpoint.lower() == "graphql":
        return False

    if has_body_flag:
        return False

    return method is None or method not in WRITE_METHODS


def _evaluate_single(command: str) -> str:
    try:
        tokens = shlex.split(command)
    except ValueError:
        _logger.debug("shlex parse error for command")
        return ASK

    if not tokens or tokens[0] != "gh":
        _logger.debug("not a gh command")
        return ALLOW

    if len(tokens) < 2:
        _logger.debug("gh with no subcommand")
        return ASK

    cmd = tokens[1]
    subcmd = tokens[2] if len(tokens) >= 3 else None
    _logger.debug("evaluating subcommand: %s %s", cmd, subcmd or "")

    if cmd in TOP_LEVEL_READONLY:
        _logger.debug("matched TOP_LEVEL_READONLY: %s", cmd)
        return ALLOW

    if cmd in ALLOW_ALL_SUBCOMMANDS and subcmd is not None:
        _logger.debug("matched ALLOW_ALL_SUBCOMMANDS: %s", cmd)
        return ALLOW

    if cmd == "api":
        result = ALLOW if _is_api_readonly(tokens) else ASK
        _logger.debug("api evaluation: %s", result)
        return result

    if cmd in READONLY_SUBCOMMANDS and subcmd in READONLY_SUBCOMMANDS[cmd]:
        _logger.debug("matched READONLY_SUBCOMMANDS: %s %s", cmd, subcmd)
        return ALLOW

    _logger.debug("no match, returning ask for: %s", cmd)
    return ASK


def evaluate_command(command: str) -> str:
    parts = _COMPOUND_SPLIT.split(command)
    _logger.debug("compound parts: %d", len(parts))
    for part in parts:
        stripped = part.strip()
        if not stripped:
            continue
        if _evaluate_single(stripped) == ASK:
            return ASK
    return ALLOW


def setup_logging(level: str, log_dir: Path | None = None) -> None:
    if log_dir is None:
        log_dir = Path.home() / ".agentic-ai-gh-guard" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("gh_guard")
    if logger.handlers:
        return

    logger.setLevel(level.upper())
    logger.propagate = False

    handler = RotatingFileHandler(
        log_dir / "gh_guard.log",
        maxBytes=1_048_576,
        backupCount=3,
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--log-level",
        choices=("debug", "info", "warning", "error", "critical"),
        required=True,
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    with contextlib.suppress(OSError, ValueError):
        setup_logging(args.log_level)

    try:
        data = json.loads(sys.stdin.read())
        command = data.get("tool_input", {}).get("command", "")
        decision = evaluate_command(command)
        _logger.info("decision: %s", decision)
    except (json.JSONDecodeError, KeyError, TypeError):
        _logger.warning("failed to parse input")
        decision = ASK

    json.dump({"permissionDecision": decision}, sys.stdout)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
