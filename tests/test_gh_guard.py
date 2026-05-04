import io
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from unittest.mock import patch

import pytest

from gh_guard import evaluate_command, main, parse_args, setup_logging


class TestReadOnlyCommands:
    """Read-only gh commands should return 'allow'."""

    @pytest.mark.parametrize(
        "command",
        [
            "gh pr view 123",
            "gh pr list",
            "gh pr list --state open",
            "gh pr status",
            "gh pr checks 123",
            "gh pr diff 123",
            "gh pr view 123 -R owner/repo",
            "gh pr view 123 --repo owner/repo",
        ],
    )
    def test_pr_read_commands(self, command: str) -> None:
        assert evaluate_command(command) == "allow"

    @pytest.mark.parametrize(
        "command",
        [
            "gh issue list",
            "gh issue view 456",
            "gh issue status",
            "gh issue list --label bug",
        ],
    )
    def test_issue_read_commands(self, command: str) -> None:
        assert evaluate_command(command) == "allow"

    @pytest.mark.parametrize(
        "command",
        [
            "gh repo view",
            "gh repo list",
            "gh repo view owner/repo",
            "gh repo gitignore list",
            "gh repo license list",
        ],
    )
    def test_repo_read_commands(self, command: str) -> None:
        assert evaluate_command(command) == "allow"

    @pytest.mark.parametrize(
        "command",
        [
            "gh run view 789",
            "gh run list",
            "gh run watch 789",
        ],
    )
    def test_run_read_commands(self, command: str) -> None:
        assert evaluate_command(command) == "allow"

    @pytest.mark.parametrize(
        "command",
        [
            "gh release view v1.0",
            "gh release list",
            "gh gist view abc123",
            "gh gist list",
            "gh workflow view ci.yml",
            "gh workflow list",
            "gh cache list",
        ],
    )
    def test_misc_read_commands(self, command: str) -> None:
        assert evaluate_command(command) == "allow"

    @pytest.mark.parametrize(
        "command",
        [
            "gh search repos python",
            "gh search issues bug",
            'gh search issues "bug report"',
            "gh search prs fix",
            "gh search commits fix",
            "gh search code TODO",
        ],
    )
    def test_search_commands(self, command: str) -> None:
        assert evaluate_command(command) == "allow"

    @pytest.mark.parametrize(
        "command",
        [
            "gh label list",
            "gh ruleset view 1",
            "gh ruleset list",
            "gh ruleset check main",
            "gh secret list",
            "gh variable list",
            "gh variable get MY_VAR",
            "gh ssh-key list",
            "gh gpg-key list",
        ],
    )
    def test_admin_read_commands(self, command: str) -> None:
        assert evaluate_command(command) == "allow"

    @pytest.mark.parametrize(
        "command",
        [
            "gh codespace list",
            "gh codespace view",
            "gh codespace logs",
            "gh codespace ports",
        ],
    )
    def test_codespace_read_commands(self, command: str) -> None:
        assert evaluate_command(command) == "allow"

    @pytest.mark.parametrize(
        "command",
        [
            "gh project view 1",
            "gh project list",
            "gh project field-list 1",
            "gh project item-list 1",
        ],
    )
    def test_project_read_commands(self, command: str) -> None:
        assert evaluate_command(command) == "allow"

    @pytest.mark.parametrize(
        "command",
        [
            "gh org list",
            "gh attestation verify artifact.tar.gz",
            "gh attestation verify-asset asset.zip",
            "gh attestation download artifact.tar.gz",
            "gh attestation trusted-root",
        ],
    )
    def test_org_and_attestation_commands(self, command: str) -> None:
        assert evaluate_command(command) == "allow"

    def test_status_top_level(self) -> None:
        assert evaluate_command("gh status") == "allow"

    def test_status_with_flags(self) -> None:
        assert evaluate_command("gh status -o cli") == "allow"


