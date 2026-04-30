import io
import json
from unittest.mock import patch

import pytest

from gh_guard import evaluate_command, main


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


class TestMain:
    """Test the main() stdin/stdout JSON wrapper."""

    def _run_main(self, input_data: dict) -> dict:
        stdin = io.StringIO(json.dumps(input_data))
        stdout = io.StringIO()
        with patch("sys.stdin", stdin), patch("sys.stdout", stdout):
            main()
        return json.loads(stdout.getvalue())

    def test_main_allow(self) -> None:
        result = self._run_main({"tool_input": {"command": "gh pr list"}})
        assert result == {"permissionDecision": "allow"}

    def test_main_ask(self) -> None:
        result = self._run_main({"tool_input": {"command": "gh pr create --fill"}})
        assert result == {"permissionDecision": "ask"}

    def test_main_invalid_json(self) -> None:
        stdin = io.StringIO("not json")
        stdout = io.StringIO()
        with patch("sys.stdin", stdin), patch("sys.stdout", stdout):
            main()
        result = json.loads(stdout.getvalue())
        assert result == {"permissionDecision": "ask"}

    def test_main_missing_tool_input(self) -> None:
        result = self._run_main({})
        assert result == {"permissionDecision": "allow"}

    def test_main_missing_command(self) -> None:
        result = self._run_main({"tool_input": {}})
        assert result == {"permissionDecision": "allow"}