class TestGhApiReadOnly:
    """gh api commands that are read-only GET requests should return 'allow'."""

    @pytest.mark.parametrize(
        "command",
        [
            "gh api repos/{owner}/{repo}/pulls",
            "gh api repos/cli/cli/issues",
            "gh api -X GET repos/{owner}/{repo}/issues",
            "gh api --method GET repos/{owner}/{repo}/issues",
            "gh api repos/{owner}/{repo}/pulls --paginate",
            "gh api repos/{owner}/{repo}/pulls -q '.[].title'",
            "gh api repos/{owner}/{repo}/pulls --jq '.[].title'",
            "gh api repos/{owner}/{repo}/issues -H 'Accept: application/json'",
            "gh api repos/{owner}/{repo}/releases --cache 3600s",
            "gh api repos/{owner}/{repo}/pulls -t '{{.title}}'",
            "gh api repos/{owner}/{repo}/pulls --template '{{.title}}'",
            "gh api repos/{owner}/{repo}/pulls -i",
            "gh api repos/{owner}/{repo}/pulls --include",
        ],
    )
    def test_api_get_requests(self, command: str) -> None:
        assert evaluate_command(command) == "allow"

    def test_api_get_with_jq_and_redirect(self) -> None:
        cmd = (
            "gh api repos/kubeflow/pipelines/git/trees/master"
            " --jq '.tree[].path' 2>/dev/null"
        )
        assert evaluate_command(cmd) == "allow"


class TestWriteCommands:
    """Write gh commands should return 'ask'."""

    @pytest.mark.parametrize(
        "command",
        [
            "gh pr create --fill",
            "gh pr merge 123",
            "gh pr close 123",
            "gh pr comment 123 --body hello",
            "gh pr edit 123 --title new",
            "gh pr review 123 --approve",
            "gh pr ready 123",
            "gh pr reopen 123",
            "gh pr checkout 123",
            "gh pr lock 123",
            "gh pr unlock 123",
            "gh pr revert 123",
            "gh pr update-branch 123",
        ],
    )
    def test_pr_write_commands(self, command: str) -> None:
        assert evaluate_command(command) == "ask"

    @pytest.mark.parametrize(
        "command",
        [
            'gh issue create --title "bug"',
            "gh issue edit 123",
            "gh issue close 123",
            "gh issue delete 123",
            "gh issue comment 123 --body hello",
            "gh issue reopen 123",
            "gh issue lock 123",
            "gh issue unlock 123",
            "gh issue pin 123",
            "gh issue unpin 123",
            "gh issue transfer 123 other/repo",
            "gh issue develop 123",
        ],
    )
    def test_issue_write_commands(self, command: str) -> None:
        assert evaluate_command(command) == "ask"

    @pytest.mark.parametrize(
        "command",
        [
            "gh repo create myrepo",
            "gh repo delete owner/repo",
            "gh repo edit --description new",
            "gh repo clone cli/cli",
            "gh repo fork cli/cli",
            "gh repo archive owner/repo",
            "gh repo unarchive owner/repo",
            "gh repo rename newname",
            "gh repo sync",
        ],
    )
    def test_repo_write_commands(self, command: str) -> None:
        assert evaluate_command(command) == "ask"

    @pytest.mark.parametrize(
        "command",
        [
            "gh run cancel 123",
            "gh run delete 123",
            "gh run download 123",
            "gh run rerun 123",
        ],
    )
    def test_run_write_commands(self, command: str) -> None:
        assert evaluate_command(command) == "ask"

    @pytest.mark.parametrize(
        "command",
        [
            "gh release create v1.0",
            "gh release delete v1.0",
            "gh release edit v1.0",
            "gh release upload v1.0 file.tar.gz",
            "gh gist create file.txt",
            "gh gist delete abc123",
            "gh gist edit abc123",
            "gh workflow run ci.yml",
            "gh workflow disable ci.yml",
            "gh workflow enable ci.yml",
            "gh cache delete abc",
            "gh label create bug",
            "gh label delete bug",
            "gh label edit bug",
            "gh secret set MY_SECRET",
            "gh secret delete MY_SECRET",
            "gh variable set MY_VAR",
            "gh variable delete MY_VAR",
            "gh ssh-key add key.pub",
            "gh ssh-key delete 123",
            "gh gpg-key add key.pub",
            "gh gpg-key delete 123",
        ],
    )
    def test_misc_write_commands(self, command: str) -> None:
        assert evaluate_command(command) == "ask"


class TestGhApiWrite:
    """gh api commands that write should return 'ask'."""

    @pytest.mark.parametrize(
        "command",
        [
            "gh api -X POST repos/{owner}/{repo}/issues -f title=bug",
            "gh api --method POST repos/{owner}/{repo}/issues",
            "gh api -X PUT repos/{owner}/{repo}/issues/1",
            "gh api -X PATCH repos/{owner}/{repo}/issues/1",
            "gh api -X DELETE repos/{owner}/{repo}/issues/1",
            "gh api --method DELETE repos/{owner}/{repo}/issues/1",
            "gh api -f body=hello repos/{owner}/{repo}/issues/1/comments",
            "gh api -F field=value some/endpoint",
            "gh api --field key=value some/endpoint",
            "gh api --raw-field key=value some/endpoint",
            "gh api --input body.json some/endpoint",
            "gh api graphql -f query='{ viewer { login } }'",
            "gh api -X GET -f body=hello repos/{owner}/{repo}/issues/1/comments",
            "gh api graphql",
        ],
    )
    def test_api_write_requests(self, command: str) -> None:
        assert evaluate_command(command) == "ask"

    def test_api_no_endpoint(self) -> None:
        assert evaluate_command("gh api") == "ask"


class TestNonGhCommands:
    """Non-gh commands should return 'allow' (not our concern)."""

    @pytest.mark.parametrize(
        "command",
        [
            "ls -la",
            "git status",
            "echo hello",
            "cat file.txt",
            "grep -r TODO .",
        ],
    )
    def test_non_gh_commands(self, command: str) -> None:
        assert evaluate_command(command) == "allow"


class TestEdgeCases:
    """Edge cases should fail closed (return 'ask')."""

    def test_empty_command(self) -> None:
        assert evaluate_command("") == "allow"

    def test_only_gh(self) -> None:
        assert evaluate_command("gh") == "ask"

    def test_gh_unknown_command(self) -> None:
        assert evaluate_command("gh unknown-command") == "ask"

    def test_compound_all_read(self) -> None:
        assert evaluate_command("gh pr list && gh issue list") == "allow"

    def test_compound_with_write(self) -> None:
        assert evaluate_command("gh pr list && gh pr create --fill") == "ask"

    def test_piped_with_write(self) -> None:
        assert evaluate_command("gh api repos/foo/bar | gh issue create") == "ask"

    def test_semicolon_with_write(self) -> None:
        assert evaluate_command("gh pr list ; gh pr merge 123") == "ask"

    def test_or_with_write(self) -> None:
        assert evaluate_command("gh pr list || gh pr close 123") == "ask"

    def test_piped_all_read(self) -> None:
        assert evaluate_command("gh pr list | grep open") == "allow"

    def test_compound_non_gh_and_read(self) -> None:
        assert evaluate_command("echo hello && gh pr list") == "allow"

    def test_search_no_subcommand(self) -> None:
        assert evaluate_command("gh search") == "ask"

    def test_api_method_lowercase(self) -> None:
        assert evaluate_command("gh api --method get repos/foo/bar") == "allow"

    def test_api_method_delete_lowercase(self) -> None:
        assert evaluate_command("gh api -X delete repos/foo/bar") == "ask"


class TestUnlistedCommandsAsk:
    """Commands not in the positive list should return 'ask' (fail closed)."""

    @pytest.mark.parametrize(
        "command",
        [
            "gh auth login",
            "gh auth status",
            "gh auth logout",
            "gh config list",
            "gh config set editor vim",
            "gh extension install owner/repo",
            "gh extension remove ext",
            "gh alias set co 'pr checkout'",
            "gh alias delete co",
            "gh browse",
            "gh browse --repo owner/repo",
            "gh copilot suggest",
            "gh co 123",
        ],
    )
    def test_unlisted_commands_ask(self, command: str) -> None:
        assert evaluate_command(command) == "ask"


class TestGhApiReadOnlyFlags:
    """gh api read-only flags should not block the request."""

    @pytest.mark.parametrize(
        "command",
        [
            "gh api repos/foo/bar --verbose",
            "gh api repos/foo/bar --silent",
            "gh api repos/foo/bar --hostname github.example.com",
            "gh api repos/foo/bar --preview nebula",
            "gh api repos/foo/bar --paginate --slurp",
        ],
    )
    def test_api_readonly_flags_allow(self, command: str) -> None:
        assert evaluate_command(command) == "allow"


class TestApiArgParserEdgeCases:
    """Edge cases in gh api argument parsing."""

    def test_api_endpoint_looks_like_flag(self) -> None:
        assert evaluate_command("gh api /repos/-f/bar") == "allow"

    def test_api_multiple_headers(self) -> None:
        assert (
            evaluate_command(
                "gh api repos/foo/bar -H 'Accept: json' -H 'X-Custom: val'"
            )
            == "allow"
        )

    def test_api_get_explicit_with_multiple_readonly_flags(self) -> None:
        assert (
            evaluate_command(
                "gh api -X GET repos/foo/bar --paginate -q '.[].title' --cache 60s"
            )
            == "allow"
        )

    def test_api_short_preview_flag_with_value(self) -> None:
        assert evaluate_command("gh api -p nebula repos/foo/bar") == "allow"

    def test_api_short_preview_flag_before_endpoint(self) -> None:
        assert evaluate_command("gh api -p corsair,nebula repos/foo/bar") == "allow"

    def test_api_short_preview_with_graphql_endpoint(self) -> None:
        assert evaluate_command("gh api -p nebula graphql") == "ask"


class TestShellEdgeCases:
    """Shell parsing edge cases."""

    def test_quoted_args(self) -> None:
        assert evaluate_command("gh pr list --search 'is:open author:me'") == "allow"

    def test_single_quotes_in_double_quotes(self) -> None:
        assert evaluate_command('gh issue list --label "won\'t fix"') == "allow"

    def test_command_substitution_in_arg(self) -> None:
        assert evaluate_command("gh pr list --limit $(echo 10)") == "allow"

    def test_backtick_substitution(self) -> None:
        assert evaluate_command("gh pr list --limit `echo 10`") == "allow"

    def test_long_command(self) -> None:
        long_flags = " ".join(f"--label label{i}" for i in range(100))
        assert evaluate_command(f"gh issue list {long_flags}") == "allow"


class TestCompoundSplitQuoting:
    """Compound operators inside quotes should not split the command."""

    @pytest.mark.parametrize(
        "command",
        [
            "gh api repos/foo/bar --jq '.items[]|.name'",
            "gh api repos/foo/bar --jq '.|keys'",
            "gh api repos/foo/bar --jq '.[]|select(.state)|.title'",
            'gh api repos/foo/bar --jq ".items[]|.name"',
            "gh api repos/foo/bar --jq '.x&&.y'",
            "gh api repos/foo/bar --jq '.a||.b'",
            "gh api repos/foo/bar --jq '.a;.b'",
        ],
    )
    def test_quoted_operators_in_jq(self, command: str) -> None:
        assert evaluate_command(command) == "allow"

    def test_quoted_pipe_with_real_pipe(self) -> None:
        assert (
            evaluate_command("gh api repos/foo/bar --jq '.items[]|.name' | cat")
            == "allow"
        )

    def test_quoted_pipe_with_real_compound(self) -> None:
        assert (
            evaluate_command("gh api repos/foo/bar --jq '.items[]|.name' && gh pr list")
            == "allow"
        )

    def test_quoted_pipe_with_write_after_real_compound(self) -> None:
        assert (
            evaluate_command(
                "gh api repos/foo/bar --jq '.items[]|.name' && gh pr create --fill"
            )
            == "ask"
        )

    def test_unmatched_quote_fails_closed(self) -> None:
        assert evaluate_command("gh api repos/foo/bar --jq '.items[]") == "ask"

    def test_shell_redirect_with_jq(self) -> None:
        assert (
            evaluate_command("gh api repos/foo/bar --jq '.items[]|.name' 2>/dev/null")
            == "allow"
        )


class TestMain:
    """Test the main() stdin/stdout JSON wrapper."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path: Path) -> None:
        self._tmp_path = tmp_path
        logger = logging.getLogger("gh_guard")
        for h in logger.handlers:
            h.close()
        logger.handlers.clear()
        logger.setLevel(logging.WARNING)

    def _run_main(self, input_data: dict) -> dict:
        stdin = io.StringIO(json.dumps(input_data))
        stdout = io.StringIO()
        with (
            patch("sys.stdin", stdin),
            patch("sys.stdout", stdout),
            patch("sys.argv", ["gh_guard.py", "--log-level", "warning"]),
            patch("gh_guard.Path.home", return_value=self._tmp_path),
        ):
            main()
        return json.loads(stdout.getvalue())

    @staticmethod
    def _hook_response(decision: str) -> dict:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": decision,
            }
        }

    def test_main_allow(self) -> None:
        result = self._run_main({"tool_input": {"command": "gh pr list"}})
        assert result == self._hook_response("allow")

    def test_main_ask(self) -> None:
        result = self._run_main({"tool_input": {"command": "gh pr create --fill"}})
        assert result == self._hook_response("ask")

    def test_main_invalid_json(self) -> None:
        stdin = io.StringIO("not json")
        stdout = io.StringIO()
        with (
            patch("sys.stdin", stdin),
            patch("sys.stdout", stdout),
            patch("sys.argv", ["gh_guard.py", "--log-level", "warning"]),
            patch("gh_guard.Path.home", return_value=self._tmp_path),
        ):
            main()
        result = json.loads(stdout.getvalue())
        assert result == self._hook_response("ask")

    def test_main_missing_tool_input(self) -> None:
        result = self._run_main({})
        assert result == self._hook_response("allow")

    def test_main_missing_command(self) -> None:
        result = self._run_main({"tool_input": {}})
        assert result == self._hook_response("allow")

    def test_main_no_log_on_stdout(self) -> None:
        stdin = io.StringIO(json.dumps({"tool_input": {"command": "gh pr list"}}))
        stdout = io.StringIO()
        with (
            patch("sys.stdin", stdin),
            patch("sys.stdout", stdout),
            patch("sys.argv", ["gh_guard.py", "--log-level", "debug"]),
            patch("gh_guard.Path.home", return_value=self._tmp_path),
        ):
            main()
        lines = stdout.getvalue().strip().split("\n")
        assert len(lines) == 1
        assert json.loads(lines[0]) == self._hook_response("allow")


class TestParseArgs:
    @pytest.mark.parametrize(
        ("flag", "expected"),
        [
            ("debug", "debug"),
            ("info", "info"),
            ("warning", "warning"),
            ("error", "error"),
            ("critical", "critical"),
        ],
    )
    def test_valid_levels(self, flag: str, expected: str) -> None:
        args = parse_args(["--log-level", flag])
        assert args.log_level == expected

    def test_missing_log_level_raises(self) -> None:
        with pytest.raises(SystemExit):
            parse_args([])

    def test_invalid_level_raises(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(["--log-level", "trace"])

    def test_defaults_to_sys_argv(self) -> None:
        with patch("sys.argv", ["gh_guard.py", "--log-level", "info"]):
            args = parse_args()
        assert args.log_level == "info"


class TestSetupLogging:
    @pytest.fixture(autouse=True)
    def _clean_logger(self) -> None:
        logger = logging.getLogger("gh_guard")
        for h in logger.handlers:
            h.close()
        logger.handlers.clear()
        logger.setLevel(logging.WARNING)

    def test_creates_directory(self, tmp_path: Path) -> None:
        log_dir = tmp_path / "logs"
        setup_logging("info", log_dir=log_dir)
        assert log_dir.is_dir()

    def test_creates_log_file(self, tmp_path: Path) -> None:
        log_dir = tmp_path / "logs"
        setup_logging("debug", log_dir=log_dir)
        logger = logging.getLogger("gh_guard")
        logger.debug("test message")
        assert (log_dir / "gh_guard.log").exists()

    @pytest.mark.parametrize(
        ("level_str", "level_const"),
        [
            ("debug", logging.DEBUG),
            ("info", logging.INFO),
            ("warning", logging.WARNING),
            ("error", logging.ERROR),
            ("critical", logging.CRITICAL),
        ],
    )
    def test_sets_level(self, tmp_path: Path, level_str: str, level_const: int) -> None:
        setup_logging(level_str, log_dir=tmp_path)
        logger = logging.getLogger("gh_guard")
        assert logger.level == level_const

    def test_uses_rotating_handler(self, tmp_path: Path) -> None:
        setup_logging("info", log_dir=tmp_path)
        logger = logging.getLogger("gh_guard")
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], RotatingFileHandler)

    def test_handler_max_bytes(self, tmp_path: Path) -> None:
        setup_logging("info", log_dir=tmp_path)
        handler = logging.getLogger("gh_guard").handlers[0]
        assert isinstance(handler, RotatingFileHandler)
        assert handler.maxBytes == 1_048_576

    def test_handler_backup_count(self, tmp_path: Path) -> None:
        setup_logging("info", log_dir=tmp_path)
        handler = logging.getLogger("gh_guard").handlers[0]
        assert isinstance(handler, RotatingFileHandler)
        assert handler.backupCount == 3

    def test_no_propagation(self, tmp_path: Path) -> None:
        setup_logging("info", log_dir=tmp_path)
        logger = logging.getLogger("gh_guard")
        assert logger.propagate is False

    def test_does_not_write_to_stdout(self, tmp_path: Path) -> None:
        stdout = io.StringIO()
        setup_logging("debug", log_dir=tmp_path)
        logger = logging.getLogger("gh_guard")
        with patch("sys.stdout", stdout):
            logger.debug("should not appear on stdout")
        assert stdout.getvalue() == ""

    def test_idempotent(self, tmp_path: Path) -> None:
        setup_logging("info", log_dir=tmp_path)
        setup_logging("debug", log_dir=tmp_path)
        logger = logging.getLogger("gh_guard")
        assert len(logger.handlers) == 1

    def test_default_log_dir(self, tmp_path: Path) -> None:
        with patch("gh_guard.Path.home", return_value=tmp_path):
            setup_logging("info")
        handler = logging.getLogger("gh_guard").handlers[0]
        assert isinstance(handler, RotatingFileHandler)
        expected = str(tmp_path / ".agentic-ai-gh-guard" / "logs" / "gh_guard.log")
        assert handler.baseFilename == expected

    def test_invalid_level_raises_value_error(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="INVALID"):
            setup_logging("invalid", log_dir=tmp_path)


class TestLogOutput:
    @pytest.fixture(autouse=True)
    def _setup_logging(self, tmp_path: Path) -> None:
        logger = logging.getLogger("gh_guard")
        for h in logger.handlers:
            h.close()
        logger.handlers.clear()
        logger.setLevel(logging.WARNING)
        self._log_dir = tmp_path / "logs"
        setup_logging("debug", log_dir=self._log_dir)
        self._log_file = self._log_dir / "gh_guard.log"

    def _log_contents(self) -> str:
        logging.getLogger("gh_guard").handlers[0].flush()
        return self._log_file.read_text()

    def test_evaluate_logs_subcommand(self) -> None:
        evaluate_command("gh pr list")
        logs = self._log_contents()
        assert "pr" in logs
        assert "READONLY_SUBCOMMANDS" in logs

    def test_evaluate_logs_compound_parts(self) -> None:
        evaluate_command("gh pr list && gh issue list")
        logs = self._log_contents()
        assert "compound" in logs.lower()

    def test_evaluate_logs_non_gh(self) -> None:
        evaluate_command("ls -la")
        logs = self._log_contents()
        assert "not a gh command" in logs

    def test_evaluate_logs_api_structure(self) -> None:
        evaluate_command("gh api repos/foo/bar")
        logs = self._log_contents()
        assert "repos/foo/bar" in logs
        assert "has_body_flag" in logs

    def test_main_logs_decision(self, tmp_path: Path) -> None:
        stdin = io.StringIO(json.dumps({"tool_input": {"command": "gh pr list"}}))
        stdout = io.StringIO()
        with (
            patch("sys.stdin", stdin),
            patch("sys.stdout", stdout),
            patch("sys.argv", ["gh_guard.py", "--log-level", "debug"]),
            patch("gh_guard.Path.home", return_value=tmp_path),
        ):
            main()
        logs = self._log_contents()
        assert "allow" in logs

    def test_api_secret_in_header_not_logged(self) -> None:
        evaluate_command(
            "gh api -H 'Authorization: Bearer sk-secret-token' repos/foo/bar"
        )
        logs = self._log_contents()
        assert "sk-secret-token" not in logs
        assert "Authorization" not in logs
        assert "repos/foo/bar" in logs

    def test_secret_set_value_not_logged(self) -> None:
        evaluate_command("gh secret set MY_SECRET --body super-secret-value")
        logs = self._log_contents()
        assert "super-secret-value" not in logs
        assert "secret" in logs

    def test_api_field_value_not_logged(self) -> None:
        evaluate_command("gh api -f token=my-private-token repos/foo/bar")
        logs = self._log_contents()
        assert "my-private-token" not in logs

    def test_main_does_not_log_full_command(self, tmp_path: Path) -> None:
        command = "gh api -H 'Authorization: Bearer leaked' repos/foo/bar"
        stdin = io.StringIO(json.dumps({"tool_input": {"command": command}}))
        stdout = io.StringIO()
        with (
            patch("sys.stdin", stdin),
            patch("sys.stdout", stdout),
            patch("sys.argv", ["gh_guard.py", "--log-level", "debug"]),
            patch("gh_guard.Path.home", return_value=tmp_path),
        ):
            main()
        logs = self._log_contents()
        assert "leaked" not in logs
        assert "allow" in logs

    def test_main_logs_warning_on_parse_failure(self, tmp_path: Path) -> None:
        stdin = io.StringIO("not json")
        stdout = io.StringIO()
        with (
            patch("sys.stdin", stdin),
            patch("sys.stdout", stdout),
            patch("sys.argv", ["gh_guard.py", "--log-level", "debug"]),
            patch("gh_guard.Path.home", return_value=tmp_path),
        ):
            main()
        logs = self._log_contents()
        assert "WARNING" in logs
        assert "failed to parse input" in logs


class TestLoggingResilience:
    @pytest.fixture(autouse=True)
    def _clean_logger(self) -> None:
        logger = logging.getLogger("gh_guard")
        for h in logger.handlers:
            h.close()
        logger.handlers.clear()
        logger.setLevel(logging.WARNING)

    def test_main_works_when_logging_setup_fails(self) -> None:
        stdin = io.StringIO(json.dumps({"tool_input": {"command": "gh pr list"}}))
        stdout = io.StringIO()
        with (
            patch("sys.stdin", stdin),
            patch("sys.stdout", stdout),
            patch("sys.argv", ["gh_guard.py", "--log-level", "info"]),
            patch("gh_guard.setup_logging", side_effect=OSError("disk full")),
        ):
            main()
        result = json.loads(stdout.getvalue())
        assert result == {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
            }
        }

    def test_main_works_when_log_dir_unwritable(self, tmp_path: Path) -> None:
        unwritable = tmp_path / "readonly"
        unwritable.mkdir()
        unwritable.chmod(0o444)
        try:
            stdin = io.StringIO(json.dumps({"tool_input": {"command": "gh pr list"}}))
            stdout = io.StringIO()
            with (
                patch("sys.stdin", stdin),
                patch("sys.stdout", stdout),
                patch("sys.argv", ["gh_guard.py", "--log-level", "info"]),
                patch("gh_guard.Path.home", return_value=unwritable),
            ):
                main()
            result = json.loads(stdout.getvalue())
            assert result == {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                }
            }
        finally:
            unwritable.chmod(0o755)
